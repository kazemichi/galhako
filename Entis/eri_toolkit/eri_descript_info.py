import os
import sys

sys.path.append('./_libs')
import orjson
from eri_meta import extract_descript, get_reference_file


def process_single_eri(filepath: str):
    '''处理单个eri文件，返回字典'''
    basename = os.path.basename(filepath)
    item = {'name': basename}

    res = extract_descript(filepath)
    if res is not None:
        text, _, _ = res
        ref = get_reference_file(text)
        if ref:
            item['reference_file'] = ref
    return item

def scan_path(input_path: str):
    out_list = []
    if os.path.isdir(input_path):
        # 文件夹：遍历所有 *.eri
        for fname in os.listdir(input_path):
            full_path = os.path.join(input_path, fname)
            if os.path.isfile(full_path) and fname.lower().endswith('.eri'):
                out_list.append(process_single_eri(full_path))
    elif os.path.isfile(input_path) and input_path.lower().endswith('.eri'):
        # 单个eri文件
        out_list.append(process_single_eri(input_path))
    return out_list

def main():
    if len(sys.argv) < 2:
        print(f'Usage: python {sys.argv[0]} <eri_file | folder>')
        sys.exit(1)

    target = sys.argv[1]
    data = scan_path(target)

    with open('eri_descript_info.json', 'wb') as f:
        f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

if __name__ == '__main__':
    main()