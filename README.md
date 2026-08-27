# English Learning Tools

一套三个 AI Agent Skill，覆盖英文学习的完整闭环：**遇见生词 → 初步学习 → 练习巩固 → 长期记忆**。

```
┌──────────────────────┐                          ┌──────────────────┐
│ english-reading-     │   import_review_vocab    │ vocab-drill      │
│ exercises            │ ─────────────────────→   │                  │
│ 读文章 · 遇见生词      │   （单向词流输送带）        │ SM2 调度 · 防遗忘 │
└──────────────────────┘                          └──────────────────┘
┌──────────────────────┐
│ english-writing      │   （独立，无依赖）
│ 雅思写作 · 批改 · 范文库│
└──────────────────────┘
```

## Skills

### [english-reading-exercises](english-reading-exercises/)

双入口：把英文文章变成交互式阅读练习页（划词即译、自动单词本、六种练习：单词释义 / 句型改写 / 摘要完形 / 句子重排 / 概念图 / 背诵段落），以及跨文章汇总复习页（Anki 式翻卡、句型运用、词汇重叠分析）。

- 输入：文章 URL / 粘贴文本 / Notion LR Materials 数据库
- 输出（`~/Desktop/English Learning/`）：`articles/*-reading.html`（单文件，浏览器打开即用）→ 根目录 `review-all.html` + `review-vocab.json`

### [vocab-drill](vocab-drill/)

独立通用记忆引擎：SM2 间隔重复调度，管「今天该复习哪几个词」。词源不限于阅读——自带 GRE / SAT / TOEFL / IELTS 词表，也可从任意文章提词或直接报词单。词卡带 quirky 例句和情境故事，学习记录落本地。

- **它不知道 reading 的存在**。整个套件里唯一的连接点是 reading 侧的 `import_review_vocab.py`，把复习汇总的词（推荐只导跨文章重复的 `--core`）单向灌进来。

### [english-writing](english-writing/)

雅思写作练习，独立无依赖：范文收录（划词进个人词库）+ 四项评分标准批改（TA/CC/LR/GRA 批注式批改页、个人库替换词推荐、重写循环）。

## 安装

整套 clone（或复制）到你的 Agent skills 目录：

```bash
git clone https://github.com/wanziwan666-crypto/english-learning-tools.git \
  ~/.agents/skills/english-learning-tools
```

三个 skill 保持 `english-learning-tools/<skill>/` 的兄弟布局 —— `import_review_vocab.py` 靠相对路径找 `vocab-drill/vocab.mjs`，必须整套安装这个桥才通。

skill 安装本身不执行任何代码：english-writing 的产出目录 `~/Desktop/English Writing/`（含 `essays/`、`corrections/`、`writing/` 子目录）和 english-reading-exercises 的 `~/Desktop/English Learning/articles/` 都会在安装后的第一次 skill 会话里由 agent 自动创建，无需手动建目录。

## 更新

已 clone 的用户在仓库目录跑一句即可（也可以让 agent 代跑）：

```bash
git pull
```

clone 过旧仓库名 `english-reading-skills` 的同样直接 pull —— GitHub 会对旧地址自动重定向，无需改 remote。通过 Download ZIP 或手动复制安装的是静态快照，更新需重新下载覆盖。

## 共享架构

三个 skill 由同一套模式构成：

- **Python 脚本 + HTML 模板**：数据 JSON 用 `json.dumps(..., ensure_ascii=False).replace("</", "<\\/")` 注入模板占位符（`</` 转义防止 `</script>` 提前闭合），生成自包含单文件 HTML，浏览器打开即用，无需服务器。
- **生成前校验**：`validate_data.py` 检查「原文逐字存在」「批注落在对应段落」等约束 —— LLM 编造不在原文中的句子是实测最高频 bug，校验不过不许出文件。
- **浏览器侧状态**：单词本 / 词本存 localStorage，按页面 slug 分 key；长期记忆类状态（vocab-drill 调度、雅思个人库）落本地 JSON 文件。
- **视觉**：navy / cream 手绘笔记本风，同一套 CSS 变量。
