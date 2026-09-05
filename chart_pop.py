# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

df = pd.read_csv(r"d:\git仓库\Git test repository\china_pop_2016_2026_2036.csv")
age_order = ["0-4","5-9","10-14","15-19","20-24","25-29","30-34","35-39","40-44",
             "45-49","50-54","55-59","60-64","65-69","70-74","75-79","80-84",
             "85-89","90-94","95-99","100+"]
df["AgeGrp"] = pd.Categorical(df["AgeGrp"], categories=age_order, ordered=True)
df = df.sort_values(["Time", "AgeGrp"])
df["AgeLbl"] = df["AgeGrp"].astype(str) + "岁"

years = [2016, 2026, 2036]
YEAR_TITLES = {2016: "2016年（10年前）", 2026: "2026年（现在）", 2036: "2036年（10年后·预测）"}

stats = {}
for y in years:
    d = df[df["Time"] == y]
    tot = d["PopTotal"].sum()                    # 千
    over65 = d[d["AgeGrpStart"] >= 65]["PopTotal"].sum()
    under15 = d[d["AgeGrpStart"] < 15]["PopTotal"].sum()
    # 近似中位年龄（组内均匀）
    vals = d["PopTotal"].values
    cum = np.cumsum(vals)
    half = tot / 2
    k = int(np.searchsorted(cum, half))
    start = d["AgeGrpStart"].values[k]
    prev = cum[k - 1] if k > 0 else 0
    median_age = start + (half - prev) / (cum[k] - prev) * 5
    stats[y] = dict(total_billion=tot/1e5, over65_pct=over65/tot*100,
                    under15_pct=under15/tot*100, median=median_age)

fig, axes = plt.subplots(1, 3, figsize=(17, 8.2), sharey=True)
MALE_C, FEMALE_C = "#3a6ea5", "#d64c5e"

for ax, y in zip(axes, years):
    d = df[df["Time"] == y]
    pos = np.arange(len(age_order))
    male = -d["PopMale"].values / 1000.0     # 百万
    fem = d["PopFemale"].values / 1000.0
    ax.barh(pos, male, color=MALE_C, edgecolor="white", linewidth=0.4, label="男")
    ax.barh(pos, fem, color=FEMALE_C, edgecolor="white", linewidth=0.4, label="女")
    ax.set_yticks(pos)
    ax.set_yticklabels(d["AgeLbl"].values, fontsize=9)
    ax.axvline(0, color="0.3", lw=0.8)
    ax.set_title(YEAR_TITLES[y], fontsize=14, fontweight="bold")
    ax.grid(axis="x", color="0.92", lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=9)
    s = stats[y]
    box = (f"总人口 {s['total_billion']:.2f} 亿\n"
           f"中位年龄 {s['median']:.1f} 岁\n"
           f"65岁+ 占比 {s['over65_pct']:.1f}%\n"
           f"0-14岁 占比 {s['under15_pct']:.1f}%")
    ax.text(0.985, 0.05, box, transform=ax.transAxes, ha="right", va="bottom",
            fontsize=10.5, family="Microsoft YaHei",
            bbox=dict(boxstyle="round,pad=0.45", fc="#f5f5f5", ec="#bbbbbb"))

axes[0].set_xlabel("人口（百万人）", fontsize=11)
axes[0].legend(loc="upper right", fontsize=10, frameon=False)
fig.suptitle("中国人口年龄结构变化：2016 → 2026 → 2036（男左女右）",
             fontsize=17, fontweight="bold", y=0.99)
fig.text(0.5, 0.012, "数据来源：联合国《世界人口展望 2024》(WPP2024)，中方案预测，每年7月1日人口",
         ha="center", fontsize=9, color="0.45")

out = r"d:\git仓库\Git test repository\china_pop_pyramid_2016_2026_2036.png"
fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
print("saved:", out)
for y in years:
    s = stats[y]
    print(f"{y}: 总人口 {s['total_billion']:.2f}亿 | 中位年龄 {s['median']:.1f} | "
          f"65+ {s['over65_pct']:.1f}% | 0-14 {s['under15_pct']:.1f}%")
