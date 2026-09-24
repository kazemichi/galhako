import os
import struct
import sys


def parse_chunks(data: bytes, offset: int = 0) -> list:
    '''
    通用块解析：从指定偏移开始解析所有 EMC 记录块
    每个块头结构：8字节签名 + 8字节64位小端长度（共16字节头）
    '''
    chunks = []
    total_size = len(data)

    while offset + 16 <= total_size:
        sig_raw = data[offset:offset+8]
        # 64位小端无符号长度，兼容官方规格与32位实现（高32位为0）
        data_length = struct.unpack_from('<Q', data, offset + 8)[0]

        data_start = offset + 16
        data_end = min(data_start + data_length, total_size)
        chunk_data = data[data_start:data_end]

        # 签名转成可读字符串（去除末尾填充空格）
        sig_str = sig_raw.rstrip(b' ').decode('ascii', errors='replace')

        chunks.append({
            'sig_raw': sig_raw,
            'sig': sig_str,
            'data_length': data_length,
            'data_start': data_start,
            'data': chunk_data
        })
        
        offset = data_end

    return chunks

def parse_emc_file_header(data: bytes) -> dict | None:
    '''解析最外层 64 字节 EMC 文件头'''
    if len(data) < 64:
        return None

    header = {}
    header['signature'] = data[0:8]
    header['file_id'] = struct.unpack_from('<I', data, 0x08)[0]
    header['ext_info'] = struct.unpack_from('<I', data, 0x0C)[0]

    # 格式名称：取到第一个空字符为止
    format_raw = data[0x10:0x10 + 0x30]
    null_pos = format_raw.find(b'\x00')
    if null_pos != -1:
        header['format_name'] = format_raw[:null_pos].decode('ascii', errors='replace')
    else:
        header['format_name'] = format_raw.decode('ascii', errors='replace')

    return header

def parse_file_hdr(data: bytes) -> dict | None:
    '''解析 Header 内的 FileHdr 子块（文件全局信息）'''
    if len(data) < 20:
        return None
    ver, flag, kf_cnt, frames, duration = struct.unpack_from('<IIIII', data, 0)
    return {
        'version': f'0x{ver:08X}',
        'contain_flag': f'0x{flag:08X}',
        'keyframe_count': kf_cnt,
        'total_frames': frames,
        'total_duration_ms': duration
    }

def parse_image_info(data: bytes) -> dict | None:
    '''解析 ImageInf 子块（图像核心元数据）'''
    if len(data) < 68:
        return None
    fields = struct.unpack_from('<IIIIIIIIIIIIIIIII', data, 0)

    # 高度为有符号值，负数表示自顶向下
    height_raw = fields[5]
    height_signed = struct.unpack('<i', struct.pack('<I', height_raw))[0]
    is_top_down = height_signed < 0

    return {
        'version': f'0x{fields[0]:08X}',
        'transform_flag': f'0x{fields[1]:08X}',
        'architecture': f'0x{fields[2]:08X}',
        'image_format': f'0x{fields[3]:08X}',
        'width': fields[4],
        'height': abs(height_signed),
        'pixel_bits': fields[6],
        'clip_pixel': fields[7],
        'sampling_flag': f'0x{fields[8]:08X}',
        'quant_bits': [fields[9], fields[10]],
        'quant_scale': [fields[11], fields[12]],
        'block_factor': fields[13],
        'intra_overlap': fields[14],
        'time_transform_flag': f'0x{fields[15]:08X}',
        'time_transform_factor': fields[16],
        'is_top_down': is_top_down
    }

def parse_sound_info(data: bytes) -> dict | None:
    '''解析 SoundInf 子块（音频核心元数据）'''
    if len(data) < 40:
        return None
    fields = struct.unpack_from('<IIIIIIIIII', data, 0)
    return {
        'version': f'0x{fields[0]:08X}',
        'transform_flag': f'0x{fields[1]:08X}',
        'architecture': f'0x{fields[2]:08X}',
        'channels': fields[3],
        'sample_rate': fields[4],
        'block_set_count': fields[5],
        'subband_order': fields[6],
        'total_samples': fields[7],
        'overlap_factor': fields[8],
        'bit_depth': fields[9]
    }

