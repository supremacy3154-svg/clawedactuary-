#!/usr/bin/env python3
"""Daily research publishing workflow for clawedactuary.com.cn.

Usage:
  python3 scripts/daily_research.py brief          # 今日研究简报（新闻 + 队列）
  python3 scripts/daily_research.py queue         # 列出话题队列
  python3 scripts/daily_research.py next          # 下一个待写话题
  python3 scripts/daily_research.py publish-check # 发布前检查
  python3 scripts/daily_research.py mark-published SLUG [topic_id]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SITE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE = SITE_DIR.parent
CONFIG_PATH = SITE_DIR / "workflows" / "daily-research.json"
STATE_PATH = SITE_DIR / "_generated" / "daily-research-state.json"
POSTS_DIR = SITE_DIR / "posts"
BRIEF_DIR = SITE_DIR / "_generated" / "daily-briefs"
TZ = ZoneInfo("Asia/Shanghai")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"缺少配置: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"published_today": [], "history": [], "last_brief_date": None}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def today_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d")


def fetch_news(queries: list[str], max_each: int = 3) -> list[dict]:
    results: list[dict] = []
    tvly = subprocess.run(["which", "tvly"], capture_output=True, text=True)
    if tvly.returncode != 0:
        return results
    for q in queries[:6]:
        try:
            proc = subprocess.run(
                ["tvly", "search", q, "--time-range", "week", "--max-results", str(max_each), "--json"],
                capture_output=True,
                text=True,
                timeout=45,
            )
            if proc.returncode != 0:
                continue
            data = json.loads(proc.stdout)
            items = data.get("results", data) if isinstance(data, dict) else data
            for item in items[:max_each]:
                if isinstance(item, dict):
                    results.append({
                        "query": q,
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": (item.get("content") or item.get("snippet") or "")[:280],
                    })
        except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
            continue
    return results


def cmd_brief() -> int:
    cfg = load_config()
    state = load_state()
    today = today_str()
    queries = cfg.get("news_queries", [])
    if isinstance(queries, dict):
        queries = []
    news = fetch_news(queries if isinstance(queries, list) else [])

    queue = cfg.get("topic_queue", [])
    pending = [t for t in queue if isinstance(t, dict) and t.get("status") == "pending"]
    in_prog = [t for t in queue if isinstance(t, dict) and t.get("status") == "in_progress"]

    brief = {
        "date": today,
        "generated_at": datetime.now(TZ).isoformat(),
        "max_posts_today": cfg.get("schedule", {}).get("max_posts_per_day", 2)
        if isinstance(cfg.get("schedule"), dict)
        else 2,
        "pillars": cfg.get("pillars", []),
        "news": news,
        "topic_queue_pending": pending,
        "topic_queue_in_progress": in_prog,
        "published_today": state.get("published_today", []),
        "agent_prompt": (
            "读取本简报与 skills/daily-research-publish/SKILL.md。"
            "今日写 1–2 篇深度稿：优先 in_progress，再取 pending；"
            "结合 news 热点与 data_sources；风格对齐现有 posts/*.qmd；"
            "完成后 sync_posts.py + quarto render + publish-check。"
        ),
    }

    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    out = BRIEF_DIR / f"{today}.json"
    out.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"简报已写入: {out.relative_to(SITE_DIR)}")
    print(f"待写话题: {len(pending)} pending, {len(in_prog)} in_progress")
    print(f"新闻条数: {len(news)}")
    if in_prog:
        print("进行中:", ", ".join(t.get("title", t.get("id", "?")) for t in in_prog))
    elif pending:
        print("建议下一篇:", pending[0].get("title", pending[0].get("id")))
    if not news:
        print("提示: tvly 未返回新闻，可运行 tvly login 或手动补充热点")
    return 0


def cmd_queue() -> int:
    cfg = load_config()
    for t in cfg.get("topic_queue", []):
        if not isinstance(t, dict):
            continue
        print(f"[{t.get('status', '?'):12}] {t.get('id', '?'):30} {t.get('title', '')}")
    return 0


def cmd_next() -> int:
    cfg = load_config()
    queue = cfg.get("topic_queue", [])
    for t in queue:
        if isinstance(t, dict) and t.get("status") == "in_progress":
            print(json.dumps(t, ensure_ascii=False, indent=2))
            return 0
    for t in queue:
        if isinstance(t, dict) and t.get("status") == "pending":
            print(json.dumps(t, ensure_ascii=False, indent=2))
            return 0
    print("队列已空")
    return 0


def list_post_slugs() -> set[str]:
    return {p.stem for p in POSTS_DIR.glob("*.qmd") if not p.name.startswith("_")}


def cmd_publish_check() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for path in sorted(POSTS_DIR.glob("*.qmd")):
        if path.name.startswith("_"):
            continue
        raw = path.read_text(encoding="utf-8")
        if not raw.startswith("---"):
            errors.append(f"{path.name}: 缺少 YAML front matter")
            continue
        meta = raw.split("---", 2)[1]
        if "draft: true" in meta:
            warnings.append(f"{path.name}: 仍为 draft")
        if "description:" not in meta or 'description: ""' in meta:
            errors.append(f"{path.name}: 缺少 description")
        if "categories:" not in meta:
            warnings.append(f"{path.name}: 建议添加 categories")

    sync = SITE_DIR / "scripts" / "sync_posts.py"
    if sync.exists():
        proc = subprocess.run([sys.executable, str(sync)], cwd=SITE_DIR, capture_output=True, text=True)
        if proc.returncode != 0:
            errors.append(f"sync_posts.py 失败:\n{proc.stderr}")
        else:
            print(proc.stdout.strip() or "sync_posts.py OK")

    if errors:
        print("❌ 发布检查未通过:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    if warnings:
        print("⚠ 警告:")
        for w in warnings:
            print(f"  - {w}")
    print(f"✓ 可发布文章: {len(list_post_slugs())} 篇")
    return 0


def cmd_mark_published(slug: str, topic_id: str | None = None) -> int:
    state = load_state()
    today = today_str()
    if state.get("last_brief_date") != today:
        state["published_today"] = []
        state["last_brief_date"] = today
    entry = {"slug": slug, "topic_id": topic_id, "at": datetime.now(TZ).isoformat()}
    if slug not in state["published_today"]:
        state["published_today"].append(slug)
    state.setdefault("history", []).append(entry)
    save_state(state)
    print(f"已记录发布: {slug}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "brief":
        return cmd_brief()
    if cmd == "queue":
        return cmd_queue()
    if cmd == "next":
        return cmd_next()
    if cmd == "publish-check":
        return cmd_publish_check()
    if cmd == "mark-published":
        if len(sys.argv) < 3:
            print("用法: mark-published SLUG [topic_id]", file=sys.stderr)
            return 1
        return cmd_mark_published(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(f"未知命令: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
