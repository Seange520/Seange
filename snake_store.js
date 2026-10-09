/* ============================================================
 * snake_store.js —— 贪吃蛇的本地存储层（最高分 / 局数 / 最近战绩 / 主题）
 *
 * 单独抽出来的原因：数据逻辑和界面逻辑分开，既好测试也好讲清楚。
 * 浏览器里挂到 window.SnakeStore；Node 里可以 require 做单元测试
 * （测试时会传入一个内存版的 storage，不依赖浏览器）。
 * ============================================================ */
(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.SnakeStore = factory();
    }
})(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const KEYS = {
        highScore: 'snake.highScore',
        gamesPlayed: 'snake.gamesPlayed',
        history: 'snake.history',
        theme: 'snake.theme'
    };
    const HISTORY_LIMIT = 10;   // 任务要求：记录最近 10 局

    function createStore(storage) {
        const s = storage;

        function readInt(key, fallback) {
            const raw = s.getItem(key);
            if (raw === null) return fallback;
            const n = parseInt(raw, 10);
            return Number.isFinite(n) ? n : fallback;
        }

        function write(key, value) {
            try { s.setItem(key, String(value)); } catch (e) { /* 隐私模式等情况下静默失败 */ }
        }

        return {
            KEYS: KEYS,
            HISTORY_LIMIT: HISTORY_LIMIT,

            getHighScore: function () { return readInt(KEYS.highScore, 0); },

            getGamesPlayed: function () { return readInt(KEYS.gamesPlayed, 0); },

            getTheme: function () {
                const t = s.getItem(KEYS.theme);
                return (t === 'dark' || t === 'light') ? t : 'light';
            },

            setTheme: function (t) { write(KEYS.theme, t); },

            // 只读的战绩列表（最近 10 局，最新的在前）
            getHistory: function () {
                const raw = s.getItem(KEYS.history);
                if (!raw) return [];
                try {
                    const arr = JSON.parse(raw);
                    return Array.isArray(arr) ? arr.slice(0, HISTORY_LIMIT) : [];
                } catch (e) {
                    return [];
                }
            },

            /* 一局结束：更新最高分、局数、并追加一条战绩。
               返回 { isNewRecord, highScore, gamesPlayed } 供界面做提示。 */
            recordGame: function (score, cause, durationMs) {
                const prevHigh = readInt(KEYS.highScore, 0);
                const isNewRecord = score > prevHigh;
                if (isNewRecord) write(KEYS.highScore, score);

                const games = readInt(KEYS.gamesPlayed, 0) + 1;
                write(KEYS.gamesPlayed, games);

                const history = this.getHistory();
                history.unshift({
                    score: score,
                    cause: cause || 'unknown',      // wall | self | win
                    at: Date.now(),
                    durationMs: durationMs || 0
                });
                try {
                    s.setItem(KEYS.history, JSON.stringify(history.slice(0, HISTORY_LIMIT)));
                } catch (e) { /* 忽略写入失败 */ }

                return { isNewRecord: isNewRecord, highScore: Math.max(score, prevHigh), gamesPlayed: games };
            },

            /* 「重置」按钮用：清空最高分、局数与战绩。
               注意与「重新开始」的区别——重新开始只重开一局，不动纪录。 */
            resetAll: function () {
                [KEYS.highScore, KEYS.gamesPlayed, KEYS.history].forEach(function (k) {
                    try { s.removeItem(k); } catch (e) { /* 忽略 */ }
                });
            }
        };
    }

    // 浏览器环境下自动建一个基于 localStorage 的实例
    const auto = (typeof localStorage !== 'undefined') ? createStore(localStorage) : null;

    return { createStore: createStore, KEYS: KEYS, HISTORY_LIMIT: HISTORY_LIMIT, instance: auto };
});
