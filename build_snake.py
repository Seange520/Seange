"""
把 snake_core.js 与 snake_store.js 内联进 snake.html，生成一个自包含的单文件版本。

为什么要有这一步：
  任务书对小游戏的要求是「纯前端单文件（HTML/CSS/JS），浏览器双击即可打开，无框架依赖」。
  开发时把逻辑拆成三个文件便于测试（audit/ 下的脚本能直接 require 游戏本体逻辑），
  所以交付前用这个脚本把两个模块原样内联回去，保证交付物是单文件。

  snake_core.js / snake_store.js 仍是唯一事实来源（single source of truth），
  snake.html 里内联的代码是从它们读出来的，不存在两份手工维护的副本。

用法：
    python build_snake.py
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, 'snake.html')
CORE = os.path.join(HERE, 'snake_core.js')
STORE = os.path.join(HERE, 'snake_store.js')

BEGIN = '<!-- INLINE:BEGIN 本段由 build_snake.py 从 snake_core.js 与 snake_store.js 内联生成，请勿手工修改 -->'
END = '<!-- INLINE:END -->'


def read(path):
    with io.open(path, encoding='utf-8') as f:
        return f.read()


def strip_umd(source):
    """去掉 UMD 包装，只保留工厂函数的函数体，使其在 <script> 里直接可用。

    两个模块的结构都是：
        (function (root, factory) { ...UMD... })(this, function () {
            'use strict';
            ...真正的内容...
        });
    内联时把外层换成普通声明即可，内容一行不动。
    """
    start = source.index('function () {')
    body_start = source.index('{', start) + 1
    # 从结尾往前找最后一个 '});'
    body_end = source.rindex('});')
    body = source[body_start:body_end]
    return body.rstrip()


def build():
    html = read(HTML)
    core = read(CORE)
    store = read(STORE)

    core_body = strip_umd(core)
    store_body = strip_umd(store)

    inline = (
        BEGIN + '\n'
        + '<script>\n'
        + '/* ==================== 来自 snake_core.js ==================== */\n'
        + 'var SnakeCore = (function () {\n'
        + core_body + '\n'
        + '})();\n'
        + '\n'
        + '/* ==================== 来自 snake_store.js ==================== */\n'
        + 'var SnakeStore = (function () {\n'
        + store_body + '\n'
        + '})();\n'
        + '</script>\n'
        + END
    )

    # 替换原来的两行外链 script
    pattern = re.compile(
        r'[ \t]*<script src="snake_core\.js"></script>\r?\n'
        r'[ \t]*<script src="snake_store\.js"></script>'
    )
    if not pattern.search(html):
        # 已经内联过：把旧的内联块换掉
        pattern = re.compile(re.escape(BEGIN) + r'.*?' + re.escape(END), re.S)
        if not pattern.search(html):
            raise SystemExit('找不到需要替换的外链或内联块，请检查 snake.html')
        new_html = pattern.sub(lambda m: inline, html, count=1)
    else:
        new_html = pattern.sub(lambda m: inline, html, count=1)

    with io.open(HTML, 'w', encoding='utf-8', newline='\n') as f:
        f.write(new_html)

    print('已内联：')
    print(f'  snake_core.js   {len(core):>7d} 字符')
    print(f'  snake_store.js  {len(store):>7d} 字符')
    print(f'  snake.html      {len(new_html):>7d} 字符，{new_html.count(chr(10)) + 1} 行')
    # 校验：内联后不应再出现外链
    left = re.findall(r'<script src="([^"]+)"', new_html)
    print(f'  剩余外部 script 引用：{left if left else "无（已是自包含单文件）"}')


if __name__ == '__main__':
    build()
