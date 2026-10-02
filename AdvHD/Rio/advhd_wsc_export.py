import os
import re
import sys


def is_valid_text(s: str) -> bool:
    '''
    判断文本是否需要保留
    :param s: 需要判断的文本字符串
    :return: bool值，表示文本是否需要保留
    '''
    if not s or len(s.strip()) == 0:
        return False

    # 字符正则：汉字、平假名、片假名、全角标点、省略号、直角引号
    pat = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uFF01-\uFF5E\u2026\u300C\u300D]')
    keep = bool(pat.search(s))

    return keep

def export_wsc(inpath: str, outpath: str, encoding: str):
    with open(inpath, 'rb') as f:
        buf = f.read()

    pos = 0
    total = len(buf)
    text_data = []

    # 00 42 [id 4] [name n] 00 [text n] 00
    while pos < total - 2:
        # 匹配块头 00 41 / 00 42
        if buf[pos] == 0x00 and buf[pos+1] in (0x41, 0x42):
            start = pos
            start_mark = buf[pos + 1]

            # 从 start+2 开始找下一个块标记 00 41 / 00 42
            end_pos = None
            scan = start + 2
            while scan < total - 2:
                if buf[scan] == 0x00 and buf[scan + 1] in (0x41, 0x42):
                    end_pos = scan
                    break
                scan += 1
            if end_pos is None:
                end_pos = total

            block_data = buf[start + 2: end_pos]

            # 00 42 [id 4] [name n] 00 [text n] 00
            if start_mark == 0x42:
                if not block_data.startswith((b'LACK', b'G', b'UN')):
                # 去除头 4 字节
                    sub_buf = block_data[4:]
                    parts = sub_buf.split(b'\x00')
                    # 防止分割后元素不足，越界崩溃
                    if len(parts) > 1:
                        raw_name = parts[0]
                        raw_msg = parts[1]

                        name = raw_name.decode(encoding, errors='replace').replace('\ufffd', '')
                        text_data.append({'addr': start + 6, 'text': f'%LC{name}'})
                        message = raw_msg.decode(encoding, errors='replace').replace('\ufffd', '')
                        text_data.append({'addr': start + 6 + len(raw_name) + 1, 'text': f'{message}%K%P'})

            # 00 41 [id 3] [text n] 00
            elif start_mark == 0x41:
                # 去除头 3 字节
                sub_buf = block_data[3:]
                parts = sub_buf.split(b'\x00')
                raw_msg = parts[0]
                message = raw_msg.decode(encoding, errors='replace').replace('\ufffd', '')

                if is_valid_text(message):
                    text_data.append({'addr': start + 5, 'text': f'{message}%K%P'})

            pos = end_pos
        else:
            pos += 1

    pos = 0
    option_magic = b'\x03\x00\x01\x00\x00\x02'
    option_magic_len = len(option_magic)

    # 03 00 01 00 00 02 [noption 2] 
    #   [id 2] [text n] 00 [hash 4] [file n] 00
    while pos+option_magic_len <= total:
        if buf[pos:pos+option_magic_len] == option_magic:
            start = pos + option_magic_len
            noption = int.from_bytes(buf[start:start+2], 'little', signed=False)
            start += 2

            sub_buf = buf[start:]
            for _ in range(noption):
                text_b = sub_buf.split(b'\x00')[_ * 2][2:]
                text = text_b.decode(encoding, errors='replace')
                text_data.append({'addr': start + 2, 'text': f'{text}%K'})
                start += len(text_b) + 1
            pos = start
        else:
            pos += 1

    text_data.sort(key=lambda x: x['addr'])

    # write to lst file
    with open(os.path.join(outpath, os.path.basename(inpath) + '.lst'), 'w', encoding='utf-8') as f:
        f.writelines(f'{text['text']}\n' for text in text_data)

    print(f'完成，共提取 {len(text_data)} 条文本，输出到 {outpath}')

def main():
    if len(sys.argv) < 4:
        print('Usage:')
        print(f' python {sys.argv[0]} <wsc_file> <output_dir> <encoding>')
        print(f' python {sys.argv[0]} <wsc_folder> <output_dir> <encoding>')
        print('Example:')
        print(' python advhd_wsc_export.py 0000.wsc out gbk')
        print(' python advhd_wsc_export.py wsc out gbk')
        sys.exit(1)

    inpath = sys.argv[1]
    outpath = sys.argv[2]
    encoding = sys.argv[3]

    os.makedirs(outpath, exist_ok=True)

    if os.path.isdir(inpath):
        # 文件夹
        for file in os.listdir(inpath):
            if file.endswith('.wsc'):
                export_wsc(os.path.join(inpath, file), outpath, encoding)
    else:
        # 单文件
        if os.path.isfile(inpath) and inpath.endswith('.wsc'):
            export_wsc(inpath, outpath, encoding)

if __name__ == '__main__':
    main()
