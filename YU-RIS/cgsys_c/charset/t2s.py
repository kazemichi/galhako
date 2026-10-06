import sys
sys.path.append(r'../libs')

from opencc import OpenCC

cc = OpenCC('t2s')
with open('cp950_c_T.json', 'r', encoding='utf-8') as fr, open('cp950_c_S.json', 'w', encoding='utf-8') as fw:
    fw.write(cc.convert(fr.read()))