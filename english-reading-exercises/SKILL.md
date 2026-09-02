---
name: english-reading-exercises
title: "English Reading Exercises"
description: "英文阅读学习闭环，两个入口：(1) 生成练习：上传英文文章链接或文本，自动生成交互式阅读网页。划词即译、自动记录单词本，阅读后生成六种练习（单词释义三题型、句型改写、全文摘要完形、句子重排、概念关系图、背诵段落）。(2) 汇总复习：扫描已生成的 *-reading.html 文件，汇总词汇和句型，生成统一复习页面——Anki 式单词翻卡、句型运用练习，并可一键送进 vocab-drill 做间隔重复。当用户说「阅读练习」「英文阅读」「reading exercises」「文章练习」「interactive reading」「划词翻译」「单词本」「完形填空」「概念图」，或「复习」「review」「总结学过的文章」「复习单词」「复习句型」时触发。"
read_when:
  - User provides an English article URL or text and wants to learn from it
  - User says "阅读练习", "英文阅读", "reading exercises", "文章练习", "interactive reading"
  - User says "阅读练习" or "练练阅读" without providing a link — should auto-fetch from Notion database
  - User wants to create exercises based on an English article
  - User mentions "划词翻译", "单词本", "完形填空", "概念图" related to English articles
  - User says "复习", "review", "总结学过的文章", "复习单词", "复习句型"
  - User has multiple *-reading.html files and wants to review them together
---

# English Reading Exercises（生成 + 复习）

一条学习闭环，两个入口：**入口 1** 把一篇英文长文变成交互式练习页（`*-reading.html`），
**入口 2** 把这些练习页汇总成统一复习页，并可桥接到 vocab-drill 间隔重复。
两个入口共享同一批 `*-reading.html` 文件——入口 1 是生产者，入口 2 是消费者。

## 前置条件

- **LLM API Key**：agent 需要 LLM API 访问权限（用于文章分析、词典生成、练习出题）。托管平台（Claude Desktop 等）通常已内置；自建 agent（opencode 等）需用户自行配置 API Key，参考所用平台的文档。
- **WebFetch**：如果用户提供的是 URL（非粘贴文本），agent 需要有网页抓取能力。部分网站（如 Notion）需要 JS 渲染，可能抓取失败，此时提示用户粘贴正文。
- **Python 3**：推荐用 Python 脚本生成 HTML（避免 JSON 转义错误）。手动拼接也可但容易出错。
- **浏览器**：生成的 HTML 在浏览器中打开即可使用。划词翻译优先查本地词典，查不到时走 Google Translate 免费接口（无需 API Key，但可能受网络限制）。
- **生成文件目录懒创建（每次会话开始先做，幂等）**：产出目录是 `~/Desktop/English Learning/`（阅读页在 `articles/` 子目录，复习页在根目录，见入口 2 前置条件）。skill 安装只是复制文件、不会执行任何代码，所以**每次会话开始（无论用户来干什么）**先跑一句，首次安装后的第一次会话就把目录建好，用户无需手动创建（与 english-writing 的懒建目录同款）：
  ```bash
  mkdir -p ~/Desktop/English\ Learning/articles
  ```

## 入口判定

- 用户给文章（URL / 粘贴文本），或说「阅读练习」「练练阅读」但没给文章 → **入口 1**（无文章时从 Notion 自动拉取）。
- 用户说「复习」「review」「总结学过的文章」「复习单词/句型」→ **入口 2**。
- 两个入口可在同一对话内先后发生（先读新文章，再复习旧的）。

---

# 入口 1：生成阅读练习页

将一篇英文长文转化为**交互式学习网页**（单个 HTML 文件）。核心体验：

1. **划词即译** — 鼠标选中任何单词或句子，立刻显示中文翻译
2. **自动单词本** — 划过的内容自动收入侧边栏单词本，可导出
3. **六种练习** — 阅读完毕后一键生成：单词释义（来自单词本）、句型练习、全文摘要完形、句子重排、概念关系图、背诵段落

输出为单个自包含 HTML 文件，保存到 `~/Desktop/English Learning/articles/` 目录（按类型分目录，与 english-writing 的 `essays/`、`corrections/` 同款布局；汇总复习页 `review-all.html` 在上一级根目录）。划词翻译需要联网。

