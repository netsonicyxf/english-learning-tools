#!/usr/bin/env node
// vocab-drill 的确定性内核：词库登记 + SM2-lite 间隔调度 + 学情日志。
//
// 为什么这个文件必须存在：间隔调度是纯数字计算（ef/interval/due），
// agent 心算必然漂移且不可复现——所有调度决策只能从这里出（套件约定：
// 「统计/边界/校验放脚本」）。agent 只负责内容：提词、词卡、故事、出题。
//
// 用法（agent 调用，全部幂等可重复执行）：
//   node vocab.mjs --add "ephemeral,laconic,cogent"     # 登记新词（自动小写去重）
//   node vocab.mjs --due                                 # 到期词列表（每次开场先跑这个）
//   node vocab.mjs --due --json                          # 同上但带词卡：复习要用上次的例句当锚点
//   node vocab.mjs --review "ephemeral=good,laconic=again"  # 学生作答后更新调度
//   node vocab.mjs --card "ephemeral" --json '{"pos":"adj.","meaning":"短暂的",...}'
//   node vocab.mjs --show "ephemeral"                    # 读回词卡 + 调度状态（--card 的反向）
//   node vocab.mjs --remove "ephemeral,laconic"          # 用户明确说不背了才用，调度史一起没
//   node vocab.mjs --stats                               # 词库概览 JSON
//   node vocab.mjs --list                                # 全部词 + 状态表
//   node vocab.mjs --render --type session --json '{...}' [--out f.html]  # 学习页 HTML
//   node vocab.mjs --render --type dashboard [--out f.html]               # 进度页 HTML
//   node vocab.mjs --log --session '{"mode":"story",...}'    # 结束一次学习写日志
//   node vocab.mjs --selftest
//
// 退出码：0 成功 / 1 selftest 失败或词不存在 / 2 用法错误（套件统一约定）。
// --render：HTML 由脚本从 templates/*.html 确定性生成，LLM 永不手写 HTML；
// 内容 JSON 注入前先校验，数据里所有 < 转成 \u003c（防 </script> 提前关闭 +
// 防 <!--/<script 双转义态；JSON.parse 可还原）。
//
// 状态文件按学生分文件：~/.vocab-drill-state.json（default）或
// ~/.vocab-drill-state-<name>.json。**不**共用一个词库——两个学习者共用
// 同一份调度记录会互相污染（A 记住的词被 B 标成不认识，间隔全乱）。
// 学生日志则统一追加到 ~/.vocab-drill-log.jsonl，带 student 字段，
// 供未来的 vocab-analytics 分组统计（对齐 math-tutor 的日志约定）。
// 测试隔离：设 VOCAB_DRILL_HOME 环境变量重定向状态目录。

