import struct
import sys


def parse_chunks(data: bytes, offset: int = 0):
    '''解析所有EMC记录块'''
    chunks = []
    total = len(data)
    while offset + 16 <= total:
        sig = data[offset:offset+8]
        data_len = struct.unpack_from('<Q', data, offset + 8)[0]
        data_start = offset + 16
        data_end = min(data_start + data_len, total)
        chunks.append({
            'sig_raw': sig,
            'sig_str': sig.rstrip(b' ').decode('ascii', errors='replace'),
            'length': data_len,
            'data': data[data_start:data_end]
        })
        offset = data_end
    return chunks

def rebuild_chunks(chunks: list) -> bytes:
    '''将块列表重新拼接为二进制数据'''
    result = b''
    for chunk in chunks:
        result += chunk['sig_raw']
        result += struct.pack('<Q', len(chunk['data']))
        result += chunk['data']
    return result

def extract_descript(eri_path: str):
    '''
    从ERI文件中提取descript文本
    返回 (text: str, is_utf16: bool)，失败返回 None
    '''
    with open(eri_path, 'rb') as f:  # 以二进制模式打开文件
        file_data = f.read()
    
    if len(file_data) < 64:  # 检查文件大小是否足够
        return None

    # 跳过64字节文件头
    top_chunks = parse_chunks(file_data, 64)
    
    # 找 Header 块
    header_chunk = None
    for c in top_chunks:
        if c['sig_str'] == 'Header':
            header_chunk = c
            break
    if not header_chunk:
        return None

    # 解析 Header 内子块，找 descript
    sub_chunks = parse_chunks(header_chunk['data'])
    descript_chunk = None
    for sc in sub_chunks:
        if sc['sig_str'] == 'descript':
            descript_chunk = sc
            break
    if not descript_chunk:
        return None

    # 解码文本，识别编码
    data = descript_chunk['data']
    if len(data) >= 2 and data[:2] == b'\xff\xfe':
        is_utf16 = True
        text = data[2:].decode('utf-16-le', errors='replace')
    else:
        is_utf16 = False
        # 日文游戏默认Shift-JIS，中文资源请改为 gbk
        text = data.decode('shift_jis', errors='replace')
    
    # 清理末尾空字符
    text = text.rstrip('\x00\r\n\t ')
    return text, is_utf16

def main():
    if len(sys.argv) != 4:
        print(f'USAGE: python {sys.argv[0]} <src.eri> <dst.eri> <out.eri>')
        sys.exit(-1)

    src_path = sys.argv[1]
    dst_path = sys.argv[2]
    out_path = sys.argv[3]

    # 从源文件提取描述文本
    src_result = extract_descript(src_path)
    if not src_result:
        print(f'错误：源文件 {src_path} 中未找到 descript 描述文本', file=sys.stderr)
        sys.exit(1)
    src_text, _ = src_result
    print(f'已从源文件提取描述文本，共 {len(src_text)} 个字符')

    # 读取目标文件并解析
    with open(dst_path, 'rb') as f:
        dst_data = f.read()

    if len(dst_data) < 64:
        print('错误：目标文件不是合法的ERI格式', file=sys.stderr)
        sys.exit(1)

    file_header = dst_data[:64]
    top_chunks = parse_chunks(dst_data, 64)

    # 找到目标文件的 Header 块
    header_idx = None
    for i, c in enumerate(top_chunks):
        if c['sig_str'] == 'Header':
            header_idx = i
            break

    if header_idx is None:
        print('错误：目标文件中未找到 Header 块', file=sys.stderr)
        sys.exit(1)

    # 解析 Header 内部子块
    header_chunk = top_chunks[header_idx]
    sub_chunks = parse_chunks(header_chunk['data'])

    # 找到 descript 子块
    descript_idx = None
    for i, sc in enumerate(sub_chunks):
        if sc['sig_str'] == 'descript':
            descript_idx = i
            break

    if descript_idx is None:
        print('错误：目标文件中未找到 descript 子块', file=sys.stderr)
        sys.exit(1)

    # 按目标文件原编码重新编码文本
    orig_data = sub_chunks[descript_idx]['data']
    is_utf16_dst = len(orig_data) >= 2 and orig_data[:2] == b'\xff\xfe'

    if is_utf16_dst:
        new_data = b'\xff\xfe' + src_text.encode('utf-16-le')
    else:
        # 日文默认 Shift-JIS
        new_data = src_text.encode('shift_jis', errors='replace')

    # 替换并重建文件
    sub_chunks[descript_idx]['data'] = new_data

    # 重建 Header 块
    new_header_data = rebuild_chunks(sub_chunks)
    top_chunks[header_idx]['data'] = new_header_data

    # 重建整个文件
    new_body = rebuild_chunks(top_chunks)
    output_data = file_header + new_body

    # 写入输出文件
    with open(out_path, 'wb') as f:
        f.write(output_data)

    print(f'替换完成！已输出到: {out_path}')
    # print(f'目标文件原编码: {'UTF-16 LE' if is_utf16_dst else 'Shift-JIS'}')
    # print(f'原 descript 长度: {len(orig_data)} 字节')
    # print(f'新 descript 长度: {len(new_data)} 字节')

if __name__ == '__main__':
    main()