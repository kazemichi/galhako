import os
import sys
from collections import namedtuple

# ws2 functions
ws2name_t = namedtuple('ws2name_t', ['addr', 'size', 'text'])
ws2option_t = namedtuple('ws2option_t', ['addr', 'size', 'text', 'rawaddr', 'rawsize'])
ws2text_t = namedtuple('ws2text_t', ['addr', 'size', 'text'])

def export_ws2(inpath: str, outpath: str, encoding: str):
    with open(inpath, 'rb') as fp:
        data = bytearray(fp.read())

    # find text to extract
    # should consider about the overlap with name char %LC, and filter this
    names: list[ws2name_t] = []
    cur = 0
    pattern = b'%LC'
    while True:
        cur = data.find(pattern, cur)
        if cur < 0:
            break
        textaddr = cur
        textsize = data.find(b'\x00', textaddr) - textaddr
        text = data[textaddr: textaddr+textsize].decode(encoding)
        if not (cur > 5 and data[cur-5: cur] == b'char\0'):
            names.append(ws2name_t(textaddr, textsize, text))
        cur +=  textsize + 1

    options: list[ws2option_t] = []
    cur = 0 # hard code fix for option 2, 3, 4
    for pattern in [b'\x00\x00\x0f\x02', b'\x00\x00\x0f\x03', b'\x00\x00\x0f\x04', b'\x00\x01\x0f\x02']:
        cur = 0
        while cur < len(data) :
            cur = data.find(pattern, cur)
            if cur < 0: break
            cur += len(pattern)
            noption = pattern[-1]
            if data[cur] == 0 and data[cur+1] == 0:
                continue
            for i in range(noption):
                rawaddr = cur
                textaddr = cur + 2
                textsize = data.find(b'\x00', textaddr) - textaddr
                text = data[textaddr: textaddr+textsize].decode(encoding)
                rawsize = data.find(b'\x00', textaddr+textsize+5)  - rawaddr + 1
                # print('option %d/%d'%(i+1, noption), hex(textaddr), text)
                options.append(ws2option_t(textaddr, textsize, text, rawaddr, rawsize))
                cur += rawsize

    texts: list[ws2text_t] = []
    cur = 0
    pattern = b'char\x00'
    while True:
        cur = data.find(pattern, cur)
        if cur < 0: break
        textaddr = cur + len(pattern)
        textsize = data.find(b'\x00', textaddr) - textaddr
        text = data[textaddr: textaddr+textsize].decode(encoding)
        texts.append(ws2text_t(textaddr, textsize, text))
        cur +=  textsize + 1

    # merge text to ftext
    ftexts = []
    ftexts.extend([{'addr': x.addr, 'size': x.size, 'text': x.text} for x in names]) 
    ftexts.extend([{'addr': x.addr, 'size': x.size, 'text': x.text} for x in options]) 
    ftexts.extend([{'addr': x.addr, 'size': x.size, 'text': x.text} for x in texts]) 
    ftexts.sort(key=lambda x: x['addr'])

    # write to lst file
    with open(os.path.join(outpath, os.path.basename(inpath) + '.lst'), 'w', encoding='utf-8') as f:
        f.writelines(f'{ftext['text']}\n' for ftext in ftexts)


def main():
    if len(sys.argv) < 4:
        print('Usage:')
        print(f' python {sys.argv[0]} <ws2_file> <output_dir> <encoding>')
        print(f' python {sys.argv[0]} <ws2_folder> <output_dir> <encoding>')
        print('Example:')
        print(' python advhd_ws2_export.py 0000.ws2 out sjis')
        print(' python advhd_ws2_export.py ws2 out sjis')
        sys.exit(1)

    inpath = sys.argv[1]
    outpath = sys.argv[2]
    encoding = sys.argv[3]

    os.makedirs(outpath, exist_ok=True)

    if os.path.isdir(inpath):
        # 文件夹
        for file in os.listdir(inpath):
            if file.endswith('.ws2'):
                export_ws2(os.path.join(inpath, file), outpath, encoding)
    else:
        # 单文件
        if os.path.isfile(inpath) and inpath.endswith('.ws2'):
            export_ws2(inpath, outpath, encoding)

if __name__ == '__main__':
    main()
