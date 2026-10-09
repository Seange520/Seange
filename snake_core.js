/* ============================================================
 * snake_core.js —— 贪吃蛇的纯逻辑核心（无 DOM 依赖）
 *
 * 这个文件被两处使用：
 *   1. snake.html 通过 <script> 引入，浏览器里跑真正的游戏
 *   2. audit/snake_ai_test.js 通过 require() 引入，做批量统计测试
 * 两边共用同一份代码，因此"测出来的成功率"就是"演示时的成功率"。
 * ============================================================ */
(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.SnakeCore = factory();
    }
})(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const DIRS = {
        up: { x: 0, y: -1 },
        down: { x: 0, y: 1 },
        left: { x: -1, y: 0 },
        right: { x: 1, y: 0 }
    };
    const OPPOSITE = { up: 'down', down: 'up', left: 'right', right: 'left' };
    const ORDER = ['up', 'right', 'down', 'left'];

    function key(c) { return c.x + ',' + c.y; }

    function createGame(options) {
        const opt = options || {};
        const gridSize = opt.gridSize || 20;
        const rng = opt.rng || Math.random;
        // 安全性阈值：走完这一步后，剩余可活动空间至少要达到"蛇长 × spaceFactor"。
        // 1.0 是最宽松的下限，调大更保守（更不容易把自己盘死，但可能更保守而少吃食物）。
        const spaceFactor = opt.spaceFactor || 1.0;

        const state = {
            gridSize: gridSize,
            snake: [],
            food: { x: 0, y: 0 },
            direction: 'right',
            nextDirection: 'right',
            score: 0,
            status: 'ready',          // ready | running | over | win
            deathCause: null,         // wall | self | null
            aiStrategy: opt.aiStrategy || 'smart',   // smart | greedy | off
            aiPath: [],               // AI 最近规划的路径（画在画布上）
            aiLost: false             // AI 是否处于"先保命"状态
        };

        function inBounds(x, y) {
            return x >= 0 && x < gridSize && y >= 0 && y < gridSize;
        }

        /* ---------- 初始化 / 放食物 ---------- */
        function placeFood() {
            const occupied = new Set(state.snake.map(key));
            const free = [];
            for (let y = 0; y < gridSize; y++) {
                for (let x = 0; x < gridSize; x++) {
                    if (!occupied.has(x + ',' + y)) free.push({ x: x, y: y });
                }
            }
            if (free.length === 0) { state.status = 'win'; return; }
            // 枚举空格后均匀取样，避免"随机试 N 次"可能退化的情况
            state.food = free[Math.floor(rng() * free.length)];
        }

        function reset() {
            const mid = Math.floor(gridSize / 2);
            state.snake = [
                { x: mid, y: mid },
                { x: mid - 1, y: mid },
                { x: mid - 2, y: mid }
            ];
            state.direction = 'right';
            state.nextDirection = 'right';
            state.score = 0;
            state.status = 'ready';
            state.deathCause = null;
            state.aiPath = [];
            state.aiLost = false;
            placeFood();
        }

        /* ---------- 基础工具 ---------- */
        function bodyKeys(snakeArr, skipLast) {
            const s = new Set();
            const end = skipLast ? snakeArr.length - 1 : snakeArr.length;
            for (let i = 0; i < end; i++) s.add(key(snakeArr[i]));
            return s;
        }

        // BFS 最短路。blocked 为不可通行格集合；start/goal 永远视为可通行。
        function bfs(start, goal, blocked) {
            if (start.x === goal.x && start.y === goal.y) return [];
            const goalKey = key(goal);
            const prev = new Map();
            const startKey = key(start);
            prev.set(startKey, null);
            const queue = [start];
            let head = 0;
            while (head < queue.length) {
                const cur = queue[head++];
                for (let i = 0; i < ORDER.length; i++) {
                    const d = ORDER[i];
                    const nx = cur.x + DIRS[d].x, ny = cur.y + DIRS[d].y;
                    if (!inBounds(nx, ny)) continue;
                    const k = nx + ',' + ny;
                    if (prev.has(k)) continue;
                    if (k !== goalKey && blocked.has(k)) continue;   // 终点永远可达
                    prev.set(k, cur);
                    if (k === goalKey) {
                        const path = [];
                        let node = { x: nx, y: ny };
                        while (node) { path.push(node); node = prev.get(key(node)); }
                        path.pop();              // 去掉起点
                        return path.reverse();
                    }
                    queue.push({ x: nx, y: ny });
                }
            }
            return null;
        }

        // 从 start 出发能到达的空格数（洪水填充），用于判断是否把自己关死
        function reachableCount(start, blocked) {
            const seen = new Set([key(start)]);
            const queue = [start];
            let head = 0;
            while (head < queue.length) {
                const cur = queue[head++];
                for (let i = 0; i < ORDER.length; i++) {
                    const d = ORDER[i];
                    const nx = cur.x + DIRS[d].x, ny = cur.y + DIRS[d].y;
                    if (!inBounds(nx, ny)) continue;
                    const k = nx + ',' + ny;
                    if (blocked.has(k) || seen.has(k)) continue;
                    seen.add(k);
                    queue.push({ x: nx, y: ny });
                }
            }
            return seen.size;
        }

        // 手玩模式：不能掉头、不能撞自己（尾巴会让出）
        function legalMoves(snakeArr, dir) {
            const head = snakeArr[0];
            const out = [];
            for (let i = 0; i < ORDER.length; i++) {
                const d = ORDER[i];
                if (OPPOSITE[d] === dir) continue;
                const nx = head.x + DIRS[d].x, ny = head.y + DIRS[d].y;
                if (!inBounds(nx, ny)) continue;
                const eats = (nx === state.food.x && ny === state.food.y);
                const blocked = bodyKeys(snakeArr, !eats);
                if (blocked.has(nx + ',' + ny)) continue;
                out.push(d);
            }
            return out;
        }

        /* ---------- 安全性校验：走这一步之后会不会把自己关死 ---------- */
        function isSafeMove(snakeArr, dir) {
            const head = snakeArr[0];
            const nh = { x: head.x + DIRS[dir].x, y: head.y + DIRS[dir].y };
            if (!inBounds(nh.x, nh.y)) return false;

            const eats = (nh.x === state.food.x && nh.y === state.food.y);
            const newSnake = eats
                ? [nh].concat(snakeArr)
                : [nh].concat(snakeArr.slice(0, snakeArr.length - 1));

            // 撞自己
            for (let i = 1; i < newSnake.length; i++) {
                if (newSnake[i].x === nh.x && newSnake[i].y === nh.y) return false;
            }

            const headNew = newSnake[0];
            const tailNew = newSnake[newSnake.length - 1];
            // 目标格是尾巴，视为可通行；其余身体格视为障碍
            const blocked = bodyKeys(newSnake, true);
            blocked.delete(key(tailNew));

            // 不变量一：头必须还能追到自己的尾巴（经典"别把自己盘死"判据）
            if (bfs(headNew, tailNew, blocked) === null) return false;

            // 不变量二：剩余活动空间不能小于蛇长的 spaceFactor 倍
            const space = reachableCount(headNew, bodyKeys(newSnake, false));
            if (space < Math.ceil(newSnake.length * spaceFactor)) return false;

            return true;
        }

        function dirFromStep(head, stepCell) {
            for (let i = 0; i < ORDER.length; i++) {
                const d = ORDER[i];
                if (head.x + DIRS[d].x === stepCell.x && head.y + DIRS[d].y === stepCell.y) return d;
            }
            return null;
        }

        /* ---------- AI 策略一：朴素贪心（原始作业的实现，保留做对比） ---------- */
        function greedyMove() {
            const head = state.snake[0];
            const dx = state.food.x - head.x;
            const dy = state.food.y - head.y;
            let preferred;
            if (Math.abs(dx) >= Math.abs(dy)) {
                preferred = dx > 0 ? ['right', 'up', 'down', 'left'] : ['left', 'up', 'down', 'right'];
            } else {
                preferred = dy > 0 ? ['down', 'right', 'left', 'up'] : ['up', 'right', 'left', 'down'];
            }
            const legal = legalMoves(state.snake, state.direction);
            const blocked = bodyKeys(state.snake, true);   // 原版：只排除到倒数第二节
            for (let i = 0; i < preferred.length; i++) {
                const d = preferred[i];
                if (legal.indexOf(d) === -1) continue;
                const nh = { x: head.x + DIRS[d].x, y: head.y + DIRS[d].y };
                if (blocked.has(nh.x + ',' + nh.y)) continue;
                state.aiPath = [];
                state.aiLost = false;
                return d;
            }
            state.aiPath = [];
            return legal.length ? legal[0] : state.direction;
        }

        /* ---------- AI 策略二：BFS 最短路 + 安全性校验 + 追尾保命 ---------- */
        function smartMove() {
            const snake = state.snake;
            const head = snake[0];
            const legal = legalMoves(snake, state.direction);
            if (legal.length === 0) return state.direction;

            // 相邻就是食物：能安全吃就直接吃
            for (let i = 0; i < legal.length; i++) {
                const d = legal[i];
                const nh = { x: head.x + DIRS[d].x, y: head.y + DIRS[d].y };
                if (nh.x === state.food.x && nh.y === state.food.y && isSafeMove(snake, d)) {
                    state.aiPath = [];
                    state.aiLost = false;
                    return d;
                }
            }

            // 1) 沿 BFS 最短路走第一步，且这一步必须安全
            const blocked = bodyKeys(snake, true);
            const toFood = bfs(head, state.food, blocked);
            if (toFood && toFood.length > 0) {
                const d = dirFromStep(head, toFood[0]);
                if (d && legal.indexOf(d) !== -1 && isSafeMove(snake, d)) {
                    state.aiPath = toFood;
                    state.aiLost = false;
                    return d;
                }
                // 最短路第一步不安全：退一步，找"缩短距离且安全"的方向
                const curDist = Math.abs(head.x - state.food.x) + Math.abs(head.y - state.food.y);
                let best = null, bestDist = curDist;
                for (let i = 0; i < legal.length; i++) {
                    const d2 = legal[i];
                    const nh = { x: head.x + DIRS[d2].x, y: head.y + DIRS[d2].y };
                    const dist = Math.abs(nh.x - state.food.x) + Math.abs(nh.y - state.food.y);
                    if (dist < bestDist && isSafeMove(snake, d2)) { best = d2; bestDist = dist; }
                }
                if (best) { state.aiPath = []; state.aiLost = false; return best; }
            }

            // 2) 食物不可达或路径不安全 → 追自己的尾巴，先活下去
            state.aiLost = true;
            const tail = snake[snake.length - 1];
            if (!(head.x === tail.x && head.y === tail.y)) {
                const blocked2 = bodyKeys(snake, true);
                blocked2.delete(key(tail));
                const toTail = bfs(head, tail, blocked2);
                if (toTail && toTail.length > 0) {
                    const d = dirFromStep(head, toTail[0]);
                    if (d && legal.indexOf(d) !== -1 && isSafeMove(snake, d)) {
                        state.aiPath = toTail;
                        return d;
                    }
                }
            }

            // 3) 退而求其次：选活动空间最大的安全方向
            let bestD = null, bestSpace = -1;
            for (let i = 0; i < legal.length; i++) {
                const d = legal[i];
                if (!isSafeMove(snake, d)) continue;
                const nh = { x: head.x + DIRS[d].x, y: head.y + DIRS[d].y };
                const space = reachableCount(nh, bodyKeys(snake, false));
                if (space > bestSpace) { bestSpace = space; bestD = d; }
            }
            state.aiPath = [];
            if (bestD) return bestD;

            // 4) 实在没有安全方向 → 随便走一个合法的
            return legal[Math.floor(rng() * legal.length)];
        }

        function aiDecide() {
            if (state.aiStrategy === 'greedy') return greedyMove();
            if (state.aiStrategy === 'smart') return smartMove();
            return state.direction;
        }

        /* ---------- 走一步 ---------- */
        function step() {
            if (state.status !== 'running') return { moved: false };

            let dir;
            if (state.aiStrategy !== 'off') {
                dir = aiDecide();
            } else {
                dir = state.nextDirection;
                if (OPPOSITE[dir] === state.direction) dir = state.direction;
            }
            state.direction = dir;

            const head = state.snake[0];
            const nh = { x: head.x + DIRS[dir].x, y: head.y + DIRS[dir].y };

            if (!inBounds(nh.x, nh.y)) {
                state.status = 'over';
                state.deathCause = 'wall';
                return { moved: false, died: 'wall' };
            }

            const eats = (nh.x === state.food.x && nh.y === state.food.y);
            const newSnake = eats
                ? [nh].concat(state.snake)
                : [nh].concat(state.snake.slice(0, state.snake.length - 1));

            for (let i = 1; i < newSnake.length; i++) {
                if (newSnake[i].x === nh.x && newSnake[i].y === nh.y) {
                    state.status = 'over';
                    state.deathCause = 'self';
                    return { moved: false, died: 'self' };
                }
            }

            state.snake = newSnake;
            if (eats) {
                state.score++;
                if (state.snake.length === gridSize * gridSize) {
                    state.status = 'win';
                    return { moved: true, ate: true, win: true };
                }
                placeFood();
            }
            return { moved: true, ate: eats };
        }

        function setDirection(d) {
            if (!DIRS[d]) return false;
            if (OPPOSITE[d] === state.direction) return false;
            state.nextDirection = d;
            return true;
        }

        reset();

        return {
            state: state,
            reset: reset,
            step: step,
            setDirection: setDirection,
            start: function () { if (state.status === 'ready') state.status = 'running'; },
            DIRS: DIRS
        };
    }

    return { createGame: createGame, DIRS: DIRS };
});
