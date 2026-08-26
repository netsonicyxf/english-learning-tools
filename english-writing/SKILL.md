---
name: "english-writing"
description: "雅思写作练习系统：两个入口 —— (1) 范文收录：传入一篇雅思范文，生成可划词的交互式阅读页，划词即收进单词本（localStorage），可导出为 txt；(2) 批改作文：给题目则生成写作页（打开时弹窗自选倒计时时长），或直接粘贴写好的作文，agent 生成按雅思四项评分标准（TA/CC/LR/GRA）的批注式批改 HTML，薄弱处高亮并推荐个人库里的更好替换词，含「重写」按钮循环练习。当用户说 '雅思作文'、'雅思写作'、'范文收录'、'批改作文'、'写作练习'、'IELTS writing'、'帮我改作文'、'生成写作页面'、'收录好词' 等时触发。"
---

# IELTS Writing Practice

帮助用户建个人「好词好句 / 同义替换库」并循环练习雅思写作与批改。

## 前置条件

- **Python 3**：用脚本把 JSON 注入 HTML 模板（避免手工转义出错）。
- **浏览器**：生成的 HTML 用浏览器打开即可交互。
- **本 skill 目录**：脚本与模板都相对 `SKILL.md` 所在目录定位，不要写死绝对路径。
- **生成文件目录**：`~/Desktop/IELTS Writing/`（首次运行自动创建）。

## 核心概念

- **单词本（localStorage）**：范文阅读页的划词即收录，跟 `english-reading-exercises` 一样零摩擦 — 划选即存、刷新不丢，无需任何粘贴操作。
- **两条入口互不依赖**：入口 1 往单词本里「存」好词好句，入口 2 从个人库「取」做批改建议。用户可以只用来收录、只用来批改，或两者配合。
- **个人库（library.json）**：`~/Documents/ielts-writing/library.json`，长期积累的同义替换库，按「汉语释义」聚成同义组。单词本是单篇范文的临时产物，个人库是跨范文的长期资产 —— 两者靠**入库**这一步连接（见「入库」小节）。批改时 agent 从库里取替换建议。可选，不影响收录功能。

## 接收粘贴内容的判定

agent 在对话里收到用户粘贴的内容时：

- 以 `[IELTS 作文]` 开头、含 `essay:` 块 → 来自写作页「提交」→ 走 **入口 2 批改**。
- 每行形如 `词\t释义\t例句` 的多行文本 → 来自阅读页「导出单词本」→ 走 **入库**（见下）。
- 否则按用户的自然语言意图分流（给题目 / 给范文 / 直接贴作文）。

## 传数据给脚本：优先用 `--data-file`

所有 build 脚本都同时支持 `--data '<json>'` 和 `--data-file <path>`。**默认用 `--data-file`**：
英文作文里 `people's`、`don't` 这类撇号会截断 shell 单引号，`--data` 必然失败。先把 JSON
写到临时文件（如 `/tmp/ielts-<slug>.json`），再传 `--data-file`。只有短的、确定无引号的
数据（如 writer 的题目）才可以图省事用 `--data`。

---

# 入口 1：范文收录（单词本）

收录功能完全在浏览器内完成，跟 `english-reading-exercises` 一样：划词即收、无需粘贴回 agent。

### Step 1：拿到范文
用户提供一篇雅思范文（直接粘贴文本，或给 URL 用 WebFetch 抓正文）。标题、来源一并记下。

### Step 2：生成词典 + 组装阅读数据
为范文中 **非基础、值得积累** 的词与词组生成语境化中文释义（CEFR B1+ 以上，含动词/名词/形容词/副词/词组，如 "play a pivotal role", "shed light on"）。输出 `dictionary`：`{ "小写词或原样词组": "中文释义" }`。

组装阅读数据对象（与 `english-reading-exercises` 同构）：
```json
{
  "id": "从标题生成的 slug",
  "title": "范文标题",
  "source": "URL 或 '用户粘贴'",
  "content": "<p>段落1</p><p>段落2</p>...",
  "dictionary": { "term": "释义", "...": "..." }
}
```
`content` 用 `<p>` 包裹段落，保留 `<h2>/<blockquote>/<strong>` 等语义标签。

### Step 3：生成阅读页（build_reader.py）
把上面的 JSON 写入 `/tmp/ielts-<slug>-reader.json`，然后：
```bash
python3 "<skill>/scripts/build_reader.py" --data-file /tmp/ielts-<slug>-reader.json --out ~/Desktop/IELTS\ Writing/<slug>-reader.html
```
脚本把数据注入 `templates/reader.html`（`{{READER_DATA_JSON}}` 占位），写出自包含 HTML。用 `present_files` 或告知路径，让用户在浏览器打开。

