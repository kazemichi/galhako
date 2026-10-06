import sys
sys.path.append(r'../libs')

import orjson

def main() -> None:
    '''
    导出CP950编码中的双字节有效字符集到JSON文件，按分区组织 (每个引导字节对应一个键)
    '''
    json_data = {}
    # CP950 双字节范围: 0x8140-0xFEFE，按引导字节(lead byte)分区，排除前后造字区
    for lead in range(0xA1, 0xFA):
        valid_chars = []
        # 遍历该引导字节下的所有尾随字节
        for trail in range(0x40, 0xFF):
            try:
                # 替换指定位置为空格（如A17F和A1A0）
                if trail == 0x7F or trail == 0xA0:
                    valid_chars.append(' ')
                else:
                    # 构建双字节编码
                    bytes_pair = bytes([lead, trail])
                    # 尝试解码
                    char = bytes_pair.decode('cp950')
                    valid_chars.append(char)
            except UnicodeDecodeError:
                # 无效字符，跳过
                continue
        # 如果该分区有有效字符，添加到JSON数据
        if valid_chars:
            key = f'n{lead - 0xA0}'  # n1对应0xA1, n2对应0xA2, 依此类推
            json_data[key] = ''.join(valid_chars)

    # dump to json
    with open('cp950_chars_template.json', 'wb') as f:
        f.write(orjson.dumps(json_data, option=orjson.OPT_INDENT_2))

if __name__ == '__main__':
    main()
