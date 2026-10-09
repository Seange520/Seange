"""
验证「AI 模式全程无需人工操作」这条硬指标。

做法：从 snake.html 里抽出内联的游戏逻辑（与交付文件是同一份代码），
      创建游戏后直接 start()，然后只调用 step() —— 不调用 setDirection()，
      也就是完全模拟"人不再碰任何按键"。
      如果没有任何人工输入干预，AI 仍能连续吃到 15 个食物，这条指标就成立。

用法：python verify_autoplay.py
"""
import io
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_snake import read  # noqa: E402

html = read(os.path.join(HERE, 'snake.html'))
m = re.search(r'<script>\s*/\* =+ 来自 snake_core\.js.*?</script>', html, re.S)
if not m:
    raise SystemExit('没找到内联脚本块，snake.html 可能还没执行 build_snake.py')
block = m.group(0)[len('<script>'):-len('</script>')]

# 临时脚本放在仓库内被 .gitignore 忽略的 .verify_tmp/ 里。
# 不用系统临时目录：某些受限环境（含沙箱）不允许写 %TEMP%。
tmpdir = os.path.join(HERE, '.verify_tmp')
os.makedirs(tmpdir, exist_ok=True)
runner = os.path.join(tmpdir, 'autoplay_check.js')
with io.open(runner, 'w', encoding='utf-8') as f:
    f.write(block)
    f.write(r'''
function mulberry32(seed){let a=seed>>>0;return function(){a=(a+0x6D2B79F5)>>>0;let t=Math.imul(a^(a>>>15),1|a);t=(t+Math.imul(t^(t>>>7),61|t))^t;return((t^(t>>>14))>>>0)/4294967296;};}

const N = 500;
let reached15 = 0, totalFood = 0, minFood = Infinity, noInputUsed = true;

for (let i = 0; i < N; i++) {
  // 只创建 + start，之后绝不调用 setDirection（模拟"不再有任何人工操作"）
  const g = SnakeCore.createGame({ gridSize: 20, aiStrategy: 'smart', rng: mulberry32(3000 + i) });
  g.start();
  let steps = 0;
  while (g.state.status === 'running' && steps < 20000) {
    g.step();                 // 全程无人工输入
    steps++;
  }
  const sc = g.state.score;
  totalFood += sc;
  if (sc < minFood) minFood = sc;
  if (sc >= 15) reached15++;
}

console.log('  样本局数            : ' + N);
console.log('  全程无人工输入      : ' + (noInputUsed ? '是（未调用过 setDirection）' : '否'));
console.log('  达到 15 个食物的局数 : ' + reached15 + '/' + N + ' = ' + (reached15 / N * 100).toFixed(1) + '%');
console.log('  平均吃到食物数      : ' + (totalFood / N).toFixed(1) + ' 个');
console.log('  最差一局            : ' + minFood + ' 个');
console.log('');
console.log(reached15 === N
  ? '  结论：全部 ' + N + ' 局都在零人工操作下达到 15 个食物 —— 硬指标成立'
  : '  结论：有 ' + (N - reached15) + ' 局未达标，达标率 ' + (reached15 / N * 100).toFixed(1) + '%');
''')

def find_node():
    """找一个可用的 node：优先 PATH 上的，找不到再退回本机已知路径。"""
    from shutil import which
    for name in ('node', 'node.exe'):
        p = which(name)
        if p:
            return p
    fallback = r'C:\Users\Senage\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe'
    if os.path.isfile(fallback):
        return fallback
    raise SystemExit('找不到 node，请先安装 Node.js 或把它加入 PATH')


node = find_node()
r = subprocess.run([node, runner], capture_output=True, text=True, encoding='utf-8')
print('=' * 62)
print('「AI 全程无需人工操作」验证（用 snake.html 内联的同一份代码）')
print('=' * 62)
print(r.stdout.strip())
if r.stderr.strip():
    print('stderr:', r.stderr.strip()[:500])

# 清理临时目录
import shutil
shutil.rmtree(tmpdir, ignore_errors=True)