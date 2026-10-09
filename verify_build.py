"""
校验 snake.html 里内联的代码与 snake_core.js / snake_store.js 完全一致，
并且内联后的代码仍然能跑（用它跑一遍 AI 达标率测试）。

用法：
    python verify_build.py
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, 'snake.html')
CORE = os.path.join(HERE, 'snake_core.js')
STORE = os.path.join(HERE, 'snake_store.js')

sys.path.insert(0, HERE)
from build_snake import strip_umd, read  # noqa: E402

html = read(HTML)
core_body = strip_umd(read(CORE)).strip()
store_body = strip_umd(read(STORE)).strip()

start = html.index('var SnakeCore = (function () {')
end = html.index('var SnakeStore = (function () {')
after_store = html.index('})();', end)

inline_core = html[html.index('{', start) + 1:html.rindex('})();', start, end)].strip()
inline_store = html[html.index('{', end) + 1:after_store].strip()

print('=' * 62)
print('1. 内联代码与源文件是否逐字节一致')
print('=' * 62)
print(f'  snake_core.js   {len(core_body):>6d} 字符 -> 内联 {"一致 OK" if inline_core == core_body else "不一致 BAD"}')
print(f'  snake_store.js  {len(store_body):>6d} 字符 -> 内联 {"一致 OK" if inline_store == store_body else "不一致 BAD"}')

print()
print('=' * 62)
print('2. 是否真的自包含')
print('=' * 62)
ext = re.findall(r'<script[^>]*\ssrc="([^"]+)"', html)
print(f'  外部 script 引用：{ext if ext else "无 OK"}')
print(f'  外部样式引用：{re.findall(r"<link[^>]+>", html) or "无 OK"}')
print(f'  文件行数：{html.count(chr(10)) + 1}')

print()
print('=' * 62)
print('3. 内联后的代码能否实际运行（用 Node 跑一遍达标率）')
print('=' * 62)
# 从 HTML 里抠出内联块，交给 Node 执行
m = re.search(r'<script>\s*/\* =+ 来自 snake_core\.js.*?</script>', html, re.S)
block = m.group(0)
block = block[len('<script>'):-len('</script>')]

runner = os.path.join(HERE, '_inline_check.js')
with io.open(runner, 'w', encoding='utf-8') as f:
    f.write(block)
    f.write('''
// 用内联出来的 SnakeCore 跑 200 局，验证行为与源模块一致
function mulberry32(seed){let a=seed>>>0;return function(){a=(a+0x6D2B79F5)>>>0;let t=Math.imul(a^(a>>>15),1|a);t=(t+Math.imul(t^(t>>>7),61|t))^t;return((t^(t>>>14))>>>0)/4294967296;};}
let ok15=0, sum=0, n=200;
for(let i=0;i<n;i++){
  const g=SnakeCore.createGame({gridSize:20,aiStrategy:'smart',rng:mulberry32(1000+i)});
  g.start();
  let steps=0;
  while(g.state.status==='running'&&steps<20000){g.step();steps++;}
  if(g.state.score>=15)ok15++;
  sum+=g.state.score;
}
console.log('  内联代码实测：' + ok15 + '/' + n + ' 局达到 15 个，平均 ' + (sum/n).toFixed(1) + ' 个');
''')

node = r'C:\Users\Senage\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe'
r = subprocess.run([node, runner], capture_output=True, text=True, encoding='utf-8')
print(r.stdout.strip() or r.stderr.strip()[:600])
os.remove(runner)
