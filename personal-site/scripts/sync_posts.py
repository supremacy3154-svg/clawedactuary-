#!/usr/bin/env python3
"""Sync homepage + blog listing from posts/*.qmd. Run before quarto render."""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent
POSTS_DIR = SITE_DIR / "posts"
GENERATED_DIR = SITE_DIR / "_generated"
INDEX_PATH = SITE_DIR / "index.qmd"
BLOG_PATH = SITE_DIR / "blog.qmd"
CONFIG_PATH = SITE_DIR / "site-config.yml"

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
SIDEBAR_NUM = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]


@dataclass
class Post:
    slug: str
    title: str
    date: date
    description: str
    categories: list[str]
    kicker: str
    title_html: str
    reading_minutes: int
    draft: bool

    @property
    def url(self) -> str:
        return f"posts/{self.slug}.html"

    @property
    def year(self) -> str:
        return str(self.date.year)

    @property
    def date_iso(self) -> str:
        return self.date.isoformat()

    @property
    def date_display(self) -> str:
        return f"{self.date.year}-{self.date.month:02d}-{self.date.day:02d}"

    @property
    def date_blog(self) -> str:
        return f"{self.date.year}.{self.date.month:02d}.{self.date.day:02d}"

    @property
    def type_label(self) -> str:
        if " · " in self.kicker:
            return self.kicker.split(" · ", 1)[1].strip()
        return self.kicker or "文章"


def load_yaml_block(text: str) -> dict[str, object]:
    meta: dict[str, object] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            meta[key] = (
                [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
                if inner
                else []
            )
        elif val.lower() in {"true", "false"}:
            meta[key] = val.lower() == "true"
        else:
            meta[key] = val
    return meta


def parse_post(path: Path) -> Post | None:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return None
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return None
    meta = load_yaml_block(parts[1])
    body = parts[2]

    if meta.get("draft") is True:
        return None

    title = str(meta.get("title", path.stem))
    desc = str(meta.get("description", ""))
    slug = path.stem

    date_val = meta.get("date")
    if isinstance(date_val, str):
        post_date = datetime.strptime(date_val, "%Y-%m-%d").date()
    else:
        post_date = date.today()

    cats = meta.get("categories", [])
    if not isinstance(cats, list):
        cats = []

    kicker_m = re.search(
        r'<div class="post-kicker">([^<]+)</div>', body, re.IGNORECASE
    )
    kicker = kicker_m.group(1).strip() if kicker_m else "文章"

    title_m = re.search(
        r'<h1 class="post-title">(.*?)</h1>', body, re.DOTALL | re.IGNORECASE
    )
    title_html = title_m.group(1).strip() if title_m else html.escape(title)

    text_only = re.sub(r"<[^>]+>", " ", body)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text_only))
    latin = len(re.findall(r"[A-Za-z0-9]+", text_only))
    reading = max(1, round((cjk + latin) / 350))

    return Post(
        slug=slug,
        title=title,
        date=post_date,
        description=desc,
        categories=[str(c) for c in cats],
        kicker=kicker,
        title_html=title_html,
        reading_minutes=reading,
        draft=False,
    )


def load_posts() -> list[Post]:
    posts: list[Post] = []
    for path in sorted(POSTS_DIR.glob("*.qmd")):
        post = parse_post(path)
        if post:
            posts.append(post)
    posts.sort(key=lambda p: p.date, reverse=True)
    return posts


def masthead_title_html(post: Post) -> str:
    if "<" in post.title_html:
        return post.title_html.replace("<h1", "<span").replace("</h1>", "</span>")
    text = post.title_html
    if "：" in text:
        head, tail = text.split("：", 1)
        return f"{html.escape(head)}：<br>{html.escape(tail)}"
    if len(text) > 18:
        return f"{html.escape(text[:18])}<br>{html.escape(text[18:])}"
    return html.escape(text)


def tags_html(categories: list[str], limit: int = 4) -> str:
    tags = categories[:limit]
    if not tags:
        return ""
    return "\n".join(f'          <span class="tag">{html.escape(t)}</span>' for t in tags)


def replace_block(text: str, name: str, content: str) -> str:
    start = f"<!-- AUTO:{name}:START -->"
    end = f"<!-- AUTO:{name}:END -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"Missing markers {start} … {end} in target file")
    return pattern.sub(f"{start}\n{content}\n{end}", text, count=1)


def render_masthead(featured: Post) -> str:
    return f"""      <div class="masthead-kicker">Featured · 精选</div>
      <h1 class="masthead-title">
        {masthead_title_html(featured)}
      </h1>
      <p class="masthead-desc">
        {html.escape(featured.description)}
      </p>
      <a class="masthead-cta" href="{featured.url}">阅读全文 →</a>"""


