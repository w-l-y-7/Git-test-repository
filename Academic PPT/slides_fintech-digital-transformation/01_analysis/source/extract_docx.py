"""把 docx 抽成纯文本，保留标题层级和公式标记，方便后面做 PPT。

docx 本质是个 zip，里面 word/document.xml 存正文。这里不装任何第三方库，
直接用标准库解压 + 解析 XML。
"""

import re
import sys
import zipfile
from pathlib import Path

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
}

DOC = Path(sys.argv[1])
OUT = Path(sys.argv[2])

with zipfile.ZipFile(DOC) as z:
    xml = z.read('word/document.xml')

import xml.etree.ElementTree as ET

root = ET.fromstring(xml)
body = root.find('w:body', NS)

lines = []


def para_text(p):
    """取一个段落里的文字，遇到公式就打个 [公式] 占位。"""
    parts = []
    for node in p.iter():
        tag = node.tag
        if tag == f'{{{NS["m"]}}}oMath':
            parts.append(' [公式] ')
        elif tag == f'{{{NS["w"]}}}t':
            parts.append(node.text or '')
        elif tag == f'{{{NS["w"]}}}br':
            parts.append('\n')
    return ''.join(parts).strip()


def para_style(p):
    pr = p.find('w:pPr', NS)
    if pr is None:
        return ''
    st = pr.find('w:pStyle', NS)
    if st is None:
        return ''
    return st.get(f'{{{NS["w"]}}}val', '')


for el in body:
    tag = el.tag
    if tag == f'{{{NS["w"]}}}p':
        txt = para_text(el)
        style = para_style(el)
        if not txt:
            continue
        m = re.match(r'^(?:Heading|heading)\s*(\d)|^(\d)$', style)
        if style.startswith('Heading') or style.startswith('heading'):
            lvl = re.sub(r'\D', '', style) or '1'
            lines.append('#' * int(lvl) + ' ' + txt)
        elif style in ('Title', 'Subtitle'):
            lines.append('# ' + txt)
        else:
            lines.append(txt)
    elif tag == f'{{{NS["w"]}}}tbl':
        lines.append('')
        lines.append('【表格】')
        for row in el.findall('w:tr', NS):
            cells = []
            for cell in row.findall('w:tc', NS):
                cells.append(' '.join(para_text(p) for p in cell.findall('w:p', NS)).strip())
            lines.append('| ' + ' | '.join(cells) + ' |')
        lines.append('')

text = '\n'.join(lines)
OUT.write_text(text, encoding='utf-8')
print(f'写完 {OUT}，共 {len(lines)} 行，{len(text)} 字')
