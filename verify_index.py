"""
校验 index.html（个人主页）里的链接是否都能解析到真实文件。

注意中文文件名：snake.html / index.html 走的是 GitHub Pages，
浏览器会对中文文件名做百分号编码，直接用原名写在 href 里通常没问题，
但必须确认文件确实存在、名字完全一致。
"""
import io
import os
import re
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, 'index.html')

with io.open(HTML, encoding='utf-8') as f:
    html = f.read()

print('=' * 60)
print('index.html 链接校验')
print('=' * 60)

hrefs = re.findall(r'<a[^>]+href="([^"]+)"', html)
bad = 0
for h in hrefs:
    if h.startswith(('http://', 'https://', 'mailto:')):
        print(f'  外链  {h}')
        continue
    # 页面内相对链接：解码后检查文件是否存在
    target = urllib.parse.unquote(h)
    p = os.path.join(HERE, target)
    ok = os.path.isfile(p)
    if not ok:
        bad += 1
    print(f'  {"OK " if ok else "BAD"}  {h}   ->  {target}  {"" if ok else "（文件不存在）"}')

print()
print('=' * 60)
print('仓库根目录实际文件（用于比对）')
print('=' * 60)
for f in sorted(os.listdir(HERE)):
    if f.endswith(('.html', '.pdf')):
        print('   ', f)

print()
print('=' * 60)
print(f'结论：失效链接 {bad} 个')