**模板自动处理的功能（无需在数据中指定）**：
- 单词释义练习从单词本自动生成，三种题型交叉出题：英→中、中→英、选词填空（每题带文章原句语境，目标词高亮）
- 概念图用力导向自动布局（force-directed layout），AI 提供的坐标仅作为初始参考，渲染时自动优化间距、消除重叠
- 概念图空白节点/边用下拉菜单选择（非手打填空），检查后显示关系总结面板

## Notion 数据库参考

LR Materials 数据库：
- 数据库页面：`https://lonelyreader.notion.site/c672f915433443dfa0d14570493e7f5d`
- Collection ID：`f4909729-788b-459f-8681-4456274467f5`
- Collection View ID：`31a202c6-de74-802d-951a-000cc3d6c4d4`
- Space ID：`758a535f-f32a-4e6f-b3fc-bc3cabc2bcf2`

Property schema（字段名/类型）：
| 属性名 | 字段 ID | 类型 | 说明 |
|--------|---------|------|------|
| 资料名称 | `title` | title | 文章标题 |
| 发布日期 | `XOQK` | date | 发布日期（`start_date` 格式） |
| 语言 | `\\R\`H` | select | 语言组合（如 中英、中英西） |
| 资料类型 | `awgs` | select | 文章/视频/外语杂志速读指南 |
| 资料主题 | `G\\_R` | multi_select | 标签（如 宏观经济、科技资讯） |

## Workflow

### Step 1: 获取文章来源

有两种路径：

**路径 A — 用户提供了文章 URL 或粘贴了文本**

- **URL**: 用 WebFetch 获取网页内容，提取正文（去掉导航、广告、侧边栏等非正文元素）。标题、作者等元信息一并提取。
- **粘贴文本**: 直接使用用户提供的文本。

如果用户给的 URL 内容无法正常提取，提示用户粘贴文本。

**路径 B — 用户没有提供具体文章（只说"阅读练习"、"练练阅读"等）**

从 Notion LR Materials 数据库自动拉取近期文章列表，让用户选择：

1. 该站点是公开的 notion.site，API **无需认证**，直接裸调即可（实测 2026-08 可用）。不要预先向用户要 cookie；仅当 API 返回 401/403 时，才让用户提供 `token_v2`（浏览器 DevTools → Application → Cookies → `lonelyreader.notion.site` → `token_v2` 复制），在 curl 里加 `-H "Cookie: token_v2=${TOKEN}"` 重试。

2. 调用 `queryCollection` 获取文章列表（server 端 sort 会返回 400，不带 sort，Python 侧排序）：
```bash
curl -s 'https://www.notion.so/api/v3/queryCollection' \
  -H 'Content-Type: application/json' \
  -d '{
    "collectionId": "f4909729-788b-459f-8681-4456274467f5",
    "collectionViewId": "31a202c6-de74-802d-951a-000cc3d6c4d4",
    "spaceId": "758a535f-f32a-4e6f-b3fc-bc3cabc2bcf2",
    "loader": {
      "type": "table",
      "reducers": {"collection_group_results": {"type": "results", "limit": 100}},
      "sort": [],
      "searchQuery": "",
      "userTimeZone": "Asia/Shanghai",
      "userLocale": "zh-CN"
    },
    "query": {"filter": {"filters": [], "operator": "and"}, "sort": []}
  }'
```

3. 解析返回结果：
   - `result.reducerResults.collection_group_results.blockIds` → 文章 block ID 列表
   - `recordMap.block[blockId].value.value.properties` → 文章属性
   - 标题：`properties.title` 中所有片段的 `[0]` 拼接
   - 日期：`properties.XOQK[0][1][0][1].start_date`
   - 语言：`properties["\\R\`H"][0][0]`
   - 类型：`properties.awgs[0][0]`
   - 标签：`properties["G\\_R"]` 所有元素的 `[0]` 拼接

   注意：`recordMap` 在响应**顶层**（`data.recordMap`，不在 `data.result` 里）；block 值有**双重嵌套**：`data.recordMap.block[bid].value.value.properties`（不是 `...block[bid].value.properties`）。

4. Python 侧按日期降序排列，展示**最新 10 篇**给用户选择。格式：`序号 | 日期 | 标题（前 60 字）`。说「最近更新这几篇，看看有哪个想练的？」。如果用户想选更早的，再展示更多。

