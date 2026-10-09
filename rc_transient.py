# -*- coding: utf-8 -*-
"""
rc_transient.py —— RC 低通滤波器：方波瞬态响应 + 完整波特图

电路拓扑与 rc_lowpass.py 完全一致：
    V(input) -- R=1kΩ -- out -- C=1μF -- gnd

内容：
  A1. ±1V / 200Hz 方波瞬态分析（0→20ms，步长 2μs）
      - rc_transient.png      输入/输出波形 + 上升沿放大子图（实测时间常数 τ）
      - rc_transient_data.txt 波形数据（每 0.1ms 一行）
  A2. 完整波特图（幅频 + 相频，10Hz→100kHz，每十倍频程 20 点）
      - rc_bode.png
  A3. rc_table.txt            τ / fc 手算 vs 仿真、方波瞬态关键点

运行： $env:MPLBACKEND='Agg'; python rc_transient.py
"""

import unicodedata
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 0. 电路参数（与 rc_lowpass.py 一致）
# ============================================================
R = 1e3                         # 1 kΩ
C = 1e-6                        # 1 μF
TAU = R * C                     # 手算时间常数 = 1 ms
FC = 1 / (2 * np.pi * R * C)    # 手算截止频率 ≈ 159.1549 Hz

V_LOW = -1.0                    # 方波低电平
V_HIGH = 1.0                    # 方波高电平
F_SQ = 200.0                    # 方波频率 200 Hz
T_SQ = 1 / F_SQ                 # 周期 5 ms
T_HALF = T_SQ / 2               # 高低电平各 2.5 ms = 2.5τ
T_RISE = 1e-6                   # 上升/下降沿 1 μs（近似理想方波，远小于 τ）

print('=' * 70)
print('RC 低通滤波器：方波瞬态响应 + 完整波特图')
print(f'  R = {R:.0f} Ω , C = {C * 1e6:.0f} μF')
print(f'  手算 τ  = R·C = {TAU * 1e3:.4f} ms')
print(f'  手算 fc = 1/(2πRC) = {FC:.4f} Hz')
print(f'  方波 {F_SQ:.0f} Hz，周期 {T_SQ * 1e3:.1f} ms，高/低电平各 '
      f'{T_HALF * 1e3:.1f} ms = {T_HALF / TAU:.1f}τ')
print('=' * 70)

# ============================================================
# A1. 方波瞬态分析
# ============================================================
circuit = Circuit('RC Low-Pass Filter - Square Wave Transient')
# 节点名不能用 in（Python 关键字），沿用 rc_lowpass.py 的 input/out
circuit.PulseVoltageSource('in', 'input', circuit.gnd,
                           V_LOW @ u_V, V_HIGH @ u_V,
                           pulse_width=T_HALF @ u_s, period=T_SQ @ u_s,
                           delay_time=0 @ u_s,
                           rise_time=T_RISE @ u_s, fall_time=T_RISE @ u_s)
circuit.R('1', 'input', 'out', R @ u_Ohm)
circuit.C('1', 'out', circuit.gnd, C @ u_F)

simulator = circuit.simulator()
analysis = simulator.transient(step_time=2 @ u_us, end_time=20 @ u_ms)

time = np.array(analysis.time)          # 单位：s
vin = np.array(analysis['input'])       # 输入方波
vout = np.array(analysis['out'])        # 电容两端 = 输出
print(f'\n[A1] 瞬态仿真完成：{len(time)} 个数据点，'
      f't = {time[0] * 1e3:.3f} ms → {time[-1] * 1e3:.3f} ms')

# ---------- A1-1. 实测时间常数 τ ----------
# 找第一个上升沿：输入由低电平跨越 0V 的时刻（线性插值，精度优于采样步长）
cross_idx = np.where((vin[:-1] < 0) & (vin[1:] > 0))[0][0]
t_edge = float(np.interp(0.0, [vin[cross_idx], vin[cross_idx + 1]],
                         [time[cross_idx], time[cross_idx + 1]]))

# 初始值 Vstart：跳变前输出已稳定在低电平（取跳变前各点的平均值）
pre = time <= t_edge
V_start = float(np.mean(vout[pre]))
# 终值 Vfinal：电容充电的渐近终值 = 方波高电平
V_final = V_HIGH

# 三点法从仿真数据本身估计渐近终值（等间隔三点 x1,x2,x3 → A=(x1x3-x2²)/(x1+x3-2x2)）
def _sample(t_query):
    return float(np.interp(t_edge + t_query, time, vout))

