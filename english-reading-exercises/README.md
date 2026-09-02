# English Reading Skills

一个 AI Agent Skill（双入口），把任何英文文章变成互动阅读练习，并提供跨文章复习。

## 入口

### 入口 1：生成阅读练习

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

### 入口 2：汇总复习

扫描目录下所有 `*-reading.html` 文件（入口 1 的产出），提取词汇和句型，生成统一复习页面。

**三大功能：**
- 总览面板：已读文章数、当前词库词数、句型数，文章列表可跳转原文
- 单词卡片（Anki 式）：词汇来自阅读时划词添加的单词（localStorage），三档自评
- 句型运用：所有文章句型集中展示，跨文章练习

**可选桥接**：复习词汇可一键送进兄弟 skill [vocab-drill](../vocab-drill/)（SM2 间隔重复调度），`import_review_vocab.py` 全走其 `vocab.mjs` 官方命令。

## 文件

- `SKILL.md` — Skill 说明（Agent 读取，双入口工作流）
- `template.html` — 阅读练习页模板（入口 1，含 `{{ARTICLE_DATA_JSON}}` 占位符）
- `review-template.html` — 复习页模板（入口 2，含 `{{REVIEW_DATA_JSON}}` 占位符）
- `validate_data.py` — 数据校验（句型/重排/背诵必须在原文中逐字存在等）
- `build_review.py` — 复习页构建脚本（扫描文件、提取数据、生成 review-all.html）
- `import_review_vocab.py` — 复习词灌进 vocab-drill 的桥接脚本

## 使用方式

### 前置条件

- 一个已配置 LLM API Key 的 Agent（如 Claude Desktop、opencode 等）
- Python 3（校验与复习构建脚本用）
- 浏览器

### 安装

将本目录复制到你的 Agent skills 目录（vocab-drill 桥接功能需将其与 `vocab-drill/` 作为同级目录安装）：

```bash
cp -r english-reading-exercises ~/.workbuddy/skills/
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
python3 ~/.workbuddy/skills/english-reading-exercises/build_review.py
```

## 技术细节

- **单文件 HTML**：生成的阅读练习页面自包含，无需服务器，双击打开即用
- **划词翻译**：需要联网（调用翻译 API）；本地词典预先翻译非基础词汇，优先查本地
- **数据存储**：单词本和自定义背诵段落存在浏览器 localStorage 中
- **语音播放**：使用浏览器内置 Web Speech API
- **模板替换**：Agent 分析文章后生成 JSON 数据，替换模板中的占位符（阅读页 `{{ARTICLE_DATA_JSON}}`，复习页由 `build_review.py` 注入 `{{REVIEW_DATA_JSON}}`）
