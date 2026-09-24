import os
import struct


def parse_chunks(data: bytes, offset: int = 0):
    '''
    解析EMC记录块
    :param data: 原始二进制
    :param offset: 起始偏移
    :return: [{'sig_raw':bytes, 'sig_str':str, 'length':int, 'data':bytes}, ...]
    '''
    chunks = []
    total = len(data)
    while offset + 16 <= total:
        sig_raw = data[offset:offset + 8]
        length = struct.unpack_from('<Q', data, offset + 8)[0]
        sub_data_start = offset + 16
        sub_data_end = min(sub_data_start + length, total)
        chunk_data = data[sub_data_start:sub_data_end]

        chunks.append({
            'sig_raw': sig_raw,
            'sig_str': sig_raw.rstrip(b' ').decode('ascii', errors='replace'),
            'length': length,
            'data': chunk_data
        })
        offset = sub_data_end
    return chunks


def rebuild_chunks(chunks):
    '''
    将块列表序列化为EMC二进制数据
    '''
    buf = b''
    for ck in chunks:
        buf += ck['sig_raw']
        buf += struct.pack('<Q', len(ck['data']))
        buf += ck['data']
    return buf


def extract_descript(eri_path: str):
    '''
    读取ERI文件内 descript 注释内容
    :param eri_path: ERI文件路径
    :return: (text:str, is_utf16:bool, raw_descript_bytes:bytes)
            读取失败返回 None
    is_utf16=True → 原编码 UTF‑16‑LE(带 \xff\xfe BOM)
    is_utf16=False → 原编码 Shift‑JIS
    '''
    if not os.path.isfile(eri_path):
        return None
    with open(eri_path, 'rb') as f:
        file_data = f.read()
    if len(file_data) < 64:
        return None

    # EMC文件头固定64字节，跳过，解析顶层记录
    top_chunks = parse_chunks(file_data, offset=64)

    header_chunk = None
    for ck in top_chunks:
        if ck['sig_str'] == 'Header':
            header_chunk = ck
            break
    if header_chunk is None:
        return None

    # 解析Header内部子记录，寻找 descript
    sub_chunks = parse_chunks(header_chunk['data'])
    descript_chunk = None
    for sc in sub_chunks:
        if sc['sig_str'] == 'descript':
            descript_chunk = sc
            break
    if descript_chunk is None:
        return None

    raw_bytes = descript_chunk['data']
    if len(raw_bytes) >= 2 and raw_bytes[:2] == b'\xff\xfe':
        is_utf16 = True
        text = raw_bytes[2:].decode('utf‑16‑le', errors='replace')
    else:
        is_utf16 = False
        text = raw_bytes.decode('shift_jis', errors='replace')

    text = text.rstrip('\x00\r\n\t ')
    return text, is_utf16, raw_bytes


def get_reference_file(descript_text: str):
    '''
    从descript文本提取 #reference‑file 引用文件名
    返回：引用文件名(str)；无标签/解析异常返回 False
    处理：行前后空白、空行，避免空格换行导致解析失败
    '''
    lines = [line.rstrip('\r\n') for line in descript_text.splitlines()]
    tag_index = None
    for idx, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line == '#reference-file':
            tag_index = idx
            break
    if tag_index is None:
        return False
    if tag_index + 1 >= len(lines):
        return False
    ref_name = lines[tag_index + 1].strip()
    if not ref_name:
        return False
    return ref_name


def build_descript_payload(new_text: str, is_utf16: bool):
    '''
    根据原始文件编码模式，生成新的descript子块payload
    :param new_text: 需要写入的文本
    :param is_utf16: True → UTF‑16‑LE带BOM；False → Shift‑JIS
    :return: descript块内部data二进制
    '''
    if is_utf16:
        payload = b'\xff\xfe' + new_text.encode('utf‑16‑le')
    else:
        payload = new_text.encode('shift_jis', errors='replace')
    return payload


def rewrite_eri_descript_from_text(src_text: str, dst_eri_path: str, out_eri_path: str):
    '''
    读取dst_eri_path，替换其descript文本为src_text，输出out_eri_path
    沿用目标ERI原本的编码格式，不会强制修改编码
    :param src_text: 新descript文本
    :param dst_eri_path: 原始待修改ERI路径
    :param out_eri_path: 输出ERI路径，可以与dst_eri_path相同做原地覆盖
    :return: True成功 / False失败（捕获内部全部异常）
    '''
    try:
        with open(dst_eri_path, 'rb') as f:
            dst_file_data = f.read()
        if len(dst_file_data) < 64:
            return False

        file_global_header = dst_file_data[:64]
        top_chunks = parse_chunks(dst_file_data, offset=64)

        # 定位顶层 Header 记录
        header_idx = None
        for i, ck in enumerate(top_chunks):
            if ck['sig_str'] == 'Header':
                header_idx = i
                break
        if header_idx is None:
            return False

        header_chunk = top_chunks[header_idx]
        sub_chunks = parse_chunks(header_chunk['data'])

        # 定位descript子块，读取原始编码标记
        descript_idx = None
        orig_is_utf16 = False
        for i, sc in enumerate(sub_chunks):
            if sc['sig_str'] == 'descript':
                descript_idx = i
                raw_sub_data = sc['data']
                orig_is_utf16 = (len(raw_sub_data) >= 2 and raw_sub_data[:2] == b'\xff\xfe')
                break
        if descript_idx is None:
            return False

        # 使用目标文件原始编码生成payload
        new_payload = build_descript_payload(src_text, orig_is_utf16)
        sub_chunks[descript_idx]['data'] = new_payload

        # 重建Header内部二进制、顶层EMC记录、完整ERI文件
        new_header_body = rebuild_chunks(sub_chunks)
        top_chunks[header_idx]['data'] = new_header_body
        new_body_data = rebuild_chunks(top_chunks)
        final_eri_data = file_global_header + new_body_data

        with open(out_eri_path, 'wb') as f:
            f.write(final_eri_data)
        return True
    except Exception:
        return False