x1, x2, x3 = _sample(0.5e-3), _sample(1.0e-3), _sample(1.5e-3)
V_final_est = (x1 * x3 - x2 ** 2) / (x1 + x3 - 2 * x2)

# 63.2% 交点法实测 τ
K_632 = 0.632
v_target = V_start + (V_final - V_start) * K_632
i_cross = int(np.argmax(vout >= v_target))
t_cross = float(np.interp(v_target, [vout[i_cross - 1], vout[i_cross]],
                          [time[i_cross - 1], time[i_cross]]))
tau_meas = t_cross - t_edge

# 对数线性拟合交叉校核：ln(Vfinal - vout) 对 t 的斜率 = -1/τ
mask = (time >= t_edge + 0.2 * TAU) & (time <= t_edge + 2.2 * TAU)
slope, _ = np.polyfit(time[mask], np.log(V_final - vout[mask]), 1)
tau_fit = -1.0 / slope

print(f'[A1] 上升沿时刻 t_edge = {t_edge * 1e6:.3f} μs')
print(f'[A1] 初始值 V_start = {V_start:.6f} V（跳变前输出稳定值）')
print(f'[A1] 终值   V_final = {V_final:.6f} V'
      f'（方波高电平；三点法由仿真数据估计 = {V_final_est:.6f} V）')
print(f'[A1] 63.2% 目标电平 = {v_target:.6f} V，在 t = {t_cross * 1e3:.6f} ms 达到')
print(f'[A1] ★ 实测时间常数 τ = {tau_meas * 1e3:.6f} ms  （手算 {TAU * 1e3:.6f} ms，'
      f'相对误差 {abs(tau_meas - TAU) / TAU * 100:.2f}%）')
print(f'[A1]   对数拟合校核 τ = {tau_fit * 1e3:.6f} ms')
print(f'[A1]   由实测 τ 反推 fc = 1/(2πτ) = {1 / (2 * np.pi * tau_meas):.4f} Hz')

# ---------- A1-2. 辅助校核：单阶跃仿真（用于 3τ 关键点） ----------
# 200Hz 方波高电平只有 2.5ms = 2.5τ，输出最高只到 +0.8357V（91.8% 摆幅），
# 永远到不了 3τ 的 95% 电平，所以另跑一次「单阶跃」仿真取 3τ 数据点。
step_circuit = Circuit('RC - Single Step (tau check)')
step_circuit.PulseVoltageSource('in', 'input', step_circuit.gnd,
                                V_LOW @ u_V, V_HIGH @ u_V,
                                pulse_width=50 @ u_ms, period=100 @ u_ms,
                                delay_time=0 @ u_s,
                                rise_time=T_RISE @ u_s, fall_time=T_RISE @ u_s)
step_circuit.R('1', 'input', 'out', R @ u_Ohm)
step_circuit.C('1', 'out', step_circuit.gnd, C @ u_F)
step_analysis = step_circuit.simulator().transient(step_time=2 @ u_us, end_time=10 @ u_ms)
t_step = np.array(step_analysis.time)
v_step = np.array(step_analysis['out'])
print('[A1] 辅助单阶跃仿真完成（供 3τ 校核，t = 0→10ms）')

# ---------- A1-3. 保存波形数据（每 0.1ms 一行） ----------
grid = np.arange(0, 20.0001, 0.1) * 1e-3
vin_g = np.interp(grid, time, vin)
vout_g = np.interp(grid, time, vout)
with open('rc_transient_data.txt', 'w', encoding='utf-8') as f:
    f.write('time(s) | vin(V) | vout(V)\n')
    for t_g, vi_g, vo_g in zip(grid, vin_g, vout_g):
        f.write(f'{t_g:.6f} | {vi_g:8.4f} | {vo_g:8.4f}\n')
print(f'[A1] 波形数据已写入 rc_transient_data.txt（{len(grid)} 行，每 0.1ms 一行）')

# ---------- A1-4. 画图：方波瞬态 + 上升沿放大 ----------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6),
                               gridspec_kw={'height_ratios': [1.15, 1.0]})
fig.suptitle('RC 低通滤波器 方波瞬态响应（R=1kΩ, C=1μF, τ=1ms, 方波 200Hz ±1V）',
             fontsize=13)

t_ms = time * 1e3
pct_list = [(0.632, '63.2%'), (0.865, '86.5%'), (0.950, '95%')]
level_v = {name: V_start + (V_final - V_start) * pct for pct, name in pct_list}

