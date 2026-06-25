#!/usr/bin/env python3
"""Export web-sized opinion charts for personal-site (matches BYD article style)."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[2]
SITE_IMG = BASE / "personal-site" / "images"

SENTIMENT_LABELS = ["正面", "负面/质疑", "混合", "中性/咨询", "中性/其他"]
SENTIMENT_COLORS = ["#2171b5", "#cb181d", "#e6550d", "#6baed6", "#bdbdbd"]

DATASETS = {
    "huawei_qiankun": {
        "comments": BASE / "data/douyin_huawei_qiankun/douyin/jsonl/detail_comments_toplevel_dedup.jsonl",
        "sentiment": BASE / "data/douyin_huawei_qiankun/sentiment_llm.jsonl",
        "out_dir": SITE_IMG / "huawei-qiankun",
        "topics": {
            "无忧权益与保障范围": ["无忧权益", "保障", "兜底", "赔付", "赔偿", "保险", "智驾险", "平安", "300万", "500万"],
            "ADS涨价与老车主": ["涨价", "4000", "3.6万", "老车主", "背刺", "7月", "7.1", "三年", "一年", "6000", "12000"],
            "智驾能力与ADS升级": ["ADS", "智驾", "辅助驾驶", "NCA", "泊车", "小艺", "ADS5", "升级", "体验"],
            "竞品对比（比亚迪等）": ["比亚迪", "笛子", "小米", "特斯拉", "理想", "小鹏", "FSD", "跟进", "遥遥领先"],
            "责任边界与免责担忧": ["免责", "小字", "退出", "接管", "前一秒", "文字游戏", "条款", "条件", "扯皮"],
            "信任与观望": ["不敢", "怀疑", "观望", "再看看", "怎么领", "如何领取", "蹲", "真的吗"],
        },
        "sentiment_title": "一级评论情感分布（N={n:,}，LLM推理）",
    },
}

# Tuned to match personal-site/images/byd-zhijia/*.png (~1580×880px)
WEB = dict(fig_w=7.2, fig_h=4.0, dpi=160, title=15, label=12, tick=11, anno=10)
PAPER = "#f8f5f0"  # site --paper; figure + axes must both use this


def setup_plt():
    os.environ["MPLCONFIGDIR"] = str(BASE / ".mplconfig")
    plt.rcParams.update({
        "font.sans-serif": ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"],
        "axes.unicode_minus": False,
    })


def load_comments(comments_path: Path, sentiment_path: Path) -> list[dict]:
    sm = {}
    for line in sentiment_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            sm[d["comment_id"]] = d["sentiment"]
    rows = []
    for line in comments_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        sent = sm.get(d["comment_id"])
        if sent:
            d["sentiment"] = sent
            rows.append(d)
    return rows


def topic_counts(comments: list[dict], topics: dict) -> Counter:
    c = Counter()
    for row in comments:
        text = row.get("content") or ""
        for name, kws in topics.items():
            if any(k in text for k in kws):
                c[name] += 1
    return c


def style_axes(ax):
    ax.set_facecolor(PAPER)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="both", colors="#1a1814", width=0.8, length=4)


def export_sentiment(comments: list[dict], out: Path, title_tpl: str) -> None:
    setup_plt()
    total = len(comments)
    sentiment = Counter(c["sentiment"] for c in comments)
    labels = SENTIMENT_LABELS
    vals = [sentiment.get(k, 0) for k in labels]

    fig, ax = plt.subplots(figsize=(WEB["fig_w"], WEB["fig_h"]), facecolor=PAPER)
    bars = ax.bar(labels, vals, color=SENTIMENT_COLORS, width=0.52)
    ax.set_title(title_tpl.format(n=total), fontsize=WEB["title"], fontweight="bold", pad=12, color="#1a1814")
    ax.set_ylabel("条数", fontsize=WEB["label"], color="#1a1814")
    ax.tick_params(axis="both", labelsize=WEB["tick"])
    style_axes(ax)
    ymax = max(vals) if vals else 1
    for b, v in zip(bars, vals):
        if v:
            ax.text(
                b.get_x() + b.get_width() / 2,
                v + ymax * 0.02,
                f"{v:,}",
                ha="center",
                fontsize=WEB["anno"],
                fontweight="bold",
                color="#1a1814",
            )
    ax.set_ylim(0, ymax * 1.16)
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=WEB["dpi"], bbox_inches="tight", facecolor=PAPER, edgecolor="none")
    plt.close()


def export_topics(comments: list[dict], topics: dict, out: Path) -> None:
    setup_plt()
    tc = topic_counts(comments, topics)
    pairs = sorted(tc.most_common(7), key=lambda x: x[1])
    names = [p[0] for p in pairs]
    counts = [p[1] for p in pairs]
    h = max(WEB["fig_h"], len(names) * 0.55)

    fig, ax = plt.subplots(figsize=(WEB["fig_w"], h), facecolor=PAPER)
    bars = ax.barh(names, counts, color="#2171b5", height=0.55)
    ax.set_title(
        "舆情主题提及频次（关键词匹配）",
        fontsize=WEB["title"],
        fontweight="bold",
        pad=12,
        color="#1a1814",
    )
    ax.set_xlabel("提及条数", fontsize=WEB["label"], color="#1a1814")
    ax.tick_params(axis="both", labelsize=WEB["tick"])
    style_axes(ax)
    xmax = max(counts) if counts else 1
    for b, v in zip(bars, counts):
        ax.text(v + xmax * 0.02, b.get_y() + b.get_height() / 2, f"{v:,}", va="center", fontsize=WEB["anno"], color="#1a1814")
    ax.set_xlim(0, xmax * 1.12)
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=WEB["dpi"], bbox_inches="tight", facecolor=PAPER, edgecolor="none")
    plt.close()


def export_dataset(name: str) -> None:
    cfg = DATASETS[name]
    comments = load_comments(cfg["comments"], cfg["sentiment"])
    out_dir = cfg["out_dir"]
    export_sentiment(comments, out_dir / "sentiment-dist.png", cfg["sentiment_title"])
    export_topics(comments, cfg["topics"], out_dir / "topic-hits.png")
    print(f"✓ {name}: {len(comments):,} comments → {out_dir}")


def main() -> int:
    names = sys.argv[1:] or ["huawei_qiankun"]
    for name in names:
        if name not in DATASETS:
            print(f"未知数据集: {name}", file=sys.stderr)
            return 1
        export_dataset(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
