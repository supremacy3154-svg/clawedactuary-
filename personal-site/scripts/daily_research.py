#!/usr/bin/env python3
"""Daily research publishing workflow for clawedactuary.com.cn.

Usage:
  python3 scripts/daily_research.py brief          # 今日研究简报（发现式新闻 + 选题推荐）
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
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

SITE_DIR = Path(__file__).resolve().parent.parent
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


def day_index() -> int:
    return datetime.now(TZ).toordinal()


def pick_rotated(items: list, count: int, offset: int = 0) -> list:
    if not items or count <= 0:
        return []
    n = len(items)
    start = (day_index() + offset) % n
    return [items[(start + i) % n] for i in range(min(count, n))]


def tvly_available() -> bool:
    return subprocess.run(["which", "tvly"], capture_output=True).returncode == 0


def tvly_search(query: str, time_range: str, max_results: int) -> list[dict]:
    try:
        proc = subprocess.run(
            ["tvly", "search", query, "--time-range", time_range, "--max-results", str(max_results), "--json"],
            capture_output=True,
            text=True,
            timeout=45,
        )
        if proc.returncode != 0:
            return []
        data = json.loads(proc.stdout)
        items = data.get("results", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        return []


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip().lower())
    host = parsed.netloc.removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{host}{path}"


def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def title_tokens(text: str) -> set[str]:
    text = text.lower()
    words = re.findall(r"[\w\u4e00-\u9fff]+", text)
    stop = {"the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "as", "by", "at", "is"}
    return {w for w in words if len(w) > 2 and w not in stop}


def is_noise_title(title: str, patterns: list[str]) -> bool:
    lower = title.lower()
    return any(p.lower() in lower for p in patterns)


def is_excluded_domain(url: str, exclude_domains: list[str]) -> bool:
    host = domain_of(url)
    return any(host == d or host.endswith("." + d) for d in exclude_domains)


def is_quality_domain(url: str, quality_domains: list[str]) -> bool:
    host = domain_of(url)
    return any(host == d or host.endswith("." + d) for d in quality_domains)


def build_search_plan(cfg: dict) -> list[dict]:
    disc = cfg.get("discovery", {})
    if not disc:
        return [{"source": "legacy", "query": q} for q in cfg.get("news_queries", [])[:6]]

    plan: list[dict] = []
    for q in disc.get("wide_queries", []):
        plan.append({"source": "wide", "query": q})

    event_types = disc.get("event_types", [])
    selected_types = pick_rotated(event_types, disc.get("event_types_per_day", 4))
    q_per_type = disc.get("queries_per_event_type", 2)
    for i, et in enumerate(selected_types):
        for q in pick_rotated(et.get("queries", []), q_per_type, offset=i * 3):
            plan.append({
                "source": "event_type",
                "event_type": et.get("id"),
                "event_label": et.get("label"),
                "pillar": et.get("pillar"),
                "query": q,
            })

    for q in pick_rotated(cfg.get("exploration_queries", []), disc.get("exploration_queries_per_day", 2), offset=7):
        plan.append({"source": "exploration", "query": q})

    carriers = cfg.get("carrier_watch", {}).get("examples", [])
    carrier = pick_rotated(carriers, 1, offset=11)
    if carrier:
        c = carrier[0]
        for q in pick_rotated(c.get("search_queries", []), disc.get("carrier_watch_queries_per_day", 1), offset=13):
            plan.append({
                "source": "carrier_watch",
                "carrier_id": c.get("id"),
                "carrier_name": c.get("name"),
                "query": q,
            })

    return plan


def discover_news(cfg: dict) -> tuple[list[dict], dict]:
    disc = cfg.get("discovery", {})
    time_range = disc.get("time_range", "week")
    max_each = disc.get("max_results_per_query", 3)
    plan = build_search_plan(cfg)

    raw: list[dict] = []
    for entry in plan:
        query = entry["query"]
        for item in tvly_search(query, time_range, max_each):
            raw.append({
                "query": query,
                "search_source": entry.get("source"),
                "event_type": entry.get("event_type"),
                "event_label": entry.get("event_label"),
                "pillar_hint": entry.get("pillar"),
                "carrier_name": entry.get("carrier_name"),
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": (item.get("content") or item.get("snippet") or "")[:320],
                "tavily_score": item.get("score"),
            })

    news = dedup_news(raw)
    meta = {
        "mode": "discovery" if disc else "legacy",
        "queries_run": len(plan),
        "raw_hits": len(raw),
        "after_dedup": len(news),
        "search_plan": plan,
    }
    return news, meta


def dedup_news(items: list[dict]) -> list[dict]:
    seen_urls: set[str] = set()
    seen_titles: list[set[str]] = []
    out: list[dict] = []

    for item in items:
        url_key = normalize_url(item.get("url", ""))
        if not url_key or url_key in seen_urls:
            continue
        tokens = title_tokens(item.get("title", ""))
        if len(tokens) >= 4:
            for prev in seen_titles:
                overlap = len(tokens & prev) / max(len(tokens), len(prev))
                if overlap >= 0.75:
                    break
            else:
                seen_titles.append(tokens)
                seen_urls.add(url_key)
                out.append(item)
                continue
            continue
        seen_urls.add(url_key)
        out.append(item)
    return out


def parse_post_meta(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return {}
    meta_block = raw.split("---", 2)[1]
    meta: dict[str, str] = {}
    for line in meta_block.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip().strip('"')
    return meta


def recent_posts(cfg: dict) -> list[dict]:
    sel = cfg.get("topic_selection", {})
    window = sel.get("recent_post_window_days", 14)
    cutoff = datetime.now(TZ).date() - timedelta(days=window)
    posts: list[dict] = []

    for path in sorted(POSTS_DIR.glob("*.qmd")):
        if path.name.startswith("_"):
            continue
        meta = parse_post_meta(path)
        date_s = meta.get("date", path.stem[:10])
        try:
            post_date = datetime.strptime(date_s[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if post_date >= cutoff:
            posts.append({
                "slug": path.stem,
                "title": meta.get("title", path.stem),
                "date": date_s[:10],
                "categories": meta.get("categories", ""),
            })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def overlaps_recent(item: dict, recent: list[dict]) -> bool:
    item_tokens = title_tokens(item.get("title", "") + " " + item.get("snippet", ""))
    for post in recent:
        post_tokens = title_tokens(post.get("title", "") + " " + post.get("slug", ""))
        if len(item_tokens & post_tokens) >= 3:
            return True
    return False


def infer_event_type(text: str, event_types: list[dict]) -> dict | None:
    lower = text.lower()
    signals = {
        "rate_filing": ["rate filing", "pure premium", "reference rate", "料率", "纯率", "费率", "备案", "reference pure"],
        "legislation_regulation": ["legislation", "regulation passed", "regulatory reform", "立法", "监管", "新规", "gesetz", "aufsicht"],
        "underwriting_results": ["combined ratio", "underwriting profit", "loss ratio", "earnings", "承保", "综合成本率"],
        "product_channel": ["embedded insurance", "mga", "parametric", "telematics", "ubi", "usage based"],
        "catastrophe_capital": ["catastrophe bond", "cat bond", "reinsurance renewal", "巨灾", "再保"],
        "av_mobility_liability": ["autonomous", "self-driving", "智驾", "自动驾驶", "l3", "autonomes fahren"],
        "china_auto_insurance": ["新能源车险", "中国 车险", "车险 新能源", "电池 分开投保"],
    }
    best_id, best_hits = None, 0
    for et_id, keys in signals.items():
        hits = sum(1 for k in keys if k in lower)
        if hits > best_hits:
            best_id, best_hits = et_id, hits
    if not best_id or best_hits == 0:
        return None
    for et in event_types:
        if et.get("id") == best_id:
            return et
    return None


def match_pillar(text: str, pillars: list[str]) -> str | None:
    lower = text.lower()
    keywords = {
        "美国财险定价与费率创新": ["rate", "filing", "pricing", "premium", "combined ratio", "费率", "定价", "纯率", "料率"],
        "财险经营创新与渠道模式": ["embedded", "mga", "distribution", "channel", "ubi", "telematics", "渠道"],
        "国际财险与再保": ["reinsurance", "international", "global", "再保", "国际"],
        "车险与财产险风险": ["auto insurance", "motor", "car insurance", "车险", "新能源"],
        "巨灾气候与宏观风险": ["catastrophe", "cat bond", "hurricane", "wildfire", "巨灾", "气候"],
        "AI 核保理赔与精算自动化": [" ai ", "artificial intelligence", "machine learning", "精算自动化"],
        "保险科技与初创颠覆": ["insurtech", "startup", "funding", "venture"],
        "监管偿付与会计准则": ["regulation", "legislation", "solvency", "ifrs", "监管", "立法", "偿付"],
        "精算前沿与风险模型": ["actuarial", "reserving", "精算"],
        "智能网联与产品责任": ["autonomous", "self-driving", "智驾", "自动驾驶", "av "],
        "舆情与公众认知": ["opinion", "sentiment", "舆情"],
    }
    for pillar in pillars:
        for kw in keywords.get(pillar, [pillar[:4]]):
            if kw in lower:
                return pillar
    return None


def score_item(item: dict, cfg: dict, recent: list[dict]) -> float | None:
    disc = cfg.get("discovery", {})
    exclude = disc.get("exclude_domains", [])
    quality = disc.get("quality_domains", [])
    noise = disc.get("noise_title_patterns", [])
    pillars = cfg.get("pillars", [])
    title = item.get("title", "")
    url = item.get("url", "")

    if not title or not url:
        return None
    if is_excluded_domain(url, exclude):
        return None
    if is_noise_title(title, noise):
        return None

    score = 0.0
    tavily = item.get("tavily_score")
    if isinstance(tavily, (int, float)):
        score += float(tavily) * 5.0

    if item.get("search_source") == "wide":
        score += 1.0
    if item.get("event_type"):
        score += 2.5
    if item.get("search_source") == "carrier_watch":
        score += 1.5
    if is_quality_domain(url, quality):
        score += 2.0

    text = f"{title} {item.get('snippet', '')}"
    if not item.get("event_type"):
        inferred = infer_event_type(text, disc.get("event_types", []))
        if inferred:
            item["event_type"] = inferred.get("id")
            item["event_label"] = inferred.get("label")
            item["pillar_hint"] = inferred.get("pillar")

    pillar = item.get("pillar_hint") or match_pillar(text, pillars)
    if pillar:
        score += 1.5
        item["pillar"] = pillar

    if overlaps_recent(item, recent):
        score -= 2.5
        item["recent_overlap"] = True

    sel = cfg.get("topic_selection", {})
    if sel.get("ai_not_default") and item.get("event_type") not in {"av_mobility_liability"}:
        ai_noise = [" ai ", "insurtech", "generative ai", "chatgpt"]
        if any(k in text.lower() for k in ai_noise):
            score -= 1.0

    return score


def priority_label(score: float) -> str:
    if score >= 7:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def build_rationale(item: dict) -> str:
    parts: list[str] = []
    if item.get("event_label"):
        parts.append(f"事件：{item['event_label']}")
    elif item.get("search_source") == "wide":
        parts.append("宽网发现")
    if item.get("pillar"):
        parts.append(f"pillar：{item['pillar']}")
    if item.get("carrier_name"):
        parts.append(f"关注主体：{item['carrier_name']}")
    if item.get("recent_overlap"):
        parts.append("与近稿主题相近，降权")
    else:
        parts.append("非队列续篇")
    return "；".join(parts)


def build_topic_suggestions(news: list[dict], cfg: dict, recent: list[dict]) -> list[dict]:
    disc = cfg.get("discovery", {})
    min_score = disc.get("min_score_for_suggestion", 4.0)
    max_suggestions = disc.get("max_topic_suggestions", 5)

    scored: list[tuple[float, dict]] = []
    for item in news:
        s = score_item(item, cfg, recent)
        if s is None:
            continue
        scored.append((s, {**item, "score": round(s, 2)}))

    scored.sort(key=lambda x: x[0], reverse=True)
    suggestions: list[dict] = []
    used_event_types: set[str] = set()

    for score, item in scored:
        if score < min_score:
            continue
        et = item.get("event_type") or item.get("search_source") or "wide"
        if et in used_event_types:
            continue
        suggestions.append({
            "source": "discovery",
            "event_type": item.get("event_type"),
            "event_label": item.get("event_label"),
            "pillar": item.get("pillar"),
            "title": item.get("title"),
            "url": item.get("url"),
            "query": item.get("query"),
            "score": item.get("score"),
            "priority": priority_label(score),
            "rationale": build_rationale(item),
        })
        used_event_types.add(et)
        if len(suggestions) >= max_suggestions:
            break
    return suggestions


def queue_fallback(cfg: dict) -> dict | None:
    for status in ("pending", "backlog"):
        for t in cfg.get("topic_queue", []):
            if isinstance(t, dict) and t.get("status") == status:
                return t
    return None


def build_recommendation(suggestions: list[dict], cfg: dict) -> dict:
    rec: dict = {"strategy": "discover_from_news"}
    if suggestions:
        rec["recommended"] = suggestions[0]
    else:
        rec["recommended"] = None
        rec["note"] = "当日宽网+事件扫描未达阈值，建议查看队列备选或手动补充"
    fb = queue_fallback(cfg)
    if fb:
        rec["queue_fallback"] = fb
    rec["topic_suggestions"] = suggestions
    return rec


def cmd_brief() -> int:
    cfg = load_config()
    state = load_state()
    today = today_str()
    recent = recent_posts(cfg)
    news, discovery_meta = discover_news(cfg)

    disc = cfg.get("discovery", {})
    max_news = disc.get("max_news_in_brief", 30) if disc else 20
    scored_news: list[dict] = []
    for item in news:
        s = score_item(item, cfg, recent)
        if s is not None:
            scored_news.append({**item, "score": round(s, 2)})
    scored_news.sort(key=lambda x: x.get("score", 0), reverse=True)

    suggestions = build_topic_suggestions(news, cfg, recent)
    recommendation = build_recommendation(suggestions, cfg)

    queue = cfg.get("topic_queue", [])
    pending = [t for t in queue if isinstance(t, dict) and t.get("status") == "pending"]
    in_prog = [t for t in queue if isinstance(t, dict) and t.get("status") == "in_progress"]
    backlog = [t for t in queue if isinstance(t, dict) and t.get("status") == "backlog"]

    brief = {
        "date": today,
        "generated_at": datetime.now(TZ).isoformat(),
        "max_posts_today": cfg.get("schedule", {}).get("max_posts_per_day", 2)
        if isinstance(cfg.get("schedule"), dict)
        else 2,
        "pillars": cfg.get("pillars", []),
        "topic_selection": cfg.get("topic_selection", {}),
        "discovery": discovery_meta,
        "news": scored_news[:max_news],
        "topic_suggestions": suggestions,
        "recommendation": recommendation,
        "topic_queue_pending": pending,
        "topic_queue_in_progress": in_prog,
        "topic_queue_backlog": backlog,
        "recent_posts": [p["slug"] for p in recent[:8]],
        "published_today": state.get("published_today", []),
        "agent_prompt": (
            "读取本简报与 skills/daily-research-publish/SKILL.md、CONTENT-GUIDE.md §二。"
            "选题：优先 recommendation / topic_suggestions 中的新热点（已按事件类型+pillar 打分）；"
            "勿机械续写 recent_posts 或队列 backlog。"
            "仅产出选题建议与资料摘要，等待用户确认选题后再写稿；"
            "禁止未经确认创建 posts/*.qmd。"
            "用户确认后：写 1 篇深度稿，sync + render + publish-check + cross_check；"
            "draft: false 以便预览；禁止 push。"
        ),
    }

    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    out = BRIEF_DIR / f"{today}.json"
    out.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"简报已写入: {out.relative_to(SITE_DIR)}")
    print(f"发现模式: {discovery_meta.get('mode')} | 执行 {discovery_meta.get('queries_run')} 条查询")
    print(f"新闻: {discovery_meta.get('raw_hits')} 命中 → {discovery_meta.get('after_dedup')} 去重 → {len(suggestions)} 条选题推荐")
    print(f"待写话题: {len(pending)} pending, {len(in_prog)} in_progress")
    if suggestions:
        print("推荐选题:")
        for s in suggestions[:3]:
            print(f"  [{s['priority']}] {s.get('event_label') or '宽网'}: {s['title'][:70]}")
    elif in_prog:
        print("进行中:", ", ".join(t.get("title", t.get("id", "?")) for t in in_prog))
    if not news and not tvly_available():
        print("提示: tvly 未安装或未登录，可运行 tvly login")
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
