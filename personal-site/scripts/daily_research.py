#!/usr/bin/env python3
"""Daily research publishing workflow for clawedactuary.com.cn.

Usage:
  python3 scripts/daily_research.py brief          # 今日研究简报（新闻 + 队列）
  python3 scripts/daily_research.py queue         # 列出话题队列
  python3 scripts/daily_research.py next          # 下一个待写话题
  python3 scripts/daily_research.py pick           # 今日最高优先级选题（全自动）
  python3 scripts/daily_research.py quality-check SLUG
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
            "读取本简报、skills/daily-research-publish/SKILL.md、"
            "personal-site/article-writing-prompt.md。"
            "运行 python3 scripts/daily_research.py pick，写优先级最高的一篇；"
            "核对通过后 git push origin main，并发送平安邮箱。"
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


def _post_meta(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    meta: dict = {"path": str(path), "slug": path.stem, "title": path.stem, "date": None}
    if raw.startswith("---"):
        block = raw.split("---", 2)[1]
        tm = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", block, re.M)
        dm = re.search(r"^date:\s*([0-9-]+)", block, re.M)
        if tm:
            meta["title"] = tm.group(1).strip().strip('"').strip("'")
        if dm:
            try:
                meta["date"] = date.fromisoformat(dm.group(1))
            except ValueError:
                pass
    return meta


def cmd_pick() -> int:
    cfg = load_config()
    today = date.fromisoformat(today_str())
    window = int(cfg.get("topic_selection", {}).get("recent_post_window_days", 14))
    posts = [_post_meta(p) for p in POSTS_DIR.glob("*.qmd") if not p.name.startswith("_")]
    today_posts = [p for p in posts if p.get("date") == today]
    if today_posts:
        out = {
            "skip": True,
            "reason": f"今日已有正式稿 {today_posts[0]['slug']}，不再加写",
            "pick": None,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    recent_titles = [
        p["title"]
        for p in posts
        if p.get("date") and (today - p["date"]).days <= window
    ]
    queries = cfg.get("news_queries", [])
    news = fetch_news(queries if isinstance(queries, list) else [])
    queue = [t for t in cfg.get("topic_queue", []) if isinstance(t, dict)]
    live = [t for t in queue if t.get("status") in {"in_progress", "pending"}]
    backlog = [t for t in queue if t.get("status") == "backlog"]

    pick = None
    source = "news"
    if news:
        pick = {
            "title": news[0].get("title") or "当日热点",
            "url": news[0].get("url", ""),
            "snippet": news[0].get("snippet", ""),
            "angle": "结合保险/精算作业层改写成站点中文稿；热度优先",
        }
    elif live:
        source = "queue"
        pick = {k: live[0].get(k) for k in ("id", "title", "pillar", "notes")}
    elif backlog:
        source = "backlog"
        pick = {k: backlog[0].get(k) for k in ("id", "title", "pillar", "notes")}

    out = {
        "skip": pick is None,
        "reason": "按热度优先选出一篇" if pick else "简报无新闻且队列为空，请用英文源自行检索后写一篇",
        "source": source,
        "recent_titles": recent_titles[:12],
        "news_count": len(news),
        "pick": pick,
        "rules": cfg.get("topic_selection", {}).get("instructions", ""),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_quality_check(slug: str) -> int:
    cfg = load_config()
    content = cfg.get("content", {})
    min_fig = int(content.get("min_figures", 2))
    min_tbl = int(content.get("min_data_tables", 2))
    min_num = int(content.get("min_sourced_numbers", 5))
    path = POSTS_DIR / f"{slug}.qmd"
    if not path.exists():
        path = POSTS_DIR / slug
    if not path.exists():
        print(f"✗ 找不到稿件: {slug}", file=sys.stderr)
        return 1
    raw = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if re.search(r"不是.{0,12}而是", raw) or re.search(r"并非.{0,12}而是", raw):
        errors.append("含禁用句式「不是/并非…而是…」")
    body = raw.split("---", 2)[-1] if raw.startswith("---") else raw
    if "平安" in body:
        errors.append("正文出现「平安」，主观段落禁止点名国内险企")
    n_img = len(re.findall(r"!\[[^\]]*\]\([^)]+\)", raw))
    n_tables = len(re.findall(r"^\|[-: |]+\|$", raw, re.M))
    n_num = len(re.findall(r"\*\*[0-9][0-9.,%万亿美美元]*\*\*", raw))
    if n_img < min_fig:
        errors.append(f"配图 {n_img} < min_figures {min_fig}")
    if n_tables < min_tbl:
        errors.append(f"表格 {n_tables} < min_data_tables {min_tbl}")
    if n_num < min_num:
        errors.append(f"加粗数字 {n_num} < min_sourced_numbers {min_num}")
    img_dir = SITE_DIR / "images" / path.stem
    pngs = list(img_dir.glob("*.png")) if img_dir.exists() else []
    if len(pngs) < min_fig:
        errors.append(f"images/{path.stem} 下 PNG {len(pngs)} < {min_fig}")
    src = img_dir / "data-sources.json"
    if content.get("require_data_cross_check") and not src.exists():
        errors.append(f"缺少 {src.relative_to(SITE_DIR)}")
    yaml_block = raw.split("---", 2)[1] if raw.startswith("---") else ""
    if "draft: true" in yaml_block:
        errors.append("仍为 draft: true")
    if errors:
        print("❌ quality-check 未通过:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(f"  (images={n_img}, tables={n_tables}, bold_nums={n_num})")
        return 1
    print(f"✓ quality-check 通过: {path.name} 图{n_img} 表{n_tables} 加粗数字{n_num}")
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
    if cmd == "pick":
        return cmd_pick()
    if cmd == "quality-check":
        if len(sys.argv) < 3:
            print("用法: quality-check SLUG", file=sys.stderr)
            return 1
        return cmd_quality_check(sys.argv[2])
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
