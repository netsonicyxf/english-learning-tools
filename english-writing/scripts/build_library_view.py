#!/usr/bin/env python3
"""Generate an HTML page to view the personal IELTS vocabulary library.

Two layers on one page:
- 划词词本: read LIVE from browser localStorage (english_collect_<essayId> keys,
  same-origin file:// pages share storage — the reading skill's review page uses
  the same trick via mergeWordBank). Shows exactly the words the user 划过.
- 个人库: rendered from library.json (the durable asset corrections read).
"""
import argparse, json, glob, sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
LIB = Path.home() / "Documents" / "english-writing" / "library.json"
ESSAYS_DIR = Path.home() / "Desktop" / "English Writing" / "essays"
DEFAULT_OUT = ESSAYS_DIR / "my-library.html"

sys.path.insert(0, str(SKILL_DIR / "scripts"))
import extract_dictionary  # reuse its HTML parser; essay id → title map


def essay_titles():
    """id → title for every essay inside essays/*-reader.html, so the
    wordbank section can show 来源篇名 instead of a raw storage key."""
    titles = {}
    for fpath in sorted(glob.glob(str(ESSAYS_DIR / "*-reader.html"))):
        data = extract_dictionary.extract_data(Path(fpath).read_text("utf-8"))
        if not data:
            continue
        for e in (data.get("essays") or [data]):
            if e.get("id"):
                titles[e["id"]] = e.get("title", e["id"])
    return titles


ap = argparse.ArgumentParser()
ap.add_argument("--out", help="output HTML path (default: ~/Desktop/English Writing/essays/my-library.html)")
args = ap.parse_args()
OUT = Path(args.out) if args.out else DEFAULT_OUT

