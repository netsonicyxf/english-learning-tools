---
title: "English Reading Exercises"
description: "上传英文文章链接或文本，自动生成交互式阅读网页。划词即译、自动记录单词本，阅读后生成六种练习：单词释义（三题型交叉）、句型改写、全文摘要完形、句子重排、概念关系图、背诵段落。"
read_when:
  - User provides an English article URL or text and wants to learn from it
  - User says "阅读练习", "英文阅读", "reading exercises", "文章练习", "interactive reading"
  - User wants to create exercises based on an English article
  - User mentions "划词翻译", "单词本", "完形填空", "概念图" related to English articles
---

# English Reading Exercises

## 前置条件

- **LLM API Key**：agent 需要 LLM API 访问权限（用于文章分析、词典生成、练习出题）。托管平台（Claude Desktop 等）通常已内置；自建 agent（opencode 等）需用户自行配置 API Key，参考所用平台的文档。
- **WebFetch**：如果用户提供的是 URL（非粘贴文本），agent 需要有网页抓取能力。部分网站（如 Notion）需要 JS 渲染，可能抓取失败，此时提示用户粘贴正文。
- **Python 3**：推荐用 Python 脚本生成 HTML（避免 JSON 转义错误）。手动拼接也可但容易出错。
- **浏览器**：生成的 HTML 在浏览器中打开即可使用。划词翻译优先查本地词典，查不到时走 Google Translate 免费接口（无需 API Key，但可能受网络限制）。

## Overview

将一篇英文长文转化为**交互式学习网页**（单个 HTML 文件）。核心体验：

1. **划词即译** — 鼠标选中任何单词或句子，立刻显示中文翻译
2. **自动单词本** — 划过的内容自动收入侧边栏单词本，可导出
3. **六种练习** — 阅读完毕后一键生成：单词释义（来自单词本）、句型练习、全文摘要完形、句子重排、概念关系图、背诵段落

输出为单个自包含 HTML 文件，保存到 `~/Desktop/English Learning/` 目录。划词翻译需要联网。

**模板自动处理的功能（无需在数据中指定）**：
- 单词释义练习从单词本自动生成，三种题型交叉出题：英→中、中→英、选词填空（每题带文章原句语境，目标词高亮）
- 概念图用力导向自动布局（force-directed layout），AI 提供的坐标仅作为初始参考，渲染时自动优化间距、消除重叠
- 概念图空白节点/边用下拉菜单选择（非手打填空），检查后显示关系总结面板

## Workflow

### Step 1: 接收输入

- **URL**: 用 WebFetch 获取网页内容，提取正文（去掉导航、广告、侧边栏等非正文元素）。标题、作者等元信息一并提取。
- **粘贴文本**: 直接使用用户提供的文本。

如果用户给的 URL 内容无法正常提取，提示用户粘贴文本。

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
- `source`：文章中的**原句**（完整引用，不改写）
- `questions`：2-3 道**句式改写选择题**——给一个简单句，列出 4 个改写版本，选正确的一个

要求：
- 句型必须是文章中**实际出现**的，不要编造
- `source` 是文章原句（展示用）
- 每道题的 `input` 是一个简单句（话题与文章相关），要求用目标句型改写
- 4 个 `options` 中只有一个语法正确、语义通顺的改写版本
- 干扰项应包含常见错误：时态错误、结构残缺、语序错误、搭配错误等
- 难度递进：简单结构在前，复杂结构在后

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

### Step 6: 填入模板

推荐用脚本生成（避免 JSON 转义错误）：

```python
import json
from pathlib import Path

template = Path.home().joinpath(".workbuddy/skills/english-reading-exercises/template.html").read_text("utf-8")
# ensure_ascii=False 保留中文；替换 </ 防止 content 里出现 </script> 提前关闭标签
data_json = json.dumps(article_data, ensure_ascii=False).replace("</", "<\\/")  # article_data 是组装好的字典
html = template.replace("{{ARTICLE_DATA_JSON}}", data_json)
slug = article_data["id"]  # 用文章 slug 命名，与 Step 7 一致
out = Path.home() / "Desktop/English Learning" / f"{slug}-reading.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html, "utf-8")  # 注意 () 包裹：/ 优先级低于 . ，否则会对 str 调 write_text 报错
```

或手动替换：读取模板文件，将 `{{ARTICLE_DATA_JSON}}` 替换为 JSON 字符串（注意 `content` 字段中 HTML 标签和引号的转义）。保存为 `{slug}-reading.html` 到 `~/Desktop/English Learning/`。

### Step 7: 交付

用 present_files 展示生成的 HTML 文件，简要说明功能。

## Important Notes

- **JSON 转义**：`content` 字段包含 HTML，需要特别注意引号和特殊字符的转义。推荐用脚本（Python `json.dumps`）生成而非手动拼接。
- **词典质量**：词典是核心功能，必须覆盖面广、释义语境贴合。词典不仅用于划词翻译，还用于单词释义练习的干扰项生成。宁可多收录一些词，也不要遗漏学习者可能不懂的词。
- **摘要完形的英文摘要**：必须是英文，不是中文。摘要用英文概括文章核心论点与逻辑。
- **句子重排的句子**：保持原文句子，不要改写。
- **概念图坐标**：只需大致合理即可，力导向布局会自动优化。重点关注概念选择和关系标签的质量，而非坐标精度。
- **文章内容 HTML**：段落用 `<p>` 标签，保留原文结构。不要用纯文本换行。
