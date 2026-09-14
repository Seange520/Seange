import matplotlib.pyplot as plt
import numpy as np
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ===== 1. 定义电路 =====
circuit = Circuit('RC Low-Pass Filter')

# 交流电压源：直流偏置 0V，交流幅值 1V
circuit.V('input', 'input', circuit.gnd, 'DC 0V AC 1V')
circuit.R('1', 'input', 'out', 1 @ u_kOhm)
circuit.C('1', 'out', circuit.gnd, 1 @ u_uF)

# ===== 2. 运行交流分析 =====
simulator = circuit.simulator()
analysis = simulator.ac(start_frequency=10 @ u_Hz, stop_frequency=100 @ u_kHz,
                        number_of_points=40, variation='dec')

# ===== 3. 提取结果 =====
out_voltage = np.abs(analysis['out'])
freq = np.array(analysis.frequency)   # 转成纯数字数组

# ===== 4. 理论值计算 =====
R = 1e3   # 1kΩ
C = 1e-6  # 1μF
theoretical = 1 / np.sqrt(1 + (2 * np.pi * freq * R * C)**2)

# ===== 5. 画图对比 =====
plt.figure(figsize=(10, 6))
plt.semilogx(freq, out_voltage, 'bo-', label='PySpice 仿真')
plt.semilogx(freq, theoretical, 'r--', label='理论值')
plt.xlabel('频率 (Hz)')
plt.ylabel('输出电压 (V)')
plt.title('RC 低通滤波器 频率响应')
plt.legend()
plt.grid(True)
plt.savefig('rc_lowpass.png')
plt.show()

# ===== 6. 打印对比表 =====
print("\n频率(Hz) | 理论值(V) | 仿真值(V) | 误差")
print("-" * 50)
for i in range(0, len(freq), 5):   # 每隔5个点打印一次
    f = freq[i]
    t = theoretical[i]
    s = float(out_voltage[i])
    err = abs(t - s) / t * 100
    print(f"{f:8.1f} | {t:9.4f} | {s:9.4f} | {err:5.2f}%")