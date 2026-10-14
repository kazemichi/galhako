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

    text_data = []

    # 纯文本
    # 41 [id 3] [text n] 00
    pos = 0
    text_magic = b'\x00\x41'
    while True:
        pos = buf.find(text_magic, pos)
        #  未找到则退出循环
        if pos == -1:
            break
        pos += len(text_magic)
        # entry_id = int.from_bytes(buf[pos:pos+3], 'little', signed=False)
        addr = pos + 3
        size = buf.find(b'\x00', addr) - addr
        try:
            text = buf[addr: addr+size].decode(encoding)
            if size > 0 and is_valid_text(text):
                text_data.append({'addr': addr, 'text': f'{text}%K%P'})
            cur = addr + size + 1
        except UnicodeDecodeError:
            cur += 1
            continue

    # 带人名对话
    # 00 42 [id 4] [name n] 00 [text n] 00
    pos = 0
    dialog_magic = b'\x00\x42'
    while True:
        pos = buf.find(dialog_magic, pos)
        #  未找到则退出循环
        if pos == -1:
            break
        pos += len(dialog_magic)
        # entry_id = int.from_bytes(buf[pos:pos+3], 'little', signed=False)
        addr = pos + 4
        size = buf.find(b'\x00', addr) - addr
        try:
            text = buf[addr:addr+size].decode(encoding)
            if size > 0 and is_valid_text(text):
                text_data.append({'addr': addr, 'text': f'%LC{text}'})
            cur = addr + size + 1
        except UnicodeDecodeError:
            cur += 1
            continue
        addr = cur
        size = buf.find(b'\x00', addr) - addr
        try: 
            text = buf[addr:addr+size].decode(encoding)
            if size > 0 and is_valid_text(text):
                text_data.append({'addr': addr, 'text': f'{text}%K%P'})
            cur = addr + size + 1
        except UnicodeDecodeError:
            cur += 1
            continue

    # 03 00 01 00 00 02 [noption 2] 
        #   [id 2] [text n] 00 [hash 4] [file n] 00
    pos = 0
    option_magic = b'\x03\x00\x01\x00\x00\x02'
    noption = 0
    while True:
        pos = buf.find(option_magic, pos)
        # 未找到则退出循环
        if pos == -1:
            break
        pos += len(option_magic)
        noption = int.from_bytes(buf[pos:pos+2], 'little', signed=False)
        pos += 2

        for _ in range(noption):
            raw_addr = pos
            addr = raw_addr + 2
            size = buf.find(b'\x00', addr) - addr
            text = buf[addr:addr+size].decode(encoding)
            text_data.append({'addr': raw_addr, 'text': text})
            raw_size = buf.find(b'\x00', addr+size+5) - raw_addr + 1
            pos += raw_size

    text_data.sort(key=lambda x: x['addr'])

    if noption > 0:
        text_data[-noption - 1]['text'] = text_data[-noption - 1]['text'].replace('%K%P', '%K')

    # write to lst file
    with open(os.path.join(outpath, os.path.basename(inpath) + '.lst'), 'w', encoding='utf-8') as f:
        f.writelines(f'{text['text']}\n' for text in text_data)

    print(f'{os.path.basename(inpath)} 完成，共提取 {len(text_data)} 条文本，输出到 {outpath}')

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
