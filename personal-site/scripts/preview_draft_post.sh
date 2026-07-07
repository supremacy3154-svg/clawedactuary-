#!/usr/bin/env bash
# 预览 draft: true 的文章：Quarto 默认只生成空壳 HTML，需临时 override draft:false
set -euo pipefail
cd "$(dirname "$0")/.."

SLUG="${1:-}"
PORT="${2:-4343}"

if [[ -z "$SLUG" ]]; then
  echo "用法: $0 <posts/xxx.qmd 或 slug> [port]" >&2
  exit 1
fi

if [[ "$SLUG" != *.qmd ]]; then
  SLUG="posts/${SLUG}.qmd"
fi
[[ "$SLUG" != posts/* ]] && SLUG="posts/$SLUG"

if [[ ! -f "$SLUG" ]]; then
  echo "找不到: $SLUG" >&2
  exit 1
fi

echo "→ 停掉 :${PORT} 上的 preview / http.server"
for pid in $(lsof -ti ":${PORT}" 2>/dev/null || true); do
  kill "$pid" 2>/dev/null || true
done
sleep 1

echo "→ 渲染（draft:false override）: $SLUG"
quarto render "$SLUG" -M draft:false

BASENAME=$(basename "$SLUG" .qmd)
BYTES=$(wc -c < "_site/posts/${BASENAME}.html" | tr -d ' ')
if [[ "$BYTES" -lt 1000 ]]; then
  echo "✗ HTML 仍过小（${BYTES} bytes），渲染可能失败" >&2
  exit 1
fi

touch _site/.nojekyll
echo "→ 静态服务 http://localhost:${PORT}/posts/${BASENAME}.html"
cd _site
exec python3 -m http.server "$PORT"
