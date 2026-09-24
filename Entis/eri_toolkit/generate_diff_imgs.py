import sys

sys.path.append('_libs')

import os
import shutil

import config
import orjson
from img_bgr_diff import generate_diff
from tqdm.contrib.concurrent import thread_map

IMG_OUT_PATH = config.IMG_OUT_PATH
DIFF_OUT_PATH = config.DIFF_OUT_PATH
ERI_DESCRIPT_JSON = config.ERI_DESCRIPT_JSON

MAX_WORKERS = 4 # 线程数

def diff_worker(item: dict):
    base_path = item['reference_file'].replace('.eri', '.bmp')
    cur_path = item['name'].replace('.eri', '.png')

    base_img = os.path.join(IMG_OUT_PATH, base_path)
    cur_img = os.path.join(IMG_OUT_PATH, cur_path)
    out_diff = os.path.join(DIFF_OUT_PATH, cur_path)
    out_base = os.path.join(DIFF_OUT_PATH, base_path)

    # 生成差分图
    generate_diff(base_img, cur_img, out_diff)
    # 复制基准bmp
    shutil.copyfile(base_img, out_base)

def main():
    # 检查 json 文件
    if not os.path.exists(ERI_DESCRIPT_JSON):
        print(f'找不到中间json文件：{ERI_DESCRIPT_JSON}，请先运行 eri_descript_info.py')
        sys.exit(1)

    # 检查图像文件夹
    if not os.path.exists(IMG_OUT_PATH):
        print('找不到 ERI 图像文件夹，请先运行 eri_to_img.py')
        sys.exit(1)

    # 读取 json
    with open(ERI_DESCRIPT_JSON, 'rb') as f:
        data = orjson.loads(f.read())

    task_list = [x for x in data if 'reference_file' in x]
    thread_map(
        diff_worker,
        task_list,
        max_workers = MAX_WORKERS,
        desc = '差分生成',
        chunksize = 1
    )

if __name__ == '__main__':
    main()
