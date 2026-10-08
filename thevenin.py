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
# 第三部分：接不同负载，对比原电路和等效电路的输出电压
# ============================================================
loads = [100, 220, 470, 1000, 2000, 4700, 10000]  # 负载电阻（Ω）
v_orig = []
v_equiv = []

for RL in loads:
    # 原电路 + 负载
    c1 = Circuit('Original with Load')
    c1.V('1', 'input', c1.gnd, 5 @ u_V)
    c1.R('1', 'input', 'out', 1 @ u_kOhm)
    c1.R('2', 'out', c1.gnd, 2 @ u_kOhm)
    c1.R('L', 'out', c1.gnd, RL @ u_Ohm)
    a1 = c1.simulator().operating_point()
    v_orig.append(float(a1['out'][0]))

    # 等效电路 + 负载
    c2 = Circuit('Thevenin with Load')
    c2.V('1', 'input', c2.gnd, Vth @ u_V)
    c2.R('th', 'input', 'out', Rth @ u_Ohm)
    c2.R('L', 'out', c2.gnd, RL @ u_Ohm)
    a2 = c2.simulator().operating_point()
    v_equiv.append(float(a2['out'][0]))

# ============================================================
# 第四部分：打印对比表
# ============================================================
print("\n负载(Ω) | 原电路(V) | 等效电路(V) | 误差")
print("-" * 55)
for i, RL in enumerate(loads):
    err = abs(v_orig[i] - v_equiv[i]) / v_orig[i] * 100
    print(f"{RL:8.0f} | {v_orig[i]:9.4f} | {v_equiv[i]:10.4f} | {err:5.2f}%")

# ============================================================
# 第五部分：画图
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