#!/usr/bin/env python3
"""Send a clawedactuary.com.cn post as HTML email (same format as glm_article_email.html)."""
from __future__ import annotations

import argparse
import re
import smtplib
import ssl
import sys
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SITE_HTML = BASE / "personal-site" / "_site" / "posts"
DEFAULT_TO = "yanghailin508@pingan.com.cn"

SMTP_HOST = "smtp.sina.com"
SMTP_PORT = 465
USERNAME = "pajsxiaolongxia2@sina.com"
PASSWORD = "60207bc4f5c572f7"
FROM_ADDR = "pajsxiaolongxia2@sina.com"

EMAIL_CSS = """
body { font-family: "PingFang SC", "Microsoft YaHei", "STHeiti", sans-serif;
       background: #f8f5f0; color: #1a1814; max-width: 960px; margin: 0 auto; padding: 24px; }
.post-kicker { color: #8b2020; font-size: 13px; letter-spacing: 0.08em; }
.post-title { font-size: 28px; line-height: 1.25; margin: 8px 0; }
.post-meta { color: #4a4740; font-size: 14px; margin-bottom: 20px; }
.post-lead { background: #f0ece5; border-left: 4px solid #8b2020; padding: 16px 20px; margin: 20px 0; }
.post-note { color: #4a4740; font-size: 14px; border-top: 1px solid #bab6b0; padding-top: 12px; margin-top: 24px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }
th, td { border: 1px solid #bab6b0; padding: 6px 10px; }
th { background: #f0ece5; }
img { max-width: 100%; height: auto; display: block; margin: 12px 0; }
h2 { border-bottom: 1px solid #bab6b0; padding-bottom: 6px; margin-top: 28px; font-size: 20px; }
h3 { font-size: 16px; margin-top: 20px; }
p, li { line-height: 1.7; font-size: 15px; }
"""


def strip_scripts(html: str) -> str:
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<nav\b[^>]*>.*?</nav>", "", html, flags=re.S | re.I)
    return html


def latex_to_html(tex: str) -> str:
    s = tex.strip()
    s = re.sub(r"^\\[\[\(]", "", s)
    s = re.sub(r"\\[\]\)]$", "", s)
    s = s.replace(r"\approx", " ≈ ")
    s = s.replace(r"\%", "%")
    s = s.replace(r"\times", "×")
    s = re.sub(r"\^{([^}]+)}", r"<sup>\1</sup>", s)
    s = re.sub(r"_\{([^}]+)\}", r"<sub>\1</sub>", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fix_math_spans(html: str) -> str:
    """Email clients don't run MathJax; convert Quarto math spans to HTML."""
    display_style = (
        "text-align:center;font-size:18px;margin:20px 0;"
        "font-family:Georgia,'Times New Roman',serif;"
    )

    html = re.sub(
        r'<p>\s*<span class="math display">([\s\S]*?)</span>\s*</p>',
        lambda m: f'<p style="{display_style}">{latex_to_html(m.group(1))}</p>',
        html,
    )
    html = re.sub(
        r'<span class="math inline">([\s\S]*?)</span>',
        lambda m: latex_to_html(m.group(1)),
        html,
    )
    html = re.sub(
        r'<span class="math display">([\s\S]*?)</span>',
        lambda m: f'<p style="{display_style}">{latex_to_html(m.group(1))}</p>',
        html,
    )
    return html


def strip_internal_email_boilerplate(html: str) -> str:
    """Personal email omits public-site liability disclaimer."""
    html = re.sub(r"<li>\s*文责个人[^<]*</li>\s*", "", html, flags=re.I)
    html = re.sub(r"<p>\s*文责个人[^<]*</p>\s*", "", html, flags=re.I)
    return html


def extract_post_article(html: str) -> str:
    m = re.search(r'<div class="post-article">([\s\S]*?)</div>\s*\n\s*\n\s*\n</main>', html)
    if not m:
        m = re.search(r'<div class="post-article">([\s\S]*?)</div>', html)
    return m.group(1).strip() if m else ""


def wrap_html(title: str, inner: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{EMAIL_CSS}
</style>
</head>
<body>
<div class="post-article">
{inner}
</div>
</body>
</html>"""


def attach_cid_images(html: str, html_dir: Path) -> tuple[str, list[tuple[str, Path]]]:
    attachments: list[tuple[str, Path]] = []
    seen: dict[str, str] = {}

    def repl(m):
        src = m.group(1)
        if src.startswith("cid:") or src.startswith("data:"):
            return m.group(0)
        path = (html_dir / src).resolve()
        if not path.exists():
            return m.group(0)
        key = str(path)
        if key not in seen:
            cid = f"img_{len(seen) + 1}@clawedactuary"
            seen[key] = cid
            attachments.append((cid, path))
        cid = seen[key]
        alt = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
        return f'<img src="cid:{cid}" alt="{alt}" style="max-width:100%;height:auto;" />'

    html = re.sub(
        r'<img[^>]+src="([^"]+\.(?:png|jpg|jpeg|gif|webp))"[^>]*alt="([^"]*)"[^>]*/?>',
        repl,
        html,
        flags=re.I,
    )
    html = re.sub(
        r'<img[^>]+src="([^"]+\.(?:png|jpg|jpeg|gif|webp))"[^>]*/?>',
        repl,
        html,
        flags=re.I,
    )
    return html, attachments


def page_title(html: str) -> str:
    m = re.search(r'<h1 class="post-title">([\s\S]*?)</h1>', html)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    m = re.search(r"<title>([^<]+)</title>", html, re.I)
    return m.group(1).split("–")[0].strip() if m else "Clawed Actuary"


def send_html(to: str, subject: str, html: str, images: list[tuple[str, Path]]) -> None:
    msg = MIMEMultipart("related")
    msg["From"] = FROM_ADDR
    msg["To"] = to
    msg["Subject"] = subject
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)
    for cid, path in images:
        subtype = path.suffix.lstrip(".").lower()
        if subtype == "jpg":
            subtype = "jpeg"
        img = MIMEImage(path.read_bytes(), _subtype=subtype)
        img.add_header("Content-ID", f"<{cid}>")
        img.add_header("Content-Disposition", "inline", filename=path.name)
        msg.attach(img)
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as s:
        s.login(USERNAME, PASSWORD)
        s.sendmail(FROM_ADDR, [to], msg.as_string())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", help="post slug, e.g. 2026-06-25-corgi-ai-insurance-study")
    parser.add_argument("--to", default=DEFAULT_TO)
    parser.add_argument("--subject-prefix", default="")
    args = parser.parse_args()

    html_path = SITE_HTML / f"{args.slug}.html"
    if not html_path.exists():
        print(f"✗ 未找到站点 HTML，请先 quarto render: {html_path}", file=sys.stderr)
        return 1

    raw = strip_scripts(html_path.read_text(encoding="utf-8"))
    inner = extract_post_article(raw)
    if not inner:
        print("✗ 无法提取 post-article", file=sys.stderr)
        return 1

    inner = strip_internal_email_boilerplate(inner)
    inner = fix_math_spans(inner)
    title = page_title(raw)
    subject = f"{args.subject_prefix}{title}"
    body = wrap_html(title, inner)
    body, images = attach_cid_images(body, html_path.parent)

    out = BASE / "data" / "article-emails" / f"{args.slug}_email.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")

    send_html(args.to, subject, body, images)
    print(f"✅ 已发送站点原文 HTML → {args.to}", file=sys.stderr)
    print(f"   {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
