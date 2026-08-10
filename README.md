# English Reading Skills

两个 AI Agent Skill，把任何英文文章变成互动阅读练习，并提供跨文章复习。

## Skills

### english-reading-exercises

输入一篇英文文章（URL 或文本），生成交互式阅读网页（单文件 HTML，浏览器打开即用）。

**核心功能：**
- 划词即译：选中单词或句子，弹出中文翻译，自动加入单词本
- 单词本可导出为 txt

**六种练习：**

| 练习 | 说明 |
|------|------|
| 单词释义 | 英→中、中→英、选词填空三种题型交叉，每题带原文语境 |
| 句型练习 | 从文章提取真实句型，做句式改写选择题（四选一） |
| 摘要完形 | AI 撰写英文摘要，挖空关键术语，从词库选词填入 |
| 句子重排 | 打乱核心段落句子顺序，拖拽恢复逻辑 |
| 概念关系图 | 提取核心概念构建关系图，空白节点下拉选择 |
| 背诵段落 | 语音播放、隐藏原文自测、导出文本、自定义段落 |

**文件：**
- `SKILL.md` — Skill 说明（Agent 读取）
- `template.html` — 交互网页模板（含 `{{ARTICLE_DATA_JSON}}` 占位符）

### english-reading-review

扫描目录下所有 `*-reading.html` 文件，提取词汇和句型，生成统一复习页面。

**三大功能：**
- 总览面板：已读文章数、累计生词数、句型数，文章列表可跳转原文
- 单词卡片（Anki 式）：词汇来自阅读时划词添加的单词（localStorage），三档自评
- 句型运用：所有文章句型集中展示，跨文章练习

**文件：**
- `SKILL.md` — Skill 说明
- `build_review.py` — 构建脚本（扫描文件、提取数据、生成 review-all.html）
- `template.html` — 复习页面模板

## 使用方式

### 前置条件

- 一个已配置 LLM API Key 的 Agent（如 Claude Desktop、opencode 等）
- Python 3（复习页面构建脚本用）
- 浏览器

### 安装

将两个目录复制到你的 Agent skills 目录：

```bash
cp -r english-reading-exercises english-reading-review ~/.workbuddy/skills/
```

### 生成阅读练习

把文章链接或文本发给 Agent：

> 帮我读这篇英文文章：https://example.com/article

Agent 会分析文章、生成练习数据，输出一个 `*-reading.html` 到指定目录。

### 生成复习页面

学了多篇文章后：

> 帮我复习学过的文章

Agent 运行构建脚本，扫描目录下所有 `*-reading.html`，生成 `review-all.html`。

```bash
python3 ~/.workbuddy/skills/english-reading-review/build_review.py
```

## 技术细节

- **单文件 HTML**：生成的阅读练习页面自包含，无需服务器，双击打开即用
- **划词翻译**：需要联网（调用翻译 API）；本地词典预先翻译非基础词汇，优先查本地
- **数据存储**：单词本和自定义背诵段落存在浏览器 localStorage 中
- **语音播放**：使用浏览器内置 Web Speech API
- **模板替换**：Agent 分析文章后生成 JSON 数据，替换 `template.html` 中的 `{{ARTICLE_DATA_JSON}}` 占位符
