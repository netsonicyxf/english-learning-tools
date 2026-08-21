---
title: "English Reading Review"
description: "扫描已生成的英文阅读练习 HTML 文件，汇总词汇和句型，生成一个统一的复习页面。包含单词翻卡（Anki 式）、句型运用练习、跨文章词汇重叠分析。"
read_when:
  - User says "复习", "review", "总结学过的文章", "复习单词", "复习句型"
  - User has multiple *-reading.html files and wants to review them together
  - User wants to see vocabulary overlap across articles
---

# English Reading Review

## 前置条件

- **Python 3**：构建脚本为 Python，无需任何 API Key 或网络连接。
- **阅读文件**：需要至少一个由 `english-reading-exercises` skill 生成的 `*-reading.html` 文件。
- **文件位置**：所有阅读文件必须在**同一目录**中（默认 `~/Desktop/English Learning/`）。复习页面也生成到该目录，文章链接为相对路径，必须同目录才能点击跳转。
- **文件命名**：必须匹配 `*-reading.html` 模式（如 `sunshine-policy-reading.html`），否则扫描不到。

## Overview

将多篇英文阅读练习（`*-reading.html`）汇总为一个**统一复习页面**。核心体验：

1. **总览面板** — 已读文章数、累计生词数、跨文章重复词数、句型数
2. **单词卡片** — Anki 式翻卡，认识/模糊/不认识三档自评，不认识的词优先再出现
3. **句型运用** — 所有文章的句型结构集中展示，每题用新句子练习（非原文）
4. **词汇 & 句型重叠** — 哪些词在多篇文章重复出现、各文章词汇量对比

数据来源：直接扫描 `*-reading.html` 文件，提取其中的 `ARTICLE_DATA` JSON。零依赖，离线可用。

## Workflow

### Step 1: 扫描文件

用 Python 脚本扫描目录（默认 `~/Desktop/English Learning/`）下的 `*-reading.html` 文件：

```bash
python3 <本 skill 安装目录>/build_review.py [目录] [输出路径]
```

脚本与模板同目录，路径按实际安装位置替换（勿写死绝对路径）。macOS 上若目录枚举被 TCC 拦截（如未授权的 ~/Desktop），脚本会自动尝试借 Finder 枚举，只需在弹窗里允许一次。

### Step 2: 提取 & 汇总

对每个文件：
1. 正则提取 `const ARTICLE_DATA = {...};` 中的 JSON
2. 收入 `dictionary`（词汇表）到主词典
3. 收入 `exercises.sentencePatterns`（句型）到句型库
4. 从文章 `content` 中为每个词提取一个例句
5. 记录文章元信息（标题、来源、词汇数、句型数）

汇总后得到：
- `masterVocab`：所有文章的词汇去重合并，每个词记录出现在哪些文章
- `allPatterns`：所有文章的句型，每个标注来源文章
- `stats`：统计数字

### Step 3: 生成复习页面

读取模板（`build_review.py` 同目录下的 `template.html`，脚本已按自身位置解析），将 `{{REVIEW_DATA_JSON}}` 替换为汇总 JSON，输出 `review-all.html`。

### Step 4: 交付

告知用户复习页面路径，简要说明功能。

## 重要说明

- **数据完全来自已有文件**：不需要额外的学习记录、数据库或网络
- **向后兼容**：旧版（无句型数据）的阅读文件也能正常汇总，只是"句型"tab 内容较少
- **跨文章词汇**：同一词在多篇文章出现时，`count > 1`，这些是最值得优先掌握的核心词
- **复习进度不持久化**：每次打开复习页面都是全新一轮（不做 localStorage 持久化，保持简单）
