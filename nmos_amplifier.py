import matplotlib.pyplot as plt
import numpy as np
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 电路参数
# ============================================================
VDD = 5
Rg1 = 60e3
Rg2 = 40e3
Rd = 2e3
K = 0.8e-3      # 0.8 mA/V²
Vth = 1
lam = 0.02

# ============================================================
# 第一部分：直流工作点分析
# ============================================================
circuit_dc = Circuit('NMOS Common Source - DC')

# 电源
circuit_dc.V('DD', 'vdd', circuit_dc.gnd, VDD @ u_V)

# 偏置电阻
circuit_dc.R('g1', 'vdd', 'g', Rg1 @ u_Ohm)
circuit_dc.R('g2', 'g', circuit_dc.gnd, Rg2 @ u_Ohm)

# 漏极负载
circuit_dc.R('d', 'vdd', 'd', Rd @ u_Ohm)

# NMOS 模型
circuit_dc.model('nmos_model', 'NMOS', level=1, KP=K, VTO=Vth, LAMBDA=lam)

# NMOS 管：漏极 d，栅极 g，源极 s（接地），衬底 b（接地）
circuit_dc.MOSFET('1', 'd', 'g', circuit_dc.gnd, circuit_dc.gnd, model='nmos_model')

# 运行直流分析
sim_dc = circuit_dc.simulator()
analysis_dc = sim_dc.operating_point()

V_G = float(analysis_dc['g'][0])
V_D = float(analysis_dc['d'][0])
V_S = 0.0
V_GS = V_G - V_S
V_DS = V_D - V_S

print("=" * 50)
print("直流工作点分析")
print("=" * 50)
print(f"栅极电压 V_G = {V_G:.4f} V")
print(f"漏极电压 V_D = {V_D:.4f} V")
print(f"栅源电压 V_GS = {V_GS:.4f} V")
print(f"漏源电压 V_DS = {V_DS:.4f} V")

# 理论值
I_D_theory = K / 2 * (V_GS - Vth) ** 2
V_D_theory = VDD - I_D_theory * Rd
print(f"\n理论值：")
print(f"I_D (理论) = {I_D_theory * 1000:.4f} mA")
print(f"V_DS (理论) = {V_D_theory:.4f} V")

# ============================================================
# 第二部分：瞬态分析（输入正弦波，看输出波形）
# ============================================================
circuit_ac = Circuit('NMOS Common Source - AC')

# 电源
circuit_ac.V('DD', 'vdd', circuit_ac.gnd, VDD @ u_V)

# 输入交流源
circuit_ac.SinusoidalVoltageSource('in', 'vi', circuit_ac.gnd,
                                   amplitude=10 @ u_mV, frequency=1 @ u_kHz)

# 耦合电容
circuit_ac.C('b1', 'vi', 'g', 1 @ u_uF)

# 偏置电阻
circuit_ac.R('g1', 'vdd', 'g', Rg1 @ u_Ohm)
circuit_ac.R('g2', 'g', circuit_ac.gnd, Rg2 @ u_Ohm)

# 漏极负载
circuit_ac.R('d', 'vdd', 'd', Rd @ u_Ohm)

# NMOS 模型
circuit_ac.model('nmos_model', 'NMOS', level=1, KP=K, VTO=Vth, LAMBDA=lam)
circuit_ac.MOSFET('1', 'd', 'g', circuit_ac.gnd, circuit_ac.gnd, model='nmos_model')

# 运行瞬态分析：0 到 5ms
sim_ac = circuit_ac.simulator()
analysis_ac = sim_ac.transient(step_time=1 @ u_us, end_time=5 @ u_ms)

# 提取波形
time = np.array(analysis_ac.time)
v_out = np.array(analysis_ac['d'])
v_in = np.array(analysis_ac['vi'])

# 计算增益（取稳定后的峰值，3ms 到 5ms）
mask = (time >= 3e-3) & (time <= 5e-3)
v_out_stable = v_out[mask]
v_in_stable = v_in[mask]

gain = (v_out_stable.max() - v_out_stable.min()) / (v_in_stable.max() - v_in_stable.min())

print("\n" + "=" * 50)
print("瞬态分析")
print("=" * 50)
print(f"输入信号幅值: 10 mV")
print(f"输出信号幅值: {(v_out_stable.max() - v_out_stable.min()) / 2 * 1000:.2f} mV")
print(f"实测增益 |Av| = {abs(gain):.4f}")

# 理论增益
gm = K * (V_GS - Vth)
ro = 1 / (lam * I_D_theory)
Rout = (Rd * ro) / (Rd + ro)
Av_theory = gm * Rout
print(f"\n理论增益 |Av| = {Av_theory:.4f}")

# ============================================================
# 第三部分：画图（交流分量）
# ============================================================
v_out_ac = v_out - np.mean(v_out)
v_in_ac = v_in - np.mean(v_in)

plt.figure(figsize=(12, 6))
plt.plot(time * 1000, v_in_ac * 1000, 'b-', label='输入 vi (mV)')
plt.plot(time * 1000, v_out_ac * 1000, 'r-', label='输出 vo (mV)')
plt.xlabel('时间 (ms)')
plt.ylabel('电压 (mV)')
plt.title('NMOS 共源放大电路 瞬态分析（交流分量）')
plt.legend()
plt.grid(True)
plt.savefig('nmos_transient.png')
plt.show()