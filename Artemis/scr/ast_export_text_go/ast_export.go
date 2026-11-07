package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"

	lua "github.com/yuin/gopher-lua"
)

var langs = []string{"ja", "en", "cn", "tw"}

// naturalLess：数字前缀按数值比较，其余按字符串比较
func naturalLess(a, b string) bool {
	na, erra := leadingInt(a)
	nb, errb := leadingInt(b)
	if erra == nil && errb == nil && na != nb {
		return na < nb
	}
	return a < b
}

func leadingInt(s string) (int, error) {
	end := 0
	for end < len(s) && s[end] >= '0' && s[end] <= '9' {
		end++
	}
	if end == 0 {
		return 0, fmt.Errorf("no leading digits")
	}
	return strconv.Atoi(s[:end])
}

func luaValueToGo(v lua.LValue) interface{} {
	switch v.Type() {
	case lua.LTString:
		return string(v.(lua.LString))
	case lua.LTNumber:
		return float64(v.(lua.LNumber))
	case lua.LTBool:
		return bool(v.(lua.LBool))
	case lua.LTNil:
		return nil
	case lua.LTTable:
		tb := v.(*lua.LTable)
		// 判断是否为纯数组 (键为 1..n)
		isArray := true
		count := 0
		tb.ForEach(func(key, _ lua.LValue) {
			count++
			if key.Type() != lua.LTNumber || float64(key.(lua.LNumber)) != float64(count) {
				isArray = false
			}
		})
		if isArray && count > 0 {
			arr := make([]interface{}, 0, count)
			for i := 1; i <= count; i++ {
				arr = append(arr, luaValueToGo(tb.RawGetInt(i)))
			}
			return arr
		}
		// 作为字典处理
		d := make(map[string]interface{})
		tb.ForEach(func(key, val lua.LValue) {
			k := fmt.Sprintf("%v", luaValueToGo(key))
			d[k] = luaValueToGo(val)
		})
		return d
	default:
		return nil
	}
}

func toText(v interface{}) string {
	if v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return s
	}
	return fmt.Sprintf("%v", v)
}

func getDispName(langItem interface{}) *string {
	m, ok := langItem.(map[string]interface{})
	if !ok {
		return nil
	}
	nameRaw, ok := m["name"]
	if !ok {
		return nil
	}
	arr, ok := nameRaw.([]interface{})
	if !ok || len(arr) == 0 {
		return nil
	}
	var dispName interface{}
	if len(arr) >= 2 {
		dispName = arr[1]
	} else {
		dispName = arr[0]
	}
	s := toText(dispName)
	return &s
}

func cleanTextBlock(langItem interface{}) string {
	var buf []string
	switch item := langItem.(type) {
	case map[string]interface{}:
		for k, v := range item {
			if k == "name" {
				continue
			}
			if _, isList := v.([]interface{}); isList {
				continue
			}
			if s, ok := v.(string); ok {
				buf = append(buf, s)
			}
		}
	case []interface{}:
		for _, v := range item {
			if s, ok := v.(string); ok {
				buf = append(buf, s)
			}
		}
	}
	return strings.Join(buf, "\n")
}

func asList(v interface{}) []interface{} {
	if arr, ok := v.([]interface{}); ok {
		return arr
	}
	return nil
}

type TextEntry struct {
	ID   string                 `json:"id"`
	Ja   map[string]interface{} `json:"ja"`
	En   map[string]interface{} `json:"en"`
	Cn   map[string]interface{} `json:"cn"`
	Tw   map[string]interface{} `json:"tw"`
}

func buildTextEntries(blockID string, block map[string]interface{}) []TextEntry {
	text, ok := block["text"].(map[string]interface{})
	if !ok {
		return nil
	}
	arrs := make(map[string][]interface{})
	for _, lang := range langs {
		arrs[lang] = asList(text[lang])
	}
	maxLen := 0
	for _, arr := range arrs {
		if len(arr) > maxLen {
			maxLen = len(arr)
		}
	}
	var entries []TextEntry
	for i := 0; i < maxLen; i++ {
		entry := TextEntry{ID: blockID}
		entry.Ja = make(map[string]interface{})
		entry.En = make(map[string]interface{})
		entry.Cn = make(map[string]interface{})
		entry.Tw = make(map[string]interface{})
		for _, lang := range langs {
			var item interface{}
			if i < len(arrs[lang]) {
				item = arrs[lang][i]
			} else {
				item = map[string]interface{}{}
			}
			m := make(map[string]interface{})
			m["name"] = getDispName(item)
			m["text"] = cleanTextBlock(item)
			switch lang {
			case "ja":
				entry.Ja = m
			case "en":
				entry.En = m
			case "cn":
				entry.Cn = m
			case "tw":
				entry.Tw = m
			}
		}
		entries = append(entries, entry)
	}
	return entries
}

