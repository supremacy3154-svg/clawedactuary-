---
name: daily-research-publish
description: >-
  每日全自动发文：选出优先级最高的一篇，写完核对后 push main，
  并发送平安邮箱 HTML。用户提到每日发文、自动化工作流、定时写稿时使用。
---

# 每日深度研究发布（全自动）

站点：`personal-site/` → https://clawedactuary.com.cn

**写文、图表规范 → [`personal-site/CONTENT-GUIDE.md`](../personal-site/CONTENT-GUIDE.md) 与 [`personal-site/article-writing-prompt.md`](../personal-site/article-writing-prompt.md)**

配置：`personal-site/workflows/daily-research.json`  
触发：GitHub Actions `daily-article.yml`（工作日 09:30 上海时区）或 Cursor Automations

## 硬规则

1. **每天最多 1 篇。** 若 `posts/` 里已有今日日期的正式稿，停止，不要再写。
2. **自己选题并写全文。** 不要等用户确认选题，不要只交简报。
3. **核对通过后 `git push origin main`。** 不要只开草稿 PR 就结束。`publish.require_approval` 已为 false。
4. **push 之后立刻发个人邮件**到 `yanghailin508@pingan.com.cn`，主题不加【预览】。
5. **不要提交** `tools/smtp_config.py` 或 `data/article-emails/*`。
6. 文责个人：主观段落不要点名国内险企。

## 每日流程

```bash
cd personal-site
python3 scripts/daily_research.py brief
python3 scripts/daily_research.py pick
```

读 `pick` 的 JSON。`skip: true` 则退出。

### 选题优先级

1. 当日正在热议、且能落到保险/精算作业的新闻（定价、理赔、核保、责任、资本、监管、车险、前沿模型进作业系统）。
2. 有一手英文或监管原文可核对的题，高于只有转载口吻的题。
3. 队列里 `in_progress` / `pending` / `backlog` 仅在当日没有更热新题时使用。
4. 14 天内已写过的同一主体不续写。
5. 前沿大模型若正在热议，允许写 AI 题；热度不够时不要硬写 AI。

选定后用英文一手来源核对事实，再按站点中文稿写作。

### 写稿与图表

- YAML：`draft: false`，`author: 龙虾精算师`，`description` 必填
- `## 核心判断`；禁止「不是…而是…」、禁止括号堆说明、禁止点名平安
- 至少 2 张图、2 张表、5 个有来源的数字
- `images/<slug>/charts.json` + `gen_research_charts.py`；示意图用 GenerateImage 后转成真正 PNG
- `images/<slug>/data-sources.json`

### 核对

```bash
cd personal-site
python3 scripts/sync_posts.py
python3 scripts/gen_research_charts.py <slug>   # 若有 charts.json
python3 ../tools/render_post_html.py <slug>     # 无 Quarto 时用
python3 scripts/daily_research.py quality-check <slug>
python3 scripts/daily_research.py publish-check
```

`quality-check` 失败则改稿，不要 push。

### 发布

```bash
git add personal-site/posts personal-site/images personal-site/index.qmd personal-site/blog.qmd personal-site/workflows
git commit -m "post: <标题摘要>"
git push origin main
python3 tools/send_site_article_email.py <slug>
python3 personal-site/scripts/daily_research.py mark-published <slug>
```

SMTP 优先读环境变量 `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM`；否则读 gitignored 的 `tools/smtp_config.py`。Cloudflare 构建会另行给 Buttondown 订阅者发信。

## 定时触发

| 方式 | 说明 |
|------|------|
| GitHub Actions | `.github/workflows/daily-article.yml`，仓库密钥 `CURSOR_API_KEY`（必填）以及 SMTP 一组（推荐） |
| Cursor Automations | [cursor.com/automations](https://cursor.com/automations)，提示词用 `personal-site/workflows/daily-auto-publish-prompt.md`，仓库选本 repo，分支 `main` |
| 手动 | Actions → Daily article → Run workflow |

只保留一种调度，避免同一天写两篇。
