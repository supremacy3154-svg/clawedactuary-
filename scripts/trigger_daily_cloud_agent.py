#!/usr/bin/env python3
"""Launch a Cursor Cloud Agent to write and publish today's top article.

Requires env:
  CURSOR_API_KEY
Optional SMTP (injected into the agent):
  SMTP_HOST SMTP_PORT SMTP_USERNAME SMTP_PASSWORD SMTP_FROM PERSONAL_EMAIL_TO
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "personal-site" / "workflows" / "daily-auto-publish-prompt.md"
REPO_URL = os.environ.get(
    "DAILY_ARTICLE_REPO_URL",
    "https://github.com/supremacy3154-svg/clawedactuary-",
)
API = "https://api.cursor.com/v1/agents"


def main() -> int:
    key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not key:
        print("SKIP: 未设置 CURSOR_API_KEY，无法拉起每日写稿 Agent。", file=sys.stderr)
        print("在 GitHub → Settings → Secrets 添加 CURSOR_API_KEY（Cursor Dashboard → API Keys）。", file=sys.stderr)
        return 0
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    env_vars = {}
    for name in (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "PERSONAL_EMAIL_TO",
    ):
        val = os.environ.get(name, "").strip()
        if val:
            env_vars[name] = val
    payload = {
        "prompt": {"text": prompt},
        "name": "Daily clawedactuary article",
        "repos": [{"url": REPO_URL, "startingRef": "main"}],
        "workOnCurrentBranch": True,
        "autoCreatePR": False,
    }
    if env_vars:
        payload["envVars"] = env_vars
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Cursor API {exc.code}: {detail}", file=sys.stderr)
        return 1
    agent = data.get("agent") or data
    print(json.dumps({"id": agent.get("id") or data.get("id"), "url": agent.get("url") or data.get("url")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