5. 用户选择后，调用 `loadPageChunk` 获取文章正文。**必须循环翻页取完**：单次调用只返回约 100 个 block（实测一篇约 3600 词的文章有 3 页，只调一次会静默丢掉 2/3 正文），响应顶层的 `cursor.stack` 非空表示还有下一页：
```bash
# 第 0 页：cursor 传 {"stack": []}
curl -s 'https://www.notion.so/api/v3/loadPageChunk' \
  -H 'Content-Type: application/json' \
  -d "{\"pageId\":\"<用户选的blockId>\",\"limit\":100,\"cursor\":{\"stack\":[]},\"chunkNumber\":0,\"verticalColumns\":false}"
```

Python 侧翻页循环（每页的 `recordMap.block` 合并进同一 dict，blockId 作 key 天然去重）：
```python
cursor, num, blocks = {"stack": []}, 0, {}
while True:
    resp = load_page_chunk(page_id, cursor, num)   # 上面 curl 的封装
    blocks.update(resp["recordMap"]["block"])
    if not resp["cursor"]["stack"]:
        break                                       # stack 为空 = 正文取完
    cursor, num = resp["cursor"], num + 1
```

6. 从合并后的 block dict 中提取正文：
   - 过滤出 content block，按 `type` 映射 HTML：`text` → `<p>`，`header` → `<h2>`，`sub_header` → `<h3>`，`sub_sub_header` → `<h4>`（小节标题，本文库很常见），`quote` → `<blockquote>`，`bulleted_list` → `<ul><li>`，`numbered_list` → `<ol><li>`
   - `callout` 自身 `properties` 为空（文本在子 block 里），作为容器递归处理其子 block 即可；`page`、`collection_view_page`、`table_of_contents` 及未列出的类型直接跳过
   - 从每个 block 的 `properties.title` 中提取文本（title 格式为 `[["text", [["b"]]], ...]`）
   - block 的 content 数组可能包含子 block，需递归处理

7. 标题从 `properties.title` 中提取（同上格式），作为 `article_data.title`。

然后回到 Step 2 继续处理。

### Step 2: 处理文章内容

1. 清洗文本：去掉 HTML 标签中的广告、导航等干扰内容，保留正文段落
2. 将正文转为干净 HTML：段落用 `<p>` 包裹，保留 `<h2>` `<h3>` `<blockquote>` `<strong>` `<em>` 等语义标签
3. 如果原文过长（>3000词），考虑适当精简，但保留完整逻辑

### Step 3: 生成词典（dictionary）

提取文章中**非基础词汇**（CEFR B1+ 级别以上的词），为每个词提供**语境匹配的中文释义**。

词典格式：`{ "英文小写": "中文释义" }`

要求：
- 包含名词、动词、形容词、副词中非日常词（如 "ubiquitous", "paradigm", "mitigate"）
- **不要**包含基础词（如 "the", "is", "have", "big"）
- 释义要贴合文章语境（不是通用词典释义）。比如 "mitigate" 在讨论风险的语境下译为"减轻"而非"缓和"
- 词典应覆盖 100-300 个词条（视文章长度而定）
- 键名用小写原形（如 "paradigms" → key 写 "paradigm"），JS 侧有简单的词形还原逻辑

### Step 4: 生成练习数据

#### 4a. 全文摘要完形（summaryCloze）

1. 用**英文**撰写 3-5 句摘要（约 60-100 词），准确概括文章核心论点与逻辑
2. 将 6-8 个关键术语替换为编号空白 `{{1}}`, `{{2}}`, ...
3. 提供 4-6 个干扰项（与文章相关但不是正确答案）
4. 摘要必须是英文，不是中文

数据格式：
```json
{
  "text": "This article discusses how {{1}} has transformed {{2}}. The author argues that while {{3}} brings convenience, it also raises concerns about {{4}}. Ultimately, {{5}} may be the key to addressing {{6}}.",
  "blanks": [
    {"id": 1, "answer": "AI"},
    {"id": 2, "answer": "education"},
    {"id": 3, "answer": "automation"},
    {"id": 4, "answer": "ethical concerns"},
    {"id": 5, "answer": "regulation"},
    {"id": 6, "answer": "bias"}
  ],
  "distractors": ["efficiency", "privacy", "innovation", "competition"]
}
```