def render_sidebar(posts: list[Post]) -> str:
    lines = ['      <div class="sidebar-label">本站索引 · Index</div>']
    for i, post in enumerate(posts[:3]):
        short = post.title if len(post.title) <= 28 else post.title[:27] + "…"
        lines.append(
            f'      <a class="sidebar-item" href="{post.url}">\n'
            f'        <span class="si-num">{SIDEBAR_NUM[i]}.</span>\n'
            f'        <span class="si-title">{html.escape(short)}</span>\n'
            f'        <span class="si-tag">文章</span>\n'
            f"      </a>"
        )
    lines.extend(
        [
            '      <a class="sidebar-item" href="#articles">',
            '        <span class="si-num">iv.</span>',
            '        <span class="si-title">近期文章</span>',
            '        <span class="si-tag">文章</span>',
            '      </a>',
            '      <a class="sidebar-item" href="#about">',
            '        <span class="si-num">v.</span>',
            '        <span class="si-title">关于本站与作者</span>',
            '        <span class="si-tag">关于</span>',
            '      </a>',
            '      <a class="sidebar-item" href="disclaimer.html">',
            '        <span class="si-num">vi.</span>',
            '        <span class="si-title">免责声明</span>',
            '        <span class="si-tag">声明</span>',
            '      </a>',
        ]
    )
    return "\n".join(lines)


def render_featured_pair(posts: list[Post]) -> str:
    if len(posts) < 2:
        return ""
    a, b = posts[0], posts[1]
    return f"""    <div class="featured-paper">
      <div>
        <div class="fp-roman">{ROMAN[0]}</div>
        <div class="fp-type">Article · {html.escape(a.type_label)}</div>
        <a class="fp-title" href="{a.url}">{html.escape(a.title)}</a>
        <div class="fp-venue">已发布 · {a.date_display} · Clawed Actuary</div>
        <div class="fp-abstract">
          {html.escape(a.description)}
        </div>
        <div class="fp-tags">
{tags_html(a.categories)}
        </div>
        <a class="masthead-cta" href="{a.url}">阅读全文 →</a>
      </div>
      <div class="fp-right">
        <div class="fp-roman">{ROMAN[1]}</div>
        <div class="fp-type">Article · {html.escape(b.type_label)}</div>
        <a class="fp-title" href="{b.url}">{html.escape(b.title)}</a>
        <div class="fp-venue">已发布 · {b.date_display} · Clawed Actuary</div>
        <div class="fp-abstract">
          {html.escape(b.description)}
        </div>
        <div class="fp-tags">
{tags_html(b.categories)}
        </div>
        <a class="masthead-cta" href="{b.url}">阅读全文 →</a>
      </div>
    </div>"""


def render_papers_list(posts: list[Post]) -> str:
    rest = posts[2:]
    if not rest:
        return ""
    rows = ['    <div class="papers">']
    for i, post in enumerate(rest):
        num = ROMAN[i + 2] if i + 2 < len(ROMAN) else str(i + 3)
        rows.append(
            f"""      <div class="paper">
        <div class="p-num">{num}</div>
        <div class="p-body">
          <div class="p-type">Article · {html.escape(post.type_label)}</div>
          <a class="p-title" href="{post.url}">{html.escape(post.title)}</a>
          <div class="p-venue">已发布 · {post.date_display} · Clawed Actuary</div>
          <div class="p-tags">
{tags_html(post.categories)}
          </div>
        </div>
        <div class="p-year">{post.year}</div>
      </div>"""
        )
    rows.append("    </div>")
    return "\n".join(rows)


def render_blog_category_bar(posts: list[Post]) -> str:
    counts: dict[str, int] = {}
    for post in posts:
        for cat in post.categories:
            counts[cat] = counts.get(cat, 0) + 1

    sorted_cats = sorted(counts.keys(), key=lambda c: (-counts[c], c))
    lines = [
        '<div class="blog-category-bar" role="navigation" aria-label="文章分类">',
        '  <span class="blog-category-label">分类</span>',
        '  <div class="blog-categories">',
        f'    <button type="button" class="blog-category active" data-category="">全部'
        f' <span class="blog-category-count">({len(posts)})</span></button>',
    ]
    for cat in sorted_cats:
        lines.append(
            f'    <button type="button" class="blog-category" data-category="{html.escape(cat)}">'
            f"{html.escape(cat)}"
            f' <span class="blog-category-count">({counts[cat]})</span></button>'
        )
    lines.extend(["  </div>", "</div>"])
    return "\n".join(lines)


