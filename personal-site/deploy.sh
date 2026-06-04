#!/usr/bin/env bash
# Build static site into _site/ (ready for GitHub Pages, OSS, or any static host).
set -euo pipefail
cd "$(dirname "$0")"

echo "→ quarto render"
quarto render

touch _site/.nojekyll
echo ""
echo "✓ 产物目录: $(pwd)/_site"
echo "  本地预览: quarto preview"
echo ""
echo "上线方式（任选其一）:"
echo "  1) GitHub Pages: 推送 main 并启用 Settings → Pages → Source: GitHub Actions"
echo "  2) 手动上传: 将 _site/ 内全部文件上传到静态托管根目录"
echo "  3) rsync 示例: rsync -avz --delete _site/ user@host:/var/www/clawed-actuary/"
