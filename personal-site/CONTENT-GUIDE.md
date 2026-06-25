# 内容与图表规范 · clawedactuary.com.cn

> **Agent / 写稿前必读。** 结构模板见 `post-template.qmd`；发布流程见 `SITE-FEATURES.md`；每日队列见 `workflows/daily-research.json`。

---

## 一、文风与结构

### 口吻

- 结论先行，有观点；精算视角，数据说话
- **不要**官腔、套话、模板腔
- **禁止**标题或小节名里写「（先说结论）」「综上所述」等 AI 痕迹——用 `## 核心判断` 即可（对标 `posts/2026-06-22-l3-l4-mandatory-standard-insurance.qmd`）

### 文章骨架

1. YAML：`title` / `date` / `description` / `categories` / `author: 龙虾精算师` / `draft: false`
2. `post-kicker` → `post-title` → `post-meta` → `post-lead`
3. `## 核心判断`（分「对车企 / 对行业 / 对消费者」等短段）
4. 政策或数据方法 → 分析章节 → 跟踪点 → `## 局限与声明`
5. 可选 `::: {.post-note}` 方法论一句（见下文）
6. 文末链到相关文章，**不要**链内部仓库路径

### 锚点范文

| 类型 | 参考 |
|------|------|
| 舆情 + 精算判断 | `posts/2026-06-04-byd-zhijia-douyin-opinion.qmd` |
| 监管 + 定量估算 | `posts/2026-06-22-l3-l4-mandatory-standard-insurance.qmd` |
| 实验 / 建模 | `posts/2026-06-05-glm-fremtpl2-ai-exploration.qmd` |

### 禁止出现在正文的内容

- 内部目录（`data/…`、`tools/…`）、docx 报告路径、流水线命令
- 未标注假设的「官方数据」；精算估算须写「作者假设，非企业披露」
- 机构背书（文责个人，文末声明已有）

### post-note 写法

只写公开方法论，一行即可。示例：

```markdown
::: {.post-note}
方法论说明：2026-06-23 采集 6 条相关视频一级评论 1,335 条（去重），LLM 五类情感标注；主题分布为关键词辅助统计。
:::
```

---

## 二、图表规范

### 总原则

- **网站用图 ≠ Word 报告用图。** 报告脚本（`tools/gen_douyin_*_report.py`）字号按 A4 排版放大，**禁止**直接拷 `report_images/` 到站点。
- 舆情类图表统一走 **`scripts/export_opinion_charts.py`**，输出到 `images/<topic-slug>/`。

### 站点视觉参数

| 项 | 值 |
|----|-----|
| 纸色背景 | `#f8f5f0`（`figure` **与** `axes` 都要设，不能只改外侧） |
| 墨色文字 | `#1a1814` |
| 强调色 | `#8b2020` |
| 情感柱色 | 蓝 `#2171b5`、红 `#cb181d`、橙 `#e6550d`、浅蓝 `#6baed6`、灰 `#bdbdbd` |
| 主题横条 | `#2171b5` |
| 画布 | 宽约 7.2×4.0 in @ 160 dpi（≈ BYD 站图 1500×850 量级） |
| 字体 | PingFang SC / Heiti SC |

### 文件命名

- 情感分布：`sentiment-dist.png`（连字符，勿用 `sentiment_dist`）
- 主题分布：`topic-hits.png`
- 两期对比：`sentiment-compare.png`（如有）

### 文中引用

```markdown
![一级评论情感分布（N=1,335）](../images/huawei-qiankun/sentiment-dist.png){fig-alt="…"}
```

Quarto 会包成 `<figure>`，站点 CSS 自动加细边框（`theme/clawed.scss` → `.post-article figure img`）。

### 生成命令

```bash
cd personal-site
python3 scripts/export_opinion_charts.py huawei_qiankun   # 在脚本 DATASETS 里注册新数据集
```

新舆情项目：在 `export_opinion_charts.py` 的 `DATASETS` 增加条目后执行上述命令。

---

## 三、评论与分享

- **Giscus 主题：** `theme/giscus-clawed.css`（纸色底，勿改回 `preferred_color_scheme` / GitHub 白底）
- **分享栏：** `theme/clawed-share.html` 已含微信 / 朋友圈 / 复制 / 更多（本地无系统分享时 fallback 扫码）

---

## 四、发布前检查

```bash
cd personal-site
python3 scripts/export_opinion_charts.py <dataset>   # 若有新图
python3 scripts/sync_posts.py
quarto render
python3 scripts/daily_research.py publish-check
```

人工扫一眼：

- [ ] 无「（先说结论）」、无内部路径
- [ ] 图表米色底内外一致、尺寸与 BYD 文相当
- [ ] `description` 已填、`draft: false`

---

## 五、相关文件索引

| 文件 | 用途 |
|------|------|
| `CONTENT-GUIDE.md` | **本文** — 写文与图表规范 |
| `post-template.qmd` | 新文章骨架 |
| `SITE-FEATURES.md` | 评论 / 订阅 / 阅读量配置 |
| `scripts/export_opinion_charts.py` | 网站尺寸舆情图 |
| `skills/daily-research-publish/SKILL.md` | 每日自动化流水线 |
| `theme/giscus-clawed.css` | 评论区配色 |
| `theme/clawed.scss` | 站点设计 token（`--paper` 等） |
