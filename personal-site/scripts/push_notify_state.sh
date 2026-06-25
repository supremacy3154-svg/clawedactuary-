#!/usr/bin/env bash
# 发信成功后把 notify-state.json 推回 GitHub（需 GITHUB_TOKEN）
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_REL="personal-site/_generated/notify-state.json"
cd "$REPO_ROOT"

if [[ ! -f "$STATE_REL" ]]; then
  echo "⊘ notify-state.json missing — skip push"
  exit 0
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "⊘ GITHUB_TOKEN not set — notify-state stays local only"
  echo "  在 Cloudflare Pages → Environment variables 添加 GITHUB_TOKEN 以自动回写"
  exit 0
fi

REPO="${GITHUB_REPOSITORY:-supremacy3154-svg/clawedactuary-}"
BRANCH="${NOTIFY_STATE_BRANCH:-main}"

git add "$STATE_REL"
if git diff --staged --quiet; then
  echo "✓ notify-state unchanged — skip push"
  exit 0
fi

git -c user.name="Clawed Actuary Bot" \
    -c user.email="notify@clawedactuary.com.cn" \
    commit -m "$(cat <<'EOF'
chore: update notify-state after subscriber email [skip ci]

Auto-committed by Cloudflare Pages build after Buttondown send.
EOF
)"

REMOTE="https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO}.git"
git push "$REMOTE" "HEAD:${BRANCH}"
echo "✓ Pushed notify-state → ${REPO}@${BRANCH}"