# --- 上：全局波形 ---
ax1.plot(t_ms, vin, color='tab:blue', lw=1.0, label='输入方波 $V_{in}$（±1V, 200Hz）')
ax1.plot(t_ms, vout, color='tab:red', lw=1.4, label='输出 $V_{out}$（电容电压）')
ax1.axvspan(0, 3, color='orange', alpha=0.12, zorder=0)
ax1.text(1.5, 1.34, '放大区间 0–3ms', color='darkorange', fontsize=9,
         ha='center', va='center')

for name in level_v:                              # ±63.2% / ±86.5% / ±95% 摆幅参考线
    lv = level_v[name]
    for sign in (+1, -1):
        ax1.axhline(sign * lv, color='gray', ls=':', lw=0.8, alpha=0.8, zorder=1)

for k in (1, 2, 3):                               # τ / 2τ / 3τ 参考线
    ax1.axvline(k * TAU * 1e3, color='green', ls='--', lw=1.0, alpha=0.85, zorder=1)
    ax1.text(k * TAU * 1e3, -1.43, f'{k}τ', color='green', fontsize=10,
             ha='center', va='bottom')

ax1.plot([t_cross * 1e3], [v_target], 'ko', ms=5, zorder=5)
ax1.annotate(f'实测 τ = {tau_meas * 1e3:.4f} ms（63.2% 交点法，详见下图放大）',
             xy=(t_cross * 1e3, v_target), xytext=(4.2, -1.40),
             arrowprops=dict(arrowstyle='->', color='black', lw=1.0),
             fontsize=9, ha='left', va='bottom',
             bbox=dict(boxstyle='round', fc='lightyellow', ec='gray', alpha=0.95), zorder=6)
ax1.text(5.2, 1.24, '方波高电平只有 2.5τ，输出最高只到 +0.8357V（91.8% 摆幅），\n'
                    '±95% 摆幅参考线（±0.900V）在方波激励下永远达不到',
         fontsize=8.5, color='purple', va='center', ha='left')

ax1.set_xlim(0, 20)
ax1.set_ylim(-1.45, 1.45)
ax1.set_xlabel('时间 (ms)')
ax1.set_ylabel('电压 (V)')
ax1.set_title('(a) 输入方波与输出波形（0→20ms），绿色虚线为 τ / 2τ / 3τ', fontsize=11)
ax1.grid(True, alpha=0.35)

# --- 下：上升沿放大（0–3ms） ---
zoom = time <= 3e-3
ax2.plot(time[zoom] * 1e3, vin[zoom], color='tab:blue', lw=1.0, label='输入方波 $V_{in}$')
ax2.plot(time[zoom] * 1e3, vout[zoom], color='tab:red', lw=1.8,
         label='输出 $V_{out}$（方波激励）')
step_zoom = t_step <= 3e-3
ax2.plot(t_step[step_zoom] * 1e3, v_step[step_zoom], color='gray', lw=1.3, ls='--',
         label='输出（单阶跃激励，辅助校核 3τ）')

for name in level_v:                              # 摆幅参考电平
    ax2.axhline(level_v[name], color='gray', ls=':', lw=0.9)
for k in (1, 2, 3):
    ax2.axvline(k * TAU * 1e3, color='green', ls='--', lw=1.0, alpha=0.85)

ax2.text(0.03, level_v['63.2%'] + 0.015, f'63.2% 摆幅  {level_v["63.2%"]:+.3f} V',
         fontsize=8.5, color='dimgray', ha='left', va='bottom')
ax2.text(0.03, level_v['86.5%'] + 0.015, f'86.5% 摆幅  {level_v["86.5%"]:+.3f} V',
         fontsize=8.5, color='dimgray', ha='left', va='bottom')
ax2.text(0.42, level_v['95%'] - 0.20, f'95% 摆幅  {level_v["95%"]:+.3f} V'
         f'（方波激励够不到）',
         fontsize=8.5, color='dimgray', ha='left', va='top')

for pct, name, tx in [(0.632, 'τ', 1.05), (0.865, '2τ', 1.83)]:   # 方波激励下真实可测的交点
    lv = V_start + (V_final - V_start) * pct
    i_c = int(np.argmax(vout >= lv))
    t_c = float(np.interp(lv, [vout[i_c - 1], vout[i_c]], [time[i_c - 1], time[i_c]]))
    ax2.plot([t_c * 1e3], [lv], 'o', color='black', ms=6, zorder=5)
    ax2.annotate(f'{name} 交点  ({t_c * 1e3:.4f} ms, {lv:+.3f} V)',
                 xy=(t_c * 1e3, lv), xytext=(tx, lv - 0.61),
                 fontsize=9, ha='left', va='center',
                 arrowprops=dict(arrowstyle='->', color='black', lw=1.0), zorder=6)

