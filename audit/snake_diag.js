/* 诊断脚本：找出智能 AI 唯一一次没吃到 15 个的原因，并确认 timeout 局是不是真的赢了 */
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
    const game = SnakeCore.createGame({ gridSize: 20, aiStrategy: strategy, rng: mulberry32(seed) });
    game.start();
    let steps = 0;
    while (game.state.status === 'running' && steps < maxSteps) { game.step(); steps++; }
    return { score: game.state.score, status: game.state.status, cause: game.state.deathCause, steps };
}

const startSeed = parseInt(process.argv[2] || '1000', 10);
const runs = parseInt(process.argv[3] || '300', 10);
const failures = [];
const notOver = [];
for (let i = 0; i < runs; i++) {
    const r = playOne('smart', startSeed + i, 20000);
    if (r.score < 15) failures.push({ seed: startSeed + i, ...r });
    if (r.status === 'running') notOver.push({ seed: startSeed + i, ...r });
}
console.log('未达到 15 个的局：', failures.length ? failures : '无');
console.log('\n步数用尽但游戏未结束的局（检查是不是卡死）：');
notOver.forEach(r => console.log(`  seed=${r.seed} 分数=${r.score} 步数=${r.steps}/${20000} 蛇长=${r.score + 3}  推断=${r.steps >= 20000 ? '达到步数上限' : ''}`));
if (notOver.length === 0) console.log('  无——说明没有卡死，所有 timeout 都对应真正的 380 满盘胜利或死局');

/* 单独复跑一局并打印最后 40 步，观察死亡瞬间 */
if (failures.length) {
    const seed = failures[0].seed;
    console.log(`\n复跑 seed=${seed} 的最后阶段：`);
    const game = SnakeCore.createGame({ gridSize: 20, aiStrategy: 'smart', rng: mulberry32(seed) });
    game.start();
    let steps = 0;
    const trace = [];
    while (game.state.status === 'running' && steps < 20000) {
        const before = { len: game.state.snake.length, lost: game.state.aiLost, path: game.state.aiPath.length, dir: game.state.direction };
        game.step();
        trace.push({ step: steps, ...before, head: JSON.stringify(game.state.snake[0]) });
        steps++;
    }
    trace.slice(-25).forEach(t => console.log(
        `  step=${String(t.step).padStart(4)} 蛇长=${String(t.len).padStart(3)} 方向=${t.dir.padEnd(5)} 保命=${t.lost ? 'Y' : 'N'} 路径长=${String(t.path).padStart(3)} 头=${t.head}`));
    console.log(`  结局：分数=${game.state.score} 状态=${game.state.status} 死因=${game.state.deathCause}`);
}
