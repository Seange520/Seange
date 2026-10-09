/**
 * 运行时冒烟测试：搭一个最小可用的假 DOM，把 snake.html 里的内联脚本真正执行一遍。
 *
 * 为什么需要这个：
 *   node --check 只做语法检查，捕获不到"运行时抛异常"这类问题——
 *   例如某个 getElementById 拿不到元素、某个函数拼错名字、初始化时读了不存在的属性。
 *   这些错误在浏览器里会直接让页面变成一块死板子。
 *
 * 做法：
 *   用一个 Proxy 兜住 DOM 元素和 Canvas 2D 上下文，任何未定义的方法都当成空操作，
 *   任何未知属性都返回另一个 Proxy。这样子真正的游戏逻辑就能跑起来，
 *   而每次 setInterval 回调（tick）都会被我们捕获并手动推进，从而验证 AI 真的在动。
 *
 * 用法：node audit/smoke_test_snake_html.js
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = path.join(__dirname, '..', 'snake.html');
const html = fs.readFileSync(HTML, 'utf8');

/* ---------- 抽出 <script> 块（跳过内联的核心模块块也行，一起执行） ---------- */
const blocks = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (blocks.length === 0) {
    console.error('没有找到内联 script 块');
    process.exit(1);
}

/* ---------- 最小 DOM ---------- */
function makeElement(id) {
    const listeners = {};
    const el = {
        id,
        _text: '',
        _html: '',
        className: '',
        checked: false,
        value: '0',
        style: {},
        dataset: {},
        attributes: {},
        classList: {
            _set: new Set(),
            add(c) { this._set.add(c); },
            remove(c) { this._set.delete(c); },
            toggle(c, on) { if (on === undefined) { this._set.has(c) ? this._set.delete(c) : this._set.add(c); } else if (on) { this._set.add(c); } else { this._set.delete(c); } },
            contains(c) { return this._set.has(c); }
        },
        get textContent() { return this._text; },
        set textContent(v) { this._text = String(v); },
        get innerHTML() { return this._html; },
        set innerHTML(v) { this._html = String(v); },
        getAttribute(k) { return this.attributes[k] !== undefined ? this.attributes[k] : null; },
        setAttribute(k, v) { this.attributes[k] = String(v); },
        addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
        removeEventListener() { },
        dispatch(type, ev) { (listeners[type] || []).forEach(fn => fn(ev || { preventDefault() { } })); },
        _listeners: listeners,
        appendChild() { }, removeChild() { }, focus() { }, blur() { }, click() { this.dispatch('click'); },
        getBoundingClientRect() { return { left: 0, top: 0, width: 440, height: 440 }; },
        width: 440, height: 440
    };
    // Canvas 上下文：任何方法都当空操作，任何属性都可读写
    el.getContext = () => new Proxy({}, {
        get(t, k) {
            if (k in t) return t[k];
            return (...args) => undefined;   // 所有绘图调用都是空操作
        },
        set(t, k, v) { t[k] = v; return true; }
    });
    return el;
}

const elements = {};
function getEl(id) {
    if (!elements[id]) elements[id] = makeElement(id);
    return elements[id];
}

const timers = [];
const store = {};

const documentStub = {
    documentElement: makeElement('html'),
    body: makeElement('body'),
    getElementById: getEl,
    querySelector: (sel) => getEl('sel:' + sel),
    querySelectorAll: (sel) => {
        if (sel.includes('name="ai"')) {
            return ['off', 'greedy', 'smart'].map(v => { const e = getEl('radio:' + v); e.value = v; if (v === 'smart') e.checked = true; return e; });
        }
        if (sel.includes('radio-item')) {
            return ['off', 'greedy', 'smart'].map(v => { const e = getEl('item:' + v); e.attributes['data-mode'] = v; return e; });
        }
        return [];
    },
    addEventListener: (type, fn) => { (documentStub._l = documentStub._l || {})[type] = (documentStub._l[type] || []).concat(fn); },
    createElement: () => makeElement('tmp'),
    _l: {}
};

