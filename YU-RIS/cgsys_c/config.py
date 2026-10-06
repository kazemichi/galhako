FONT_CONFIG = {
    'font_c20': {
        'font_size': 20, # CONSTANT
        'canvas_size': (720, 400), # CONSTANT
        'x0': 10, # 6 <= x0 <= 14
        'y0': 14, # 10 <= y0 <= 18
        'vertical_spacing': 10, # CONSTANT
        'horizontal_spacing': 10, # CONSTANT
        'stroke_alpha': 170,
        'group_exclude': ['n2__']
    },
    'font_c30': {
        'font_size': 30, # CONSTANT
        'canvas_size': (720, 440), # CONSTANT
        'x0': 10, # 6 <= x0 <= 14
        'y0': 14, # 10 <= y0 <= 18
        'vertical_spacing': 10, # CONSTANT
        'horizontal_spacing': 10, # CONSTANT
        'stroke_alpha': 170,
        'group_exclude': ['n1__', 'n2__']
    }
}

# 路径
BASE_SAVE_PATH = r'./update2/cgsys_c/font'
FONT_PATH = r'./fonts'

# 回落字体
FALLBACK_FONTS = [
    'NotoSansSC-Regular.otf', # https://github.com/notofonts/noto-cjk Noto Sans CJK v2.004
    'NotoSansTC-Regular.otf',
    'NotoSansSymbols2-Regular.ttf', # https://github.com/notofonts/symbols Noto Sans Symbols 2 v2.008
    'NotoMusic-Regular.otf' # https://github.com/notofonts/music Noto Music v2.003
]