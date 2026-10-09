/* ============================================================
 * 贪吃蛇 AI 批量统计测试
 *
 * 直接 require 仓库里真正的 snake_core.js —— 也就是 snake.html 用的那份逻辑，
 * 所以这里跑出来的成功率就是演示时的成功率，不存在"测试代码和游戏代码不一致"。
 *
 * 运行：node audit/snake_ai_test.js [每种策略的局数]
 * ============================================================ */
const path = require('path');
const SnakeCore = require(path.join(__dirname, '..', 'snake_core.js'));

function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
        a = (a + 0x6D2B79F5) >>> 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

function playOne(strategy, seed, maxSteps) {
    const game = SnakeCore.createGame({
        gridSize: 20,
        aiStrategy: strategy,
        rng: mulberry32(seed)
    });
    game.start();
    let steps = 0;
    let lostCount = 0;
    while (game.state.status === 'running' && steps < maxSteps) {
        game.step();
        if (game.state.aiLost) lostCount++;
        steps++;
    }
    return {
        score: game.state.score,
        status: game.state.status,
        cause: game.state.deathCause,
        steps: steps,
        lostRatio: steps ? lostCount / steps : 0
    };
}

function stats(nums) {
    const s = nums.slice().sort((a, b) => a - b);
    const n = s.length;
    const mean = s.reduce((a, b) => a + b, 0) / n;
    const median = n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
    const stdev = Math.sqrt(s.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1));
    return { mean, median, stdev, min: s[0], max: s[n - 1], sorted: s };
}

function bench(strategy, runs) {
    const results = [];
    const t0 = Date.now();
    for (let i = 0; i < runs; i++) results.push(playOne(strategy, 1000 + i, 20000));
    const elapsed = Date.now() - t0;

    const scores = results.map(r => r.score);
    const st = stats(scores);
    const reached = (thr) => scores.filter(s => s >= thr).length;
    const causes = {};
    results.forEach(r => { causes[r.cause || 'win/timeout'] = (causes[r.cause || 'win/timeout'] || 0) + 1; });
    const avgLost = results.reduce((a, r) => a + r.lostRatio, 0) / results.length;

    console.log(`\n===== AI 策略：${strategy} （${runs} 局，${elapsed} ms，${(runs / (elapsed / 1000)).toFixed(0)} 局/秒） =====`);
    console.log(`吃到食物数：均值 ${st.mean.toFixed(1)}  中位数 ${st.median}  标准差 ${st.stdev.toFixed(1)}  最差 ${st.min}  最好 ${st.max}`);
    console.log(`死亡原因分布：`, causes);
    if (strategy === 'smart') console.log(`处于"追尾保命"状态的步数占比：${(avgLost * 100).toFixed(1)}%`);
    for (const thr of [5, 10, 15, 20, 30, 50, 100]) {
        const ok = reached(thr);
        console.log(`  达到 >= ${String(thr).padStart(3)} 个：${String(ok).padStart(4)}/${runs} = ${(ok / runs * 100).toFixed(1)}%`);
    }
    return { scores, st, reached15: reached(15), runs };
}

const runs = parseInt(process.argv[2] || '400', 10);
console.log('贪吃蛇 AI 统计测试 —— 题目硬指标：连续吃完 15 个食物不死\n');
const greedy = bench('greedy', runs);
const smart = bench('smart', runs);

console.log('\n================= 结论 =================');
const gFail = 1 - greedy.reached15 / greedy.runs;
const sFail = 1 - smart.reached15 / smart.runs;
console.log(`朴素贪心：单局达到 15 个的概率 ${((1 - gFail) * 100).toFixed(1)}%，均值 ${greedy.st.mean.toFixed(1)} 个`);
console.log(`智能 BFS：单局达到 15 个的概率 ${((1 - sFail) * 100).toFixed(1)}%，均值 ${smart.st.mean.toFixed(1)} 个`);
for (const n of [1, 3, 5]) {
    console.log(`  连开 ${n} 局全部达标的概率：贪心 ${((1 - gFail) ** n * 100).toFixed(1)}%  →  智能 ${((1 - sFail) ** n * 100).toFixed(1)}%`);
}
