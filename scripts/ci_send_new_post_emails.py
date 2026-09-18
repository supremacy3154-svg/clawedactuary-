#!/usr/bin/env python3
"""CI helper: email newly added posts/*.qmd on a main push."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def new_slugs() -> list[str]:
    before = os.environ.get("GITHUB_EVENT_BEFORE") or ""
    if not before or set(before) <= {"0"}:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD", "--", "personal-site/posts"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    else:
        proc = subprocess.run(
            ["git", "diff", "--name-only", before, "HEAD", "--", "personal-site/posts"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    slugs = []
    for line in (proc.stdout or "").splitlines():
        p = Path(line.strip())
        if p.suffix == ".qmd" and not p.name.startswith("_"):
            slugs.append(p.stem)
    return slugs


def main() -> int:
    if not os.environ.get("SMTP_PASSWORD", "").strip():
        print("SKIP: 未配置 SMTP_PASSWORD，由写稿 Agent 发信。")
        return 0
    slugs = new_slugs()
    if not slugs:
        print("没有新增 posts/*.qmd")
        return 0
    sys.path.insert(0, str(ROOT / "tools"))
    send = ROOT / "tools" / "send_site_article_email.py"
    for slug in slugs:
        print(f"→ 发送 {slug}")
        proc = subprocess.run([sys.executable, str(send), slug], cwd=ROOT)
        if proc.returncode != 0:
            return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
