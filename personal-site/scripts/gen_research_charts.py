#!/usr/bin/env python3
"""Generate site-sized research charts from images/<slug>/charts.json.

Spec example (charts.json):
{
  "charts": [
    {
      "id": "pnc-ai-adoption",
      "type": "bar",
      "title": "财险 AI 用例分布（AAA 2026 归纳）",
      "labels": ["理赔", "核保", "定价", "准备金", "其他"],
      "values": [4, 5, 4, 2, 3],
      "ylabel": "用例条目数（作者归纳）",
      "source": "AAA Issue Brief, 2026-06"
    }
  ]
}

Usage:
  python3 scripts/gen_research_charts.py <slug>
  python3 scripts/gen_research_charts.py <slug> --spec path/to/charts.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SITE_DIR = Path(__file__).resolve().parent.parent
PAPER = "#f8f5f0"
INK = "#1a1814"
ACCENT = "#8b2020"  # site emphasis (clawed.scss)
ACCENT2 = "#2171b5"  # secondary series only
WEB = dict(fig_w=7.2, fig_h=4.0, dpi=160)


def setup_plt() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(SITE_DIR.parent / ".mplconfig"))
    plt.rcParams.update({
        "font.sans-serif": ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"],
        "axes.unicode_minus": False,
    })


def style_ax(ax, fig) -> None:
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=INK)
    ax.title.set_color(INK)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)


def render_bar(chart: dict, out: Path) -> None:
    labels = chart["labels"]
    values = chart["values"]
    fig, ax = plt.subplots(figsize=(WEB["fig_w"], WEB["fig_h"]), dpi=WEB["dpi"])
    style_ax(ax, fig)
    colors = [ACCENT if i % 2 == 0 else "#a84848" for i in range(len(values))]
    ax.bar(labels, values, color=colors, edgecolor=INK, linewidth=0.3, width=0.55)
    ax.set_title(chart.get("title", ""), fontsize=14, pad=12, loc="left", fontweight="600")
    if chart.get("ylabel"):
        ax.set_ylabel(chart["ylabel"], fontsize=11)
    plt.xticks(rotation=25, ha="right", fontsize=10)
    src = chart.get("source")
    if src:
        fig.text(0.01, 0.01, f"来源：{src}", fontsize=8, color="#666")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


def render_hbar(chart: dict, out: Path) -> None:
    labels = chart["labels"]
    values = chart["values"]
    fig, ax = plt.subplots(figsize=(WEB["fig_w"], WEB["fig_h"]), dpi=WEB["dpi"])
    style_ax(ax, fig)
    y = range(len(labels))
    ax.barh(list(y), values, color=ACCENT, edgecolor=INK, linewidth=0.3, height=0.55)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_title(chart.get("title", ""), fontsize=14, pad=12, loc="left", fontweight="600")
    if chart.get("xlabel"):
        ax.set_xlabel(chart["xlabel"], fontsize=11)
    src = chart.get("source")
    if src:
        fig.text(0.01, 0.01, f"来源：{src}", fontsize=8, color="#666")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


def render_line(chart: dict, out: Path) -> None:
    labels = chart["labels"]
    series = chart.get("series") or [{"name": chart.get("title", "序列"), "values": chart["values"]}]
    fig, ax = plt.subplots(figsize=(WEB["fig_w"], WEB["fig_h"]), dpi=WEB["dpi"])
    style_ax(ax, fig)
    ref = chart.get("reference_line")
    if ref is not None:
        ax.axhline(ref, color="#999", linestyle="--", linewidth=1, label=f"100% 参考线")
    for i, s in enumerate(series):
        color = ACCENT if i == 0 else ACCENT2
        ax.plot(labels, s["values"], marker="o", linewidth=2, markersize=6, color=color, label=s.get("name", f"S{i+1}"))
    ax.set_title(chart.get("title", ""), fontsize=14, pad=12, loc="left", fontweight="600")
    if chart.get("ylabel"):
        ax.set_ylabel(chart["ylabel"], fontsize=11)
    if len(series) > 1 or ref is not None:
        ax.legend(frameon=False, fontsize=9, loc="upper right")
    plt.xticks(rotation=20, ha="right", fontsize=10)
    src = chart.get("source")
    if src:
        fig.text(0.01, 0.01, f"来源：{src}", fontsize=8, color="#666")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


RENDERERS = {
    "bar": render_bar,
    "hbar": render_hbar,
    "horizontal_bar": render_hbar,
    "line": render_line,
}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 1
    slug = sys.argv[1]
    spec_path = SITE_DIR / "images" / slug / "charts.json"
    if "--spec" in sys.argv:
        idx = sys.argv.index("--spec")
        if idx + 1 < len(sys.argv):
            spec_path = Path(sys.argv[idx + 1])
    if not spec_path.exists():
        print(f"✗ 缺少图表规格: {spec_path}", file=sys.stderr)
        return 1
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    charts = data.get("charts", [])
    if not charts:
        print("✗ charts.json 为空", file=sys.stderr)
        return 1
    setup_plt()
    out_dir = SITE_DIR / "images" / slug
    for chart in charts:
        cid = chart.get("id")
        if not cid:
            print("✗ chart 缺少 id", file=sys.stderr)
            return 1
        ctype = chart.get("type", "bar")
        fn = RENDERERS.get(ctype)
        if not fn:
            print(f"✗ 不支持的 type: {ctype}", file=sys.stderr)
            return 1
        out = out_dir / f"{cid}.png"
        fn(chart, out)
        print(f"✓ {out.relative_to(SITE_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
