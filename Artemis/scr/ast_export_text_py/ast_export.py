import sys
sys.path.append('libs')

import os

import orjson
from luaparser import ast, astnodes


LANGS = ('ja', 'en', 'cn', 'tw')


def _to_text(v):
    '''
    bytes/str/其他 -> str，safe
    '''
    if v is None:
        return ''
    if isinstance(v, bytes):
        return v.decode('utf-8', errors='replace')
    if isinstance(v, str):
        return v
    return str(v)


def _decode_deep(v):
    '''
    递归 decode bytes，方便 orjson 序列化；顺便把 dict key 统一成 str
    '''
    if isinstance(v, bytes):
        return v.decode('utf-8', errors='replace')
    if isinstance(v, list):
        return [_decode_deep(x) for x in v]
    if isinstance(v, dict):
        return {_to_text(k): _decode_deep(val) for k, val in v.items()}
    return v


def lua_ast_to_py(node):
    if isinstance(node, astnodes.String):
        return node.s
    if isinstance(node, astnodes.Number):
        return node.n
    if isinstance(node, astnodes.Table):
        arr, d = [], {}
        for field in node.fields:
            val = lua_ast_to_py(field.value)
            if field.key is None:
                arr.append(val)
            else:
                d[lua_ast_to_py(field.key)] = val
        if not d:
            return arr
        if not arr:
            return d
        for idx, item in enumerate(arr):
            d.setdefault(idx + 1, item)
        return d
    if isinstance(node, astnodes.Name):
        return node.id
    return None


def get_disp_name(lang_item):
    if not isinstance(lang_item, dict):
        return None
    name_raw = lang_item.get('name')
    if not isinstance(name_raw, list) or not name_raw:
        return None
    disp_name = name_raw[1] if len(name_raw) >= 2 else name_raw[0]
    return _to_text(disp_name)


def clean_text_block(lang_item):
    buf = []
    if isinstance(lang_item, dict):
        for k, v in lang_item.items():
            if k == 'name' or isinstance(v, list):
                continue
            if isinstance(v, (bytes, str)):
                buf.append(_to_text(v))
    elif isinstance(lang_item, list):
        for item in lang_item:
            if isinstance(item, (bytes, str)):
                buf.append(_to_text(item))
    return '\n'.join(buf)


def _as_list(v):
    return v if isinstance(v, list) else []


def _extract_root_data(tree):
    root_data = {}
    for stmt in tree.body.body:
        if not isinstance(stmt, astnodes.Assign):
            continue
        if not stmt.values or not stmt.targets:
            continue
        val = lua_ast_to_py(stmt.values[0])
        for var in stmt.targets:
            if isinstance(var, astnodes.Name) and var.id == 'ast' and isinstance(val, dict):
                root_data.update(val)
    return root_data


def _build_text_entries(block_id, block):
    text = block.get('text')
    if not isinstance(text, dict):
        return []

    arrs = {lang: _as_list(text.get(lang)) for lang in LANGS}
    max_len = max((len(a) for a in arrs.values()), default=0)
    block_id_str = _to_text(block_id)

    entries = []
    for i in range(max_len):
        entry = {'id': block_id_str}
        for lang in LANGS:
            item = arrs[lang][i] if i < len(arrs[lang]) else {}
            entry[lang] = {
                'name': get_disp_name(item),
                'text': clean_text_block(item),
            }
        entries.append(entry)
    return entries


def _build_select_entries(block):
    sel = block.get('select')
    if not isinstance(sel, dict):
        return []
    return [{lang: _decode_deep(sel.get(lang, [])) for lang in LANGS}]


def _write_json(path, data) -> None:
    '''
    写入 JSON 文件
    :param path: 文件路径
    :param data: 要写入的数据
    '''
    with open(path, 'wb') as f:
        f.write(orjson.dumps(
            data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS,
        ))


def process_ast(filepath: str):
    base_dir = os.path.dirname(filepath)
    name_no_ext, _ = os.path.splitext(os.path.basename(filepath))
    out_dir = os.path.join(base_dir, name_no_ext)
    os.makedirs(out_dir, exist_ok=True)

    with open(filepath, 'r') as f:
        src = f.read()

    try:
        tree = ast.parse(src)
    except Exception as e:
        print(f'❌ AST parse fail: {filepath} | {e}')
        return

    root_data = _extract_root_data(tree)

    text_list, select_list = [], []
    for block_id, block in root_data.items():
        if not isinstance(block, dict):
            continue
        try:
            text_list.extend(_build_text_entries(block_id, block))
            select_list.extend(_build_select_entries(block))
        except Exception as e:
            print(f'⚠️  block {_to_text(block_id)} 处理失败: {e}')

    if text_list:
        _write_json(os.path.join(out_dir, 'text.json'), text_list)
    if select_list:
        _write_json(os.path.join(out_dir, 'select.json'), select_list)
    print(f'✅ Done: {out_dir} | text={len(text_list)} select={len(select_list)}')


def main():
    if len(sys.argv) < 2:
        print(f'Usage: python {sys.argv[0]} <ast_file | ast_folder>')
        return
    target = sys.argv[1]
    # 处理单个文件
    if os.path.isfile(target) and target.endswith('.ast'):
        process_ast(target)
    # 处理文件夹
    elif os.path.isdir(target):
        for file in os.listdir(target):
            if file.endswith('.ast'):
                process_ast(os.path.join(target, file))


if __name__ == '__main__':
    main()