#!/usr/bin/env python3
"""Notify Buttondown subscribers when a new post lands in this commit.

Requires BUTTONDOWN_API_KEY in the environment (Cloudflare Pages → Settings →
Environment variables). By default creates a *draft* email in Buttondown for
review; set subscribe.notify.mode to \"send\" in site-config.yml (or
BUTTONDOWN_NOTIFY_MODE=send) to publish immediately.

Detection: compares posts/*.qmd added/changed in the latest git commit.
"""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent
POSTS_DIR = SITE_DIR / "posts"
CONFIG_PATH = SITE_DIR / "site-config.yml"
QUARTO_CONFIG = SITE_DIR / "_quarto.yml"
STATE_PATH = SITE_DIR / "_generated" / "notify-state.json"
BUTTONDOWN_API = "https://api.buttondown.com/v1/emails"
SEND_STATUSES = frozenset({"about_to_send", "in_flight", "sent", "scheduled", "resending"})


def load_yaml_block(text: str) -> dict[str, object]:
    meta: dict[str, object] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.lower() in {"true", "false"}:
            meta[key] = val.lower() == "true"
        else:
            meta[key] = val
    return meta


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


def site_url() -> str:
    if not QUARTO_CONFIG.exists():
        return "https://clawedactuary.com.cn"
    for line in QUARTO_CONFIG.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("site-url:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return "https://clawedactuary.com.cn"


def parse_post(path: Path) -> dict | None:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return None
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return None
    meta = load_yaml_block(parts[1])
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
    return {
        "slug": slug,
        "title": title,
        "description": desc,
        "date": post_date.isoformat(),
        "url": f"{site_url().rstrip('/')}/posts/{slug}.html",
    }


def load_posts() -> list[dict]:
    posts: list[dict] = []
    for path in sorted(POSTS_DIR.glob("*.qmd")):
        post = parse_post(path)
        if post:
            posts.append(post)
    return posts


def git_changed_post_slugs() -> set[str]:
    repo_root = SITE_DIR.parent
    path_args = ["--", "personal-site/posts/", "posts/"]
    for rev_range in ("HEAD~1..HEAD", "HEAD^..HEAD"):
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", rev_range, *path_args],
                cwd=repo_root,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            slugs = _slugs_from_diff_lines(out.splitlines())
            if slugs:
                return slugs
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return set()


def _slugs_from_diff_lines(lines: list[str]) -> set[str]:
    slugs: set[str] = set()
    for line in lines:
        line = line.strip()
        if not line.endswith(".qmd"):
            continue
        name = Path(line).name
        if name.startswith("_") or name == "post-template.qmd":
            continue
        slugs.add(Path(name).stem)
    return slugs


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"notified_slugs": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"notified_slugs": []}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def posts_to_notify(posts: list[dict]) -> list[dict]:
    cfg = load_site_config()
    notify_cfg = cfg.get("subscribe", {}).get("notify", {})
    if notify_cfg.get("enabled") is False:
        return []

    state = load_state()
    notified = set(state.get("notified_slugs", []))

    changed = git_changed_post_slugs()
    if not changed:
        # Cloudflare Pages 等浅克隆（depth=1）拿不到 HEAD~1，改为对照 notify-state
        print(
            "⚠ git diff unavailable (shallow clone?) — using notify-state diff",
            file=sys.stderr,
        )
        changed = {p["slug"] for p in posts if p["slug"] not in notified}

    candidates: list[dict] = []
    for post in posts:
        slug = post["slug"]
        if slug not in changed or slug in notified:
            continue
        candidates.append(post)
    return candidates


def notify_mode() -> str:
    env_mode = os.environ.get("BUTTONDOWN_NOTIFY_MODE", "").strip().lower()
    if env_mode in {"draft", "send"}:
        return env_mode
    cfg = load_site_config()
    mode = str(cfg.get("subscribe", {}).get("notify", {}).get("mode", "draft")).lower()
    return mode if mode in {"draft", "send"} else "draft"