import { readFileSync, writeFileSync, appendFileSync, existsSync, mkdirSync, rmSync, renameSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

// 路径全部走函数而非模块常量：selftest 靠改 VOCAB_DRILL_HOME 重定向，
// 常量在 import 时求值会导致隔离失效（踩过：env 设晚了，靠手工拼路径侥幸没碰真实词库）。
function vocabHome() { return process.env.VOCAB_DRILL_HOME ?? homedir(); }
function logPath() { return join(vocabHome(), '.vocab-drill-log.jsonl'); }

// ---- 学生身份：与 math-tutor/writing-coach 同一约定（不问孩子名字） ----
// config 也走 vocabHome()（不是真实 homedir）：否则 selftest 的身份会随
// 这台机器有没有配 student 而变——临时目录里没有 config，恒定拿到 default。
function readStudent() {
  try {
    const cfg = JSON.parse(readFileSync(join(vocabHome(), '.ai-tutoring-config.json'), 'utf8'));
    if (cfg.student && typeof cfg.student === 'string') return cfg.student;
  } catch { /* 无配置就用 default */ }
  return 'default';
}
// 按调用求值，不做模块常量：常量在 import 期就定下来，selftest 改完
// VOCAB_DRILL_HOME 也追不回来（同文件头 31-32 行那条教训）。
function student() { return readStudent(); }
function statePath() {
  const st = student();
  return st === 'default'
    ? join(vocabHome(), '.vocab-drill-state.json')
    : join(vocabHome(), `.vocab-drill-state-${st}.json`);
}

// ---- 日期：本地时间 YYYY-MM-DD，不带时区后缀（套件约定，解析端别补 Z） ----
function todayStr(d = new Date()) {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
function addDays(dateStr, n) {
  const [y, m, d] = dateStr.split('-').map(Number);
  const dt = new Date(y, m - 1, d + n); // 本地时间构造，避免 UTC 偏移
  return todayStr(dt);
}
function daysBetween(a, b) {
  const [y1, m1, d1] = a.split('-').map(Number);
  const [y2, m2, d2] = b.split('-').map(Number);
  return Math.round((new Date(y2, m2 - 1, d2) - new Date(y1, m1 - 1, d1)) / 86400000);
}

// ---- state 读写 ----
function loadState() {
  const p = statePath();
  if (!existsSync(p)) return { student: student(), words: {} };
  try {
    const s = JSON.parse(readFileSync(p, 'utf8'));
    if (!s.words || typeof s.words !== 'object') throw new Error('bad state');
    return s;
  } catch (e) {
    console.error(`state 损坏（${p}）：${e.message}。请人工检查后删除重建。`);
    process.exit(1);
  }
}
function saveState(s) {
  // 原子写：先写临时文件再 rename——词库是养几个月的资产，
  // writeFileSync 直写遇到崩溃/断电会留下半个 JSON，整条调度史就没了。
  const dir = vocabHome();
  mkdirSync(dir, { recursive: true });
  const p = statePath();
  const tmp = `${p}.tmp`;
  writeFileSync(tmp, JSON.stringify(s, null, 2));
  renameSync(tmp, p);
}

// ---- SM2-lite：四个档位的间隔与难度因子 ----
// 实测过的数字别乱调：again 当天重见（interval=0）、good 首次 1 天/二次 3 天
// 之后 interval*ef、easy 在 good 基础上 ×1.3——这条曲线在「每天清空到期词」
// 的使用节奏下，一个词从新到 21 天间隔大约需要 4-5 次 good。
const EF_MIN = 1.3, EF_MAX = 2.8, EF_INIT = 2.5;
const GRADES = {
  again: { efDelta: -0.20 },  // 不认识：重置 reps，今天还会再见到
  hard: { efDelta: -0.15 },   // 犹豫/想起来了但慢：间隔只扩 1.2 倍
  good: { efDelta: 0 },       // 正常记得
  easy: { efDelta: +0.15 },   // 秒答：间隔额外 ×1.3
};
function clampEf(v) { return Math.min(EF_MAX, Math.max(EF_MIN, Math.round(v * 100) / 100)); }
// 间隔封顶 365 天（Anki 同款）：不封顶的话 interval×ef 连乘会爆到天文数字，
// addDays 构造 Date 超范围 → due 变 "NaN-NaN-NaN"，词库数据就脏了。
const INTERVAL_CAP = 365;
function nextInterval(entry, grade) {
  if (grade === 'again') return 0;
  let n;
  if (grade === 'hard') n = Math.max(1, Math.round((entry.interval || 1) * 1.2));
  else if (grade === 'easy') {
    if (entry.reps === 0) n = 3;
    else if (entry.reps === 1) n = 6;
    else n = Math.round(entry.interval * entry.ef * 1.3);
  } else { // good
    if (entry.reps === 0) n = 1;
    else if (entry.reps === 1) n = 3;
    else n = Math.round(entry.interval * entry.ef);
  }
  return Math.min(INTERVAL_CAP, n);
}
function applyReview(entry, grade) {
  const g = GRADES[grade];
  entry.ef = clampEf(entry.ef + g.efDelta);
  entry.interval = nextInterval(entry, grade); // 先按旧 reps 算间隔（首次/第二次的分支才判得准）
  if (grade === 'again') { entry.reps = 0; entry.lapses = (entry.lapses || 0) + 1; }
  else entry.reps += 1;
  entry.due = addDays(todayStr(), entry.interval);
  entry.last_result = grade;
  entry.last_review = todayStr();
  return entry;
}

// ---- 命令实现 ----
function cmdAdd(list) {
  const words = list.split(',').map((w) => w.trim().toLowerCase()).filter(Boolean);
  if (!words.length) { console.error('没有可添加的词'); process.exit(2); }
  const s = loadState();
  const added = [], skipped = [];
  for (const w of words) {
    if (s.words[w]) skipped.push(w);
    else {
      s.words[w] = { ef: EF_INIT, interval: 0, reps: 0, lapses: 0, added: todayStr(), due: todayStr(), last_result: null };
      added.push(w);
    }
  }
  saveState(s);
  console.log(`已登记 ${added.length} 个新词${skipped.length ? `，跳过已在词库的 ${skipped.length} 个：${skipped.join(', ')}` : ''}`);
  if (added.length) console.log(added.join('\n'));
}

// 到期词分两类，**不要合成一张表**：--add 时 due=今天，所以「登记完生成了词卡
// 但还没被测过」的词也在到期范围里。它们需要的是先测一次（QUIZ），
// 不是「复习上次学过的」——混在一起 agent 会把没考过的词当复习词考。
//
// 分流看 last_review 而不是 reps：again 会把 reps 归零，
// 拿 reps===0 当「新词」会把「刚才栽了、今天要重来」的词说成「还没考过」。
function dueWords(s) {
  const t = todayStr();
  const rows = Object.entries(s.words)
    .filter(([, e]) => daysBetween(e.due, t) >= 0) // due 距今天已过 0 天以上 = 到期（含今天）
    .sort((a, b) => a[1].due.localeCompare(b[1].due) || a[0].localeCompare(b[0]));
  return {
    review: rows.filter(([, e]) => e.last_review).map(([w]) => w), // 测过至少一次
    fresh: rows.filter(([, e]) => !e.last_review).map(([w]) => w), // 从未测过
    rows,
  };
}

function cmdDue(asJson) {
  const s = loadState();
  const { review, fresh, rows } = dueWords(s);
  const total = Object.keys(s.words).length;
  if (asJson) {
    // --json 带上词卡：复习时必须能取回上次那句 quirky 例句当记忆锚点，
    // 重新造一句就等于换了锚点，前几次的间隔投资白费（SKILL.md「例句是灵魂」）。
    const pack = (w) => ({ word: w, ...s.words[w] });
    console.log(JSON.stringify({
      student: student(), date: todayStr(), total,
      review: review.map(pack), fresh: fresh.map(pack),
    }, null, 2));
    return;
  }
  // 纯文本模式：stdout 只有词，两段之间用 stderr 的注释行分隔，
  // agent 逐词处理不会被 '#' 绊到（stderr 不进管道）。
  if (review.length) { console.error('# 到期复习：'); console.log(review.join('\n')); }
  if (fresh.length) { console.error('# 新词待首测（还没考过，不是复习）：'); console.log(fresh.join('\n')); }
  console.error(`# 到期复习 ${review.length} / 待首测 ${fresh.length} / 词库共 ${total}（${student()}）`);
  if (!rows.length && total) console.error('# 今天没有到期词，可以直接学新词');
}

function cmdList() {
  const s = loadState();
  const t = todayStr();
  const rows = Object.entries(s.words).sort((a, b) => a[1].due.localeCompare(b[1].due));
  if (!rows.length) { console.log('(词库为空)'); return; }
  for (const [w, e] of rows) {
    const overdue = daysBetween(e.due, t); // 正数=已过期天数
    // reps===0 分两种：从没测过（interval 0）和 again 打回重来（lapses>0）。
    // 前者是「等首测」，后者是「昨天栽了今天再来」，对 agent 不是一回事。
    const status = overdue > 0 ? `过期${overdue}天`
      : e.reps === 0 ? (e.lapses ? '打回重测' : '待首测')
        : `还有${-overdue}天`;
    const mastered = e.interval >= 21 ? '✓' : ' ';
    const lapses = e.lapses ? ` 栽${e.lapses}次` : ''; // 供 SKILL.md「连续 again 就换例句」那条分支判断
    const card = e.card ? ' 有卡' : ' 无卡';
    console.log(`${mastered} ${w.padEnd(22)} 间隔${String(e.interval).padStart(3)}天 reps${e.reps} ef${e.ef.toFixed(2)} ${e.due} ${status}${lapses}${card}`);
  }
}

// 词卡读回：--card 只写不读的话，复习时取不到上次的 quirky 例句，
// agent 只能重造一句——锚点一换，前几次间隔投资就废了。
function cmdShow(word) {
  const s = loadState();
  const w = word.trim().toLowerCase();
  const e = s.words[w];
  if (!e) { console.error(`词库里没有 "${w}"`); process.exit(1); }
  console.log(JSON.stringify({ word: w, ...e }, null, 2));
}

// 出口命令：红线 1 说「背什么词是用户的决定」，只有入口没出口这条就是半句话。
// 调度史一并删除且不可恢复，所以要求用户明确说过不背了才调（SKILL.md 里写死）。
function cmdRemove(list) {
  const words = list.split(',').map((w) => w.trim().toLowerCase()).filter(Boolean);
  if (!words.length) { console.error('没有指定要移除的词'); process.exit(2); }
  const s = loadState();
  const removed = [], missing = [];
  for (const w of words) {
    if (s.words[w]) { delete s.words[w]; removed.push(w); } else missing.push(w);
  }
  saveState(s);
  console.log(`已移除 ${removed.length} 个词${removed.length ? `：${removed.join(', ')}` : ''}`);
  if (missing.length) console.error(`# 词库里本来就没有：${missing.join(', ')}`);
}

// 两段式：先全量校验，再统一 apply。
// 边校验边 apply 的写法在「批量里第 2 个词拼错」时会中途 exit，
// 第 1 个词的真实作答**看似记了其实没落盘**（saveState 在循环后）。
// agent 见到报错只会补跑失败那个词，那次作答就静默丢了——正是红线 3 要防的。
// 所以报错必须明说整批未写入。
function cmdReview(list) {
  const s = loadState();
  const pairs = list.split(',').map((p) => p.split('=').map((x) => x.trim().toLowerCase()));
  const errors = [];
  for (const [word, grade] of pairs) {
    if (!word) { errors.push('有一项是空的（格式：词=档位，逗号分隔）'); continue; }
    if (!GRADES[grade]) errors.push(`"${word}" 的档位 "${grade ?? ''}" 非法（只能是 again/hard/good/easy）`);
    else if (!s.words[word]) errors.push(`词库里没有 "${word}"，先 --add`);
  }
  if (errors.length) {
    console.error(errors.join('\n'));
    console.error(`# 本批 ${pairs.length} 个词全部未写入，修正后整批重跑（别只补失败的那个，`
      + `否则已作答的词会丢掉这次档位）`);
    process.exit(errors.some((e) => e.includes('非法') || e.includes('空的')) ? 2 : 1);
  }
  const out = [];
  for (const [word, grade] of pairs) {
    const entry = s.words[word];
    applyReview(entry, grade);
    out.push(`${word}:${grade}→间隔${entry.interval}天，下次${entry.due}`);
  }
  saveState(s);
  console.log(out.join('\n'));
}

function cmdCard(word, json) {
  const s = loadState();
  const w = word.trim().toLowerCase();
  if (!s.words[w]) { console.error(`词库里没有 "${w}"，先 --add`); process.exit(1); }
  let card;
  try { card = JSON.parse(json); } catch (e) { console.error(`--json 不是合法 JSON：${e.message}`); process.exit(2); }
  s.words[w].card = card;
  saveState(s);
  console.log(`已存词卡：${w}`);
}

const HIGH_LAPSE = 3; // 栽够这么多次就该换记忆锚点，不是让学生再硬背一遍
// 统计对象只有这一份：--stats 打印它，dashboard 嵌它——两边各自拼字段已经漂过一次
//（dashboard 手拼的 stats 少了 due_review/due_fresh，页面新格显示 0）。
function statsOf(s) {
  const words = Object.values(s.words);
  const { review, fresh } = dueWords(s); // 与 --due 同一口径，别各算一份
  return {
    total: words.length,
    due: review.length + fresh.length,
    due_review: review.length,
    due_fresh: fresh.length,
    learning: words.filter((e) => e.interval > 0 && e.interval < 21).length,
    mastered: words.filter((e) => e.interval >= 21).length, // 间隔到 21 天视为长期掌握
    fresh: words.filter((e) => !e.last_review).length, // 与 dueWords 同口径看 last_review：reps===0 会把 again 打回的词误算成新词
    carded: words.filter((e) => e.card).length,
  };
}

function cmdStats() {
  const s = loadState();
  console.log(JSON.stringify({
    student: student(),
    ...statsOf(s),
    // 反复栽的词单独列出来（不只是计数）：SKILL.md 要求当场换例句重造，
    // agent 得知道是哪几个词才能执行。
    high_lapse: Object.entries(s.words)
      .filter(([, e]) => (e.lapses || 0) >= HIGH_LAPSE)
      .map(([w, e]) => ({ word: w, lapses: e.lapses })),
  }));
}


// LOG_MODES 的副本在 SKILL.md 第 5 步（收尾）——改这里要同步改那边，
// 属于套件「跨文件契约」那一类，没有编译期检查。
const LOG_MODES = new Set(['extract', 'cards', 'story', 'review', 'mixed']); // 供未来 vocab-analytics 分组

// results 的形状**在这里钉死**：四个档位各自的计数，键名与 GRADES 完全一致。
// vocab-analytics 还没建，正是钉形状的时机——math-analytics 那边字段语义
// 靠约定漂了几轮的坑不要再踩一遍。多余的键直接拒，别让脏形状进日志。
function normalizeResults(raw) {
  if (raw == null) return { counts: { again: 0, hard: 0, good: 0, easy: 0 }, errors: [] };
  if (typeof raw !== 'object' || Array.isArray(raw)) {
    return { counts: null, errors: ['results 必须是对象：{"again":1,"hard":0,"good":3,"easy":2}'] };
  }
  const counts = { again: 0, hard: 0, good: 0, easy: 0 };
  const errors = [];
  for (const [k, v] of Object.entries(raw)) {
    if (!(k in GRADES)) { errors.push(`results 里有未知档位 "${k}"（只能是 again/hard/good/easy）`); continue; }
    if (!Number.isInteger(v) || v < 0) { errors.push(`results.${k} 必须是非负整数，收到 ${JSON.stringify(v)}`); continue; }
    counts[k] = v;
  }
  return { counts, errors };
}

function cmdLog(sessionJson) {
  let sess;
  try { sess = JSON.parse(sessionJson); } catch (e) { console.error(`--session 不是合法 JSON：${e.message}`); process.exit(2); }
  if (!LOG_MODES.has(sess.mode)) { console.error(`mode 必须是 ${[...LOG_MODES].join('/')}，收到 "${sess.mode}"`); process.exit(2); }
  const { counts, errors } = normalizeResults(sess.results);
  if (errors.length) { console.error(errors.join('\n')); process.exit(2); }

  // new_words / reviewed 是 agent 自报的数，而套件约定「计数器全在脚本里，
  // agent 不数第几次」。这里没法完全接管（一次 session 的边界只有 agent 知道），
  // 但能拿 state 交叉校验：今天真正被 review 过的词数是确定的。
  // 对不上不阻断——只在 stderr 报差异并把实测值一起写进日志，
  // 让 vocab-analytics 日后能分辨「agent 报的」和「state 实测的」。
  const s = loadState();
  const today = todayStr();
  const reviewedToday = Object.values(s.words).filter((e) => e.last_review === today).length;
  const addedToday = Object.values(s.words).filter((e) => e.added === today).length;
  const gradeSum = counts.again + counts.hard + counts.good + counts.easy;

  const line = {
    date: today,
    student: student(),
    mode: sess.mode,
    new_words: sess.new_words ?? 0,
    reviewed: sess.reviewed ?? 0,
    results: counts,
    words: sess.words ?? [],
    note: sess.note ?? '',
    // state 实测值：agent 报错了也不影响分析端拿到真数
    observed: { reviewed_today: reviewedToday, added_today: addedToday, vocab_total: Object.keys(s.words).length },
  };
  mkdirSync(vocabHome(), { recursive: true });
  // append 而非「读全量+写全量」：一条记录 = 一次学习（对齐 math-tutor/log.mjs）。
  // 重写整个文件的写法崩在中间会丢**整部学习史**，比丢半行严重得多。
  appendFileSync(logPath(), JSON.stringify(line) + '\n', 'utf8');
  console.log(`已记录：${line.date} ${line.mode} 新词${line.new_words} 复习${line.reviewed}`);
  // 两个检查方向含义不同：
  // - gradeSum ≠ reviewed 是自报数内部矛盾，任何时候都报（reviewed:0 配非零 results 也算）。
  // - reviewed > reviewedToday 是「报了没发生过的复习」= 漏调 --review，要报。
  //   反方向不报：reviewedToday 是**当天累计**，同一天第二个 session 必然自报 < 累计，
  //   拿 !== 判会把正常双 session 误报成漏调，agent 照着「补调用」会把调过档位的词
  //   再 --review 一遍，间隔翻倍——恰好造成这检查想防的调度污染。
  if (gradeSum !== line.reviewed) {
    console.error(`# 对不上：results 四档合计 ${gradeSum}，但 reviewed 报了 ${line.reviewed}`);
  }
  if (line.reviewed > reviewedToday) {
    console.error(`# 对不上：reviewed 报了 ${line.reviewed}，state 里今天实际被 --review 过的只有 ${reviewedToday} 个`
      + `（漏调 --review 的话掌握状态就没记上）`);
  }
}

// ---- --render：确定性 HTML 生成（LLM 永不写 HTML，脚本只套模板） ----
// 借鉴 writing-coach 的 render.mjs（LLM 只产结构化数据，页面由脚本唯一决定）
// 和 english-reading-exercises 的模板注入法（占位符 {{DATA_JSON}} + 脚本替换）。
// 模板文件在 templates/ 下，与脚本逻辑分离——HTML 体积大，混进 vocab.mjs 难维护。
const RENDER_TYPES = ['session', 'dashboard'];

function templatePath(type) {
  // 模板相对 vocab.mjs 所在目录，不随 cwd 变
  const dir = fileURLToPath(new URL('.', import.meta.url));
  return join(dir, 'templates', `${type}.html`);
}

// 注入前校验内容 JSON：词卡字段齐不齐、题目答案结构对不对、有没有重复词。
// 沿用 english-reading 的教训——LLM 组装的数据不校验就注入，bug 出在生成端。
function validateSessionContent(c) {
  const errs = [];
  if (!c || typeof c !== 'object') return ['内容 JSON 必须是对象'];
  if (!Array.isArray(c.cards) || !c.cards.length) errs.push('cards 必须是非空数组（至少一张卡）');
  const seen = new Set();
  for (const [i, card] of (c.cards || []).entries()) {
    if (!card || typeof card !== 'object' || !card.word) errs.push(`cards[${i}] 缺少 word`);
    if (!card.meaning) errs.push(`cards[${i}]（${card?.word ?? '?'}）缺少 meaning`);
    const w = String(card?.word ?? '').trim().toLowerCase();
    if (w) {
      if (seen.has(w)) errs.push(`cards 里有重复的词：${w}（重复的卡自评会互相覆盖）`);
      seen.add(w);
    }
  }
  if (c.story !== undefined && typeof c.story !== 'object') errs.push('story 必须是对象 {title, text, translation?}');
  // 双语故事是复习时的母语脚手架（借鉴词话 story-cards）：有 story 没译文会被 SKILL.md 认为偷懒
  if (c.story && typeof c.story === 'object' && c.story.text && !c.story.translation) {
    errs.push('story 缺少 translation（中文译文，目标词保留英文原词嵌入）——双语对照是复习脚手架，别落');
  }
  if (c.quiz !== undefined && !Array.isArray(c.quiz)) errs.push('quiz 必须是数组');
  for (const [i, q] of (c.quiz || []).entries()) {
    if (!q || typeof q !== 'object' || !q.prompt) errs.push(`quiz[${i}] 缺少 prompt`);
    if (q.answer === undefined || q.answer === '') errs.push(`quiz[${i}] 缺少 answer`);
  }
  return errs;
}

// 模板注入：占位符替换 + 所有 < 转成 \u003c。
// 只转 </ 不够：HTML 解析器在 script 数据态里遇到 <!-- 或 <script 会进入「双转义态」，
// 之后第一个 </script> 关不掉标签。把 < 全部转义才是彻底解（Next.js 等框架同款做法），
// JSON.parse 能把 \u003c 正确还原回 <。
function injectTemplate(tpl, dataJson) {
  const safe = dataJson.replace(/</g, '\\u003c');
  // 替换值必须走**函数**：String.replace 的替换**串**里 $& / $` / $' / $1 是特殊模式，
  // 例句带一个 $ 就会出事（实测：`"cost $& dollars"` → $& 展开成占位符本身，
  // 页面里出现 {{DATA_JSON}}；`` "a $` b" `` 展开成整个 <head> 前缀，JSON 结构直接破）。
  // 函数返回值不做 $ 解释，原样写入。讲价格/代码/正则的例句都可能带 $，不是极端输入。
  return tpl.replace('{{DATA_JSON}}', () => safe);
}

function cmdRender(type, contentJson, outPath) {
  if (!RENDER_TYPES.includes(type)) {
    console.error(`--type 必须是 ${RENDER_TYPES.join('/')}，收到 "${type}"`);
    process.exit(2);
  }
  let tpl;
  try { tpl = readFileSync(templatePath(type), 'utf8'); } catch (e) {
    console.error(`读模板失败（${templatePath(type)}）：${e.message}。templates/ 目录是否完整？`);
    process.exit(1);
  }
  let data;
  if (type === 'session') {
    try { data = JSON.parse(contentJson); } catch (e) {
      console.error(`--json 不是合法 JSON：${e.message}`); process.exit(2);
    }
    const errs = validateSessionContent(data);
    if (errs.length) {
      console.error('内容校验失败，不渲染：');
      for (const e of errs) console.error(`  - ${e}`);
      process.exit(2);
    }
    // 词必须在词库里：渲染时不拦，学生学完回填、--review 才报「词库里没有」——白学一场。
    const s = loadState();
    const missing = [...new Set(data.cards.map((c) => String(c.word).trim().toLowerCase()))]
      .filter((w) => !s.words[w]);
    if (missing.length) {
      console.error(`以下词不在词库里，先 --add 再渲染（不然学完没法记账）：${missing.join(', ')}`);
      process.exit(2);
    }
  } else {
    // dashboard 不接收内容 JSON，数据全从 state 来（与 --stats/--list 同口径）
    data = dashboardData();
  }

  const html = injectTemplate(tpl, JSON.stringify(data));
  // 输出：给了 --out 就写文件，否则打 stdout（agent 可重定向）
  if (outPath) {
    mkdirSync(dirname(outPath), { recursive: true });
    writeFileSync(outPath, html, 'utf8');
    console.log(`已生成：${outPath}（${type}，${type === 'session' ? data.cards.length + ' 张卡' : data.words.length + ' 个词'}）`);
  } else {
    process.stdout.write(html);
  }
}

// dashboard 数据：复用 dueWords/同口径的统计逻辑，别各算一份
function dashboardData() {
  const s = loadState();
  const t = todayStr();
  const rows = Object.entries(s.words)
    .map(([word, e]) => ({
      word,
      interval: e.interval,
      reps: e.reps,
      ef: e.ef,
      due: e.due,
      lapses: e.lapses || 0,
      card: !!e.card,
      mastered: e.interval >= 21,
      overdue: daysBetween(e.due, t) > 0,
      status: daysBetween(e.due, t) > 0 ? `过期${daysBetween(e.due, t)}天`
        : e.reps === 0 ? (e.lapses ? '打回重测' : '待首测')
        : `还有${-daysBetween(e.due, t)}天`,
    }))
    .sort((a, b) => a.due.localeCompare(b.due) || a.word.localeCompare(b.word));
  return {
    student: student(),
    date: t,
    stats: statsOf(s), // 与 --stats 同一对象，别再各拼一份（这里漂过：少了 due_review/due_fresh）
    high_lapse: Object.entries(s.words)
      .filter(([, e]) => (e.lapses || 0) >= HIGH_LAPSE)
      .map(([w, e]) => ({ word: w, lapses: e.lapses })),
    words: rows,
  };
}

// ---- selftest：退出码 0=全过 1=有失败（套件约定） ----
// 原则：**能调真命令就别抄它的逻辑**。抄一遍 split/lowercase 只能证明抄得对，
// 恰好漏掉最容易回归的参数解析、排序、校验分支（这里以前就漏了三处）。
function selftest() {
  let fail = 0;
  const t = (name, cond) => { console.log(`${cond ? 'PASS' : 'FAIL'} ${name}`); if (!cond) fail++; };

  // 临时目录放系统 tmpdir，**不放真实 home**：中途抛异常时 rmSync 不会执行，
  // 建在 ~ 下就会留一坨 .vocab-selftest-<pid>/ 给用户。
  const tmp = join(tmpdir(), `vocab-selftest-${process.pid}`);
  process.env.VOCAB_DRILL_HOME = tmp;
  mkdirSync(tmp, { recursive: true });

  // 命令都是「打印 + 可能 process.exit」的顶层函数，要在进程内反复调用就得
  // 借走 stdout/stderr/exit。run() 返回 {out, err, code}，code 为 null 表示没退出。
  const run = (fn, ...a) => {
    const realLog = console.log, realErr = console.error, realExit = process.exit;
    const realWrite = process.stdout.write.bind(process.stdout);
    let out = '', err = '', code = null;
    console.log = (...x) => { out += x.join(' ') + '\n'; };
    console.error = (...x) => { err += x.join(' ') + '\n'; };
    process.stdout.write = (chunk) => { out += chunk; return true; }; // --render 走 stdout 直接输出
    process.exit = (c) => { code = c; throw { __exit: true }; }; // eslint-disable-line no-throw-literal
    try { fn(...a); } catch (e) { if (!e?.__exit) { console.log = realLog; console.error = realErr; process.stdout.write = realWrite; process.exit = realExit; throw e; } }
    console.log = realLog; console.error = realErr; process.stdout.write = realWrite; process.exit = realExit;
    return { out, err, code };
  };

  // 1. --add 走真命令：小写归一 + 已在词库则跳过（跳过分支以前没被测到）
  run(cmdAdd, 'Ephemeral, laconic ,COGENT');
  let st = loadState();
  t('add 归一小写并登记', Object.keys(st.words).length === 3 && st.words.ephemeral && st.words.cogent);
  const again = run(cmdAdd, 'ephemeral,novel');
  st = loadState();
  t('add 跳过已在词库的词', Object.keys(st.words).length === 4 && /跳过已在词库的 1 个/.test(again.out));
  t('add 空输入 → 退出码 2', run(cmdAdd, ' , ').code === 2);

  // 短语动词：词内空格不能被当分隔符（SKILL.md 承诺按完整短语入库）
  run(cmdAdd, 'give up,look forward to');
  t('短语按整条入库', loadState().words['give up'] && loadState().words['look forward to']);

  const s = loadState();

  // 2. SM2 间隔序列：good 首次 1 天 → 二次 3 天 → 之后 ×ef
  let e = s.words.ephemeral;
  applyReview(e, 'good'); t('good 首次 → 1 天', e.interval === 1);
  applyReview(e, 'good'); t('good 二次 → 3 天', e.interval === 3);
  const expected = Math.round(3 * e.ef); applyReview(e, 'good');
  t('good 之后 → interval×ef', e.interval === expected);

  // 3. again 重置并当天重现；lapses 累计
  applyReview(e, 'again');
  t('again → interval 0 / reps 0 / due 今天', e.interval === 0 && e.reps === 0 && e.due === todayStr());
  t('again 累计 lapses', e.lapses === 1);

  // 4. hard 不低于 1 天；easy 放大间隔
  const h = s.words.laconic; applyReview(h, 'hard');
  t('hard 新词 → ≥1 天', h.interval >= 1);
  applyReview(h, 'good'); applyReview(h, 'easy');
  t('easy 在 good 之后 > good 路径', h.interval >= 6);

  // 5. ef 夹紧 [1.3, 2.8]；间隔封顶 365（连乘不爆炸，due 永远是合法日期）
  const c = s.words.cogent;
  for (let i = 0; i < 20; i++) applyReview(c, 'again');
  t('ef 下限 1.3', c.ef === EF_MIN);
  for (let i = 0; i < 40; i++) applyReview(c, 'easy');
  t('ef 上限 2.8', c.ef === EF_MAX);
  t('间隔封顶 365 天且 due 合法', c.interval <= 365 && /^\d{4}-\d{2}-\d{2}$/.test(c.due));

  // 6. dueWords 走真函数：排序（过期最久的在前）+ review/fresh 分流
  //    以前这里重写了一遍 filter，所以「排序」压根没验过。
  // last_review 必须跟着给：applyReview 里这两个字段总是同时写，
  // 手造 fixture 漏掉它就不是「复习过的词」了（分流看的正是这个字段）。
  s.words.zebra = { ef: 2.5, interval: 3, reps: 2, lapses: 0, added: '2026-01-01', due: addDays(todayStr(), -5), last_result: 'good', last_review: addDays(todayStr(), -8) };
  s.words.yak = { ef: 2.5, interval: 3, reps: 2, lapses: 0, added: '2026-01-01', due: addDays(todayStr(), -1), last_result: 'good', last_review: addDays(todayStr(), -4) };
  saveState(s);
  const d = dueWords(loadState());
  t('过期最久的词排在前面', d.review.indexOf('zebra') < d.review.indexOf('yak'));
  t('测过的词进 review 段', d.review.includes('zebra') && d.review.includes('yak'));
  // novel 只被 --add 过、从没 review 过（cogent 在用例 5 里被刷了 60 次，不再是新词）
  t('从没测过的新词进 fresh 段而不是 review', d.fresh.includes('novel') && !d.review.includes('novel'));
  t('未到期的词两段都不进', !d.review.includes('laconic') && !d.fresh.includes('laconic'));
  // 回归：again 把 reps 归零，但这词是「刚才栽了今天重来」，不是「还没考过」。
  // 拿 reps===0 分流会把它误报成新词，agent 就会当没学过的词从头教一遍。
  run(cmdAdd, 'lapsedword');
  run(cmdReview, 'lapsedword=again');
  const dl = dueWords(loadState());
  t('again 打回的词算复习而不是新词', dl.review.includes('lapsedword') && !dl.fresh.includes('lapsedword'));

  // 7. 持久化往返（走真实 saveState/loadState + 原子写，连 .tmp 清理一起验）
  const re = loadState();
  t('state 写读往返一致', re.words.ephemeral.ef === s.words.ephemeral.ef && !existsSync(`${statePath()}.tmp`));

  // 8. --review 批量原子性：批里有一个坏词 → 整批不落盘（好词的档位也不能悄悄记上）
  const efBefore = loadState().words.zebra.ef;
  const bad = run(cmdReview, 'zebra=good,nonexistent=good');
  t('批量里有未知词 → 退出码 1', bad.code === 1);
  t('批量失败时好词也不落盘', loadState().words.zebra.ef === efBefore
    && loadState().words.zebra.last_review !== todayStr());
  t('批量失败的报错说明整批未写入', /全部未写入/.test(bad.err));
  t('非法档位 → 退出码 2', run(cmdReview, 'zebra=perfect').code === 2);
  const ok = run(cmdReview, 'zebra=good,yak=hard');
  t('批量合法 → 落盘且逐词报间隔', ok.code === null && loadState().words.zebra.last_review === todayStr()
    && /zebra:good→间隔/.test(ok.out));

  // 9. 词卡存了要能读回来（--card 只写不读时，复习会丢掉记忆锚点）
  run(cmdCard, 'ephemeral', '{"pos":"adj.","meaning":"短暂的","example":"我打扫车库的热情是 ephemeral 的"}');
  const shown = JSON.parse(run(cmdShow, 'EPHEMERAL').out); // 顺带验大小写归一
  t('--show 读回词卡内容', shown.card.meaning === '短暂的' && shown.word === 'ephemeral');
  t('--show 同时给出调度状态', typeof shown.ef === 'number' && typeof shown.due === 'string');
  t('--show 未知词 → 退出码 1', run(cmdShow, 'nosuchword').code === 1);
  t('--card 非法 JSON → 退出码 2', run(cmdCard, 'ephemeral', '{not json').code === 2);
  const duePack = JSON.parse(run(cmdDue, true).out);
  t('--due --json 带上词卡', duePack.fresh.concat(duePack.review).some((x) => x.card?.meaning === '短暂的'));

  // 10. --remove：红线 1 的出口
  run(cmdAdd, 'temporaryword');
  const rm = run(cmdRemove, 'temporaryword,nosuchword');
  t('--remove 删掉存在的词', !loadState().words.temporaryword && /已移除 1 个词/.test(rm.out));
  t('--remove 对不存在的词只提示不报错', rm.code === null && /本来就没有/.test(rm.err));

  // 11. --stats：口径与 --due 一致 + 反复栽的词能被 agent 看到
  const highLapseWord = loadState().words.cogent; // 前面 20 次 again 攒了 lapses
  const stats = JSON.parse(run(cmdStats).out);
  t('stats 的 due = due_review + due_fresh', stats.due === stats.due_review + stats.due_fresh);
  t('stats 列出反复栽的词', highLapseWord.lapses >= HIGH_LAPSE
    && stats.high_lapse.some((x) => x.word === 'cogent'));
  t('stats 统计有词卡的词数', stats.carded >= 1);

  // 12. --log 走真命令：mode 白名单 + results 形状 + append 不覆盖历史
  t('未知 mode → 退出码 2', run(cmdLog, '{"mode":"nonsense"}').code === 2);
  t('--session 非法 JSON → 退出码 2', run(cmdLog, '{oops').code === 2);
  t('results 有未知档位 → 退出码 2', run(cmdLog, '{"mode":"review","results":{"perfect":1}}').code === 2);
  t('results 值非整数 → 退出码 2', run(cmdLog, '{"mode":"review","results":{"good":1.5}}').code === 2);
  run(cmdLog, '{"mode":"cards","new_words":3}');
  run(cmdLog, '{"mode":"review","reviewed":2,"results":{"good":2}}');
  const logLines = readFileSync(logPath(), 'utf8').trim().split('\n').map((l) => JSON.parse(l));
  t('两次 --log 追加两行而非覆盖', logLines.length === 2);
  t('日志行为合法 JSON 且含 student', logLines[0].student === 'default' && logLines[0].date === todayStr());
  t('results 缺省也补齐四个档位', Object.keys(logLines[0].results).sort().join() === 'again,easy,good,hard');
  t('日志带 state 实测值 observed', typeof logLines[1].observed.reviewed_today === 'number');
  const mismatch = run(cmdLog, '{"mode":"review","reviewed":99,"results":{"good":1}}');
  t('自报数与实测不符时报差异但仍写入', /对不上/.test(mismatch.err) && mismatch.code === null);
  // 回归：reviewedToday 是当天累计，同一天第二个 session 自报数小于累计是常态，
  // 误报会诱导 agent 把调过档位的词再 --review 一遍（间隔翻倍）。
  const secondSession = run(cmdLog, '{"mode":"review","reviewed":1,"results":{"good":1}}');
  t('多 session 天自报数小于当日累计不告警', !/对不上/.test(secondSession.err));
  // 回归：reviewed:0 的 falsy 溜过旧 guard，配非零 results 的内部矛盾要照报。
  t('reviewed=0 但 results 合计非零也要报', /对不上/.test(run(cmdLog, '{"mode":"review","reviewed":0,"results":{"good":3}}').err));

  // 13. --render：确定性 HTML + 内容校验 + 转义（防 </script> 提前关闭）
  const sessionContent = {
    title: '今日学习', student: 'default', date: todayStr(),
    cards: [
      { word: 'ephemeral', pron: '/ɪˈfemərəl/', pos: 'adj.', meaning: '短暂的', syn: 'transient/fleeting',
        example: '我打扫车库的热情是 ephemeral 的，持续到看见第一只蜘蛛为止。</script>' },
      { word: 'laconic', pos: 'adj.', meaning: '惜字如金的', example: '那只 laconic 的猫只是眨了一下眼。' },
    ],
    story: { title: 'Moving Day', text: 'My optimism was ephemeral, and the mover was laconic.', translation: '我的乐观是 ephemeral 的，搬家工人则 laconic 得很。' },
    quiz: [
      { type: '中译英', prompt: '短暂的', answer: 'ephemeral' },
      { type: '情景填空', prompt: '他说话 _ _ _ _ _ _ ，惜字如金。', answer: 'laconic' },
    ],
  };
  const sessionHtml = run(cmdRender, 'session', JSON.stringify(sessionContent), undefined).out;
  t('session 渲染出 DOCTYPE', sessionHtml.startsWith('<!DOCTYPE html>'));
  t('session 注入词卡数据（JSON 进 script 标签）',
    sessionHtml.includes('"word":"ephemeral"') && sessionHtml.includes('"word":"laconic"'));
  // 数据里的 < 全部转成 \u003c：既防 </script> 提前关闭，也防 <!-- / <script
  // 让解析器进双转义态（第一个 </script> 就关不掉标签）
  t('session 内容里的 < 被转义为 \\u003c', sessionHtml.includes('\\u003c') && !sessionHtml.includes('蜘蛛为止。</script>'));
  t('session 渲染控制逻辑（翻卡/自评/提交按钮）',
    sessionHtml.includes('flashcard') && sessionHtml.includes('g-again') && sessionHtml.includes('submitBtn'));
  // 回归：评完卡后回填区必须能出现——showResult 是唯一出口，漏了学生拿不到回填 JSON
  t('session 评完卡后回填区展开（回归）', sessionHtml.includes("resultCard').classList.remove('hidden')"));
  // 回归：quiz 解耦后单一「提交答案」按钮整体判分，不再逐题「对答案」
  t('session quiz 单一提交按钮（回归）', sessionHtml.includes('提交答案') && !sessionHtml.includes("'对答案'"));
  // 回归：题目与档位耦合——答错降一档的代码必须在模板里（ORDER 序列 + 降档文案）
  t('session quiz 答错降一档逻辑存在（回归）',
    sessionHtml.includes("['again','hard','good','easy']") && sessionHtml.includes('答错降一档'));
  t('session 页头渲染 title（回归）', sessionHtml.includes('pageHeader'));
  // 校验：缺 meaning / quiz 缺 answer / 词不在词库 / 重复词 都被拒
  t('session 缺 meaning → 退出码 2', run(cmdRender, 'session', JSON.stringify({
    cards: [{ word: 'x' }] }), undefined).code === 2);
  t('session quiz 缺 answer → 退出码 2', run(cmdRender, 'session', JSON.stringify({
    cards: [{ word: 'x', meaning: 'm' }], quiz: [{ prompt: 'p' }] }), undefined).code === 2);
  t('session 词不在词库 → 退出码 2（先 --add 再渲染）', run(cmdRender, 'session', JSON.stringify({
    cards: [{ word: 'ghostword', meaning: 'm' }] }), undefined).code === 2);
  t('session 重复词 → 退出码 2', run(cmdRender, 'session', JSON.stringify({
    cards: [{ word: 'novel', meaning: 'm' }, { word: 'novel', meaning: 'm2' }] }), undefined).code === 2);
  t('session 非法 JSON → 退出码 2', run(cmdRender, 'session', '{oops', undefined).code === 2);
  // 双语故事：有 text 无 translation 要被拦（译文是母语脚手架，漏了退化为纯英文）
  t('session story 缺 translation → 退出码 2', run(cmdRender, 'session', JSON.stringify({
    cards: [{ word: 'novel', meaning: 'm' }], story: { title: 't', text: 'The novel word.' } }), undefined).code === 2);
  t('未知 --type → 退出码 2', run(cmdRender, 'nonsense', '{}', undefined).code === 2);

  // 回归：内容里带 $ 的替换模式。replace 的替换**串**会解释 $& / $` / $' / $1，
  // 修之前 `$&` 会展开成占位符本身、`` $` `` 会展开成整个 <head>，页面数据当场破掉。
  const dollarHtml = run(cmdRender, 'session', JSON.stringify({
    cards: [{ word: 'ephemeral', meaning: '短暂的', example: 'cost $& and $` and $1 dollars' }],
  }), undefined).out;
  t('$ 替换模式原样保留（不展开成占位符/前缀）',
    dollarHtml.includes('cost $& and $` and $1 dollars') && !dollarHtml.includes('{{DATA_JSON}}'));

  // dashboard：数据从 state 来（前面已种了 ephemeral/laconic/novel 等词）
  const dashHtml = run(cmdRender, 'dashboard', undefined, undefined).out;
  t('dashboard 渲染出 DOCTYPE', dashHtml.startsWith('<!DOCTYPE html>'));
  t('dashboard 统计来自 state 同口径', dashHtml.includes('"total":') && dashHtml.includes('ephemeral'));
  t('dashboard 词表含状态列', dashHtml.includes('待首测') || dashHtml.includes('打回重测'));
  // 回归：词表别被包成嵌套 table。这里只能查模板源码里的拼接方式
  // （没有 DOM 跑不了真渲染），够拦住「html 已带 <table> 又外包一层」这个具体错法。
  t('dashboard 词表不嵌套 table（回归）', !dashHtml.includes("innerHTML = '<table>' + html"));


  // 清理临时目录（同步删，process.exit 不等 promise）
  rmSync(tmp, { recursive: true, force: true });
  process.exit(fail ? 1 : 0);
}

// ---- 入口 ----
const args = process.argv.slice(2);

// 取 flag 的值，缺了就报**这个 flag** 的名字。
// 别用 `args[args.indexOf(f) + 1] ?? fallback`：indexOf 返回 -1 时它取的是
// args[0]（也就是上一个 flag 本身），于是 `--card alpha` 会报
// 「--json 不是合法 JSON」，实际在解析字符串 "--card"，?? 兜底永远不生效。
function flagValue(flag, { required = true } = {}) {
  const i = args.indexOf(flag);
  if (i === -1) {
    if (!required) return undefined;
    console.error(`缺少 ${flag} 的值`);
    process.exit(2);
  }
  const v = args[i + 1];
  if (v === undefined || v.startsWith('--')) {
    console.error(`${flag} 后面要跟值，收到 ${v === undefined ? '（空）' : `"${v}"`}`);
    process.exit(2);
  }
  return v;
}

if (args.includes('--selftest')) selftest();
else if (args.includes('--add')) cmdAdd(flagValue('--add'));
else if (args.includes('--due')) cmdDue(args.includes('--json'));
else if (args.includes('--list')) cmdList();
else if (args.includes('--review')) cmdReview(flagValue('--review'));
else if (args.includes('--card')) cmdCard(flagValue('--card'), flagValue('--json'));
else if (args.includes('--show')) cmdShow(flagValue('--show'));
else if (args.includes('--remove')) cmdRemove(flagValue('--remove'));
else if (args.includes('--stats')) cmdStats();
else if (args.includes('--log')) cmdLog(flagValue('--session'));
else if (args.includes('--render')) {
  const type = flagValue('--type');
  const json = flagValue('--json', { required: type === 'session' });
  cmdRender(type, json, flagValue('--out', { required: false }));
}
else {
  console.error('用法: node vocab.mjs --add|--due|--list|--review|--card|--show|--remove|--stats|--log|--render|--selftest'
    + '（详见文件头注释）');
  process.exit(2);
}
