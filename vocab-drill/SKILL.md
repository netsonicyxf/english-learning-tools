---
name: vocab-drill
description: "英语词汇学习工具：从任意材料（文章/链接/粘贴文本/直接报词表）AI 提取生词，生成记忆向词卡（quirky 例句），把生词编织成情境故事，再用 SM2 间隔重复调度复习——每次学习先清到期词，学情沉淀本地日志。当用户说「背单词」「记单词」「学词汇」「词汇练习」「帮我提生词」「这个词怎么记」「vocab」时使用；用户粘贴英文文章说「挑出生词」「值得学的词」时也应触发。"
---

# Vocab Drill — 词汇操练工具

提词 → 词卡 → 情境故事 → 自评收卡 → 间隔复习。方法论来自对一个 AI 词汇产品的拆解实测
（三个 prompt 已验证有效），调度引擎是本目录的 `vocab.mjs`（SM2-lite），**模型就是 agent 自己——
不调用任何外部网站或 API**。
学习默认发生在浏览器 session 页上（对话只做提词确认、渲染、收回填 JSON、记账），
纯对话文本是备选模式——用户明确说「在聊天里练」才走。

定位是**学习工具**，不是家教：math-tutor / writing-coach 那种「有人教」的辅导不归这里——
vocab-drill 没人教你，它陪你练。词从哪来、背哪些、不背哪些，全由用户决定。
数据落 `~/.vocab-drill-log.jsonl`，未来供 vocab-analytics（待建）出学情报告。

## 红线（不得违反）

1. **词表必须用户确认**：提词结果先展示给用户增删，确认后才 `--add` 登记并生成词卡——
   背什么词是用户的决定，不是 agent 的。
2. **故事不解释词义**：把词放进语境让意思自然浮现，禁止在故事里下定义、给翻译括号。
3. **`--review` 只在真实作答后调用**：学生答了才记档位，没答/跳过就不写。掌握状态是用户资产，
   虚报会污染整条调度曲线。反过来也是红线：**答了就必须调**，漏调等于这次学习没发生
   （收尾时 `--log` 会拿 state 交叉校验，对不上会在 stderr 报出来）。
4. **调度数字只从 vocab.mjs 出**：间隔、到期日、ef 全部以脚本输出为准，agent 不心算、不预测
   「下次应该是什么时候」。
5. **开场先清到期词**：`node vocab.mjs --due` 有到期词时，先复习再学新词——这是间隔重复生效的前提。
6. **不手改 state 文件**：`~/.vocab-drill-state*.json` 只由 vocab.mjs 写。要改词库走
   `--add` / `--remove` / `--card`，没有对应命令就说明这事不该做（对齐套件约定）。
## vocab.mjs 命令速查

```bash
node vocab.mjs --due                                  # 开场必跑：列出到期词（分两段，见下）
node vocab.mjs --due --json                           # 带词卡的到期词：复习前用这个取回上次例句
node vocab.mjs --add "ephemeral,laconic"              # 登记新词（确认词表后）
node vocab.mjs --review "ephemeral=good,laconic=again"  # 作答后：again/hard/good/easy
node vocab.mjs --card "ephemeral" --json '{...词卡...}'  # 存词卡（生成后）
node vocab.mjs --show "ephemeral"                     # 读回词卡 + 调度状态
node vocab.mjs --remove "ephemeral,laconic"           # 用户明确说不背了才用（调度史一起删，不可恢复）
node vocab.mjs --list                                 # 词库全景（含栽了几次、有没有词卡）
node vocab.mjs --stats                                # 概览 JSON（含 high_lapse 反复栽的词）
node vocab.mjs --render --type session --json '{...}' [--out ~/Downloads/vocab-session.html]  # 学习页 HTML（内容校验后才渲染）
node vocab.mjs --render --type dashboard [--out ~/Downloads/vocab-dashboard.html]  # 进度页 HTML（数据全从 state 来）
node vocab.mjs --log --session '{"mode":"story","new_words":8,"reviewed":3,"results":{"again":1,"hard":2,"good":4,"easy":1},"words":[...]}'  # 收尾
```

