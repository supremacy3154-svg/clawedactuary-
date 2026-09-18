#!/usr/bin/env python3
"""Render one Quarto post to _site HTML for email preview (no Quarto required)."""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import markdown

SITE = Path(__file__).resolve().parents[1] / "personal-site"


def render_slug(slug: str) -> Path:
    qmd = SITE / "posts" / f"{slug}.qmd"
    if not qmd.exists():
        raise FileNotFoundError(qmd)
    raw = qmd.read_text(encoding="utf-8")
    title = slug
    tm = re.search(r'^title:\s*"([^"]+)"', raw, re.M)
    if tm:
        title = tm.group(1)
    body = raw.split("---", 2)[2].strip() if raw.startswith("---") else raw
    body = re.sub(r"^:::\s*\{\.post-article\}\s*", "", body)
    body = re.sub(r"\n:::\s*$", "", body.strip())

    def fenced_div(src: str, klass: str) -> str:
        pattern = rf":::\s*\{{\.{klass}\}}\s*([\s\S]*?):::"

        def repl(m):
            inner_html = markdown.markdown(m.group(1).strip(), extensions=["tables", "sane_lists"])
            return f'<div class="{klass}">\n{inner_html}\n</div>'

        return re.sub(pattern, repl, src)

    body = fenced_div(body, "post-lead")
    body = fenced_div(body, "post-note")

    def img_repl(m):
        alt, src, figalt = m.group(1), m.group(2), m.group(3)
        return (
            f'<figure>\n<img src="{src}" alt="{figalt or alt}" />\n'
            f"<figcaption>{alt}</figcaption>\n</figure>"
        )

    body = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)\{fig-alt="([^"]*)"\}',
        img_repl,
        body,
    )
    placeholders: list[str] = []

    def stash(html: str) -> str:
        key = f"@@HTML{len(placeholders)}@@"
        placeholders.append(html)
        return key

    body = re.sub(r"<div[\s\S]*?</div>", lambda m: stash(m.group(0)), body)
    body = re.sub(r"<figure>[\s\S]*?</figure>", lambda m: stash(m.group(0)), body)
    body = re.sub(r"<h1[\s\S]*?</h1>", lambda m: stash(m.group(0)), body)
    html_md = markdown.markdown(body, extensions=["tables", "sane_lists"])
    for i, block in enumerate(placeholders):
        html_md = html_md.replace(f"@@HTML{i}@@", block)

    page = f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
</head>
<body>
<div class="post-article">
{html_md}
</div>
</body>
</html>
"""
    out_dir = SITE / "_site" / "posts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{slug}.html"
    out.write_text(page, encoding="utf-8")
    img_src = SITE / "images" / slug
    img_dst = SITE / "_site" / "images" / slug
    if img_src.exists():
        img_dst.mkdir(parents=True, exist_ok=True)
        for p in img_src.glob("*.png"):
            shutil.copy2(p, img_dst / p.name)
    print(out)
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: render_post_html.py SLUG", file=sys.stderr)
        return 1
    render_slug(sys.argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
