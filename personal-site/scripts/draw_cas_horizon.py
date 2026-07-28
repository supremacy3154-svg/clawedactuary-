#!/usr/bin/env python3
"""绘制 ADS 4 → ADS 5 CAS 关键速度参数变更对比图（分组横向条形）。

说明：gen_research_charts.py 现有渲染器为单序列，不支持分组对比，
本脚本为分项目站点配图负责绘制说明，不属于数据图表通道。
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".mplconfig"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({
    "font.sans-serif": ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"],
    "axes.unicode_minus": False,
})

PAPER = "#f8f5f0"
INK = "#1a1814"
ACCENT = "#8b2020"
SOFT = "#bdbdbd"

OUT_DIR = Path(__file__).resolve().parents[1] / "images" / "huawei-ads5-wewa2-arch"
OUT = OUT_DIR / "ads4-vs-ads5-aeb-floor.png"

# CAS 关键参数 ADS 4 → ADS 5 变更（上下限各 2 项）
metrics = [
    ("前向 AEB 最低触发速度 (km/h，越低越好)", 4, 1),
    ("侧向 LOCP 最低生效速度 (km/h，越低越好)", 30, 10),
    ("前向 AEB 刹停速度上限 (km/h)", 80, 130),
    ("eAES 最高避撞速度 (km/h)", 90, 135),
]

labels = [m[0] for m in metrics]
ads4 = [m[1] for m in metrics]
ads5 = [m[2] for m in metrics]

fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=160)
fig.patch.set_facecolor(PAPER)
ax.set_facecolor(PAPER)

y = list(range(len(labels)))
height = 0.35

bars1 = ax.barh([yi + height / 2 for yi in y], ads4, height=height,
                label="ADS 4（CAS 4.x）", color=SOFT, edgecolor=INK, linewidth=0.4)
bars2 = ax.barh([yi - height / 2 for yi in y], ads5, height=height,
                label="ADS 5（CAS 5.0）", color=ACCENT, edgecolor=INK, linewidth=0.4)

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=10, color=INK)
ax.invert_yaxis()
ax.set_xlabel("速度 (km/h)", fontsize=11, color=INK)
ax.set_title("ADS 4 → ADS 5：CAS 关键速度参数变更速览", fontsize=14, fontweight="600",
             pad=12, loc="left", color=INK)
ax.tick_params(colors=INK)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
for spine in ["left", "bottom"]:
    ax.spines[spine].set_color(INK)
    ax.spines[spine].set_linewidth(0.6)

ax.legend(frameon=False, fontsize=10, loc="lower right")

for b, v in zip(bars1, ads4):
    ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2, f"{v}",
            ha="left", va="center", fontsize=9, color="#666")
for b, v in zip(bars2, ads5):
    ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2, f"{v}",
            ha="left", va="center", fontsize=9, color=ACCENT, fontweight="600")

fig.text(0.01, 0.01,
         "来源：华为乾崑智驾 ADS 5 官方页面 auto.huawei.com/cn/ads；交叉验证：搜狐 IT、腾讯新闻 2026-06-23",
         fontsize=8, color="#666")
fig.tight_layout()
fig.savefig(OUT, bbox_inches="tight", facecolor=PAPER)
plt.close(fig)
print(f"✓ {OUT}")
