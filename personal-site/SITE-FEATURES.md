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

---

## 评论（Giscus）

1. GitHub 仓库 **Settings → General → Features** 打开 **Discussions**
2. 新建分类（默认 `General` 即可）
3. 打开 <https://giscus.app/zh-CN>，选择仓库，复制 `repo_id` / `category_id` 到 `site-config.yml`
4. 构建时 `sync_posts.py` 也会尝试自动拉取 ID（需 Discussions 已开启）

评论仅出现在 `/posts/` 文章页底部。