def parse_text_chunk(data: bytes) -> dict:
    '''解析 descript / cpyright 文本块，自动识别编码'''
    if len(data) >= 2 and data[:2] == b'\xff\xfe':
        encoding = 'UTF-16 LE (带BOM)'
        text = data[2:].decode('utf-16-le', errors='replace')
    else:
        encoding = 'Shift-JIS (日文默认，中文可改GBK)'
        text = data.decode('shift_jis', errors='replace')

    # 清理末尾空字符与空白
    text = text.rstrip('\x00\r\n\t ')
    return {'encoding': encoding, 'text': text}

def parse_palette(data: bytes, preview_limit: int = 16) -> dict:
    '''解析 Palette 调色板块'''
    entry_count = len(data) // 4
    entries = []
    for i in range(min(entry_count, preview_limit)):
        b, g, r, a = struct.unpack_from('<BBBB', data, i * 4)
        entries.append({'index': i, 'R': r, 'G': g, 'B': b, 'Reserved/Alpha': a})

    return {
        'entry_count': entry_count,
        'preview_entries': entries,
        'has_more': entry_count > preview_limit
    }

def parse_sequence(data: bytes, preview_limit: int = 10) -> dict:
    '''解析 Sequence 序列表'''
    entry_count = len(data) // 8
    entries = []
    for i in range(min(entry_count, preview_limit)):
        frame_idx, delta_ms = struct.unpack_from('<II', data, i * 8)
        entries.append({'index': i, 'frame_index': frame_idx, 'delta_time_ms': delta_ms})

    return {
        'entry_count': entry_count,
        'preview_entries': entries,
        'has_more': entry_count > preview_limit
    }

def print_indent(content: str, level: int = 0):
    '''带缩进的格式化打印'''
    indent = '  ' * level
    print(f'{indent}{content}')

