#!/usr/bin/env bash
# 每日深度研究发布 · 入口脚本（cron / launchd / GitHub Actions 调用）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SITE="${ROOT}/personal-site"
LOG_DIR="${ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG="${LOG_DIR}/daily-research-$(date +%Y%m%d).log"

exec >>"$LOG" 2>&1
echo "=== daily-research $(date -Iseconds) ==="

cd "$SITE"
python3 scripts/daily_research.py brief
python3 scripts/daily_research.py pick || true

BRIEF="${SITE}/_generated/daily-briefs/$(date +%Y-%m-%d).json"
TASK="${SITE}/_generated/daily-research-task.md"
if [[ -f "$BRIEF" ]]; then
  cat >"$TASK" <<EOF
# 每日研究任务 · $(date +%Y-%m-%d)

请读取 \`skills/daily-research-publish/SKILL.md\` 并**写完、核对、push main、发平安邮箱**。

## 简报
\`personal-site/_generated/daily-briefs/$(date +%Y-%m-%d).json\`

## 要求
- 今日最多 **1** 篇
- 选题用 \`python3 scripts/daily_research.py pick\`，不要等确认
- 核对：\`quality-check\` + \`publish-check\`
- **自动 git push origin main**，然后 \`python3 tools/send_site_article_email.py <slug>\`

## pick
\`\`\`json
$(python3 scripts/daily_research.py pick 2>/dev/null || echo '{}')
\`\`\`
EOF
  echo "任务文件: $TASK"
fi

echo "=== done ==="
