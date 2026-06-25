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
   - 可选 `BUTTONDOWN_NOTIFY_MODE` = `draft`（覆盖 `site-config.yml` 里的自动发送）
3. `site-config.yml` → `subscribe.notify`：
   - `mode: send` — 构建时**直接发给全部订阅者**（当前默认）
   - `mode: draft` — 仅在 Buttondown 生成草稿，你确认后再发
4. 新文章触发逻辑见 `notify_subscribers.py`（浅克隆时用 `notify-state.json` 补判）
5. `mode: send` 时 API 须传 `status: about_to_send`（Buttondown API ≥2026-04-01 默认 draft）
6. **发信成功后** `cloudflare-build.sh` 会调用 `push_notify_state.sh` 自动提交 `notify-state.json`（需 Cloudflare 环境变量 `GITHUB_TOKEN`）

**补发卡在 draft 的邮件：**

```bash
BUTTONDOWN_API_KEY=xxx python3 scripts/notify_subscribers.py send-draft em_xxxxx
```

---

## 文章阅读量

每篇文章标题下方 meta 行显示 **「阅读 N 次」**（`pageviews` 配置 + Cloudflare KV）。

1. `site-config.yml` → `pageviews.enabled: true`（已默认开启）
2. Cloudflare Pages 绑定 KV 命名空间 `PAGE_VIEWS`（步骤见 [DEPLOY-CLOUDFLARE.md](./DEPLOY-CLOUDFLARE.md)）
3. 访客打开文章页时自动 +1（同浏览器会话只计一次）

---

## 全站访问统计（可选信标）

编辑 `site-config.yml` → `analytics`（与文章阅读量无关；你已在 CF Web Analytics 看板有数据时可不开）：

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
