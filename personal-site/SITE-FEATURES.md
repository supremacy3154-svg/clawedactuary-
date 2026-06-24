# 评论与邮件订阅配置

## 一键同步（发新文后）

```bash
cd personal-site
python3 scripts/sync_posts.py   # 更新首页 I/II/III + 文章列表
quarto render
```

Cloudflare 构建脚本已自动执行 `sync_posts.py`。

---

## 邮件订阅

编辑 `site-config.yml`：

### Buttondown（推荐）

1. 注册 <https://buttondown.com>
2. 创建 newsletter，用户名填到 `buttondown_username`
3. `provider: buttondown`

### Formspree

1. 注册 <https://formspree.io>，创建表单
2. 表单 ID 填到 `formspree_form_id`
3. `provider: formspree`

未配置时，页面会显示 RSS 订阅提示。

### 新文章自动通知（Buttondown API）

发新文并 push 后，构建脚本会调用 `scripts/notify_subscribers.py`：

1. 在 [Buttondown → Settings → API](https://buttondown.com/settings/api) 创建 API Key
2. 在 **Cloudflare Pages → Settings → Environment variables** 添加：
   - `BUTTONDOWN_API_KEY` = 你的 API Key（**Encrypt**）
   - 可选 `BUTTONDOWN_NOTIFY_MODE` = `send`（覆盖 `site-config.yml` 里的 `draft`）
3. `site-config.yml` → `subscribe.notify`：
   - `mode: draft` — 在 Buttondown 生成草稿，你确认后再发（默认，推荐）
   - `mode: send` — 构建时直接发给全部订阅者
4. 仅当 **本次 git commit 新增/修改了** `posts/*.qmd` 且该文不在 `notify-state.json` 时才会触发

已发过的文章 slug 记录在 `personal-site/_generated/notify-state.json`（需随仓库提交）。

---

## 访问统计

编辑 `site-config.yml` → `analytics`：

### Cloudflare Web Analytics（推荐，站点已在 Cloudflare）

1. [Cloudflare Dashboard](https://dash.cloudflare.com) → 你的域名 → **Web Analytics**（或 Analytics & Logs）
2. 添加站点 `clawedactuary.com.cn`，复制 **Beacon token**
3. 填入 `cloudflare_beacon_token`，设 `enabled: true`、`provider: cloudflare`
4. `python3 scripts/sync_posts.py && quarto render`

无 Cookie、轻量，与 Cloudflare Pages 同账号。

### Umami（备选）

1. 注册 [Umami Cloud](https://cloud.umami.is) 或自托管
2. 创建网站，复制 Website ID
3. `provider: umami`，填 `umami_website_id`

---

## 评论（Giscus）

1. GitHub 仓库 **Settings → General → Features** 打开 **Discussions**
2. 新建分类（默认 `General` 即可）
3. 打开 <https://giscus.app/zh-CN>，选择仓库，复制 `repo_id` / `category_id` 到 `site-config.yml`
4. 构建时 `sync_posts.py` 也会尝试自动拉取 ID（需 Discussions 已开启）

评论仅出现在 `/posts/` 文章页底部。
