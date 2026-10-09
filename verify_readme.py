"""校验 README 里所有图片与相对链接是否真实存在，并检查小节编号是否连续。"""
import io, os, re

repo = r'D:\deepseek_file\repo\Seange'
readme = os.path.join(repo, 'README.md')
with io.open(readme, encoding='utf-8') as f:
    text = f.read()

print('=' * 60)
print('1. 图片引用')
print('=' * 60)
imgs = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', text)
bad = 0
for alt, target in imgs:
    p = os.path.join(repo, target)
    ok = os.path.isfile(p)
    size = f'{os.path.getsize(p)/1024:.0f} KB' if ok else '缺失'
    print(f'  {"OK " if ok else "BAD"} {target:38s} {size:>8s}  {alt[:34]}')
    if not ok:
        bad += 1

print()
print('=' * 60)
print('2. 相对链接')
print('=' * 60)
links = re.findall(r'(?<!!)\[([^\]]+)\]\(([^)#][^)]*)\)', text)
for label, target in links:
    if target.startswith(('http://', 'https://', 'mailto:')):
        print(f'  EXT {target[:60]:60s}  {label[:26]}')
        continue
    p = os.path.join(repo, target)
    ok = os.path.isfile(p)
    print(f'  {"OK " if ok else "BAD"} {target:38s}        {label[:30]}')
    if not ok:
        bad += 1

print()
print('=' * 60)
print('3. 一级小节编号')
print('=' * 60)
heads = re.findall(r'^# ([一二三四五六七八九十]+、.+)$', text, re.M)
order = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
seq = [h[0] for h in heads]
print('  实际顺序:', ' '.join(seq))
print('  期望顺序:', ' '.join(order[:len(seq)]))
print('  连续:', '是 OK' if seq == order[:len(seq)] else '否 BAD')
for h in heads:
    print('   ', h)

print()
print('=' * 60)
print('4. 目录锚点是否都指向存在的标题')
print('=' * 60)
toc = re.findall(r'^\s*-\s+\[([^\]]+)\]\((#[^)]+)\)', text, re.M)
def slug(t):
    s = t.strip().lower()
    s = re.sub(r'[^\w\u4e00-\u9fff\s-]', '', s)
    s = re.sub(r'\s+', '-', s)
    return '#' + s
headings = re.findall(r'^#{1,4} (.+)$', text, re.M)
have = set(slug(h) for h in headings)
for label, anchor in toc:
    ok = anchor in have
    print(f'  {"OK " if ok else "CHK"} {anchor[:52]:52s}  {label[:32]}')
    if not ok:
        bad += 1

print()
print('=' * 60)
print(f'结论：不合格项 {bad} 个')
print(f'README 行数 {text.count(chr(10)) + 1}，字符数 {len(text)}，图片 {len(imgs)} 张')
