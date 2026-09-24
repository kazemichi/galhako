import os
import subprocess
import sys

import config
import orjson
from tqdm.contrib.concurrent import thread_map

ERI_IN_PATH = config.ERI_IN_PATH
IMG_OUT_PATH = config.IMG_OUT_PATH
ERICVT_PATH = config.ERICVT_PATH
ERISACVT_PATH = config.ERISACVT_PATH
ERI_DESCRIPT_JSON = config.ERI_DESCRIPT_JSON

WORKER_PROCESS = 4 # 线程数

os.makedirs(IMG_OUT_PATH, exist_ok=True)

def eri_converter(item: dict):
    eri_name = item['name']
    in_eri = os.path.join(ERI_IN_PATH, eri_name)

    if 'reference_file' in item:
        # 差分图 ERI → PNG
        out_img = os.path.join(IMG_OUT_PATH, eri_name.replace('.eri', '.png'))
        args = [
            ERISACVT_PATH,
            '/mime:image/png',
            in_eri,
            out_img
        ]
    else:
        # 完整图 ERI → BMP
        out_img = os.path.join(IMG_OUT_PATH, eri_name.replace('.eri', '.bmp'))
        args = [
            ERICVT_PATH,
            '-d',
            in_eri,
            out_img
        ]

    subprocess.run(
        args,
        check=False,
        capture_output=True, # 关闭 exe 原始输出
        shell=False
    )

def main():
    # 检查 json 文件
    if not os.path.exists(ERI_DESCRIPT_JSON):
        print(f'找不到中间json文件：{ERI_DESCRIPT_JSON}，请先运行 eri_descript_info.py')
        sys.exit(1)

    # 读取 json
    with open(ERI_DESCRIPT_JSON, 'rb') as f:
        json_data = orjson.loads(f.read())

    total = len(json_data)
    print(f'总共待转换 ERI 文件：{total} , 线程数：{WORKER_PROCESS}')

    thread_map(
        eri_converter,
        json_data,
        max_workers=WORKER_PROCESS,
        desc='ERI→IMG',
        chunksize=1
    )

if __name__ == '__main__':
    main()