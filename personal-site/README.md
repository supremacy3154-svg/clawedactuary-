# Clawed Actuary · 个人站点

纸感编辑风个人站（基于 `clawed-actuary.html` 设计，由 [Quarto](https://quarto.org/) 构建）。文章写在 `posts/*.qmd`。

**写文 / 图表规范：** [`CONTENT-GUIDE.md`](CONTENT-GUIDE.md)

## 本机预览

```bash
cd personal-site
quarto preview
```

## 构建

```bash
./deploy.sh
# 或
quarto render
```

静态产物在 `_site/`。

## 上线

### GitHub Pages（推荐）

1. 将本仓库推送到 GitHub（`main` 分支）。
2. 仓库 **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**。
3. 推送 `personal-site/` 变更后，工作流 [personal-site-pages.yml](../.github/workflows/personal-site-pages.yml) 会自动构建并发布。
4. 发布前在 `_quarto.yml` 把 `site-url` 改成你的 Pages 域名（如 `https://<user>.github.io/<repo>/`）。

### 其他静态托管

将 `_site/` 目录内容上传到 OSS、Cloudflare Pages、Vercel 等即可。

## 新建文章

复制 `post-template.qmd` → `posts/`，改 `title`、`date`、`draft: false` 后保存并重新 render。

## 微调已发布文章

编辑 `posts/你的文章.qmd` 顶部 YAML（标题、摘要、标签）与正文；保存后 `quarto preview` 即可预览。文章页底部自动出现**分享**（微信扫码、朋友圈复制链接、复制链接）。

## 分享说明

静态站无法像 App 一样一键调起微信朋友圈；当前实现为：

- **微信**：弹出当前页二维码，用手机微信扫码打开后转发
- **朋友圈**：复制链接，提示到微信内粘贴分享
- **复制链接**：通用

上线后请在 `_quarto.yml` 将 `site-url` 改为真实域名，二维码与链接才会指向正式地址。

## 文件说明

| 文件 | 说明 |
|------|------|
| `clawed-actuary.html` | 原始设计稿（单页 HTML） |
| `theme/clawed.scss` | 已接入 Quarto 的主题样式 |
| `theme/clawed-header.html` | Google Fonts 等 head 片段 |
| `index.qmd` | 首页（masthead + 研究索引 + 文章列表 + 关于） |
