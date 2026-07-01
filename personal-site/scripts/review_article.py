#!/usr/bin/env python3
"""Post-write editorial review via MiniMax API.

Usage:
  python3 scripts/review_article.py <slug>
  python3 scripts/review_article.py posts/2026-07-01-japan-jibaiseki-rate-reform.qmd

Requires MINIMAX_API_KEY (or ~/.openclaw/openclaw.json mcp.servers.minimax.env).
Optional: MINIMAX_REVIEW_MODEL (default MiniMax-M3)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent
GUIDE = SITE_DIR / "CONTENT-GUIDE.md"
OUT_DIR = SITE_DIR / "_generated" / "reviews"
API_URL = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
DEFAULT_MODEL = os.environ.get("MINIMAX_REVIEW_MODEL", "MiniMax-M3")

REVIEW_PROMPT = """你是 clawedactuary.com.cn 的责编，审阅一篇待发布的 Markdown 文章正文（不含 YAML）。

对照规范提出**可执行的修改意见**，按优先级排序。**直接输出审阅结果，不要输出思考过程。**

重点检查：
1. 是否全文中文、读者能否读懂（禁止日式行政术语如答申/改定/见合う，禁止未解释的生造词）
2. 精算/监管术语是否需换成中文常用说法（如用「累计赔付占保费比例」而非「损害率」）
3. 图表是否必要：禁止为 2–3 个百分比拆柱状图；保留有时间序列价值的研究图；图须回答读者关心的问题
4. 表格是否过宽、列是否堆叠；应用 BYD 首篇舆情稿的简洁表格式样
5. 是否官腔、AI 痕迹（「先说结论」、元叙述）
6. 事实与数字是否需补充来源或口径说明

输出格式：
## 必须修改
- ...

## 建议优化
- ...

## 通过项
- ...

不要重写全文，只给审稿意见。"""


def resolve_path(arg: str) -> Path:
    p = Path(arg)
    if p.suffix == ".qmd":
        return p if p.is_absolute() else SITE_DIR / p
    return SITE_DIR / "posts" / f"{arg}.qmd" if not arg.endswith(".qmd") else SITE_DIR / "posts" / arg


def load_api_key() -> str:
    key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if key:
        return key
    cfg_path = Path.home() / ".openclaw/openclaw.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return cfg["mcp"]["servers"]["minimax"]["env"]["MINIMAX_API_KEY"]
    raise RuntimeError("未找到 MINIMAX_API_KEY")


def extract_body(raw: str) -> str:
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return raw


def call_minimax(api_key: str, article: str, guide_excerpt: str) -> str:
    user = f"规范摘要（CONTENT-GUIDE）：\n{guide_excerpt}\n\n---\n\n文章正文：\n{article[:28000]}"
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": REVIEW_PROMPT},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
        "max_tokens": 8192,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"MiniMax 无 choices: {data}")
    msg = choices[0].get("message") or {}
    content = msg.get("content") or ""
    if isinstance(content, list):
        content = "".join(
            p.get("text", "") for p in content if isinstance(p, dict)
        )
    content = content.strip()
    if not content:
        reasoning = (msg.get("reasoning_content") or "").strip()
        if reasoning and "## 必须修改" in reasoning:
            content = reasoning[reasoning.index("## 必须修改") :]
        elif reasoning:
            content = reasoning
    return content.strip()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 1
    path = resolve_path(sys.argv[1])
    if not path.exists():
        print(f"✗ 找不到: {path}", file=sys.stderr)
        return 1

    raw = path.read_text(encoding="utf-8")
    body = extract_body(raw)
    slug = path.stem
    guide_excerpt = ""
    if GUIDE.exists():
        guide_excerpt = GUIDE.read_text(encoding="utf-8")[:4000]

    try:
        api_key = load_api_key()
        review = call_minimax(api_key, body, guide_excerpt)
    except (urllib.error.URLError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(f"✗ 审阅失败: {exc}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{slug}.md"
    header = f"# 审阅意见 · {slug}\n\n模型：{DEFAULT_MODEL}\n\n"
    out.write_text(header + review + "\n", encoding="utf-8")
    print(review)
    print(f"\n✓ 已写入 {out.relative_to(SITE_DIR)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