const localStorageStub = {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; },
    clear: () => { Object.keys(store).forEach(k => delete store[k]); }
};

const errors = [];
const sandbox = {
    console: {
        log: () => { }, info: () => { },
        warn: (...a) => errors.push('warn: ' + a.join(' ')),
        error: (...a) => errors.push('error: ' + a.join(' '))
    },
    document: documentStub,
    localStorage: localStorageStub,
    location: { hash: process.env.SNAKE_HASH || '' },
    navigator: { userAgent: 'node' },
    getComputedStyle: () => ({ getPropertyValue: () => '#123456' }),
    setInterval: (fn, ms) => { timers.push({ fn, ms }); return timers.length; },
    clearInterval: (id) => { if (id) timers[id - 1] = null; },
    setTimeout: (fn) => { fn(); return 0; },
    requestAnimationFrame: (fn) => { fn(); return 0; },
    Date, Math, JSON, Object, Array, String, Number, Boolean, Error, isNaN, parseInt, parseFloat,
    confirm: () => true,
    alert: () => { }
};
sandbox.window = sandbox;
sandbox.self = sandbox;
sandbox.globalThis = sandbox;

const ctx = vm.createContext(sandbox);

console.log('='.repeat(62));
console.log('snake.html 运行时冒烟测试（假 DOM，真执行）');
console.log('='.repeat(62));
console.log(`内联 script 块数量: ${blocks.length}`);

let failed = 0;
try {
    for (let i = 0; i < blocks.length; i++) {
        vm.runInContext(blocks[i], ctx, { filename: `snake.html#script${i}` });
        console.log(`  块${i} 执行成功 ✅`);
    }
} catch (e) {
    failed++;
    console.log(`  ❌ 执行内联脚本时抛异常：${e.message}`);
    console.log(e.stack.split('\n').slice(0, 6).join('\n'));
}

/* ---------- 检查初始化后的状态 ---------- */
console.log('');
console.log('--- 初始化结果 ---');
const g = sandbox.game || (sandbox.window && sandbox.window.game);
const txt = (id) => (elements[id] ? elements[id].textContent : '<未创建>');
console.log(`  canvas 元素:            ${elements['canvas'] ? '已获取 ✅' : '未获取 ❌'}`);
console.log(`  得分显示:               "${txt('scoreValue')}"`);
console.log(`  最高分显示:             "${txt('highScoreValue')}"`);
console.log(`  局数显示:               "${txt('gamesValue')}"`);
console.log(`  状态文字:               "${txt('statusText')}"`);
console.log(`  主题属性:               data-theme="${documentStub.documentElement.getAttribute('data-theme')}"`);
console.log(`  定时器是否已启动:        ${timers.filter(Boolean).length > 0 ? '是 ✅' : '否 ❌'}`);

/* ---------- 推进定时器，验证 AI 真的在动 ---------- */
console.log('');
console.log('--- 推进游戏循环 400 次，验证 AI 真的在动 ---');
const live = timers.filter(Boolean);
if (live.length === 0) {
    console.log('  ❌ 没有活动的定时器，游戏不会自己跑');
    failed++;
} else {
    const before = txt('scoreValue');
    for (let i = 0; i < 400; i++) {
        timers.filter(Boolean).forEach(t => t.fn());
    }
    const after = txt('scoreValue');
    console.log(`  推进前得分: "${before}"   推进后得分: "${after}"`);
    const b = parseInt(before.replace(/\D/g, ''), 10) || 0;
    const a = parseInt(after.replace(/\D/g, ''), 10) || 0;
    if (a > b) {
        console.log(`  ✅ 分数从 ${b} 涨到 ${a}，说明 AI 在无人操作下确实在自动推进`);
    } else {
        console.log('  ❌ 分数没有变化，AI 可能没有在跑');
        failed++;
    }
    console.log(`  状态文字: "${txt('statusText')}"`);
    console.log(`  最高分:   "${txt('highScoreValue')}"   局数: "${txt('gamesValue')}"`);
    const hist = elements['history'] ? elements['history'].innerHTML : '';
    console.log(`  战绩区是否已渲染: ${hist.length > 0 ? '是 ✅' : '否（可能还没结束一局）'}`);
}

