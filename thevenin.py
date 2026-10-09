import unicodedata
import matplotlib.pyplot as plt
import numpy as np
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 第一部分：原电路（R1=1kΩ, R2=2kΩ, Vi=5V）
# ============================================================
circuit1 = Circuit('Original Circuit')
circuit1.V('1', 'input', circuit1.gnd, 5 @ u_V)      # 5V 直流
circuit1.R('1', 'input', 'out', 1 @ u_kOhm)          # R1 = 1kΩ
circuit1.R('2', 'out', circuit1.gnd, 2 @ u_kOhm)  # R2 = 2kΩ

sim1 = circuit1.simulator()
analysis1 = sim1.operating_point()
v_out1 = float(analysis1['out'][0])
print(f"原电路开路电压 Vth = {v_out1:.4f} V")

# ============================================================
# 第二部分：等效电路（Vth=3.333V, Rth=667Ω）
# ============================================================
Vth = 10/3       # 3.333V
Rth = 2/3 * 1e3  # 667Ω

circuit2 = Circuit('Thevenin Equivalent')
circuit2.V('1', 'input', circuit2.gnd, Vth @ u_V)     # 戴维南电压源
circuit2.R('th', 'input', 'out', Rth @ u_Ohm)         # 戴维南电阻

sim2 = circuit2.simulator()
analysis2 = sim2.operating_point()
v_out2 = float(analysis2['out'][0])
print(f"等效电路开路电压 Vth = {v_out2:.4f} V")

# ============================================================
# 第三部分（新增）：端口短路电流 I_sc
#   用 0V 电压源当电流表：0V 源串在端口与地之间，端口即被短路，
#   该 0V 源的支路电流就是短路电流 I_sc（PySpice 中读取
#   analysis.branches['v<源名>']，源名 sc → 支路名 vsc）。
#   R2 被 0V 源短路，原电路 Isc 应等于 5V/1kΩ = 5mA。
# ============================================================
Isc_hand = Vth / Rth                       # 手算 Isc = Vth/Rth = 5 mA
print(f"\n手算短路电流 Isc = Vth / Rth = {Vth:.4f} / {Rth:.4f} = "
      f"{Isc_hand * 1e3:.4f} mA")

# --- 原电路端口短路 ---
c_sc1 = Circuit('Original - Short Circuit')
c_sc1.V('1', 'input', c_sc1.gnd, 5 @ u_V)
c_sc1.R('1', 'input', 'out', 1 @ u_kOhm)
c_sc1.R('2', 'out', c_sc1.gnd, 2 @ u_kOhm)
c_sc1.V('sc', 'out', c_sc1.gnd, 0 @ u_V)          # 0V 电流表（端口短路）
a_sc1 = c_sc1.simulator().operating_point()
i_sc1 = float(np.array(a_sc1.branches['vsc'])[0])
print(f"原电路短路电流 Isc（0V 源实测） = {i_sc1 * 1e3:.4f} mA")

# --- 等效电路端口短路 ---
c_sc2 = Circuit('Thevenin Equivalent - Short Circuit')
c_sc2.V('1', 'input', c_sc2.gnd, Vth @ u_V)
c_sc2.R('th', 'input', 'out', Rth @ u_Ohm)
c_sc2.V('sc', 'out', c_sc2.gnd, 0 @ u_V)          # 0V 电流表（端口短路）
a_sc2 = c_sc2.simulator().operating_point()
i_sc2 = float(np.array(a_sc2.branches['vsc'])[0])
print(f"等效电路短路电流 Isc（0V 源实测） = {i_sc2 * 1e3:.4f} mA")

# ============================================================
# 第四部分：接不同负载，对比原电路和等效电路的输出电压与电流
#   电流同样用 0V 电压源当电流表：串在端口与负载之间，
#   支路名 vsense，其电流即负载电流 I_L。
# ============================================================
loads = [100, 220, 470, 1000, 2000, 4700, 10000]  # 负载电阻（Ω）
v_orig = []
v_equiv = []
i_orig = []
i_equiv = []

