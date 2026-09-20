# -*- coding: utf-8 -*-
"""
中国经济增长周期图：实际GDP增速（2016-2025）与潜在增速情景测算（2026-2046）
- 2016（10年前）与 2046（预测20年后）对比
- 实线：国家统计局官方口径实际增速
- 虚线：参考中国社科院经济研究所等对中国潜在增速的长期测算，情景外推，非官方预测
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

# 实际增速（%）—— 国家统计局历年GDP核算（统计公报口径；2019/2020/2021为最终核实数）
actual_years = list(range(2016, 2026))                      # 2016-2025
actual_growth = [6.7, 6.9, 6.6, 6.0, 2.2, 8.4, 3.0, 5.2, 5.0, 5.0]

# 情景测算锚点（平滑衔接）——
# 参考中国社科院经济研究所《中国经济报告(2020)》对潜在增速的分段测算：
#   2026-30≈4.9%、2031-35≈4.5%、2036-40≈4.0%、2041-45≈3.6%
# 锚点取各五年段均值对应年，线性衔接外推至2046≈3.3%
# 虚线从 2025 年（实线的最后一个实际点）开始，与实线共用衔接点，保证接口重合对齐
knots = [(2025, 5.0), (2028, 4.9), (2033, 4.5), (2038, 4.0), (2043, 3.6), (2046, 3.3)]
fy = np.arange(2025, 2047)                                  # 2025-2046（2025为衔接点）
fg = np.interp(fy, [k[0] for k in knots], [k[1] for k in knots])

# 关键统计
decade_mean = np.mean(actual_growth)                        # 近十年实际均值
f2046 = fg[-1]                                              # 2046情景值
print(f"2016-2025 实际均值: {decade_mean:.2f}%  |  2046 情景测算: {f2046:.2f}%")
for y, g in zip(fy, fg):
    print(f"{y}: {g:.2f}%")

fig, ax = plt.subplots(figsize=(13, 6.6), dpi=100)

ACTUAL_C = "#3a6ea5"        # 实际值（钢蓝，与人口图主色一致）
FORECAST_C = "#d64c5e"      # 情景测算（红）
GRID_C = "#e9e9e9"

# 预测段浅色背景（2025年后为情景测算区域）
ax.axvspan(2025, 2046, color=FORECAST_C, alpha=0.05, zorder=0)

# 实线：实际增速
ax.plot(actual_years, actual_growth, color=ACTUAL_C, lw=2.6,
        marker="o", ms=5, label="实际GDP增速（国家统计局）", zorder=4)

# 虚线：情景测算（从2025衔接点开始延伸，2025处不再重复画小点）
fcst_idx = list(range(1, len(fy)))          # 从第二个点(2026年)起才显示标记
ax.plot(fy, fg, color=FORECAST_C, lw=2.4, ls=(0, (5, 2)),
        marker="o", ms=3, markevery=fcst_idx,
        label="潜在增速情景测算（2025年后为预测段）", zorder=3)

# 衔接点（2025年=5.0%，实线与虚线共用，接口重合对齐）
ax.plot([2025], [fg[0]], "o", ms=15, mfc="none", mec=ACTUAL_C, mew=1.8,
        zorder=6)
ax.plot([2025], [fg[0]], "o", ms=6, mfc=ACTUAL_C, mec="white", mew=1.2,
        zorder=7)

# 每个年份点标注对应数值（实际段蓝、预测段红，与线同色）
below_years = {2020, 2022}                  # 这两个点数字放点下方，避免挤在一起
for y, v in zip(actual_years, actual_growth):
    dy, va = (-0.45, "top") if y in below_years else (0.35, "bottom")
    ax.text(y, v + dy, f"{v:.1f}", ha="center", va=va,
            fontsize=8.3, color=ACTUAL_C, zorder=8)
for y, v in zip(fy[1:], fg[1:]):            # 2026-2046（2025衔接点不重复标）
    ax.text(y, v + 0.35, f"{v:.1f}", ha="center", va="bottom",
            fontsize=8.3, color=FORECAST_C, zorder=8)

# 2016 / 2046 对比强调点
ax.scatter([2016], [actual_growth[0]], s=60, color=ACTUAL_C, zorder=6)
ax.scatter([2046], [f2046], s=80, color=FORECAST_C, zorder=6)
ax.plot([2046], [f2046], "o", ms=7, mfc="white", mec=FORECAST_C, mew=2, zorder=5)

# 对比信息框（右下，风格对齐人口图）
compare = (f"2016年（10年前）实际增速：{actual_growth[0]:.1f}%\n"
           f"2046年（预测20年后）情景测算：≈{f2046:.1f}%\n"
           f"2016-2025十年实际均值：{decade_mean:.1f}%\n"
           f"增速中枢随老龄化等结构性因素逐步下移")
ax.text(0.985, 0.03, compare, transform=ax.transAxes, ha="right", va="bottom",
        fontsize=11, family="Microsoft YaHei",
        bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f7", ec="#bbbbbb"))

ax.set_ylim(0, 9.6)
ax.set_xticks(range(2016, 2047, 2))
ax.set_xticklabels(range(2016, 2047, 2), fontsize=10)
ax.set_yticks(range(0, 10, 2))
ax.tick_params(axis="y", labelsize=10)
ax.set_ylabel("GDP实际增速（%）", fontsize=11)
ax.grid(True, axis="y", color=GRID_C, lw=0.7)
ax.set_axisbelow(True)
ax.spines[["top", "right"]].set_visible(False)

ax.legend(loc="upper right", fontsize=10, frameon=False, ncol=1)
ax.set_title("中国经济增速的长期轨迹：2016（10年前）→ 2046（预测20年后）",
             fontsize=16, fontweight="bold", pad=14)

fig.text(0.5, 0.035,
         "数据来源：2016-2025年实际增速为国家统计局历年GDP核算（《统计公报》及最终核实公告，不变价同比）。\n"
         "2026-2046年虚线为参考中国社会科学院经济研究所《中国经济报告(2020)》对潜在增速测算的情景预测，非官方预测。",
         ha="center", fontsize=8.6, color="0.45")

out = Path(__file__).with_name("china_gdp_growth_2016_2046.png")
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", out)