/* ---------- 检查按钮是否都绑定了事件 ---------- */
console.log('');
console.log('--- 按钮事件绑定 ---');
['btnStart', 'btnDemo', 'btnRestart', 'btnTheme', 'btnReset'].forEach(id => {
    const el = elements[id];
    const n = el && el._listeners && el._listeners.click ? el._listeners.click.length : 0;
    console.log(`  ${id.padEnd(11)} click 监听器: ${n} ${n > 0 ? '✅' : '❌'}`);
    if (n === 0) failed++;
});

/* ---------- 模拟点击「重置」按钮 ---------- */
console.log('');
console.log('--- 模拟点击「重置全部纪录」 ---');
store['snake.highScore'] = '99';
store['snake.gamesPlayed'] = '7';
if (elements['btnReset']) {
    elements['btnReset'].dispatch('click');
    console.log(`  最高分显示: "${txt('highScoreValue')}"   局数显示: "${gamesValue()}"`);
    console.log(`  localStorage 里的最高分键: ${localStorageStub.getItem('snake.highScore') === null ? '已清除 ✅' : '仍存在 ❌'}`);
    if (localStorageStub.getItem('snake.highScore') !== null) failed++;
}
function gamesValue() { return txt('gamesValue'); }

/* ---------- 跑完整整一局，验证结束流程（计分/局数/战绩） ---------- */
console.log('');
console.log('--- 继续推进直到这一局结束，验证结束流程 ---');
{
    let guard = 0;
    const live2 = () => timers.filter(Boolean);
    while (live2().length > 0 && guard < 20000) {
        live2().forEach(t => t.fn());
        guard++;
    }
    console.log(`  推进 ${guard} 次后，活动定时器数量: ${live2().length}（结束时应为 0）`);
    if (live2().length !== 0) { console.log('  ❌ 游戏结束后定时器没有被清除'); failed++; }
    else { console.log('  ✅ 游戏结束后定时器已清除，不会出现"两个循环同时跑"'); }

    const hs = parseInt(txt('highScoreValue'), 10) || 0;
    const gp = parseInt(txt('gamesValue'), 10) || 0;
    console.log(`  最高分: ${hs}   累计局数: ${gp}`);
    if (gp >= 1) { console.log('  ✅ 局数已累加，说明结束流程正确写入了战绩'); }
    else { console.log('  ❌ 局数没有增加'); failed++; }
    if (hs > 0) { console.log('  ✅ 最高分已更新'); }
    else { console.log('  ❌ 最高分没有更新'); failed++; }
    console.log(`  localStorage 最高分键: ${localStorageStub.getItem('snake.highScore')}`);
    console.log(`  战绩 JSON 条数: ${JSON.parse(localStorageStub.getItem('snake.history') || '[]').length}`);
    const hist = elements['history'] ? elements['history'].innerHTML : '';
    console.log(`  战绩区内容长度: ${hist.length} ${hist.includes('分') ? '（含分数，已渲染 ✅）' : ''}`);
}

/* ---------- 结果 ---------- */
console.log('');
console.log('='.repeat(62));
console.log(`运行时错误捕获: ${errors.length === 0 ? '无 ✅' : errors.length + ' 条'}`);
errors.slice(0, 5).forEach(e => console.log('   ' + e));
console.log(`结论: ${failed === 0 ? '全部通过 ✅' : failed + ' 项未通过 ❌'}`);
process.exit(failed === 0 ? 0 : 1);
