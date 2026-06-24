#!/usr/bin/env bash
# Cloudflare Pages 构建脚本（在仓库根目录执行，见 DEPLOY.md）
set -euo pipefail

QUARTO_VERSION="${QUARTO_VERSION:-1.6.40}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SITE_DIR="${REPO_ROOT}/personal-site"

echo "→ 安装 Quarto ${QUARTO_VERSION} (linux-amd64)"
TMP="$(mktemp -d)"
curl -fsSL \
  "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.tar.gz" \
  -o "${TMP}/quarto.tar.gz"
mkdir -p "${TMP}/quarto"
tar -xzf "${TMP}/quarto.tar.gz" -C "${TMP}/quarto" --strip-components=1
export PATH="${TMP}/quarto/bin:${PATH}"
quarto --version

echo "→ 同步文章列表 / 首页"
python3 "${SITE_DIR}/scripts/sync_posts.py"

echo "→ 渲染站点 ${SITE_DIR}"
cd "${SITE_DIR}"
quarto render
touch _site/.nojekyll

echo "✓ 产物: ${SITE_DIR}/_site"