lv95 = V_start + (V_final - V_start) * 0.95        # 只有单阶跃激励才能达到
t95 = float(np.interp(lv95, v_step, t_step))
ax2.plot([t95 * 1e3], [lv95], 's', color='dimgray', ms=6, zorder=5)
ax2.annotate(f'3τ 交点  ({t95 * 1e3:.4f} ms, {lv95:+.3f} V)',
             xy=(t95 * 1e3, lv95), xytext=(1.90, 1.13),
             fontsize=9, color='dimgray', ha='left', va='bottom',
             arrowprops=dict(arrowstyle='->', color='dimgray', lw=1.0), zorder=6)

ax2.axvspan(2.5, 3.0, color='red', alpha=0.07, zorder=0)
ax2.text(2.76, 1.20, '2.5ms 后输入已翻负', fontsize=8, color='red', ha='center',
         va='center')
ax2.text(0.02, -1.58,
         '摆幅参考线（灰点线）：63.2% = +0.2640 V，86.5% = +0.7292 V，95% = +0.9004 V\n'
         f'实测 τ = {tau_meas * 1e3:.4f} ms（63.2% 交点法）；对数拟合 τ = {tau_fit * 1e3:.4f} ms；'
         f'三点法终值 V∞ = {V_final_est:.4f} V',
         fontsize=8.5, va='bottom', ha='left',
         bbox=dict(boxstyle='round', fc='lightyellow', ec='gray', alpha=0.95), zorder=6)

ax2.set_xlim(0, 3)
ax2.set_ylim(-1.60, 1.32)
ax2.set_xlabel('时间 (ms)（第一个上升沿 t≈0 之后）')
ax2.set_ylabel('电压 (V)')
ax2.set_title('(b) 上升沿放大 0–3ms：实测时间常数 τ 与 τ / 2τ / 3τ 交点', fontsize=11)
ax2.grid(True, alpha=0.35)

# 上图图例放到坐标区上方，避免压住波形
h1, l1 = ax1.get_legend_handles_labels()
proxy = [Line2D([], [], color='gray', ls=':', lw=1.0,
                label='±63.2% / ±86.5% / ±95% 摆幅参考线 (±0.264 / ±0.729 / ±0.900 V)'),
         Line2D([], [], color='green', ls='--', lw=1.0, label='τ / 2τ / 3τ 参考线')]
ax1.legend(h1 + proxy, l1 + [p.get_label() for p in proxy],
           loc='lower left', bbox_to_anchor=(0, 1.02), ncol=4, fontsize=8.5,
           frameon=False)
ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.155), ncol=3, fontsize=8.5,
           frameon=False)

fig.tight_layout(rect=(0, 0, 1, 0.955))
fig.savefig('rc_transient.png', dpi=150)
print('[A1] 已生成 rc_transient.png')

# ============================================================
# A2. 完整波特图（幅频 + 相频）
# ============================================================
ac_circuit = Circuit('RC Low-Pass Filter - AC Sweep')
ac_circuit.V('input', 'input', ac_circuit.gnd, 'DC 0V AC 1V')
ac_circuit.R('1', 'input', 'out', R @ u_Ohm)
ac_circuit.C('1', 'out', ac_circuit.gnd, C @ u_F)

ac = ac_circuit.simulator().ac(start_frequency=10 @ u_Hz, stop_frequency=100 @ u_kHz,
                               number_of_points=20, variation='dec')
freq = np.array(ac.frequency)
H = np.array(ac['out'])
mag_db = 20 * np.log10(np.abs(H))
phase_deg = np.angle(H, deg=True)

# 理论曲线
theory_mag_db = 20 * np.log10(1 / np.sqrt(1 + (2 * np.pi * freq * R * C) ** 2))
theory_phase_deg = -np.degrees(np.arctan(2 * np.pi * freq * R * C))

