#!/usr/bin/env python3
"""Generate an HTML page to view the personal IELTS vocabulary library."""
import argparse, json
from pathlib import Path

LIB = Path.home() / "Documents" / "english-writing" / "library.json"
DEFAULT_OUT = Path.home() / "Desktop" / "English Writing" / "essays" / "my-library.html"

ap = argparse.ArgumentParser()
ap.add_argument("--out", help="output HTML path (default: ~/Desktop/English Writing/essays/my-library.html)")
args = ap.parse_args()
OUT = Path(args.out) if args.out else DEFAULT_OUT

lib = json.loads(LIB.read_text("utf-8")) if LIB.exists() else {"groups": [], "ungrouped": []}
data_json = json.dumps(lib, ensure_ascii=False).replace("</", "<\\/")
OUT.parent.mkdir(parents=True, exist_ok=True)

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>我的雅思词汇库</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--navy:#173b78;--cream:#fff4d8;--white:#fffaf0;--ink:#17345f;--muted:#6d6a61}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',sans-serif;background:var(--cream);color:var(--ink);line-height:1.6;padding:24px}
h1{font-size:22px;font-weight:800;color:var(--navy);margin-bottom:6px}
.sub{font-size:13px;color:var(--muted);margin-bottom:20px}
.stats{display:flex;gap:16px;margin-bottom:24px}
.stat{background:var(--white);border:2px solid var(--navy);border-radius:12px;padding:14px 20px;text-align:center;box-shadow:3px 3px 0 rgba(23,59,120,.35)}
.stat .num{font-size:28px;font-weight:800;color:var(--navy)}
.stat .label{font-size:12px;color:var(--muted);font-weight:600}
.search{width:100%;max-width:400px;padding:10px 16px;border:2px solid var(--navy);border-radius:10px;font-size:14px;margin-bottom:20px;outline:none}
.search:focus{box-shadow:3px 3px 0 var(--navy)}
.group{background:var(--white);border:2px solid var(--navy);border-radius:14px 18px 12px 16px;padding:16px 20px;margin-bottom:16px;box-shadow:5px 5px 0 rgba(23,59,120,.6)}
.group-title{font-size:13px;font-weight:800;color:var(--navy);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px dashed rgba(23,59,120,.3)}
.items{display:flex;flex-direction:column;gap:8px}
.item{display:flex;gap:12px;align-items:baseline;padding:8px 10px;background:var(--cream);border-radius:8px;transition:background .15s}
.item:hover{background:#fde68a}
.item-term{font-weight:700;font-size:15px;color:#1a1a2e;font-family:Georgia,serif;min-width:0}
.item-trans{font-size:13px;color:#5a6577;flex-shrink:0}
.item-example{font-size:12px;color:var(--muted);font-style:italic;margin-top:2px}
.item-source{font-size:10px;color:var(--muted);margin-top:2px}
.ungr{margin-top:24px}
.empty{color:var(--muted);text-align:center;padding:40px}
.copy-btn{padding:4px 10px;border:1.5px solid var(--navy);border-radius:6px;background:var(--cream);font-size:11px;cursor:pointer;font-weight:700;color:var(--navy);margin-left:auto;flex-shrink:0}
.copy-btn:hover{background:var(--navy);color:var(--white)}
</style>
</head>
<body>
<h1>我的雅思词汇库</h1>
<div class="sub" id="updated"></div>
<div class="stats" id="stats"></div>
<input class="search" id="search" placeholder="搜索词 / 释义...">
<div id="groups"></div>
<div class="ungr" id="ungrouped"></div>
<script>
const LIB = """ + data_json + """;

const $groups = document.getElementById('groups');
const $ungrouped = document.getElementById('ungrouped');
const $search = document.getElementById('search');
const $stats = document.getElementById('stats');
const $updated = document.getElementById('updated');

const totalItems = LIB.groups.reduce((s,g) => s + g.items.length, 0) + (LIB.ungrouped||[]).length;
$updated.textContent = LIB.updated_at ? '更新于 ' + LIB.updated_at : '';
$stats.innerHTML =
  '<div class="stat"><div class="num">'+LIB.groups.length+'</div><div class="label">语义组</div></div>'+
  '<div class="stat"><div class="num">'+totalItems+'</div><div class="label">总词数</div></div>';

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function copyText(t){return navigator.clipboard.writeText(t).catch(()=>{});}

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

$search.addEventListener('input', ()=>render($search.value));
render();
</script>
</body>
</html>"""

OUT.write_text(html, "utf-8")
print(f"✅ 词汇库浏览页已生成: {OUT}")
