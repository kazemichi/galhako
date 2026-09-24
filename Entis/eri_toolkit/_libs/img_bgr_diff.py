import sys
sys.path.append('libs')

import os
from pathlib import Path

import cv2
import numpy as np


def imread_safe(file_path):
    '''
    读取图片
    '''
    buf = np.fromfile(file_path, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
    # 删除 A 通道
    if img.ndim == 3 and img.shape[-1] == 4:
        img = img[..., :3]
    return img

def generate_diff(base_path, cur_path, out_file):
    '''
    生成差分图片
    '''
    base_img = imread_safe(base_path)
    cur_img = imread_safe(cur_path)

    h1, w1 = base_img.shape[:2]
    h2, w2 = cur_img.shape[:2]
    if (h1, w1) != (h2, w2):
        print(f'尺寸不匹配！基准({w1}×{h1}) 差分图({w2}×{h2}) ，跳过 {cur_img_path}')
        return False
    else:
        delta = np.subtract(cur_img, base_img, dtype=np.uint8)

        # 创建输出文件夹
        out_p = Path(out_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        cv2.imencode('.png', delta)[1].tofile(os.path.join(out_p))

def main():
    if (len(sys.argv) != 4):
        print(f'Usage: python {sys.argv[0]} <base_img> <cur_img> <out_file>')
        print('Example: python delta.py ref.png main.png ./out/delta.png')
        sys.exit(1)

    base_path, cur_path, out_file = sys.argv[1], sys.argv[2], sys.argv[3]

    generate_diff(base_path, cur_path, out_file)

if __name__ == '__main__':
    main()
