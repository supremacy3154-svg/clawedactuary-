# 内容与图表规范 · clawedactuary.com.cn

> **Agent / 写稿前必读。** 结构模板见 `post-template.qmd`；发布流程见 `SITE-FEATURES.md`；每日队列见 `workflows/daily-research.json`。

---

## 一、文风与结构

### 口吻

- 结论先行，有观点；精算视角，数据说话
- **不要**官腔、套话、模板腔
- **禁止**标题或小节名里写「（先说结论）」「综上所述」等 AI 痕迹——用 `## 核心判断` 即可（对标 `posts/2026-06-22-l3-l4-mandatory-standard-insurance.qmd`）
- **禁止**在主观判断、启示、建议段落中反复点名或暗示作者任职机构；文责个人，不借机构背书，也不暴露隶属关系（见下文「机构与署名」）

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

### 机构与署名

龙虾精算师为**个人笔名**，与任何机构无隶属关系。写稿时：

- **不要**在「对中国启示」「行业建议」「该抄 / 别抄」等主观段落中反复点名某一家国内险企（尤其不宜出现作者可能任职的机构名称）
- **不要**用「我们」「我司」或暗示内部视角的表述
- **可以**在报道事实、舆情数据、公开合作新闻中引用机构名（如某车企合作承保方出现在评论或公告里）——那是**事实陈述**，不是作者背书
- 行业分析默认指向**全行业 / 持牌财险公司**，而非单独拎出某一家

反例（避免）：

> 「对平安产险而言，应该……」「平安近 3 年已落地 xxx 单，说明……」

正例（推荐）：

> 「对国内持牌财险公司而言……」「工信部试点显示全行业已落地 1,500+ 单……」

### post-note 写法

只写公开方法论，一行即可。示例：

```markdown
::: {.post-note}
方法论说明：2026-06-23 采集 6 条相关视频一级评论 1,335 条（去重），LLM 五类情感标注；主题分布为关键词辅助统计。
:::
```

---

## 二、深度研究稿纪律（美国财险 / 案例拆解）

> 以下来自实际写稿与审稿反馈；**Agent 与 cron 写稿均须遵守**。配置镜像见 `workflows/daily-research.json` → `content.writing_rules`、`topic_selection`。

### 选题与发布

| 环节 | 规则 |
|------|------|
| **写稿前** | **选题须用户确认后再动笔**；早间 `brief` 只产出候选题，Agent **不得**未经确认直接写全文 |
| **push 前** | `publish.require_approval: true`；用户明确说「发布」后再 `git push` |
| **本地预览** | Quarto 在 `draft: true` 时渲染**空 HTML**；待审稿预览须 `draft: false` + `quarto render` |

### 用语

- 美国 **Commercial Auto**（营业货车 / 车队）→ 正文写 **「商用车险」**，**勿写「商业车险」**（易与国内财产险统称「商业险」混淆）
- 导语、摘要勿写「本文用…作引子」「下文不展开…」等**编者视角**；直接写读者要看的判断与事实
- **海外监管稿（日本、欧洲等）**：正文**全文中文**；日式行政术语（答申、改定、见合う、半税等）**禁止直写**，须换成「提交申报」「批准调价」「折半征收」等读者能懂的表述，或首次括号解释后只用中文
- **精算术语**：用中文常用说法（如「累计赔付占保费比例」），**禁止**「费率验证损害率」等中日混杂生造词
- **表格**：列数 ≤4，避免空列头对比表（易堆叠）；复杂对比拆成两段 prose 或两个小表（对标 BYD 舆情稿）

### 结构与文风

- **行业亏损 / 背景一节宜短**，主体写样本公司（产品、数据、赔付率）；**国内借鉴放后**，忌头重脚轻
- **口径说明**：仅保留美国特有或非显然概念（如 NAIC 子险口径、股息前 COR）；**COR、赔付率、滚动十二个月等基础项不解释**
- **证据闭环**：勿为凑 pillar 硬挂其他文章（如 AAA AI 图谱）——无本题证据则不引、不标 `AI` 分类
- 无公开 AI 落地披露时，**不写 AI 章节、不用 AI 当标题卖点**；能写的是 telematics / UBI / 里程定价 / 核保变量

### 图表

- **写前先规划**每张图要回答的问题（见 `workflows/daily-research.json` → `content.min_figures`）
- **禁止**无信息量的 **A vs B 双柱图**（尤其口径不同的两个单点，如「商车 vs 私车同比」）
- **禁止**为 2–3 个百分比拆分（如「+1.9% / +4.3%」）单独画柱状图——用**表格**即可
- **禁止**为作图而作图；无时间序列、无 ≥3 主体截面时，优先文字 + 表
- **禁止**因配色不对就删光图表——须改 `gen_research_charts.py` 配色（纸色 `#f8f5f0`、强调 `#8b2020`，与 BYD 站图一致）
- **优先**：时间序列、多主体截面分散（≥3）、机制表；单点对比用文字或表内一句带过
- 研究稿图表：`images/<slug>/charts.json` + `gen_research_charts.py`；关键数字 `data-sources.json` + `cross_check_research.py`

### 个人邮件

- `tools/send_site_article_email.py` 发送的 HTML **去掉**「文责个人，不代表任何任职机构」；**公网正文**文末声明保留
- 公网 push 后：`python3 tools/send_site_article_email.py <slug>`

---

## 三、图表规范（舆情 / 站点用图）

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

## 四、评论与分享

- **Giscus 主题：** `theme/giscus-clawed.css`（纸色底，勿改回 `preferred_color_scheme` / GitHub 白底）
- **分享栏：** `theme/clawed-share.html` 已含微信 / 朋友圈 / 复制 / 更多（本地无系统分享时 fallback 扫码）

---

## 五、发布前检查

```bash
cd personal-site
python3 scripts/export_opinion_charts.py <dataset>   # 若有新图
python3 scripts/sync_posts.py
quarto render
python3 scripts/review_article.py <slug>             # MiniMax 责编审阅，见 _generated/reviews/
python3 scripts/daily_research.py publish-check
```

人工扫一眼：

- [ ] 无「（先说结论）」、无内部路径、无「本篇不展开 / 本文统称」类元叙述
- [ ] 美国 Commercial Auto 已用「商用车险」；无多余基础口径表
- [ ] **海外稿无日式术语直写**；精算词用中文读者能懂的表述
- [ ] 图表非 trivial 柱图；`cross_check_research.py <slug>` 通过（若适用）
- [ ] **`review_article.py` 审阅意见已处理**（`_generated/reviews/<slug>.md`）
- [ ] 无反复点名国内险企、无暴露作者机构隶属的表述
- [ ] 图表米色底内外一致、尺寸与 BYD 文相当
- [ ] `description` 已填、`draft: false`

---

## 六、相关文件索引

| 文件 | 用途 |
|------|------|
| `CONTENT-GUIDE.md` | **本文** — 写文与图表规范 |
| `post-template.qmd` | 新文章骨架 |
| `SITE-FEATURES.md` | 评论 / 订阅 / 阅读量配置 |
| `scripts/export_opinion_charts.py` | 网站尺寸舆情图 |
| `skills/daily-research-publish/SKILL.md` | 每日自动化流水线 |
| `theme/giscus-clawed.css` | 评论区配色 |
| `theme/clawed.scss` | 站点设计 token（`--paper` 等） |