def main():
    if len(sys.argv) != 2:
        print('ERI 元数据解析工具')
        print(f'用法: python {sys.argv[0]} <输入.eri>')
        print('功能：解析文件头、Header块、Stream块的全部结构化元数据')
        sys.exit(-1)

    file_path = sys.argv[1]

    if not os.path.isfile(file_path):
        print(f'错误：文件不存在 {file_path}', file=sys.stderr)
        sys.exit(1)

    # 读取整个文件
    with open(file_path, 'rb') as f:
        file_data = f.read()

    if len(file_data) < 64:
        print('错误：文件过小，不是合法的 ERI 格式', file=sys.stderr)
        sys.exit(1)

    # ========== 1. 解析 EMC 文件头 ==========
    emc_header = parse_emc_file_header(file_data)
    print('=' * 60)
    print('【EMC 文件头】')
    print_indent(f'头部签名: {emc_header['signature']}', 1)
    print_indent(f'文件ID:  0x{emc_header['file_id']:08X}', 1)
    print_indent(f'扩展信息: 0x{emc_header['ext_info']:08X}', 1)
    print_indent(f'格式名称: {emc_header['format_name']}', 1)

    # ========== 2. 解析所有顶级块 ==========
    top_chunks = parse_chunks(file_data, 64)
    print('\n' + '=' * 60)
    print(f'【顶级块列表】共 {len(top_chunks)} 个')

    for idx, chunk in enumerate(top_chunks):
        print_indent(f'[{idx}] {chunk['sig']}  数据长度: {chunk['data_length']} 字节', 1)

        # ========== 3. 解析 Header 块内部子块 ==========
        if chunk['sig'] == 'Header':
            sub_chunks = parse_chunks(chunk['data'])
            print_indent(f'└─ 内部子块共 {len(sub_chunks)} 个：', 2)

            for sub in sub_chunks:
                print_indent(f'• {sub['sig']}  长度: {sub['data_length']} 字节', 3)

                # 识别并解析已知子块
                if sub['sig'] == 'FileHdr':
                    info = parse_file_hdr(sub['data'])
                    if info:
                        print_indent('  [文件头信息]', 4)
                        print_indent(f'版本号:     {info['version']}', 5)
                        print_indent(f'包含标志:   {info['contain_flag']}', 5)
                        print_indent(f'关键帧计数: {info['keyframe_count']}', 5)
                        print_indent(f'总帧数:     {info['total_frames']}', 5)
                        print_indent(f'总时长:     {info['total_duration_ms']} ms', 5)

                elif sub['sig'] == 'ImageInf':
                    info = parse_image_info(sub['data'])
                    if info:
                        print_indent('  [图像信息]', 4)
                        print_indent(f'版本号:     {info['version']}', 5)
                        print_indent(f'转换标志:   {info['transform_flag']}', 5)
                        print_indent(f'架构类型:   {info['architecture']}', 5)
                        print_indent(f'图像格式:   {info['image_format']}', 5)
                        print_indent(f'尺寸:       {info['width']} × {info['height']} 像素', 5)
                        print_indent(f'像素位深:   {info['pixel_bits']} bit', 5)
                        print_indent(f'扫描方向:   {'自顶向下' if info['is_top_down'] else '自底向上(默认)'}', 5)
                        print_indent(f'裁剪像素值: {info['clip_pixel']}', 5)
                        print_indent(f'分块系数:   {info['block_factor']}', 5)

                elif sub['sig'] == 'SoundInf':
                    info = parse_sound_info(sub['data'])
                    if info:
                        print_indent('  [音频信息]', 4)
                        print_indent(f'版本号:     {info['version']}', 5)
                        print_indent(f'声道数:     {info['channels']}', 5)
                        print_indent(f'采样率:     {info['sample_rate']} Hz', 5)
                        print_indent(f'总采样数:   {info['total_samples']}', 5)
                        print_indent(f'比特深度:   {info['bit_depth']} bit', 5)

                elif sub['sig'] in ('descript', 'cpyright'):
                    info = parse_text_chunk(sub['data'])
                    label = '描述文本' if sub['sig'] == 'descript' else '版权信息'
                    print_indent(f'  [{label}]', 4)
                    print_indent(f'编码: {info['encoding']}', 5)
                    # 显示所有文本
                    lines = info['text'].splitlines()
                    for line in lines:
                        print_indent(f'  {line}', 6)

                elif sub['sig'] == 'Palette':
                    info = parse_palette(sub['data'])
                    print_indent('  [调色板]', 4)
                    print_indent(f'条目总数: {info['entry_count']}', 5)
                    print_indent(f'前 {len(info['preview_entries'])} 条预览:', 5)
                    for e in info['preview_entries']:
                        print_indent(f'  [{e['index']:3d}] RGB({e['R']:3d},{e['G']:3d},{e['B']:3d}) 保留={e['Reserved/Alpha']}', 6)
                    if info['has_more']:
                        print_indent('  ... 更多省略', 6)

                elif sub['sig'] == 'Sequence':
                    info = parse_sequence(sub['data'])
                    print_indent('  [序列表]', 4)
                    print_indent(f'条目总数: {info['entry_count']}', 5)
                    print_indent(f'前 {len(info['preview_entries'])} 条预览:', 5)
                    for e in info['preview_entries']:
                        print_indent(f'  [{e['index']:2d}] 帧号={e['frame_index']}  间隔={e['delta_time_ms']}ms', 6)
                    if info['has_more']:
                        print_indent('  ... 更多省略', 6)

        # ========== 4. 解析 Stream 块内部子块 ==========
        elif chunk['sig'] == 'Stream':
            stream_subs = parse_chunks(chunk['data'])
            print_indent(f'└─ 流内子块共 {len(stream_subs)} 个：', 2)
            for s in stream_subs:
                type_desc = ''
                if s['sig'] == 'ImageFrm':
                    type_desc = '（图像帧数据）'
                elif s['sig'] == 'DiffeFrm':
                    type_desc = '（差分帧数据）'
                elif s['sig'] == 'SoundStm':
                    type_desc = '（音频流数据）'
                elif s['sig'] == 'Preview':
                    type_desc = '（预览图像数据）'
                print_indent(f'• {s['sig']}  长度: {s['data_length']} 字节 {type_desc}', 3)

    print('\n' + '=' * 60)
    print('解析完成')

if __name__ == '__main__':
    main()