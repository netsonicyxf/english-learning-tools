#!/usr/bin/env python3
"""Build a TOC/index page linking the reader pages generated from one
batch-parsed document (see SKILL.md 批量解析文档).

Data (via --data-file or --data):
{
  "id": "simon-task2",                      // used for the default --out name
  "title": "考官Simon雅思大作文范文",
  "source": "文件名或来源说明",
  "items": [
    {"title": "1. 政府是否该支持本土电影", "file": "simon-task2-01-local-films-reader.html",
     "meta": "295 words · band 9"}
  ]
}
Links are relative — the index and the reader pages must live in the same
directory (flat in ~/Desktop/English Writing/ by convention)."""
import html, json, sys, argparse
from pathlib import Path

OUT_DIR = Path.home() / "Desktop" / "English Writing"

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>范文目录</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--navy:#173b78;--sun:#ffd43b;--cream:#fff4d8;--white:#fffaf0;--ink:#17345f;--muted:#6d6a61}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',sans-serif;background:var(--cream);color:var(--ink);line-height:1.6}
.top-bar{padding:16px 24px;background:var(--navy);box-shadow:0 4px 0 rgba(23,59,120,.35)}
.top-bar h1{font-size:18px;font-weight:800;color:var(--cream)}
.top-bar p{font-size:12px;color:rgba(255,244,216,.75);margin-top:2px}
.wrap{max-width:760px;margin:26px auto;padding:0 18px}
.hint{font-size:13px;color:var(--muted);background:var(--white);border:2px dashed rgba(23,59,120,.35);border-radius:12px;padding:10px 14px;margin-bottom:18px}
.list{display:flex;flex-direction:column;gap:10px}
.item{display:flex;align-items:center;gap:14px;background:var(--white);border:2.5px solid var(--navy);border-radius:14px 18px 12px 16px;padding:13px 18px;text-decoration:none;color:var(--ink);box-shadow:4px 5px 0 rgba(23,59,120,.8);transition:all .15s}
.item:hover{transform:translate(-2px,-2px);box-shadow:6px 7px 0 rgba(23,59,120,.85);background:#fffdf5}
.num{flex-shrink:0;width:34px;height:34px;border-radius:10px;background:var(--sun);border:2px solid var(--navy);display:flex;align-items:center;justify-content:center;font-weight:800;color:var(--navy);font-size:14px}
.it-main{flex:1;min-width:0}
.it-title{font-size:15px;font-weight:700;display:block}
.it-meta{font-size:12px;color:var(--muted);display:block;margin-top:2px}
.arrow{flex-shrink:0;color:var(--navy);font-weight:800;font-size:18px}
@media(max-width:600px){.item{gap:10px;padding:11px 14px}}
</style>
</head>
<body>
<header class="top-bar">
  <h1>__TITLE__</h1>
  <p>__SOURCE__ · 共 __COUNT__ 篇</p>
</header>
<main class="wrap">
  <div class="hint">点击任意一篇进入阅读页；阅读页里<b>划词即收单词本</b>（每篇独立保存），点「导出单词本」可复制三列格式粘贴回对话入库。</div>
  <div class="list">
__ITEMS__
  </div>
</main>
</body>
</html>
"""

ITEM = ('<a class="item" href="{file}"><span class="num">{n}</span>'
        '<span class="it-main"><span class="it-title">{title}</span>{meta}</span>'
        '<span class="arrow">&rarr;</span></a>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="JSON string of index data")
    ap.add_argument("--data-file", help="path to JSON file of index data")
    ap.add_argument("--out", help="output HTML path (默认 ~/Desktop/English Writing/<id>-index.html)")
    args = ap.parse_args()

    data = json.loads(Path(args.data_file).read_text("utf-8")) if args.data_file else json.loads(args.data)
    items = data.get("items") or []
    if not items:
        sys.exit("❌ index data 缺 items（或为空）")

    rows = []
    for i, it in enumerate(items, 1):
        for k in ("title", "file"):
            if not it.get(k):
                sys.exit(f"❌ items[{i - 1}] 缺 {k}")
        meta = (f'<span class="it-meta">{html.escape(str(it["meta"]))}</span>'
                if it.get("meta") else "")
        rows.append(ITEM.format(
            file=html.escape(str(it["file"]), quote=True),
            n=i, title=html.escape(str(it["title"])), meta=meta))

    page = (TEMPLATE
            .replace("__TITLE__", html.escape(str(data.get("title", "范文目录"))))
            .replace("__SOURCE__", html.escape(str(data.get("source", ""))))
            .replace("__COUNT__", str(len(rows)))
            .replace("__ITEMS__", "\n".join(rows)))

    out = Path(args.out) if args.out else (OUT_DIR / f"{data.get('id', 'english')}-index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, "utf-8")

    # catch agent mistakes early: relative links must resolve next to the index
    missing = [it["file"] for it in items if not (out.parent / it["file"]).is_file()]
    if missing:
        print(f"⚠ 有 {len(missing)} 个链接目标不存在于 {out.parent}:")
        for f in missing:
            print(f"  - {f}")
    print(f"✅ 目录页已生成: {out}（{len(rows)} 篇）")


if __name__ == "__main__":
    main()