lib = json.loads(LIB.read_text("utf-8")) if LIB.exists() else {"groups": [], "ungrouped": []}
lib_json = json.dumps(lib, ensure_ascii=False).replace("</", "<\\/")
titles_json = json.dumps(essay_titles(), ensure_ascii=False).replace("</", "<\\/")
OUT.parent.mkdir(parents=True, exist_ok=True)

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>我的雅思词汇库</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--navy:#173b78;--cream:#fff4d8;--white:#fffaf0;--ink:#17345f;--muted:#6d6a61;--amber:#b45309}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',sans-serif;background:var(--cream);color:var(--ink);line-height:1.6;padding:24px}
h1{font-size:22px;font-weight:800;color:var(--navy);margin-bottom:6px}
h2{font-size:16px;font-weight:800;color:var(--amber);margin:28px 0 10px}
.sub{font-size:13px;color:var(--muted);margin-bottom:20px}
.stats{display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap}
.stat{background:var(--white);border:2px solid var(--navy);border-radius:12px;padding:14px 20px;text-align:center;box-shadow:3px 3px 0 rgba(23,59,120,.35)}
.stat.amber{border-color:var(--amber);box-shadow:3px 3px 0 rgba(180,83,9,.3)}
.stat .num{font-size:28px;font-weight:800;color:var(--navy)}
.stat.amber .num{color:var(--amber)}
.stat .label{font-size:12px;color:var(--muted);font-weight:600}
.search{width:100%;max-width:400px;padding:10px 16px;border:2px solid var(--navy);border-radius:10px;font-size:14px;margin-bottom:20px;outline:none}
.search:focus{box-shadow:3px 3px 0 var(--navy)}
.group{background:var(--white);border:2px solid var(--navy);border-radius:14px 18px 12px 16px;padding:16px 20px;margin-bottom:16px;box-shadow:5px 5px 0 rgba(23,59,120,.6)}
.group.wb{border-color:var(--amber);box-shadow:5px 5px 0 rgba(180,83,9,.45)}
.group-title{font-size:13px;font-weight:800;color:var(--navy);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px dashed rgba(23,59,120,.3)}
.group.wb .group-title{color:var(--amber);border-bottom-color:rgba(180,83,9,.3)}
.items{display:flex;flex-direction:column;gap:8px}
.item{display:flex;gap:12px;align-items:baseline;padding:8px 10px;background:var(--cream);border-radius:8px;transition:background .15s}
.item:hover{background:#fde68a}
.item-term{font-weight:700;font-size:15px;color:#1a1a2e;font-family:Georgia,serif;min-width:0}
.item-trans{font-size:13px;color:#5a6577;flex-shrink:0}
.item-example{font-size:12px;color:var(--muted);font-style:italic;margin-top:2px}
.item-source{font-size:10px;color:var(--muted);margin-top:2px}
.ungr{margin-top:24px}
.empty{color:var(--muted);text-align:center;padding:40px}
.hint{font-size:12px;color:var(--muted);margin-top:8px}
.wb-head{display:flex;align-items:center;gap:12px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px dashed rgba(180,83,9,.3)}
.wb-head .group-title{margin:0;padding:0;border:none}
.wb-btn{padding:5px 12px;border:1.5px solid var(--amber);border-radius:6px;background:var(--white);font-size:12px;font-weight:700;color:var(--amber);cursor:pointer;flex-shrink:0}
.wb-btn:hover{background:var(--amber);color:var(--white)}
.wb-head .wb-mode{margin-left:auto}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px}
.card{perspective:600px;cursor:pointer}
.card-inner{position:relative;height:130px;transition:transform .35s;transform-style:preserve-3d}
.card.flipped .card-inner{transform:rotateY(180deg)}
.card-face{position:absolute;inset:0;backface-visibility:hidden;-webkit-backface-visibility:hidden;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;text-align:center;padding:10px 12px;background:var(--white);border:2px solid var(--amber);border-radius:10px;box-shadow:3px 3px 0 rgba(180,83,9,.35)}
.card-front .w{font-family:Georgia,serif;font-size:19px;font-weight:700;color:#1a1a2e;line-height:1.3}
.card-front .t{font-size:10px;color:var(--muted);letter-spacing:.5px}
.card-back{transform:rotateY(180deg);background:#fff7e6}
.card-back .m{font-size:14px;font-weight:600;color:var(--ink)}
.card-back .c{font-size:11px;color:var(--muted);font-style:italic;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical}
.card-back .s{font-size:10px;color:var(--amber);font-weight:600}
</style>
</head>
<body>
<h1>我的雅思词汇库</h1>
<div class="sub" id="updated"></div>
<div class="stats" id="stats"></div>
<input class="search" id="search" placeholder="搜索词 / 释义...">
<h2>✍ 划词词本（浏览器实时）</h2>
<div id="wordbank"></div>
<h2>📚 个人库（长期，批改推荐用）</h2>
<div id="groups"></div>
<div class="ungr" id="ungrouped"></div>
<script>
const LIB = """ + lib_json + """;
const TITLES = """ + titles_json + """;

const $groups = document.getElementById('groups');
const $ungrouped = document.getElementById('ungrouped');
const $search = document.getElementById('search');
const $stats = document.getElementById('stats');
const $updated = document.getElementById('updated');
const $wordbank = document.getElementById('wordbank');

const totalItems = LIB.groups.reduce((s,g) => s + g.items.length, 0) + (LIB.ungrouped||[]).length;
$updated.textContent = LIB.updated_at ? '更新于 ' + LIB.updated_at : '';

// === 划词词本：打开本页时实时读 localStorage（与阅读 skill 复习页同款机制）===
// 同一浏览器里 file:// 页面共享 localStorage，阅读页划的词这里直接可见。
function loadWordBank(){
  const wb = [];
  try{
    const seen = {};
    for(let i=0;i<localStorage.length;i++){
      const key = localStorage.key(i);
      const m = key && key.match(/^(?:english|ielts)_collect_(.+)$/);
      if(!m) continue;
      const essayId = m[1];
      if(seen['e'+essayId]) continue;  // english_/ielts_ 双键时只取一次
      seen['e'+essayId] = 1;
      let words;
      try{ words = JSON.parse(localStorage.getItem(key)); }catch{ continue; }
      if(!Array.isArray(words)) continue;
      words.forEach(w => {
        if(!w || !w.text || !w.translation || w.translation === '（待翻译）') return;
        wb.push({text:w.text, translation:w.translation, context:w.context||'',
                 essay:essayId, key:'e'+w.text.toLowerCase()});
      });
    }
  }catch(e){ /* localStorage 不可用时词本区显示为空即可 */ }
  // 跨篇去重：同一词保留第一次出现，来源篇名并列
  const byWord = {};
  wb.forEach(w => {
    if(!byWord[w.key]) byWord[w.key] = {text:w.text, translation:w.translation, context:w.context, essays:[]};
    const t = TITLES[w.essay] || w.essay;
    if(!byWord[w.key].essays.includes(t)) byWord[w.key].essays.push(t);
  });
  return Object.values(byWord);
}

let WORDS = loadWordBank();
let WB_MODE = 'cards';

function renderStats(){
  $stats.innerHTML =
    '<div class="stat amber"><div class="num">'+WORDS.length+'</div><div class="label">划词收词</div></div>'+
    '<div class="stat"><div class="num">'+LIB.groups.length+'</div><div class="label">语义组</div></div>'+
    '<div class="stat"><div class="num">'+totalItems+'</div><div class="label">个人库词数</div></div>';
}

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

function renderWordBank(f){
  const matched = WORDS.filter(w => !f || w.text.toLowerCase().includes(f) || (w.translation||'').toLowerCase().includes(f));
  if(!matched.length){
    $wordbank.innerHTML = '<div class="group wb"><div class="empty">还没有划词记录 —— 打开任意阅读页，选中词即可收藏；本页刷新后出现在这里</div></div>';
    return;
  }
  let body;
  if(WB_MODE === 'cards'){
    // 单词卡：正面单词，点击翻面看释义 + 划词原句 + 来源（仿阅读 skill 复习页）
    body = '<div class="cards">';
    matched.forEach(w => {
      body += '<div class="card"><div class="card-inner">'+
        '<div class="card-face card-front"><div class="w">'+esc(w.text)+'</div><div class="t">点击翻面</div></div>'+
        '<div class="card-face card-back"><div class="m">'+esc(w.translation)+'</div>'+
        (w.context?'<div class="c">'+esc(w.context)+'</div>':'')+
        '<div class="s">'+esc(w.essays[0]||'')+(w.essays.length>1?' 等'+w.essays.length+'篇':'')+'</div>'+
        '</div></div></div>';
    });
    body += '</div>';
  } else {
    body = '<div class="items">';
    matched.forEach(w => {
      body += '<div class="item"><div><div class="item-term">'+esc(w.text)+'</div>'+
        (w.context?'<div class="item-example">'+esc(w.context)+'</div>':'')+
        '<div class="item-source">来自: '+esc(w.essays.join(' · '))+'</div></div>'+
        '<div class="item-trans">'+esc(w.translation)+'</div></div>';
    });
    body += '</div>';
  }
  $wordbank.innerHTML = '<div class="group wb"><div class="wb-head">'+
    '<div class="group-title">划过的词 ('+matched.length+')</div>'+
    '<button class="wb-btn wb-mode" id="wb-mode">'+(WB_MODE==='cards'?'☰ 列表':'📇 单词卡')+'</button>'+
    '<button class="wb-btn" id="wb-export">⬇ 导出词单</button></div>'+ body + '</div>';
}

function render(filter){
  const f = (filter||'').toLowerCase();
  let html = '';
  LIB.groups.forEach(g => {
    const matched = g.items.filter(it =>
      !f || it.term.toLowerCase().includes(f) || (it.translation||'').toLowerCase().includes(f)
    );
    if(!matched.length) return;
    html += '<div class="group"><div class="group-title">'+esc(g.meaning_zh)+' ('+matched.length+')</div><div class="items">';
    matched.forEach(it => {
      html += '<div class="item"><div><div class="item-term">'+esc(it.term)+'</div>'+
        (it.example?'<div class="item-example">'+esc(it.example)+'</div>':'')+
        (it.source?'<div class="item-source">来自: '+esc(it.source)+'</div>':'')+'</div>'+
        '<div class="item-trans">'+esc(it.translation)+'</div></div>';
    });
    html += '</div></div>';
  });
  $groups.innerHTML = html || '<div class="empty">没有匹配结果</div>';
  const ug = (LIB.ungrouped||[]).filter(it =>
    !f || it.term.toLowerCase().includes(f) || (it.translation||'').toLowerCase().includes(f)
  );
  if(ug.length){
    $ungrouped.innerHTML = '<div class="group"><div class="group-title">未分组 ('+ug.length+')</div><div class="items">'+
      ug.map(it=>'<div class="item"><div><div class="item-term">'+esc(it.term)+'</div>'+
        (it.example?'<div class="item-example">'+esc(it.example)+'</div>':'')+'</div>'+
        '<div class="item-trans">'+esc(it.translation)+'</div></div>').join('')+'</div></div>';
  } else {
    $ungrouped.innerHTML = '';
  }
}

$search.addEventListener('input', ()=>{
  const f = $search.value;
  renderWordBank(f.toLowerCase());
  render(f);
});

// === 导出词单（一次点击代替手动复制；浏览器不允许页面悄悄写磁盘，这是必经的用户动作）===
// 下载 word/释义/原句 三列 txt（浏览器默认下载目录，文件名固定），词单同时进剪贴板。
// 之后对 agent 说「入库我划的词」即可，agent 按文件名去下载目录找最新的。
$wordbank.addEventListener('click', ev => {
  if(ev.target.id === 'wb-mode'){
    WB_MODE = WB_MODE === 'cards' ? 'list' : 'cards';
    renderWordBank($search.value.toLowerCase());
    return;
  }
  if(ev.target.closest('.card')){ ev.target.closest('.card').classList.toggle('flipped'); return; }
  if(ev.target.id !== 'wb-export') return;
  if(!WORDS.length) return;
  const lines = WORDS.map(w => [w.text, w.translation, w.context].join('\\t'));
  const blob = new Blob([lines.join('\\n')], {type:'text/plain;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'english-wordbank-export.txt';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(a.href), 5000);
  try{ navigator.clipboard.writeText(WORDS.map(w=>w.text).join(', ')).catch(()=>{}); }catch(e){}
  const btn = ev.target;
  btn.textContent = '✓ 已下载 english-wordbank-export.txt';
  setTimeout(()=>{ btn.textContent = '⬇ 导出词单'; }, 3000);
});
renderStats();
renderWordBank('');
render();
</script>
</body>
</html>"""

OUT.write_text(html, "utf-8")
print(f"✅ 词汇库浏览页已生成: {OUT}")
