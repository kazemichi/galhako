import os
import sys
import zlib

from renpy.compat.pickle import loads


def rpa_extract(RPA_FILE, OUT_DIR, OFFSET, KEY):
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(RPA_FILE, 'rb') as f:
        f.seek(OFFSET)
        compressed = f.read()
        raw_idx = loads(zlib.decompress(compressed))

        for fname, entries in raw_idx.items():
            print(f'提取 {fname}')
            out_full = os.path.join(OUT_DIR, fname)
            os.makedirs(os.path.dirname(out_full), exist_ok=True)
            buf = b''

            # 遍历每个条目
            for ent in entries:
                # ent 原始存储：(dlen_enc, offset_enc[, start_bytes])
                if len(ent) == 2:
                    dlen_enc, off_enc = ent
                    start_bytes = b''
                elif len(ent) == 3:
                    dlen_enc, off_enc, start_bytes = ent
                else:
                    raise RuntimeError(f'未知条目长度 len={len(ent)} : {ent}')

                offset = off_enc ^ KEY
                dlen = dlen_enc ^ KEY

                f.seek(offset)
                chunk = f.read(dlen)

                buf += start_bytes + chunk

            # 写入文件
            with open(out_full, 'wb') as wf:
                wf.write(buf)

    print('\n✅全部提取完成！输出目录：', os.path.abspath(OUT_DIR))

def main():
    if len(sys.argv) != 2:
        print(f'USAGE：python {sys.argv[0]} <rpa file>')
        sys.exit(1)
    input_file = sys.argv[1]
    if not input_file.endswith('.rpa'):
        print('❌请输入.rpa后缀文件')
        sys.exit(1)

    RPA_FILE = input_file
    OUT_DIR = os.path.splitext(input_file)[0]

    # 先获取 offset 和 key
    with open(RPA_FILE,'rb') as f:
        l = f.read(40)
    OFFSET = int(l[8:24], 16)
    KEY = int(l[25:33], 16)
    rpa_extract(RPA_FILE, OUT_DIR, OFFSET, KEY)

if __name__ == '__main__':
    main()