阅读页行为（模板内置，无需在数据中指定）：
- 鼠标划词 → 自动查本地词典，查不到走免费翻译接口 → 翻译气泡 + **自动收进右侧单词本（localStorage）**。零摩擦，无需任何按钮。
- 单词本可单条删除。
- 「导出单词本」按钮 → 下载 `.txt` 文件 + 把词单（逗号分隔）复制到剪贴板（与 `english-reading-exercises` 同格式）。

### 数据完全在浏览器内
- 单词本保存在 `localStorage`（key: `ielts_collect_<slug>`），刷新不丢。
- 划词即收录，不需要粘贴回 agent。
- 如需导出，在阅读页点「导出单词本」即可下载 .txt。

### Step 4：入库（把单词本沉淀进个人库）

**这一步是可选的、用户触发的** —— 不要在生成阅读页后自动催促。当用户说「入库」「存进词汇库」
「同步一下」或直接粘贴导出的单词本内容时才做。没有这一步，入口 2 的「库推荐」就无库可取。

1. **先读已有组名**，避免把 `重要的` 和 `重要/起作用` 拆成两个近义组：
   ```bash
   python3 "<skill>/scripts/manage_library.py" --print
   ```
   合并靠 `group_meaning_zh` 的归一化字符串精确匹配（去掉非字母数字后小写比较），**不做语义判断**。
   所以复用已存在的组名是 agent 的责任：能归进已有组就用那个组的原文组名，别造新说法。

2. **聚类并入库**。把每条词按语义归组，写入 `/tmp/ielts-lib-add.json`：
   ```json
   {"items":[
     {"term":"crucial","pos":"adj","translation":"至关重要的","group_meaning_zh":"重要的",
      "example":"Education is crucial to social mobility.","source":"<范文标题>"}
   ]}
   ```
   ```bash
   python3 "<skill>/scripts/manage_library.py" --data-file /tmp/ielts-lib-add.json
   ```
   `group_meaning_zh` 留空的条目会进 `ungrouped`，批改时取不到 —— 尽量都给组名。
   同组内同名 term 自动跳过，重复入库安全。

3. **刷新浏览页**（可选，用户想看库时）：
   ```bash
   python3 "<skill>/scripts/build_library_view.py"
   ```
   阅读页右上角「词汇库」按钮打开的就是这个页面（同目录下的 `my-library.html`）。

---

# 入口 2：批改作文

### 2a：给定题目（先生成写作页）
用户提供题目（如 "Some people think... To what extent do you agree?"）和题型（task1/task2，默认 task2）。
组装写作数据：
```json
{"id":"slug","topic":"题目原文","task":"task2","minutes":45}
```
`minutes` 只是弹窗的预填默认值（首次打开时用；之后记住上次选择，localStorage）。
```bash
python3 "<skill>/scripts/build_writer.py" --data '<上面的 JSON>' --out ~/Desktop/IELTS\ Writing/<slug>-writer.html
```
写作页内置：题目展示、打开时弹窗自选倒计时时长（快捷 20/40/45/60 分钟或自定义，确认后才开始计时；计时中可「改时间」/暂停/重置）、文本框、字数与段落数实时统计、「提交」按钮（复制作文到剪贴板，格式以 `[IELTS 作文]` 开头含 `essay:` 块）。用户写完粘贴回对话框 → 走下方批改。

> 若用户直接粘贴写好的作文（不给题目），跳过写作页，直接进入批改；`topic` 留空、`task` 按用户说明或默认 task2。

### Step 2：生成批改数据
agent 对作文做四项评分标准分析（参考 `references/ielts-criteria.md`）：TA（任务回应）、CC（连贯衔接）、LR（词汇丰富度）、GRA（语法准确度）。

批改前先取个人库，用于「薄弱表达 → 库里更好替换」的推荐：
```bash
python3 "<skill>/scripts/manage_library.py" --print
```
用这个命令而不是直接读 `library.json`：库积累大了整份读进来会占掉大量 context。库为空或不存在时
输出空结构，此时所有 `suggestion` 留空即可，不影响批改。

产出批改数据：
```json
{
  "id": "slug",
  "topic": "题目（若有）",
  "task": "task2",
  "essay": "<用户作文原文，段落用换行分隔即可>",
  "band": {"overall": 6.5, "ta": 6, "cc": 6.5, "lr": 6, "gra": 6},
  "summary": "总体评语（2-4 句，点出最该改的 1-2 件事）",
  "annotations": [
    {
      "level": "word",            // word | phrase | sentence | paragraph
      "paragraph": 0,             // 第几段（0 起）
      "text": "good",             // 作文里被批注的原文片段（须在 essay 中能定位）
      "band": "LR",               // 关联哪项评分标准
      "severity": "improve",      // error（错误）| improve（可提升）| good（亮点）
      "comment": "偏口语/笼统，库里有更学术的替换",
      "suggestion": "beneficial"  // 来自个人库的更好表达（可空）
    }
  ]
}
```
`text` 必须是作文里**逐字存在**的片段，模板靠它在正文里高亮定位。`suggestion` 优先取自个人库里语义相近的 term；命中时该批注会高亮成「库推荐」样式。

