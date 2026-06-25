#!/usr/bin/env bash
# 每日深度研究发布 · 入口脚本（cron / launchd / OpenClaw cron 调用）
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
python3 scripts/daily_research.py next || true

# 输出 Agent 任务文件，供 OpenClaw / Cursor 读取
BRIEF="${SITE}/_generated/daily-briefs/$(date +%Y-%m-%d).json"
TASK="${SITE}/_generated/daily-research-task.md"
if [[ -f "$BRIEF" ]]; then
  cat >"$TASK" <<EOF
# 每日研究任务 · $(date +%Y-%m-%d)

请读取 \`skills/daily-research-publish/SKILL.md\` 并执行今日流水线。

## 简报
\`personal-site/_generated/daily-briefs/$(date +%Y-%m-%d).json\`

## 要求
- 今日最多发布 **2** 篇深度稿（见 workflows/daily-research.json）
- 风格对齐 \`personal-site/posts/*.qmd\`（结论先行、数据表格、精算视角、龙虾精算师口吻）
- 写完后：\`python3 scripts/sync_posts.py\` → \`quarto render\` → \`python3 scripts/daily_research.py publish-check\`
- 默认 **不自动 git push**；确认后由用户或 Agent 提交推送

## 下一话题
\`\`\`json
$(python3 scripts/daily_research.py next 2>/dev/null || echo '{}')
\`\`\`
EOF
  echo "任务文件: $TASK"
fi

echo "=== done ==="