for RL in loads:
    # 原电路 + 负载
    c1 = Circuit('Original with Load')
    c1.V('1', 'input', c1.gnd, 5 @ u_V)
    c1.R('1', 'input', 'out', 1 @ u_kOhm)
    c1.R('2', 'out', c1.gnd, 2 @ u_kOhm)
    c1.V('sense', 'out', 'outL', 0 @ u_V)          # 0V 电流表
    c1.R('L', 'outL', c1.gnd, RL @ u_Ohm)
    a1 = c1.simulator().operating_point()
    v_orig.append(float(a1['out'][0]))
    i_orig.append(float(np.array(a1.branches['vsense'])[0]))

    # 等效电路 + 负载
    c2 = Circuit('Thevenin with Load')
    c2.V('1', 'input', c2.gnd, Vth @ u_V)
    c2.R('th', 'input', 'out', Rth @ u_Ohm)
    c2.V('sense', 'out', 'outL', 0 @ u_V)          # 0V 电流表
    c2.R('L', 'outL', c2.gnd, RL @ u_Ohm)
    a2 = c2.simulator().operating_point()
    v_equiv.append(float(a2['out'][0]))
    i_equiv.append(float(np.array(a2.branches['vsense'])[0]))

# ============================================================
# 第五部分：打印对比表
# ============================================================
print("\n负载(Ω) | 原电路(V) | 等效电路(V) | 误差")
print("-" * 55)
for i, RL in enumerate(loads):
    err = abs(v_orig[i] - v_equiv[i]) / v_orig[i] * 100
    print(f"{RL:8.0f} | {v_orig[i]:9.4f} | {v_equiv[i]:10.4f} | {err:5.2f}%")

print("\n负载(Ω) | 原电路 I(mA) | 等效电路 I(mA) | 误差")
print("-" * 55)
for i, RL in enumerate(loads):
    err = abs(i_orig[i] - i_equiv[i]) / i_orig[i] * 100
    print(f"{RL:8.0f} | {i_orig[i] * 1e3:13.4f} | {i_equiv[i] * 1e3:14.4f} | {err:5.2f}%")

# ============================================================
# 第六部分（新增）：写入 thevenin_table.txt（三张表）
# ============================================================
def disp_width(text):
    return sum(2 if unicodedata.east_asian_width(ch) in 'WF' else 1 for ch in text)


def cell(text, width, align='<'):
    pad = ' ' * max(0, width - disp_width(text))
    return text + pad if align == '<' else pad + text


def row(cells, widths, aligns):
    return ' | '.join(cell(c, w, a) for c, w, a in zip(cells, widths, aligns))


def err_pct(sim, hand):
    return f'{abs(sim - hand) / abs(hand) * 100:.2f}%'


lines = []
lines.append('戴维南定理验证 —— 手算值 vs 仿真值 对比表')
lines.append('（原电路：Vi=5V, R1=1kΩ(input→out), R2=2kΩ(out→gnd)；'
             '等效电路：Vth=3.3333V, Rth=666.6667Ω）')
lines.append('（数据由 thevenin.py 实际运行生成；电流均由串在支路里的 0V 电压源实测）')
lines.append('')

# ---- 表一：开路电压 ----
lines.append('表一、开路电压 V_oc')
lines.append('-' * 66)
W1, A1 = [10, 11, 13, 15, 9], ['<', '>', '>', '>', '>']
lines.append(row(['项目', '手算值', '原电路仿真', '等效电路仿真', '误差'], W1, A1))
lines.append('-' * 66)
err_voc = max(abs(v_out1 - Vth) / Vth, abs(v_out2 - Vth) / Vth)
lines.append(row(['V_oc (V)', f'{Vth:.4f}', f'{v_out1:.4f}', f'{v_out2:.4f}',
                  f'{err_voc * 100:.2f}%'], W1, A1))
lines.append('-' * 66)
lines.append('手算：V_oc = Vi·R2/(R1+R2) = 5 × 2000/(1000+2000) = 3.3333 V')
lines.append('误差列取「原电路仿真值」「等效电路仿真值」相对手算值的较大者。')

# ---- 表二：短路电流 ----
lines.append('')
lines.append('表二、短路电流 I_sc（端口用 0V 电压源短接，读该源支路电流）')
lines.append('-' * 66)
W2, A2 = [10, 11, 13, 15, 9], ['<', '>', '>', '>', '>']
lines.append(row(['项目', '手算值', '原电路仿真', '等效电路仿真', '误差'], W2, A2))
lines.append('-' * 66)
err_isc = max(abs(i_sc1 - Isc_hand) / Isc_hand, abs(i_sc2 - Isc_hand) / Isc_hand)
lines.append(row(['I_sc (mA)', f'{Isc_hand * 1e3:.4f}', f'{i_sc1 * 1e3:.4f}',
                  f'{i_sc2 * 1e3:.4f}', f'{err_isc * 100:.2f}%'], W2, A2))