# 从 AC 仿真数据测 fc：幅值降到 0.7071 倍（-3dB）时的频率，log-log 插值
target = 1 / np.sqrt(2)
i_fc = int(np.where(np.abs(H) <= target)[0][0])
lf1, lf2 = np.log10(freq[i_fc - 1]), np.log10(freq[i_fc])
lm1, lm2 = np.log10(np.abs(H[i_fc - 1])), np.log10(np.abs(H[i_fc]))
fc_meas = 10 ** (lf1 + (np.log10(target) - lm1) * (lf2 - lf1) / (lm2 - lm1))
mag_at_fc = float(np.interp(np.log10(fc_meas), np.log10(freq), mag_db))
phase_at_fc = float(np.interp(np.log10(fc_meas), np.log10(freq), phase_deg))

print(f'\n[A2] AC 扫频完成：{len(freq)} 个频点，'
      f'{freq[0]:.1f} Hz → {freq[-1] / 1e3:.1f} kHz')
print(f'[A2] ★ 实测截止频率 fc = {fc_meas:.4f} Hz  （手算 {FC:.4f} Hz，'
      f'相对误差 {abs(fc_meas - FC) / FC * 100:.2f}%）')
print(f'[A2]   该点增益 = {mag_at_fc:.4f} dB，相位 = {phase_at_fc:.4f}°')
print(f'[A2]   由实测 fc 反推 τ = 1/(2πfc) = {1 / (2 * np.pi * fc_meas) * 1e3:.6f} ms')

