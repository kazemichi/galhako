import os
import subprocess
import sys

import config

sys.path.append('./_libs')
from eri_meta import extract_descript, rewrite_eri_descript_from_text
from tqdm.contrib.concurrent import thread_map

ERI_IN_PATH = config.ERI_IN_PATH
DIFF_OUT_PATH = config.DIFF_OUT_PATH
ERI_OUT_PATH = config.ERI_OUT_PATH
ERICVT_PATH = config.ERICVT_PATH
ERISACVT_PATH = config.ERISACVT_PATH

MAX_WORKERS = 4 # 线程数

def preload_descript_cache(folder_in: str):
    '''
    预加载源文件夹全部eri的descript文本
    :return cache {eri_name: descript_text}
    '''
    cache = {}
    if not os.path.isdir(folder_in):
        print(f'源ERI文件夹不存在：{folder_in}')
        return cache
    for fname in os.listdir(folder_in):
        if not fname.lower().endswith('.eri'):
            continue
        src_fp = os.path.join(folder_in, fname)
        res = extract_descript(src_fp)
        if res is not None:
            text, _, _ = res
            cache[fname] = text
    print(f'预加载descript完成，共 {len(cache)} 个eri记录\n')
    return cache

def img_to_eri(img: str):
    ''' 图片 (PNG | BMP) 转 ERI '''
    img_path = os.path.join(DIFF_OUT_PATH, img) # 图像路径
    out_eri_path = os.path.join(ERI_OUT_PATH, f'{img[:-4]}.eri') # 保存路径

    if img.lower().endswith('.png'):
        cmd = [
            ERISACVT_PATH,
            '/mime:image/x-erina',
            '/erina',
            '/clip',
            '/cp0',
            img_path,
            out_eri_path
        ]
    elif img.lower().endswith('.bmp'):
        cmd = [
            ERICVT_PATH,
            '-e',
            '-p0',
            img_path,
            out_eri_path
        ]

    # 运行 cmd 命令
    subprocess.run(
        cmd,
        shell = False,
        capture_output = True,
        check = False
    )

def main():
    # 检查 ericvt
    if not os.path.exists(ERICVT_PATH):
        print(f'找不到转换工具: {ERICVT_PATH}')
        sys.exit(1)

    # 检查 erisacvt
    if not os.path.exists(ERISACVT_PATH):
        print(f'找不到转换工具: {ERISACVT_PATH}')
        sys.exit(1)

    # 检查差分图像文件夹
    if not os.path.isdir(DIFF_OUT_PATH) or len(os.listdir(DIFF_OUT_PATH)) == 0:
        print(f'找不到差分图像文件夹：{DIFF_OUT_PATH}，或文件夹为空')
        sys.exit(1)

    os.makedirs(ERI_OUT_PATH, exist_ok=True)

    diff_list = [d for d in os.listdir(DIFF_OUT_PATH)]
    thread_map(
        img_to_eri,
        diff_list,
        max_workers = MAX_WORKERS,
        desc = 'IMG→ERI',
        chunksize = 1
    )

    ''' descript 重写 '''
    descript_cache = preload_descript_cache(ERI_IN_PATH)
    eri_name_list = [f for f in os.listdir(ERI_IN_PATH) if f.lower().endswith('.eri')]

    for eri_name in eri_name_list:
        out_eri_full = os.path.join(ERI_OUT_PATH, eri_name)

        if eri_name in descript_cache:
            txt = descript_cache[eri_name]
            rewrite_eri_descript_from_text(txt, out_eri_full, out_eri_full)
    print('所有 descript 重写完成')

if __name__ == '__main__':
    main()