#### 4b. 句子重排（sentenceReorder）

选取文章中 **1-2 个核心段落**中具有**内在逻辑关系**的句子（如因果、时间先后、问题→方案、论点→论据→结论），拆成 4-6 个句子打乱，让读者通过逻辑推理恢复正确顺序。

要求：
- 句子之间必须有**明显的逻辑递进关系**（因果、时间、条件→结果、问题→解决方案、概括→具体等），不要选并列关系或平行举例的句子
- 保持原文句子不变，不要改写
- 确保打乱后可以通过逻辑推理还原，而非靠原文记忆

数据格式（句子必须有逻辑递进关系）：
```json
[
  {
    "title": "The Problem of Algorithmic Bias",
    "sentences": [
      {"text": "The first point the author makes is that technology alone cannot solve social problems.", "correctOrder": 0},
      {"text": "This is because social problems are deeply rooted in human behavior and cultural norms.", "correctOrder": 1},
      {"text": "However, technology can amplify existing inequalities if deployed without careful consideration.", "correctOrder": 2},
      {"text": "Therefore, any technological solution must be paired with social and policy interventions.", "correctOrder": 3}
    ]
  }
]
```

#### 4c. 概念关系图（conceptMap）

从文章中提取 6-10 个核心概念，构建关系图。4-5 个节点/边标签设为空白作为练习。

数据格式：
```json
{
  "height": 560,
  "nodes": [
    {"id": "n1", "label": "Technology", "x": 400, "y": 80, "blank": false},
    {"id": "n2", "label": "", "x": 200, "y": 230, "blank": true, "answer": "Inequality"},
    {"id": "n3", "label": "Policy", "x": 600, "y": 230, "blank": false},
    {"id": "n4", "label": "Education", "x": 300, "y": 380, "blank": false},
    {"id": "n5", "label": "", "x": 500, "y": 380, "blank": true, "answer": "Regulation"},
    {"id": "n6", "label": "Bias", "x": 400, "y": 460, "blank": false}
  ],
  "edges": [
    {"from": "n1", "to": "n2", "label": "amplifies", "blank": false},
    {"from": "n1", "to": "n3", "label": "", "blank": true, "answer": "requires"},
    {"from": "n2", "to": "n4", "label": "addressed by", "blank": false},
    {"from": "n3", "to": "n5", "label": "enforces", "blank": false},
    {"from": "n5", "to": "n6", "label": "", "blank": true, "answer": "reduces"},
    {"from": "n4", "to": "n6", "label": "mitigates", "blank": false}
  ]
}
```

节点坐标说明：
- 坐标仅作为**初始参考**，模板用力导向布局自动优化间距，不需要精确计算
- 大致按层次分布即可：顶层概念 y 小（靠上），底层概念 y 大（靠下）
- x 分布在 100-700 之间，大致左右错开即可，无需严格避免重叠（布局引擎处理）
- `blank: true` 的节点 `label` 设为空字符串，`answer` 是正确答案
- 空白节点/边在渲染时自动变为下拉菜单（选项从其他空白答案 + 非空白标签中生成）
- 空白数量 3-5 个，不要太多

#### 4d. 句型练习（sentencePatterns）

从文章中提取 **3-5 个有学习价值的句型结构**（倒装、强调句、分词短语、平行结构、复杂从句、虚拟语气等），帮助学习者关注**句子怎么搭**而非单个词的意思。

每个句型包含：
- `name`：句型名称（如 "Having done... 主语 now..."）
- `formula`：结构公式（如 "Having + [过去分词], [主语] now + [谓语]"）
- `explanation`：中文简述用法和语境（1-2 句）
- `source`：文章中的**原句**（完整引用，不作任何修改）
- `questions`：1-2 道**句式改写选择题**——给一个简单句，列出 4 个改写版本，选正确的一个

