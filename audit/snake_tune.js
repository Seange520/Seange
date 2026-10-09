/* 参数扫描：找出「剩余空间阈值」的最佳取值。
   目标是在 300 局固定随机种子下，单局达到 15 个食物的成功率最高。 */
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

function run(factor, runs) {
    const scores = [];
    const t0 = Date.now();
    for (let i = 0; i < runs; i++) {
        const g = SnakeCore.createGame({ gridSize: 20, aiStrategy: 'smart', rng: mulberry32(1000 + i), spaceFactor: factor });
        g.start();
        let steps = 0;
        while (g.state.status === 'running' && steps < 20000) { g.step(); steps++; }
        scores.push(g.state.score);
    }
    const ok15 = scores.filter(s => s >= 15).length;
    const mean = scores.reduce((a, b) => a + b, 0) / scores.length;
    const min = Math.min(...scores);
    return { factor, ok15, runs, mean, min, ms: Date.now() - t0 };
}

const runs = parseInt(process.argv[2] || '300', 10);
const factors = [1.0, 1.15, 1.3, 1.5, 1.8, 2.0];
console.log(`每种阈值跑 ${runs} 局（固定种子 1000..）：\n`);
console.log('阈值倍数 | 达到15个 |  成功率 |   均值 | 最差 |  耗时');
const rows = [];
for (const f of factors) {
    const r = run(f, runs);
    rows.push(r);
    console.log(`${f.toFixed(2).padStart(8)} | ${String(r.ok15).padStart(4)}/${runs} | ${(r.ok15 / runs * 100).toFixed(1).padStart(5)}% | ${r.mean.toFixed(1).padStart(6)} | ${String(r.min).padStart(4)} | ${(r.ms / 1000).toFixed(1)}s`);
}
const best = rows.slice().sort((a, b) => b.ok15 - a.ok15 || b.mean - a.mean)[0];
console.log(`\n最佳：spaceFactor = ${best.factor}（成功率 ${(best.ok15 / runs * 100).toFixed(1)}%，均值 ${best.mean.toFixed(1)}）`);
