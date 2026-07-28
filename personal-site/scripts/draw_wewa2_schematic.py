#!/usr/bin/env python3
"""绘制 WEWA 2.0 云端↔车端架构示意图（站点配图，非数据图）。

色板沿用站点规范：纸色 #f8f5f0 / 墨色 #1a1814 / 强调红 #8b2020 /
次强调蓝 #2171b5。
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".mplconfig"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({
    "font.sans-serif": ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"],
    "axes.unicode_minus": False,
})

PAPER = "#f8f5f0"
INK = "#1a1814"
ACCENT = "#8b2020"
SECONDARY = "#2171b5"
MUTED = "#bdbdbd"

OUT_DIR = Path(__file__).resolve().parents[1] / "images" / "huawei-ads5-wewa2-arch"
OUT = OUT_DIR / "wewa2-arch.png"


def add_box(ax, xy, w, h, label, sub_lines, fill, edge):
    box = mpatches.FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        linewidth=1.2,
        edgecolor=edge,
        facecolor=fill,
    )
    ax.add_patch(box)
    cx = xy[0] + w / 2
    ax.text(cx, xy[1] + h - 0.35, label, ha="center", va="top",
            fontsize=12, fontweight="600", color=INK)
    for i, txt in enumerate(sub_lines):
        ax.text(cx, xy[1] + h - 0.95 - i * 0.32, txt,
                ha="center", va="top", fontsize=10, color=INK)


def main() -> None:
    fig, ax = plt.subplots(figsize=(11, 5.6), dpi=160)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.4)
    ax.axis("off")

    ax.text(6, 5.95, "WEWA 2.0  —  面向自动驾驶的 AI 智能体",
            ha="center", va="center", fontsize=16, fontweight="700", color=INK)
    ax.text(6, 5.45, "World Engine（云端）  ↔  World Action Model（车端）",
            ha="center", va="center", fontsize=11, color="#666")

    # 云端
    add_box(ax,
            xy=(0.6, 2.2), w=4.4, h=2.6,
            label="云端 · World Engine",
            sub_lines=["Multi-Agent 多智能体博弈",
                       "Online RL 在线强化学习",
                       "训练强度 +10× · 效率 +10×"],
            fill="#f0ece5", edge=ACCENT)

    # 车端
    add_box(ax,
            xy=(7.0, 2.2), w=4.4, h=2.6,
            label="车端 · World Action Model",
            sub_lines=["安全风险场（Safety Risk Field）",
                       "Driving Agent 出行策略",
                       "碰撞风险 −50%"],
            fill="#f0ece5", edge=SECONDARY)

    # 双向箭头 + 中段标签
    arrow_y = 3.5
    ax.annotate("", xy=(7.0, arrow_y), xytext=(5.0, arrow_y),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.4))
    ax.annotate("", xy=(5.0, arrow_y), xytext=(7.0, arrow_y),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.4))
    ax.text(6.0, arrow_y + 0.45, "World-End-to-End",
            ha="center", va="bottom", fontsize=10, fontweight="600", color=ACCENT)
    ax.text(6.0, arrow_y - 0.45, "World-Aware",
            ha="center", va="top", fontsize=10, fontweight="600", color=ACCENT)

    # 底部技术堆栈
    ax.text(6, 1.55,
            "端到端：感知—预测—规划—控制 统一神经网络 ｜ 底座：盘古大模型 3.0 多模态",
            ha="center", va="center", fontsize=10, color=INK)
    ax.text(6, 1.10,
            "数据调度：灵衢总线，车内信号时延 −30% ｜ 座舱：鸿蒙座舱 HarmonySpace 6",
            ha="center", va="center", fontsize=9.5, color="#555")

    # 注释
    ax.text(0.6, 0.45,
            "作者根据华为乾崑智驾 ADS 5 官方通稿与 2026-04-23 大会披露材料绘制，非官方示意图",
            ha="left", va="bottom", fontsize=8, color="#888")
    ax.text(11.4, 0.45,
            "数据来源：auto.huawei.com/cn/ads ｜ 腾讯新闻 2026-04-23",
            ha="right", va="bottom", fontsize=8, color="#888")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)
    print(f"✓ {OUT}")


if __name__ == "__main__":
    main()