档位含义：**again** 不认识（当天还会见到）｜**hard** 想起但很慢｜**good** 正常记得｜**easy** 秒答。
`results` 只收这四个键的计数，合计应等于 `reviewed`；多余的键会被拒（退出码 2）。
词库按学生分文件（`~/.vocab-drill-state[-名字].json`，自动读 `~/.ai-tutoring-config.json`，
读不到用 default，**不主动问名字**——两个学习者混一个词库会互相污染调度）。

**`--review` 是整批原子的**：批里有一个词拼错或不在词库，整批都不写盘。
报错后要**整批重跑**，别只补失败那个——不然已作答的词这次档位就丢了。

## 一次完整学习流

### 0. 开场
`node vocab.mjs --due` 输出**分两段，别当成一张表**：

- **到期复习**——学过至少一次、今天该重见的词。用 `--due --json` 取回它们的词卡，
  **拿上次那句例句当锚点**去考（第 4 步），不要现造新例句：换锚点等于前几次间隔白投。
- **新词待首测**——`--add` 登记了、词卡也生成了，但从没被考过。它们要的是**第一次测**，
  不是「复习」，别按学过的词那样对待。

有到期词：先清（复习段 → 首测段）再进新词；两段都空：直接问材料。
词库为空：跳过复习，直接进第 1 步。

### 1. EXTRACT — 提词（材料任意：链接 / 粘贴文本 / 用户直接报词）

> Extract ONLY the words or vocabulary terms from this document that are meant to be learned or reviewed.
> Ignore standard boilerplate text, instructions, and numbers. Return them as a JSON array of strings.

agent 直接执行这个意图（不需要逐字照搬），中文语境补充规则：只收英语词；已经偏简单的常用词
（the/very 之类）不收；专有名词不收。产出候选词表 → **展示给用户增删 → 确认**。

### 2. CARDS — 记忆向词卡（每批 3-8 个，别一次倒 30 个）

每个词生成：词性、简明中文释义、常用同/反义词、**quirky 英文例句 + 例句中文翻译**（有画面、有情绪、
略微古怪，让人过目不忘——这是整个方法的灵魂）。范例风格：

> ephemeral — My passion for cleaning the garage was ephemeral: it lasted until the first spider.
> 我打扫车库的热情是 ephemeral 的：持续到看见第一只蜘蛛为止。
> laconic — Asked if he wanted more snacks, the laconic cat simply blinked.
> 问它要不要再来点零食，那只 laconic 的猫只是眨了一下眼。

**词卡例句整句用英文，`example_trans` 给中文译文**（2026-08 用户定夺，取代拆解时验证过的
「中文叙述 + 英文嵌词」——要回滚就改这段）：译文里目标词保留英文原词嵌入（与故事 `translation`
同一写法）；中文留给释义字段；session 页模板会把例句和译文里的目标词都自动标亮。
生成后 `--add` 登记 + `--card` 存储。默认紧接着把整批渲染成 session 页发给学生——带读在页面
翻卡里完成，聊天里**别再倒一遍词卡**；仅对话模式才在聊天里逐卡带读（音标必给；环境里有现成可用的
发音能力就顺手用，没有就跳过，不要为了发音去调用不兼容的工具）。

**例句一旦存进词卡就是这个词的记忆锚点**，复习时用 `--due --json` / `--show` 取回原句，
不要重造——除了下面「连续 again」那一种情况。

### 3. STORY — 情境故事（8-15 个词一组，一组一篇）

> Create an engaging passage that naturally incorporates ALL of these vocabulary words.
> 1. 主题匹配词汇气质：学术词 → 短文，描述性/天马行空的词 → 故事
> 2. 有标题
> 3. 长度与词量成比例（每个生词约 15-20 词篇幅）
> 4. **DO NOT define the words** —— 用语境表意，不解释
> 5. 目标词加粗

默认英文故事；用户要中文故事时改写为「中文叙述 + 目标词保留英文原文嵌入」。对话模式：读完故事，
随机抽 2-3 个词问「这个词在这段里是什么意思/什么效果」做轻检验；页面模式：故事直接进
session 页（顺手写 translation 字段），检验由题目区承担，不再追问。

**HTML 学习页的故事用双语对照**：`--render` 的 `story` 带 `translation` 字段（中文译文，
目标词以英文原词嵌入译文），页面英文原文在上、中文译文在下，各自高亮目标词——
复习时母语脚手架，意思不用猜。生成故事时顺手写译文，别落掉这个字段。

