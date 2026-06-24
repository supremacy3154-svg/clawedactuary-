#!/usr/bin/env bash
# 清缓存并全量构建，避免 preview 仍显示旧版 HTML
set -euo pipefail
cd "$(dirname "$0")"

echo "→ 清理 .quarto 与 _site"
rm -rf .quarto _site

echo "→ 同步文章列表 / 站点配置"
python3 scripts/sync_posts.py

echo "→ quarto render"
quarto render

echo "→ 新文章邮件通知（需 BUTTONDOWN_API_KEY）"
python3 scripts/notify_subscribers.py

touch _site/.nojekyll
echo ""
echo "✓ 构建完成: $(pwd)/_site"
echo "  预览: quarto preview --port 4343"
echo "  若仍见旧版: 停掉旧 preview 进程后重开，浏览器 Cmd+Shift+R 硬刷新"
