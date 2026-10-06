import sys
sys.path.append(r'./libs')

import argparse
import os
import unicodedata
from pathlib import Path

import config
import orjson
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm


def get_font_cmap(font_path: str):
    '''
    加载字体，返回 TTFont 对象和最佳 cmap
    '''
    tt = TTFont(font_path)
    cmap = tt.getBestCmap()
    return tt, cmap

def select_font_for_char(char: str, main_cmap: dict, fallback_list: list) -> tuple:
    '''
    :param char: 单个字符
    :param main_cmap: 主字体 cmap
    :param fallback_list: [(pil_font, cmap)]
    :return: (main_font, is_missing)
    '''
    cp = ord(char)
    if cp in main_cmap:
        return None, False
    for fb_font, fb_cmap in fallback_list:
        if cp in fb_cmap:
            return fb_font, False
    # 所有字体都找不到
    return None, True

def is_punctuation_char(char: str) -> bool:
    '''
    判断是否是标点符号，字符不做居中处理
    :param char: 单个字符
    :return: bool
    '''
    if len(char) != 1:
        return False
    cat = unicodedata.category(char)
    return cat.startswith('P')

def draw_character(draw: ImageDraw.ImageDraw, font_cfg: dict, main_font: ImageFont.FreeTypeFont, main_cmap: dict, fallback_list: list, char_group: str) -> None:
    '''
    绘制一组字符位图
    :param draw: PIL.ImageDraw 对象
    :param font_c: 字体配置
    :param main_font: PIL.ImageFont.FreeTypeFont 对象
    :param main_cmap: 字体 cmap
    :param fallback_list: 字体备选列表
    :param char_group: 字符组内容
    '''
    font_size = font_cfg['font_size']
    x0 = font_cfg['x0']
    y0 = font_cfg['y0']
    vertical_spacing = font_cfg['vertical_spacing']
    horizontal_spacing = font_cfg['horizontal_spacing']
    stroke_alpha = font_cfg['stroke_alpha']

    canvas_w, canvas_h = draw.im.size # 画布大小，用于越界判断

    for ind, char in enumerate(char_group):
        col = ind % 16
        row = ind // 16
        # 格子左上角坐标
        x = x0 + col * (font_size + horizontal_spacing)
        y = y0 + row * (font_size + vertical_spacing)

        # 格子中心点
        center_x = x + font_size // 2
        center_y = y + font_size // 2

        # 简单越界警告
        if (x + font_size) > canvas_w or (y + font_size) > canvas_h:
            print(f'[WARN]字符 {char} 绘制位置超出画布边界! x={x},y={y}')

        # 回落字体判断
        use_fb_font, is_missing = select_font_for_char(char, main_cmap, fallback_list)
        if is_missing:
            draw_font = main_font
        elif use_fb_font is not None:
            draw_font = use_fb_font
        else:
            draw_font = main_font

        # 获取当前字符 bbox
        bbox = draw.textbbox((0, 0), char, font=draw_font, stroke_width=1)
        glyph_left, glyph_top, glyph_right, glyph_bottom = bbox

        if is_punctuation_char(char):
            # 符号不居中处理
            draw_x = x
            draw_y = y
        else:
            # 字形自身的中心点
            glyph_cx = (glyph_left + glyph_right) // 2
            glyph_cy = (glyph_top + glyph_bottom) // 2

            # 计算绘制原点：让字形中心对齐格子中心
            draw_x = center_x - glyph_cx
            draw_y = center_y - glyph_cy

        # 绘制文字+描边
        draw.text(
            (draw_x, draw_y),
            char,
            fill=(255, 255, 255, 255),
            font=draw_font,
            stroke_width=1,
            stroke_fill=(0, 0, 0, stroke_alpha)
        )

        # draw.point((x, y), fill='red') # 格子左上角定位标点

# CLI 输入参数
def arg_parser():
    parser = argparse.ArgumentParser(description='读取字体文件并生成对应的位图字体。')
    parser.add_argument('-f' ,'--font', type=str, required=True, help='TTF/OTF 字体文件路径')
    parser.add_argument('-l', '--lang', type=str, choices=['S', 'T'], default='S', help='[可选] 简繁体选择 (S/T)，默认S')
    return parser.parse_args()

def main():
    args = arg_parser()
    font_path = Path(args.font)
    allow_suffix = {'.ttf', '.otf'}

    # 文件校验
    if not font_path.exists():
        print(f'文件不存在: {font_path}')
        return
    if not font_path.is_file():
        print(f'不是有效文件: {font_path}')
        return
    if font_path.suffix.lower() not in allow_suffix:
        print(f'无效文件类型: {font_path}, 仅支持{'/'.join(allow_suffix)}')
        return

    # 读取文字表
    charset_path = Path('charset') / f'cp950_c_{args.lang}.json'
    with open(charset_path, 'rb') as f:
        charset = orjson.loads(f.read())

    font_config = config.FONT_CONFIG

    for fc_name, fc_cfg in font_config.items():
        canvas_size = fc_cfg['canvas_size']
        font_size = fc_cfg['font_size']
        fallback_font_path = config.FONT_PATH
        fallback_fonts = config.FALLBACK_FONTS

        # 加载主字体
        try:
            main_font = ImageFont.truetype(str(font_path), font_size)
            main_tt, main_cmap = get_font_cmap(str(font_path))
        except OSError as e:
            print(f'[ERROR] 加载字体失败: {font_path}, size={font_size}, err:{e}')
            sys.exit(1)

        # 加载回落字体列表
        fallback_list = []
        for fallback_font in fallback_fonts:
            fb = Path(fallback_font_path) / fallback_font
            if not fb.exists():
                print(f'[WARN] 字体文件不存在: {fallback_font}')
                continue
            try:
                fb_font = ImageFont.truetype(str(fb), font_size)
                fb_tt, fb_cmap = get_font_cmap(str(fb))
                fallback_list.append((fb_font, fb_cmap))
                fb_tt.close()
            except OSError as e:
                print(f'[ERROR] 加载字体失败: {fallback_font}, err: {e}')

        # 创建输出文件夹
        out_folder = Path(config.BASE_SAVE_PATH) / fc_name
        out_folder.mkdir(parents=True, exist_ok=True)

        # 遍历字符集分组
        for group_key, char_group in tqdm(charset.items(), desc=fc_name):
            # 跳过排除的字符组
            if 'group_exclude' in fc_cfg and group_key in fc_cfg['group_exclude']:
                continue
            # 绘制字符位图
            with Image.new(mode='RGBA', size=canvas_size) as image:
                draw = ImageDraw.Draw(image)
                draw_character(draw, fc_cfg, main_font, main_cmap, fallback_list, char_group)
                out_file = out_folder / f'fnt_s{font_size}_{group_key}.png'
                image.save(out_file, 'PNG', optimize=True)

        main_tt.close()

    print('Done.')

if __name__ == '__main__':
    main()