lines.append('-' * 66)
lines.append('手算：I_sc = Vth/Rth = 3.3333/666.6667 = 5.0000 mA')
lines.append('      也可直接看原电路：端口短路后 R2 被旁路，I_sc = Vi/R1 = 5V/1kΩ = 5 mA')
lines.append('误差列取「原电路仿真值」「等效电路仿真值」相对手算值的较大者。')

# ---- 表三：接负载验证 ----
lines.append('')
lines.append('表三、接负载验证（电压 + 电流）')
lines.append('-' * 92)
W3 = [9, 12, 12, 10, 13, 13, 10]
A3 = ['>', '>', '>', '>', '>', '>', '>']
lines.append(row(['RL(Ω)', '原电路 V(V)', '等效 V(V)', '电压误差',
                  '原电路 I(mA)', '等效 I(mA)', '电流误差'], W3, A3))
lines.append('-' * 92)
max_verr = max_ierr = 0.0
for i, RL in enumerate(loads):
    verr = abs(v_orig[i] - v_equiv[i]) / v_orig[i]
    ierr = abs(i_orig[i] - i_equiv[i]) / i_orig[i]
    max_verr = max(max_verr, verr)
    max_ierr = max(max_ierr, ierr)
    lines.append(row([f'{RL:.0f}', f'{v_orig[i]:.4f}', f'{v_equiv[i]:.4f}',
                      f'{verr * 100:.2f}%', f'{i_orig[i] * 1e3:.4f}',
                      f'{i_equiv[i] * 1e3:.4f}', f'{ierr * 100:.2f}%'], W3, A3))
lines.append('-' * 92)
lines.append('误差 = |原电路 - 等效电路| / 原电路；电流由串在负载支路的 0V 电压源实测。')
lines.append(f'各负载下电压最大相对误差 {max_verr * 100:.2f}%，'
             f'电流最大相对误差 {max_ierr * 100:.2f}%。')
lines.append('说明：电压误差均为 0.00% 是 4 位小数四舍五入的结果——'
             f'实测最大绝对电压偏差 {max(abs(a - b) for a, b in zip(v_orig, v_equiv)):.2e} V，'
             f'最大绝对电流偏差 {max(abs(a - b) for a, b in zip(i_orig, i_equiv)):.2e} A。')

with open('thevenin_table.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('\n已生成 thevenin_table.txt（表格内容见该文件）')

# 说明：上面三张表已经完整写入 thevenin_table.txt。
# 这里不再把表格重复打印到控制台——Windows 控制台默认是 GBK 编码，
# 打印含中文与特殊符号的长文本会抛 UnicodeEncodeError 导致脚本以非 0 退出
# （表格文件本身是 UTF-8，不受影响）。需要看表就直接打开该文件。

# ============================================================
# 第七部分：画图
# ============================================================
plt.figure(figsize=(10, 6))
plt.semilogx(loads, v_orig, 'bo-', label='原电路')
plt.semilogx(loads, v_equiv, 'r--', label='戴维南等效电路')
plt.xlabel('负载电阻 (Ω)')
plt.ylabel('输出电压 (V)')
plt.title('戴维南定理验证：原电路 vs 等效电路')
plt.legend()
plt.grid(True)
plt.savefig('thevenin.png')
plt.show()

# 新增：负载电流对比
plt.figure(figsize=(10, 6))
plt.semilogx(loads, np.array(i_orig) * 1e3, 'bo-', label='原电路')
plt.semilogx(loads, np.array(i_equiv) * 1e3, 'r--', label='戴维南等效电路')
plt.xlabel('负载电阻 (Ω)')
plt.ylabel('负载电流 $I_L$ (mA)')
plt.title('戴维南定理验证：原电路 vs 等效电路（负载电流）')
plt.legend()
plt.grid(True)
plt.savefig('thevenin_load_current.png')
print('已生成 thevenin.png 与 thevenin_load_current.png')
plt.show()
