#!/usr/bin/env python3
"""Notify Buttondown subscribers when a new post lands in this commit.

Requires BUTTONDOWN_API_KEY in the environment (Cloudflare Pages → Settings →
Environment variables). By default creates a *draft* email in Buttondown for
review; set subscribe.notify.mode to \"send\" in site-config.yml (or
BUTTONDOWN_NOTIFY_MODE=send) to publish immediately.

Detection: compares posts/*.qmd added/changed in the latest git commit.
"""

from __future__ import annotations

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
    try:
        out = subprocess.check_output(
            [
                "git",
                "diff",
                "--name-only",
                "HEAD~1",
                "HEAD",
                "--",
                "personal-site/posts/",
                "posts/",
            ],
            cwd=SITE_DIR.parent,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    slugs: set[str] = set()
    for line in out.splitlines():
        line = line.strip()
        if not line.endswith(".qmd"):
            continue
        name = Path(line).name
        if name == "post-template.qmd":
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

    changed = git_changed_post_slugs()
    if not changed:
        print("⊘ No post changes in latest commit — skip notify", file=sys.stderr)
        return []

    state = load_state()
    notified = set(state.get("notified_slugs", []))

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
    return (
        f"# {post['title']}\n\n"
        f"{post['description']}\n\n"
        f"[阅读全文 →]({post['url']})\n\n"
        "---\n\n"
        "你收到这封邮件是因为订阅了 Clawed Actuary（龙虾精算师）。"
        "若不想再收到更新，请使用邮件中的退订链接。"
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
    }
    if mode == "draft":
        payload["status"] = "draft"
    else:
        headers["X-Buttondown-Live-Dangerously"] = "true"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BUTTONDOWN_API, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main() -> int:
    api_key = os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if not api_key:
        print("⊘ BUTTONDOWN_API_KEY not set — skip subscriber notify", file=sys.stderr)
        return 0

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
            print(
                f"✓ Buttondown email {mode} for «{post['title']}» (id={email_id})",
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
