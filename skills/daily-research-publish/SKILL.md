---
name: daily-research-publish
description: >-
  每日深度研究发布流水线：结合新闻热点与话题队列，为 clawedactuary.com.cn
  撰写 1–2 篇车险/智驾/精算深度稿并发布。用户提到「每日发文」「自动化工作流」、
  「深度研究报告」「热点政策」时使用。
---

# 每日深度研究发布

站点：`personal-site/` → https://clawedactuary.com.cn

**写文、图表、评论区规范 → 必读 [`personal-site/CONTENT-GUIDE.md`](../../personal-site/CONTENT-GUIDE.md)**

## 配置与状态

| 文件 | 用途 |
|------|------|
| `personal-site/workflows/daily-research.json` | 话题队列、新闻检索词、每日上限 |
| `personal-site/scripts/daily_research.py` | 简报 / 队列 / 发布检查 |
| `scripts/run_daily_research.sh` | cron / launchd 入口 |
| `personal-site/_generated/daily-briefs/YYYY-MM-DD.json` | 当日简报 |
| `personal-site/_generated/daily-research-task.md` | Agent 任务摘要 |

## 每日流程（Agent 执行）

### 1. 启动

```bash
bash scripts/run_daily_research.sh
# 或
cd personal-site && python3 scripts/daily_research.py brief && python3 scripts/daily_research.py next
```

阅读 `_generated/daily-briefs/<today>.json`：
- `discovery.search_plan` — 今日执行的宽网/事件类型/探索/carrier 查询
- `topic_suggestions` / `recommendation` — 按事件类型+pillar 打分后的选题推荐
- `workflows/daily-research.json` 中的 `topic_queue`（仅作备选）

### 2. 选题（1 篇/天，须用户确认）

优先级：

1. 当日 `daily-briefs/<today>.json` 的 `topic_suggestions` / `recommendation`
2. `status: in_progress` → `pending` 队列项
3. 与用户讨论后自拟题并 `queue-add`

**写稿前必须经用户确认选题**（`topic_selection.require_user_approval_before_write`）。早间 cron **只生成 brief**，不自动写 `.qmd` 全文。

### 3. 研究与写稿

**写稿纪律 → 必读 [CONTENT-GUIDE.md §二](../../personal-site/CONTENT-GUIDE.md)**（商用车险用语、结构、图表、禁止元叙述、AI/引用边界、邮件声明）。

**风格锚点**（必读 `CONTENT-GUIDE.md` 与现有文章）：

- `posts/2026-06-04-byd-zhijia-douyin-opinion.qmd` — 舆情 + 精算判断
- `posts/2026-06-22-l3-l4-mandatory-standard-insurance.qmd` — 监管 + 定量估算
- `post-template.qmd` — 结构模板

**结构要求：**

- YAML：`title`, `date`, `description`, `categories`, `author: 龙虾精算师`, `draft: false`
- 正文：`post-kicker` → `post-title` → `post-meta` → `post-lead` → **核心判断**（勿写「先说结论」等套话） → 数据/政策 → 跟踪点 → 局限声明
- 口吻：结论先行、有观点、数据表格、精算视角；避免官腔

**数据源（按话题选用）：**

| 类型 | 路径 / 工具 |
|------|-------------|
| 抖音舆情 | `data/douyin_*` + `tools/gen_douyin_*_report.py` |
| 新闻热点 | `tvly search "…" --time-range week --json` |
| 政策原文 | 官网 / 强标 PDF / 用户提供的材料 |

图片：图表放 `personal-site/images/<topic>/`；舆情类用 `python3 scripts/export_opinion_charts.py <dataset>` 生成网站尺寸图（勿直接用 Word 报告大图）。

### 4. 构建与检查

```bash
cd personal-site
python3 scripts/sync_posts.py    # 同步首页 + blog 列表 + 阅读时间
quarto render
python3 scripts/daily_research.py publish-check
python3 scripts/cross_check_research.py <slug>   # 研究稿
```

### 5. 发布与个人邮件

默认 **不自动 push**（`publish.require_approval: true`）。用户说「发布」后再 push。

个人邮件（**不含**「文责个人…」句）：

```bash
python3 tools/send_site_article_email.py <slug>
```

### 6. Git 发布（用户确认后）

```bash
cd /path/to/repo
git add personal-site/posts/ personal-site/images/ personal-site/index.qmd personal-site/blog.qmd personal-site/workflows/
git commit -m "post: <标题摘要>"
git push origin main
```

Cloudflare Pages 自动构建；新文章触发 `notify_subscribers.py`（Buttondown）。

更新队列：将对应 `topic_queue[].status` 改为 `published`；运行：

```bash
python3 scripts/daily_research.py mark-published <slug> <topic_id>
```

## 定时触发（本机）

安装 launchd（每天 08:00 生成简报与任务文件）：

```bash
cp scripts/launchd/com.clawedactuary.daily-research.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.clawedactuary.daily-research.plist
```

实际写稿与 push 建议由 **OpenClaw cron** 或用户会话中的 Agent 在 09:30 / 18:00 执行（见 `schedule.publish_windows`）。

## 舆情类话题标准流水线

以比亚迪 / 华为项目为范本：

```
视频链接 → crawl_douyin_* → dedup → LLM 情感标注 → gen_*_report.py → 提炼网站长文
```

华为：`data/douyin_huawei_qiankun/` · `tools/douyin_huawei_finish_pipeline.sh`

## 红线

- 不把 API Key 写进仓库
- 文首/文末声明：个人研究、不代表机构
- **主观段落勿反复点名国内险企，勿暴露作者机构隶属**（见 `CONTENT-GUIDE.md` →「机构与署名」）
- 精算估算标注「作者假设，非官方披露」
- 不自动 push 除非用户明确要求或 `auto_git_push: true`
