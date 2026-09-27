import os
import sys
import zlib

from renpy.compat.pickle import loads


def rpa_extract(rpa, outdir, offset, key):
    os.makedirs(outdir, exist_ok=True)
    with open(rpa, 'rb') as f:
        f.seek(offset)
        idx = loads(zlib.decompress(f.read()))
        for fname, entries in idx.items():
            print(f'提取 {fname}')
            out_path = os.path.join(outdir, fname)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            buf = b''
            for ent in entries:
                # ent 原始存储：(dlen_enc, offset_enc[, start_bytes])
                dl, off, *sb = ent
                off ^= key
                dl ^= key
                f.seek(off)
                buf += (sb[0] if sb else b'') + f.read(dl)
            # 写入文件
            with open(out_path, 'wb') as wf:
                wf.write(buf)
    print(f'\n✅全部提取完成！输出目录：{os.path.abspath(outdir)}')

def main():
    if len(sys.argv) != 2:
        print(f'USAGE：python {sys.argv[0]} <rpa file>')
        sys.exit(1)

    rpa_file = sys.argv[1]
    if not rpa_file.endswith('.rpa'):
        print('❌请输入.rpa后缀文件')
        sys.exit(1)

    out_dir = os.path.splitext(rpa_file)[0]
    with open(rpa_file,'rb') as f:
        header = f.read(40)
        off = int(header[8:24],16)
        k = int(header[25:33],16)
    rpa_extract(rpa_file, out_dir, off, k)

if __name__ == '__main__':
    main()