### 4. QUIZ — 自评收卡

形式从三种里选（别每词都同一种）：中译英（给中文释义拼出词）、情景填空（挖掉故事里的目标词）、
同义速答（给词答同义词）。学生作答 → 按表现映射档位调 `--review`：

- 秒答且对 → easy；正常答对 → good；想很久/提示后对 → hard；答不出/错 → again
- 一次学 5-15 个词为宜；again 的词当场再过一遍（故事或词卡重读）
- **方向要平衡（中↔英双向）**：别一组题全是「看中文拼英文」——那是 production 单向。
  情景填空、同义速答的题干用**英文**（填空挖英文故事原句；同义速答给英文词答英文同义词），
  配 1-2 道中译英即可。阅读里真正吃的是 recognition（看英文立刻反应意思），
  题干全中文等于只练了半个技能。HTML 页 answer 用词卡词才能触发降档（见 HTML 节），
  英文方向的题 answer 天然是词卡词，优先出。
  **页面判分是精确匹配**（trim+lowercase 后全等）：answer 写什么，学生就得一字不差打出什么——
  `upend` 和 `upended` 互不相认。填空句要设计成**填原形就通顺**的句子，answer 永远写词卡原形。

### 5. LOG — 收尾
`--log` 记录本次 session（mode: extract/cards/story/review/mixed——这份清单在
`vocab.mjs` 的 `LOG_MODES` 里另有一份副本，改一处要同步改另一处）。
`results` 给四个档位的计数，合计等于 `reviewed`。顺口报告一句：
「今天新学 X 个，复习 Y 个，词库现在共 Z 个，下次到期 N 个。」（数字取 `--stats`，别自己数。）

脚本会拿 state 交叉校验：stderr 出现 `# 对不上` 说明自报数和实际调过的 `--review` 不符
（通常是漏调了 `--review`，那几个词的掌握状态没记上）。日志照写，但要回去补调用。

## HTML 呈现（默认：学习在页面上发生）

默认把学习搬进浏览器：带读、自评、答题、重测都在 session 页完成，对话只负责提词确认、
渲染、收学生的回填 JSON 和记账。用户明确说「不要页面 / 就在聊天里练」时才整体退回对话文本模式。
**你永不手写 HTML**——只管出内容 JSON，
页面由 `vocab.mjs --render` + `templates/*.html` 确定性生成（和 writing-coach 面板同思路）。

```bash
# 学习页：内容 JSON（词卡/故事/题目）由你生成并打 `--render`
node vocab.mjs --render --type session \
  --json '{"title":"今日学习","student":"default","date":"2026-08-18",
           "cards":[{"word":"ephemeral","pron":"/ɪˈfemərəl/","pos":"adj.","meaning":"短暂的",
                      "syn":"transient/fleeting","example":"My passion for cleaning the garage was ephemeral: it lasted until the first spider.",
                      "example_trans":"我打扫车库的热情是 ephemeral 的：持续到看见第一只蜘蛛为止。"}],
           "story":{"title":"Moving Day","text":"My optimism was ephemeral, and the mover was laconic."},
           "quiz":[{"type":"中译英","prompt":"短暂的","answer":"ephemeral"}]}' \
  --out ~/Downloads/vocab-session.html
open ~/Downloads/vocab-session.html

# 进度页：不用传内容，数据全读 state（与 --stats 同口径）
node vocab.mjs --render --type dashboard --out ~/Downloads/vocab-dashboard.html
open ~/Downloads/vocab-dashboard.html
```

- **长 JSON 先写临时文件**再 `--json "$(cat 文件)"`：英文文本里的撇号（don't）会撕碎 bash
  单引号串，内联转义必出错。
- **学习页交互**：先逐张闪卡（点击翻面看释义），再点 again/hard/good/easy 自评；
  全部评完**题目区才展开**；答题后点底部**唯一的「提交答案」**——逐题判分 + 总分 +
  降档明细 + 回填 JSON 一起出现，复制回对话即可。