def subject_prefix() -> str:
    cfg = load_site_config()
    return str(cfg.get("subscribe", {}).get("notify", {}).get("subject_prefix", ""))


def build_email_body(post: dict) -> str:
    title = html.escape(post["title"])
    desc = html.escape(post["description"])
    url = html.escape(post["url"], quote=True)
    return (
        "<!-- buttondown-editor-mode: fancy -->\n"
        f'<h1 style="color:#1a1814;font-weight:400;margin:0 0 0.75em;line-height:1.35;">'
        f"{title}</h1>\n"
        f'<p style="color:#4a4740;line-height:1.75;font-size:18px;margin:0 0 1.25em;">'
        f"{desc}</p>\n"
        f'<p style="margin:0 0 2em;">'
        f'<a href="{url}" style="display:inline-block;padding:12px 22px;'
        f"background:#1a1814;color:#f8f5f0 !important;text-decoration:none;"
        f'font-size:17px;font-weight:600;letter-spacing:0.02em;">阅读全文 →</a>'
        f"</p>\n"
        f'<hr style="border:none;border-top:1px solid #e0dcd4;margin:2em 0;">\n'
        f'<p style="color:#8a8680;font-size:14px;line-height:1.6;margin:0;">'
        f"你收到这封邮件是因为订阅了 Clawed Actuary（龙虾精算师）。"
        f"若不想再收到更新，请使用邮件中的退订链接。</p>"
    )


def create_buttondown_email(api_key: str, post: dict, mode: str) -> dict:
    payload: dict[str, object] = {
        "subject": f"{subject_prefix()}{post['title']}",
        "body": build_email_body(post),
    }
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "clawedactuary-notify/1.0",
        "X-API-Version": "2026-04-01",
    }
    if mode == "draft":
        payload["status"] = "draft"
    else:
        # Buttondown API ≥2026-04-01 defaults to draft; must set about_to_send to publish
        payload["status"] = "about_to_send"
        headers["X-Buttondown-Live-Dangerously"] = "true"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BUTTONDOWN_API, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def send_buttondown_draft(api_key: str, email_id: str) -> dict:
    url = f"{BUTTONDOWN_API}/{email_id}"
    payload = json.dumps({"status": "about_to_send"}).encode("utf-8")
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "clawedactuary-notify/1.0",
        "X-API-Version": "2026-04-01",
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main() -> int:
    api_key = os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if not api_key:
        print("⊘ BUTTONDOWN_API_KEY not set — skip subscriber notify", file=sys.stderr)
        return 0

    if len(sys.argv) >= 3 and sys.argv[1] == "send-draft":
        email_id = sys.argv[2]
        try:
            result = send_buttondown_draft(api_key, email_id)
            print(
                f"✓ Sent draft {email_id} → status={result.get('status', '?')}",
                file=sys.stderr,
            )
            return 0
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"✗ Buttondown API error: {exc.code} {body}", file=sys.stderr)
            return 1

    posts = load_posts()
    to_notify = posts_to_notify(posts)
    if not to_notify:
        print("✓ No new posts to notify", file=sys.stderr)
        return 0

    mode = notify_mode()
    state = load_state()
    notified = list(state.get("notified_slugs", []))

    for post in to_notify:
        try:
            result = create_buttondown_email(api_key, post, mode)
            email_id = result.get("id", "?")
            status = str(result.get("status", ""))
            if mode == "send" and status not in SEND_STATUSES:
                print(
                    f"✗ Buttondown returned status={status!r} (expected send) "
                    f"for «{post['title']}» (id={email_id})",
                    file=sys.stderr,
                )
                return 1
            print(
                f"✓ Buttondown email {mode} for «{post['title']}» "
                f"(id={email_id}, status={status})",
                file=sys.stderr,
            )
            if post["slug"] not in notified:
                notified.append(post["slug"])
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"✗ Buttondown API error for {post['slug']}: {exc.code} {body}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"✗ Failed to notify for {post['slug']}: {exc}", file=sys.stderr)
            return 1

    save_state({"notified_slugs": notified})
    print(f"✓ Updated {STATE_PATH.relative_to(SITE_DIR)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