def render_blog_grid(posts: list[Post]) -> str:
    parts = [render_blog_category_bar(posts), '<div class="articles-grid" id="articles-grid">']
    for post in posts:
        cats_attr = html.escape(",".join(post.categories))
        parts.append(
            f"""  <a class="article-card" href="{post.url}" data-categories="{cats_attr}">
    <div class="a-kicker">{html.escape(post.kicker)}</div>
    <div class="a-title">{post.title_html}</div>
    <div class="a-excerpt">{html.escape(post.description)}</div>
    <div class="a-foot">
      <span class="a-date">{post.date_blog}</span>
      <span class="a-readtime">约 {post.reading_minutes} 分钟</span>
    </div>
  </a>"""
        )
    parts.append("</div>")
    return "\n".join(parts)


def load_site_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    data: dict = {}
    stack: list[tuple[int, dict]] = [(0, data)]

    for raw in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip() or ":" not in line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, val = line.strip().split(":", 1)
        key = key.strip()
        raw_val = val
        val = val.strip().strip('"').strip("'")

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        current = stack[-1][1]

        bare_key = line.strip().endswith(":")
        if bare_key and raw_val == "":
            child: dict = {}
            current[key] = child
            stack.append((indent, child))
        elif val.lower() in {"true", "false"}:
            current[key] = val.lower() == "true"
        else:
            current[key] = val

    return data


def fetch_giscus_ids(repo: str, category: str) -> tuple[str, str]:
    query = urllib.parse.urlencode(
        {"repo": repo, "branch": "main", "category": category}
    )
    url = f"https://giscus.app/api/repo?{query}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        payload = json.load(resp)
    return str(payload["repoId"]), str(payload["categoryId"])


def enrich_giscus_config(cfg: dict) -> dict:
    giscus = cfg.get("comments", {}).get("giscus", {})
    if not giscus:
        return cfg
    repo = giscus.get("repo", "")
    if not repo or (giscus.get("repo_id") and giscus.get("category_id")):
        return cfg
    try:
        repo_id, category_id = fetch_giscus_ids(repo, giscus.get("category", "General"))
        giscus["repo_id"] = repo_id
        giscus["category_id"] = category_id
        print(f"→ Giscus IDs resolved for {repo}", file=sys.stderr)
    except Exception as exc:
        print(f"⚠ Could not resolve Giscus IDs: {exc}", file=sys.stderr)
    return cfg


def write_features_json(cfg: dict) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    public_cfg = {
        "comments": cfg.get("comments", {}),
        "subscribe": {
            k: v
            for k, v in cfg.get("subscribe", {}).items()
            if k != "notify"
        },
        "pageviews": cfg.get("pageviews", {}),
        "analytics": cfg.get("analytics", {}),
    }
    payload = json.dumps(public_cfg, ensure_ascii=False, indent=2)
    (GENERATED_DIR / "site-features.json").write_text(payload + "\n", encoding="utf-8")
    js = (
        "/* Generated by scripts/sync_posts.py — do not edit */\n"
        "window.__CLAWED_SITE_FEATURES__ = "
        + json.dumps(public_cfg, ensure_ascii=False)
        + ";\n"
    )
    (GENERATED_DIR / "site-features.js").write_text(js, encoding="utf-8")


def sync_index(posts: list[Post]) -> None:
    if not posts:
        return
    text = INDEX_PATH.read_text(encoding="utf-8")
    text = replace_block(text, "MASTHEAD", render_masthead(posts[0]))
    text = replace_block(text, "SIDEBAR", render_sidebar(posts))
    articles = render_featured_pair(posts)
    papers = render_papers_list(posts)
    articles_block = articles + ("\n" + papers if papers else "")
    text = replace_block(text, "ARTICLES", articles_block)
    INDEX_PATH.write_text(text, encoding="utf-8")


def sync_blog(posts: list[Post]) -> None:
    text = BLOG_PATH.read_text(encoding="utf-8")
    text = replace_block(text, "BLOG", render_blog_grid(posts))
    BLOG_PATH.write_text(text, encoding="utf-8")


def main() -> int:
    posts = load_posts()
    if not posts:
        print("No published posts found.", file=sys.stderr)
        return 1

    cfg = enrich_giscus_config(load_site_config())
    write_features_json(cfg)
    sync_index(posts)
    sync_blog(posts)
    print(f"✓ Synced {len(posts)} posts → index.qmd, blog.qmd, _generated/site-features.json|.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