### Step 3：生成批改页（build_correction.py）
先写 `/tmp/ielts-<slug>-correction.json`（**必须用 `--data-file`**：作文里的撇号会截断 shell 单引号），校验后生成：
```bash
python3 "<skill>/scripts/validate_data.py" --kind correction --data-file /tmp/ielts-<slug>-correction.json
python3 "<skill>/scripts/build_correction.py" --data-file /tmp/ielts-<slug>-correction.json --out ~/Desktop/IELTS\ Writing/<slug>-correction.html
```
模板渲染：左侧作文正文（按段，annotations 片段高亮、悬停/点击看批注），右侧批注栏（按段分组，含 band 标签与建议 chip），顶部四项分数 + 总评，底部「重写」按钮（带 `topic` 打开写作模板进入新一轮）。

### 重写循环
「重写」按钮 → 打开 `templates/writer.html` 并带 `#topic=...&task=...` → 全新写作页 + 计时 → 提交粘贴回对话框 → 再批改。如此循环。

### 批改进度汇总（可选）
多次批改后，可生成汇总页查看分数趋势与薄弱维度：
```bash
python3 "<skill>/scripts/build_correction_review.py"
```
- 数据源是 `~/Documents/ielts-writing/corrections-log.jsonl`（每次批改由 build_correction.py 自动追加，含批注明细）——log 是数据，HTML 是渲染产物，不要从批改页反解数据
- 兜底：log 功能上线前生成的旧批改页会被扫描收录，时间线取文件修改时间
- 输出 `~/Desktop/IELTS Writing/review-corrections.html`：
  - 分数折线图（Overall / TA / CC / LR / GRA；Chart.js 走 CDN，离线时自动降级，数据以下方表格为准）
  - 高频问题统计：error 批注按雅思评分维度归类（GRA 语法 / LR 词汇 / CC 结构衔接 / TA 任务回应）
  - 历次批改记录表格（按时间排序）
- 可选参数：`--dir` 指定批改页目录（兜底扫描用）、`--out` 指定输出路径

---

# 重要实现注意事项

- **JSON 转义**：所有 `content`/`essay` 含 HTML 或换行，必须用 Python `json.dumps(..., ensure_ascii=False).replace("</", "<\\/")` 注入，禁止手工拼字符串。脚本已处理。
- **批注定位**：`annotations[].text` 必须能在**它自己那一段**（`paragraph` 指定的段）里按子串找到。
  模板是按段定位的，`text` 在别的段落里不算命中，会掉进「未定位批注」。段号从 0 起，按空行分段。
  批注宁可短（一个词组/一句），必要时一条段落拆成多条。
- **库推荐一致性**：`suggestion` 写进库里真实存在的 term；若库里没有合适项就留空，不要编造库中不存在的词。
  模板会给带 `suggestion` 的批注挂「★ 来自你的库」标签，编造的词会让这个标签失真。
- **词典质量**：范文词典宁多勿漏，覆盖学习者可能想积累的搭配与词组。
- **校验**：组装完批改/阅读 JSON 后，用 `scripts/validate_data.py` 跑一遍基本校验（批注 text 在 essay 中、分数范围合理），不通过则修正后重生成。

## 脚本一览
- `build_reader.py`：范文 → 阅读页（入口 1）。顺带在同目录建 `my-library.html`（若不存在）。
- `build_writer.py`：题目 → 写作页 + 倒计时（入口 2a）。
- `build_correction.py`：批改数据 → 批改页；同时在输出目录放一份 `writer.html` 供「重写」跳转，并追加完整记录到 `corrections-log.jsonl`。
- `manage_library.py`：`--print` 读库（批改前取建议）｜`--data-file` 入库｜`--init` 建空库。
- `build_library_view.py`：库 → `my-library.html` 浏览页，`--out` 可指定路径。
- `validate_data.py`：`--kind reader|correction` 生成前校验（批注是否在对应段落、分数是否 0-9）。
- `build_correction_review.py`：读批改 log（旧 HTML 兜底，`--dir`/`--out` 可选）→ 生成进度汇总（分数折线图 + 按评分维度的问题统计）。

## 参考文件
- `references/ielts-criteria.md`：雅思写作四项评分标准与常见薄弱点清单（批改时对照）。
- `references/library-schema.md`：`library.json` 完整 schema 与示例（可选，用于个人库同步）。