fig2, (bx1, bx2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

bx1.semilogx(freq, mag_db, 'o-', color='tab:blue', ms=4, lw=1.2, label='PySpice 仿真')
bx1.semilogx(freq, theory_mag_db, 'r--', lw=1.4,
             label=r'理论曲线 $20\lg\frac{1}{\sqrt{1+(2\pi fRC)^2}}$')
bx1.axhline(-3.0103, color='green', ls=':', lw=1.2)
bx1.text(10.6, -2.3, '-3dB 线（-3.01dB）', color='green', fontsize=9,
         ha='left', va='bottom')
bx1.axvline(fc_meas, color='purple', ls='--', lw=1.3)
bx1.plot([fc_meas], [mag_at_fc], 'k*', ms=14, zorder=5)
bx1.annotate(f'fc ≈ {FC:.2f} Hz（手算）\n实测 fc = {fc_meas:.2f} Hz\n'
             f'增益 = {mag_at_fc:.2f} dB',
             xy=(fc_meas, mag_at_fc), xytext=(3200, 1.0),
             arrowprops=dict(arrowstyle='->', color='purple', lw=1.2),
             fontsize=10, ha='left', va='top',
             bbox=dict(boxstyle='round', fc='lavender', ec='purple', alpha=0.95), zorder=6)
bx1.set_ylabel('幅值 $20\\lg|H|$ (dB)')
bx1.set_title('(a) 幅频特性：仿真 vs 理论，标注 -3dB 线与 fc', fontsize=11)
bx1.set_ylim(-42, 4)
bx1.grid(True, which='both', alpha=0.35)
bx1.legend(loc='lower left', bbox_to_anchor=(0, 0.02), fontsize=9, framealpha=0.9)

bx2.semilogx(freq, phase_deg, 'o-', color='tab:orange', ms=4, lw=1.2, label='PySpice 仿真')
bx2.semilogx(freq, theory_phase_deg, 'r--', lw=1.4,
             label=r'理论曲线 $-\arctan(2\pi fRC)$')
bx2.axhline(-45, color='green', ls=':', lw=1.2)
bx2.text(10.6, -43.5, '-45° 线', color='green', fontsize=9, ha='left', va='bottom')
bx2.axvline(fc_meas, color='purple', ls='--', lw=1.3)
bx2.plot([fc_meas], [phase_at_fc], 'k*', ms=14, zorder=5)
bx2.annotate(f'fc 处相位 = {phase_at_fc:.2f}°（理论 -45°）',
             xy=(fc_meas, phase_at_fc), xytext=(2500, -66),
             arrowprops=dict(arrowstyle='->', color='purple', lw=1.2),
             fontsize=10, ha='left', va='center',
             bbox=dict(boxstyle='round', fc='lavender', ec='purple', alpha=0.95), zorder=6)
bx2.set_xlabel('频率 (Hz)')
bx2.set_ylabel('相位 (度)')
bx2.set_title('(b) 相频特性：仿真 vs 理论，标注 fc 处的 -45°', fontsize=11)
bx2.set_ylim(-95, 5)
bx2.grid(True, which='both', alpha=0.35)
bx2.legend(loc='lower left', fontsize=9, framealpha=0.9)

fig2.suptitle('RC 低通滤波器 波特图（R=1kΩ, C=1μF, fc≈159.15Hz）', fontsize=13)
fig2.tight_layout(rect=(0, 0, 1, 0.955))
fig2.savefig('rc_bode.png', dpi=150)
print('[A2] 已生成 rc_bode.png')

# ============================================================
# A3. rc_table.txt（等宽纯文本，中文按 2 个字符宽度对齐）
# ============================================================
def disp_width(text):
    return sum(2 if unicodedata.east_asian_width(ch) in 'WF' else 1 for ch in text)


def cell(text, width, align='<'):
    pad = ' ' * max(0, width - disp_width(text))
    return text + pad if align == '<' else pad + text


def row(cells, widths, aligns):
    return ' | '.join(cell(c, w, a) for c, w, a in zip(cells, widths, aligns))


def err_str(sim, hand):
    return f'{abs(sim - hand) / abs(hand) * 100:.2f}%'


lines = []
lines.append('RC 低通滤波器 —— 理论值（手算）vs 仿真值 对比表')
lines.append('（数据由 rc_transient.py 实际运行生成；R=1kΩ, C=1μF）')
lines.append('')
lines.append('表一、τ 与 fc 的手算 vs 仿真')
lines.append('-' * 64)

W1, A1 = [12, 13, 13, 10], ['<', '>', '>', '>']
lines.append(row(['项目', '手算值', '仿真测量值', '相对误差'], W1, A1))
lines.append('-' * 64)
lines.append(row(['τ (ms)', f'{TAU * 1e3:.4f}', f'{tau_meas * 1e3:.4f}',
                  err_str(tau_meas, TAU)], W1, A1))
lines.append(row(['fc (Hz)', f'{FC:.4f}', f'{fc_meas:.4f}',
                  err_str(fc_meas, FC)], W1, A1))
lines.append('-' * 64)
lines.append(f'注 1：τ 的仿真测量值由 200Hz 方波第一个上升沿后的 63.2% 交点实测'
             f'（对数线性拟合校核值 {tau_fit * 1e3:.4f} ms）；')
lines.append(f'注 2：fc 的仿真测量值由 AC 扫频数据中幅值降到 0.7071 倍处 log-log 插值实测，'
             f'该点增益 {mag_at_fc:.4f} dB、相位 {phase_at_fc:.4f}°。')

lines.append('')
lines.append('表二、方波瞬态关键点（200Hz ±1V 方波，第一个上升沿之后）')
lines.append('-' * 64)
W2, A2 = [19, 11, 11, 8], ['<', '>', '>', '>']
lines.append(row(['时间点', '理论值(V)', '仿真值(V)', '误差'], W2, A2))
lines.append('-' * 64)

t_keys = [(1, 'τ   (1.000 ms)'), (2, '2τ  (2.000 ms)'), (3, '3τ  (3.000 ms)')]
rows_t2 = []
max_dev = 0.0
for k, label in t_keys:
    t_k = k * TAU
    v_theory = V_final - (V_final - V_start) * np.exp(-t_k / TAU)
    if k <= 2:
        v_sim = float(np.interp(t_edge + t_k, time, vout))      # 方波激励下可直接取到
    else:
        v_sim = float(np.interp(t_edge + t_k, t_step, v_step))  # 方波高电平只有 2.5τ
    max_dev = max(max_dev, abs(v_sim - v_theory))
    rows_t2.append((label, v_theory, v_sim))
    lines.append(row([label, f'{v_theory:.4f}', f'{v_sim:.4f}',
                      f'{abs(v_sim - v_theory) / abs(v_theory) * 100:.2f}%'], W2, A2))
lines.append('-' * 64)
lines.append(f'理论公式：v(t) = Vfinal - (Vfinal - Vstart)·exp(-t/τ)，'
             f'Vstart = {V_start:.4f} V，Vfinal = {V_final:.4f} V')
lines.append(f'说明：200Hz 方波高电平仅 2.5ms = 2.5τ，输出最高只到 '
             f'{np.interp(t_edge + 2.5e-3, time, vout):.4f} V（91.8% 摆幅），')
lines.append('      3τ 对应的 95% 摆幅电平（+0.9004 V）在方波激励下永远达不到，')
lines.append('      故 3τ 一行的仿真值取自同参数的单阶跃辅助仿真（真实仿真数据，非外推）。')
lines.append(f'误差说明：三行误差均为 0.00% 是 4 位小数四舍五入的结果，'
             f'实测最大绝对偏差 {max_dev:.2e} V。')

with open('rc_table.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('[A3] 已生成 rc_table.txt')
print()
print('\n'.join(lines))
print()

plt.show()