要求：
- 句型必须是文章中**实际出现**的，不要编造；`source` 必须能从文章 `content` 中按字符串精确匹配找到
- `source` 是文章原句（展示用），直接复制粘贴，**不删减、不加字、不改标点**
- 每道题的 `input` 是一个简单句（话题与文章相关），要求用目标句型改写
- **关键：`input` 到正确选项的改写必须保持语义等价**——正确选项不能引入 `input` 中没有的信息（时间、数字、事实等），只能做句式转换
- 4 个 `options` 中只有一个语法正确、语义通顺的改写版本
- 干扰项应包含常见错误：时态错误、结构残缺、语序错误、搭配错误等
- 难度递进：简单结构在前，复杂结构在后
- 如果某个句型有陈述式和反问式两种变体（如 "It is + adj + that" 和 "Isn't it + adj + that"），各出一题分别测试

数据格式：
```json
[
  {
    "name": "Having done..., S now...",
    "formula": "Having + [\u8fc7\u53bb\u5206\u8bcd], [\u4e3b\u8bed] now + [\u8c13\u8bed]",
    "explanation": "\u7528\u5206\u8bcd\u77ed\u8bed\u8868\u793a\u5148\u5b8c\u6210\u7684\u52a8\u4f5c\uff0c\u4e3b\u53e5\u8868\u793a\u968f\u540e\u7684\u7ed3\u679c\u3002",
    "source": "Having picked the fruits of China's investment, America's clean-energy industry now needs higher tariffs.",
    "questions": [
      {
        "id": "q1",
        "input": "China developed rapidly. It now faces new challenges.",
        "options": [
          "Having developed rapidly, China now faces new challenges.",
          "Having facing rapid development, China now faces new challenges.",
          "Having been developed rapidly, China now faces new challenges.",
          "China having developed rapidly, now it faces new challenges."
        ],
        "answer": 0
      }
    ]
  }
]
```

**模板交互规则（已内置于 template.html，生成时无需手动处理）：**
- 选项点击**仅选中**（高亮），不立即判对错
- 整个句型练习页面底部有**两个按钮**：
  - **检查**：对所有已选答案判对错，统计正确/总数
  - **显示答案**：直接揭示全部正确答案
- 检查后选项锁定，需重新答题请刷新页面

#### 4e. 背诵段落（recitation）

选取文章中 **1-3 个值得背诵的段落**——通常是论点核心段、结构清晰的段落、或语言表达精彩的段落。

要求：
- 每段长度 80-200 词，不宜过长
- 段落必须是原文中的连续文本，不要拼接不同位置的句子
- 为每段取一个简短标题（如 "The core argument"、"The author's conclusion"）

数据格式：
```json
{
  "passages": [
    {
      "id": "p1",
      "title": "The Core Argument",
      "text": "For many young Chinese, the future doesn't look so great..."
    },
    {
      "id": "p2",
      "title": "The Meaning of Dreamcore",
      "text": "Chinese Dreamcore's primary fans are from Generation Z..."
    }
  ]
}
```

### Step 5: 组装 JSON 数据

将所有数据合为一个 JSON 对象：

```json
{
  "id": "article-slug-从标题生成",
  "title": "文章标题",
  "author": "作者名（如有）",
  "source": "URL或'用户粘贴'",
  "content": "<p>段落1</p><p>段落2</p>...",
  "dictionary": { "word": "释义", ... },
  "exercises": {
    "summaryCloze": { ... },
    "sentenceReorder": [ ... ],
    "conceptMap": { ... },
    "sentencePatterns": [ ... ],
    "recitation": { ... }
  }
}
```

建议把组装好的 JSON 写入临时文件（如 `/tmp/article-data.json`），后续校验和注入都走文件，避免长 JSON 走 shell 参数的转义问题。

### Step 5.5: 校验数据（必须执行）

组装 JSON 后、注入模板前，**必须运行**（不通过则返回 Step 4 重新生成对应部分）：

```bash
python3 <本 skill 安装目录>/validate_data.py /tmp/article-data.json
```

脚本校验四项：句型 `source` / 重排句 `text` / 背诵段落 `text` 必须在原文 `content` 中逐字存在；句型题正确选项不得引入 `input` 中没有的数字。历史上两次出 bug 都是因为 LLM 编造了不在原文中的句子、或正确选项引入了新信息——校验不通过不许保存。

### Step 6: 填入模板

推荐用脚本生成（避免 JSON 转义错误）：

