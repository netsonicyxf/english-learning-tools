# Vocab Drill

一个 AI Agent Skill：把任意英文材料变成词汇操练循环，用 SM2 间隔重复排复习。

提词 → 词卡 → 情境故事 → 自评收卡 → 间隔复习。生词从你自己的材料里来（文章、链接、
粘贴文本，或直接报词表），也可以从内置的考试词单起步。**模型就是 agent 自己**——
不调用任何外部词典网站或 API，没有 key 要配。

## 它是什么，不是什么

是**学习工具**，不是家教。没人给你讲课，它陪你练：词从哪来、背哪些、不背哪些，全由你决定。
Agent 提出候选词表后一定先给你增删确认，确认了才登记进词库。

学习默认发生在浏览器页面上（翻卡、答题、自评），对话只负责提词确认、渲染页面、
收你的回填结果和记账。想纯文字练，跟 agent 说「就在聊天里练」。

## 核心机制

| 环节 | 做什么 |
|------|--------|
| EXTRACT | 从材料里挑出值得学的词，跳过简单词和专有名词，结果给你增删确认 |
| CARDS | 每词生成音标、词性、中文释义、同反义词，加一句 quirky 英文例句 + 中文译文 |
| STORY | 8-15 个词编成一篇短文或故事，词加粗，**不解释词义**，让意思从语境里浮现 |
| QUIZ | 中译英 / 情景填空 / 同义速答三种题型交叉，中↔英双向平衡 |
| REVIEW | SM2-lite 调度，四档自评（again/hard/good/easy）决定下次什么时候再见 |

例句一旦存进词卡就是这个词的**记忆锚点**，复习时取回原句考，不重造——换锚点等于前几次间隔白投。
唯一例外是某个词连续答不出，说明那句例句不行，当场换角度重造。

## 安装

需要 Node.js（`vocab.mjs` 是零依赖 ESM 脚本）和一个支持 Skill 的 Agent。

```bash
git clone https://github.com/wanziwan666-crypto/vocab-drill.git ~/.claude/skills/vocab-drill
```

路径按你的 Agent 约定调整（`~/.claude/skills/`、`~/.agents/skills/` 等）。

## 使用

跟 agent 说话就行，不用记命令：

> 帮我背单词

> 这篇文章挑几个值得学的词：https://example.com/article

> 我要考雅思，没带材料

Agent 会先跑一遍到期词清账，再进新词。学完渲染一个 HTML 学习页到 `~/Downloads/`，
你在浏览器里翻卡、答题、自评，把页面给出的回填 JSON 复制回对话，agent 记账收尾。

想看进度：

> 看下我的词汇进度

## 内置词单

没带材料也能学。`wordlists/` 下是五份**词头清单**（只有词头，词卡现生成），按难度排序、
分段导入：

| 文件 | 定位 | 规模 |
|---|---|---|
| `ielts-core.md` | 雅思核心 | ~140 词 |
| `toefl-academic.md` | 托福学术 | ~130 词 |
| `sat-reading.md` | SAT 阅读 | ~110 词 |
| `gre-advanced.md` | GRE 进阶 | ~120 词 |
| `daily-upgrade.md` | 日常升级 | ~110 词 |

全部免费开放。但这是**入门精选**，不是完整考试词库（IELTS/GRE 完整词表在 3000 词量级）——
系统备考请导入你自己的词表、讲义或真题文章走 EXTRACT 流程，那才是这个 skill 的主战场。

## 文件

```
SKILL.md                 skill 说明（agent 读这个）
vocab.mjs                SM2-lite 调度引擎 + HTML 渲染 + 自检
templates/session.html   学习页模板（翻卡/答题/自评/回填）
templates/dashboard.html 进度页模板
wordlists/               五份预置词单
```

## 数据存在哪

| 路径 | 内容 |
|------|------|
| `~/.vocab-drill-state.json` | 词库、词卡、调度状态 |
| `~/.vocab-drill-log.jsonl` | 每次学习的流水日志 |

都在你自己机器上，不上传任何地方。多个学习者按名字分文件
（`~/.vocab-drill-state-<名字>.json`，读 `~/.ai-tutoring-config.json`），互不污染调度。
state 文件只由 `vocab.mjs` 写，改词库走 `--add` / `--remove` / `--card`，别手改。

## 脚本命令

日常用不着，agent 会调。想自己看：

```bash
node vocab.mjs --due      # 到期词（分「到期复习」和「新词待首测」两段）
node vocab.mjs --list     # 词库全景，含每个词栽了几次
node vocab.mjs --stats    # 概览 JSON，含反复栽的词
node vocab.mjs --selftest # 自检（85 项，不碰你的真实词库）
```

完整命令表在 `SKILL.md` 和 `vocab.mjs` 文件头注释里。退出码约定：0 成功 / 1 失败或词不存在 / 2 用法错误。

## 设计取舍

- **调度数字只从脚本出**：间隔、到期日、难度系数全以 `vocab.mjs` 输出为准，agent 不心算不预测。
- **答了就必须记账**：`--review` 只在真实作答后调用，虚报会污染整条调度曲线；漏调也算错，
  收尾时脚本会拿 state 交叉校验并在 stderr 报差异。
- **agent 永不手写 HTML**：只产出内容 JSON，页面由 `--render` + 模板确定性生成，渲染前校验内容
  （缺字段、重复词、词不在词库都会拦下）。
- **词单只存词头**：例句质量跟着模型升级走，不像静态词库会过时。