- **自评与降档（题目和档位是耦合的）**：翻卡自评给基准档位，提交题目后做修正——
  **答错的题，若其答案是词卡里的词，该词降一档**（easy→good→hard→again，again 保持，
  多题同词只降一次）。调整明细显示在总分下方，回填 JSON 里是降后的最终档位。
  所以出题时 answer 尽量用词卡词（中译英/情景填空天然如此）；answer 不是词卡词的题
  是纯练习，不影响档位。
- **复习会话渲染**：渲染到期复习的学习页时，cards 必须用 `--due --json` 取回的
  **原词卡**（例句是记忆锚点，现场重造等于换锚点，见第 2 步）。只有新词才现造卡。
- **回填法记账**：浏览器碰不到本地文件。学生把回填 JSON 复制回来 → 你解析 grades →
  `--review` 逐词调档位 → `--log` 收尾。别让学生把回填值当「次数」报——`reviewed`
  记去重词数、`results` 记每词最终档位。
- **回填里有 again 的词 → 必须当天重测，且走 session 页**：`--review` 后它们 due=今天
  （SM2 承诺「当天还会见到」）。重测也是一次学习，**渲染一个只含这几个词的 session**
  （cards 同样用 `--due --json` 取原词卡，锚点不换），学生翻卡重学自评，回填后二次
  `--review`，才能 `--log` 收尾。**别退回对话口头出题**——首测在页面上、重测在聊天框，
  学生体验断裂还容易不规范。
- **每次 `--review` / `--log` 后顺手重渲染 dashboard**（一条命令的事）：dashboard 是
  静态快照不自动更新，学生刚记完账看进度页却是旧数据，等于白渲染。
- **内容校验（渲染时拦，退出码 2）**：词卡缺 word/meaning、题目缺 prompt/answer、
  cards 里有重复词、**词不在词库里**（必须先 `--add` 再渲染，不然学生学完没法记账）。
- `dashboard` 是纯展示：五格统计（总数/到期复习/新词待首测/学习中/已掌握——复习与首测分开设，
  别合并成一个「今日到期」，没学过的词说「到期」会误导）+ 反复栽的词警示 + 词表，
  状态口径与 `--list` 一致（待首测/打回重测/已掌握）。

## 常见分支

- **「就问一个词」**：直接讲（词性/释义/搭配/例句），如果这个词值得记，问用户要不要收进词库，
  收了就 `--add` + `--card`。不必走完整流程。
- **到期词太多（>20）**：建议分批（先清过期最久的 10 个），别让复习变成刑罚——持久性比单次覆盖量重要。
- **长文章提出一大堆词（>30）**：提词可以全提（漏了不好补），但确认环节要主动给减法建议——
  按考试频率/实用度帮用户删到 15-25 个，或者给「分天计划」（每天 10 个新词，先到先学）。
  别把 80 个词的原样列表拍用户脸上问「都要吗」——确认压力太大，用户会无脑全收然后弃坑。
- **学生连续 again 同一个词**：这个词的记忆锚点（例句）可能不行，当场换一个角度重造例句再测，
  重造完 `--card` 覆盖存回去（不然下次复习又取到那句没用的）。
  怎么发现：`--list` 的「栽N次」列，或 `--stats` 的 `high_lapse`（栽满 3 次就会列进来）——
  别靠印象猜哪个词老出问题。
- **用户说某些词不想背了**：`--remove` 移出词库。这是红线 1 的另一半（背什么由用户定），
  但调度史一起删且不可恢复，所以只在用户明确说了才调，别替他判断「这词太简单了」。
- **用户要考试导向**（GRE/雅思/托福/SAT）或没带材料想直接学：读 `wordlists/` 对应词单
  （见 `wordlists/README.md`），展示前 10 个词问从哪段开始，走正常 CARDS→STORY→QUIZ 流程。
  词单免费全开放——不搞代币解锁那套，但「按难度分段、一段 10-15 个」的节奏保留。
  **词单只是入门精选，不是完整考试词库**——用户提到系统备考/考前冲刺时，主动引导
  导入他们自己的词表、讲义或真题文章走 EXTRACT 流程。
- **词单分段说明**：段内逗号分隔的词是并列关系；段标题带「成对记/成对学」的
  （如 GRE 形近易混、雅思同义替换），词卡生成时把整组放一起讲对比着记。
- **短语动词/词组**（give up / look forward to）：词库按完整短语处理，`--add` 逗号分隔不受词内空格影响。