```python
import json
from pathlib import Path

# 本 skill 安装目录（即本 SKILL.md 所在目录），不要写死绝对路径
SKILL_DIR = Path("<本 skill 的安装目录>")
template = (SKILL_DIR / "template.html").read_text("utf-8")
# ensure_ascii=False 保留中文；替换 </ 防止 content 里出现 </script> 提前关闭标签
data_json = json.dumps(article_data, ensure_ascii=False).replace("</", "<\\/")  # article_data 是组装好的字典
html = template.replace("{{ARTICLE_DATA_JSON}}", data_json)
slug = article_data["id"]  # 用文章 slug 命名，与入口 2 的扫描模式一致
out = Path.home() / "Desktop" / "English Learning" / "articles" / f"{slug}-reading.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html, "utf-8")  # 注意 () 包裹：/ 优先级低于 . ，否则会对 str 调 write_text 报错
```

或手动替换：读取模板文件，将 `{{ARTICLE_DATA_JSON}}` 替换为 JSON 字符串（注意 `content` 字段中 HTML 标签和引号的转义）。保存为 `{slug}-reading.html` 到 `~/Desktop/English Learning/articles/`。

### Step 7: 交付

用 present_files 展示生成的 HTML 文件，简要说明功能。

---

# 入口 2：汇总复习

将多篇阅读练习（`*-reading.html`）汇总为一个**统一复习页面**。核心体验：

1. **总览面板** — 已读文章数、当前词库词数、句型数
2. **单词卡片** — Anki 式翻卡，认识/模糊/不认识三档自评，不认识的词优先再出现
3. **句型运用** — 所有文章的句型结构集中展示，每题用新句子练习（非原文）

数据来源：直接扫描 `*-reading.html` 文件，提取其中的 `ARTICLE_DATA` JSON。零依赖，离线可用，不需要额外的学习记录或数据库。

## 前置条件（入口 2 特有）

- **阅读文件**：需要至少一个由入口 1 生成的 `*-reading.html` 文件。
- **文件位置**：阅读页统一放在 `~/Desktop/English Learning/articles/`（入口 1 的产出目录，所有阅读文件同目录）。复习页生成到上一级根目录 `~/Desktop/English Learning/`（与 english-writing 的 `review-corrections.html` 同款布局），文章链接为相对路径 `articles/<文件名>`。`build_review.py` 扫描时也优先找 `articles/` 子目录，目录里没有则回退扫目录本身（兼容旧平铺文件与自定义目录）。
- **文件命名**：必须匹配 `*-reading.html` 模式（如 `sunshine-policy-reading.html`），否则扫描不到。

## Workflow

一条命令完成扫描、提取、汇总、生成：

```bash
python3 <本 skill 安装目录>/build_review.py [目录] [输出路径]
```

脚本自动完成：扫描 `<目录>/articles/`（为空则回退扫 `<目录>` 本身）下的 `*-reading.html` → 正则提取每个文件里的 `ARTICLE_DATA` JSON → 汇总词典（`masterVocab`，跨文章去重、记录出现于哪些文章）与句型库（`allPatterns`，标注来源文章）→ 从 `content` 为每个词提取例句 → 注入 `review-template.html` 输出 `review-all.html` 到 `<目录>` 根目录（文章链接自动带 `articles/` 相对前缀）。macOS 上若目录枚举被 TCC 拦截（如未授权的 ~/Desktop），脚本会自动尝试借 Finder 枚举，只需在弹窗里允许一次。

向后兼容：旧版（无句型数据）的阅读文件也能正常汇总，只是"句型"tab 内容较少。复习进度不持久化——每次打开都是全新一轮（保持简单）。

## 词汇送进 vocab-drill（可选，间隔重复）

vocab-drill 是**独立的兄弟 skill**（与本 skill 同级安装在 `english-learning-tools/` 下），负责真正的 SM2 间隔重复调度。复习页本身不持久化进度——要间隔重复，一键把词灌进去：

构建时同目录会多写一份 `review-vocab.json`：全量词表，每词带释义和文章原句例句。

```bash
python3 <本 skill 安装目录>/import_review_vocab.py           # 一键全量导入
```