type SelectEntry struct {
	Ja interface{} `json:"ja"`
	En interface{} `json:"en"`
	Cn interface{} `json:"cn"`
	Tw interface{} `json:"tw"`
}

func buildSelectEntries(block map[string]interface{}) []SelectEntry {
	sel, ok := block["select"].(map[string]interface{})
	if !ok {
		return nil
	}
	return []SelectEntry{{
		Ja: sel["ja"],
		En: sel["en"],
		Cn: sel["cn"],
		Tw: sel["tw"],
	}}
}

type Result struct {
	File   string
	OutDir string
	Text   int
	Select int
	Err    error
}

func processAst(astPath string) Result {
	baseDir := filepath.Dir(astPath)
	nameNoExt := strings.TrimSuffix(filepath.Base(astPath), ".ast")
	outDir := filepath.Join(baseDir, nameNoExt)
	if err := os.MkdirAll(outDir, 0755); err != nil {
		return Result{File: astPath, Err: err}
	}

	L := lua.NewState()
	defer L.Close()

	if err := L.DoFile(astPath); err != nil {
		return Result{File: astPath, Err: fmt.Errorf("lua execute fail: %w", err)}
	}

	astRaw := L.GetGlobal("ast")
	if astRaw == lua.LNil {
		return Result{File: astPath, Err: fmt.Errorf("global `ast` not found")}
	}

	rootData := luaValueToGo(astRaw)
	rootMap, ok := rootData.(map[string]interface{})
	if !ok {
		return Result{File: astPath, Err: fmt.Errorf("`ast` is %T, not table", rootData)}
	}

	blockIDs := make([]string, 0, len(rootMap))
	for id := range rootMap {
		blockIDs = append(blockIDs, id)
	}
	sort.Slice(blockIDs, func(i, j int) bool {
		return naturalLess(blockIDs[i], blockIDs[j])
	})

	var textList []TextEntry
	var selectList []SelectEntry

	for _, blockID := range blockIDs {
		block, ok := rootMap[blockID].(map[string]interface{})
		if !ok {
			continue
		}
		textList = append(textList, buildTextEntries(blockID, block)...)
		selectList = append(selectList, buildSelectEntries(block)...)
	}

	if len(textList) > 0 {
		data, _ := json.MarshalIndent(textList, "", "  ")
		os.WriteFile(filepath.Join(outDir, "text.json"), data, 0644)
	}
	if len(selectList) > 0 {
		data, _ := json.MarshalIndent(selectList, "", "  ")
		os.WriteFile(filepath.Join(outDir, "select.json"), data, 0644)
	}

	return Result{
		File:   astPath,
		OutDir: outDir,
		Text:   len(textList),
		Select: len(selectList),
	}
}

func main() {
	if len(os.Args) < 2 {
		fmt.Printf("Usage: %s <ast_file | ast_folder>\n", os.Args[0])
		return
	}
	target := os.Args[1]

	// 单文件模式
	if info, err := os.Stat(target); err == nil && !info.IsDir() && strings.HasSuffix(target, ".ast") {
		r := processAst(target)
		if r.Err != nil {
			fmt.Printf("❌ %s | %v\n", r.File, r.Err)
		} else {
			fmt.Printf("✅ Done: %s | text=%d select=%d\n", r.OutDir, r.Text, r.Select)
		}
		return
	}

	// 文件夹模式
	entries, err := os.ReadDir(target)
	if err != nil {
		fmt.Printf("❌ %v\n", err)
		return
	}
	var files []string
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".ast") {
			files = append(files, filepath.Join(target, e.Name()))
		}
	}
	sort.Strings(files)
	if len(files) == 0 {
		fmt.Println("⚠️  没有找到 .ast 文件")
		return
	}

	// goroutine 并发处理，带缓冲 channel 限制并发数
	concurrency := runtime.NumCPU()
	if concurrency < 1 {
		concurrency = 1
	}
	sem := make(chan struct{}, concurrency) // 信号量限制并发
	results := make(chan Result, len(files))
	var wg sync.WaitGroup

	for _, f := range files {
		wg.Add(1)
		go func(path string) {
			defer wg.Done()
			sem <- struct{}{}        // 获取令牌
			defer func() { <-sem }() // 释放令牌
			results <- processAst(path)
		}(f)
	}

	go func() {
		wg.Wait()
		close(results)
	}()

	// 收集结果
	okCount, badCount, totalText, totalSel := 0, 0, 0, 0
	var errs []string
	for r := range results {
		if r.Err != nil {
			badCount++
			errs = append(errs, fmt.Sprintf("  %s | %v", r.File, r.Err))
		} else {
			okCount++
			totalText += r.Text
			totalSel += r.Select
		}
	}

	fmt.Printf("\n✅ 完成 %d/%d | text=%d select=%d\n", okCount, len(files), totalText, totalSel)
	if badCount > 0 {
		fmt.Printf("❌ 失败 %d 个:\n", badCount)
		for _, e := range errs {
			fmt.Println(e)
		}
	}
}