脚本行为（全走 vocab.mjs 官方命令，不碰 state 文件）：单次 `--add` 登记（幂等，已在词库的跳过）→ 只给**本次新登记**的词 `--card` 存释义+文章原句例句（**存卡即锚点**，重跑不覆盖已有词卡；加 `--backfill` 可连**已登记但还没词卡**的词一起补录，已有词卡的一律不碰）→ 重渲染并打开 dashboard。

**词本同步（导入单词库）**：阅读页顶栏和复习页都有「**导入单词库**」按钮——点击会汇总
**所有文章**的划词词本（file:// 页面共享 localStorage，不限当前篇，跨篇去重），下载
`wordbank-export.txt`（word/释义/文章原句 三列，例句是划词时的**文章原句**），词单同时进
剪贴板。落盘即导入意图，**懒导入**接手：每次 english-reading-exercises 会话开始（无论用户
来干什么）先查：

```bash
ls -t ~/Downloads/wordbank-export*.txt | head -1
```

对比 `~/.er-wordbank-import-state.json` 记录的上次导入时间（无此文件视为从未导入）。文件
比记录新（或从未导入过且文件存在）→ 静默自动执行
`python3 <本 skill 目录>/import_review_vocab.py <该文件>`（三列 txt 会连释义和文章原句一起
存卡——原句即记忆锚点，首测/复习都用这句，不重造；裸词单才只登记、词卡留到首测生成），
完成后把新时间写回 state 文件，向用户提一句已导入。导入幂等（已在词库的跳过），重复检测
无害。口令「导入单词库」仍然有效：立即强制重扫执行。复习页优先展示 localStorage 划词词本
（`mergeWordBank` 会用它替换全量词典，dashboard 有来源提示）。旧版只登记过、还没词卡的词，
用 `--backfill` 从 review-vocab.json 按文章原句补录。

说明与红线：
- 导入 = 登记进词库（新词待首测），之后**背哪些、何时背**仍由用户在学习 session 里定（vocab-drill 每批 5-15 个）；想剔除个别词用 `vocab.mjs --remove`。
- 词表来源是用户读过的文章，视为用户已确认；额外手动挑词时才需要展示增删。
- 调度数字只从 vocab.mjs 出；不手改 `~/.vocab-drill-state*.json`。
- 之后的单词记忆复习全走 vocab-drill（开场 `--due` 先清到期词）；复习页仍作随意翻卡浏览用。

---

# Important Notes

- **JSON 转义**：`content` 字段包含 HTML，需要特别注意引号和特殊字符的转义。推荐用脚本（Python `json.dumps`）生成而非手动拼接。
- **词典质量**：词典是核心功能，必须覆盖面广、释义语境贴合。词典不仅用于划词翻译，还用于单词释义练习的干扰项生成。宁可多收录一些词，也不要遗漏学习者可能不懂的词。
- **摘要完形的英文摘要**：必须是英文，不是中文。摘要用英文概括文章核心论点与逻辑。
- **句子重排的句子**：保持原文句子，不要改写。
- **概念图坐标**：只需大致合理即可，力导向布局会自动优化。重点关注概念选择和关系标签的质量，而非坐标精度。
- **文章内容 HTML**：段落用 `<p>` 标签，保留原文结构。不要用纯文本换行。
- **Step 5.5 校验不可跳过**：历史上两次出 bug 都是因为 LLM 编造了不在原文中的 `source`/`text`，或题目正确选项引入了输入中没有的信息。校验脚本必须在每次生成后运行，不通过不许保存。
- **入口 2 依赖入口 1 的产出**：文件命名（`*-reading.html`）、目录（`~/Desktop/English Learning/articles/`，复习页在其上一级）、数据格式（`ARTICLE_DATA` 里的 `dictionary` / `exercises.sentencePatterns`）都是两个入口的契约，改任何一侧都要想到另一侧。

## 文件一览

- `template.html`：阅读练习页模板（入口 1，占位符 `{{ARTICLE_DATA_JSON}}`）。
- `review-template.html`：复习页模板（入口 2，占位符 `{{REVIEW_DATA_JSON}}`）——注意与上面的阅读模板是两个文件。
- `validate_data.py`：入口 1 的数据校验（Step 5.5 必跑）。
- `build_review.py`：入口 2 的扫描汇总构建脚本。
- `import_review_vocab.py`：复习词灌进 vocab-drill 的桥接脚本（依赖同级的 `vocab-drill/` skill）。
