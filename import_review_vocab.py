#!/usr/bin/env python3
"""一键把复习构建（build_review.py）导出的 review-vocab.json 灌进 vocab-drill 词库。

用法:
  python3 import_review_vocab.py                # 全量导入（默认 ~/Desktop/English Learning/review-vocab.json）
  python3 import_review_vocab.py --core         # 只导跨文章重复词（core）
  python3 import_review_vocab.py <文件路径>     # review-vocab.json，或纯词单 txt
                                                 #（复习页导出的 wordbank-export.txt 三列取首列；
                                                 #  也吃逗号/换行分隔的裸词单——词单模式只登记，
                                                 #  词卡留到 vocab-drill 首测时生成）

行为（全部走 vocab.mjs 官方命令，不碰 state 文件）:
  1. 单次 --add 登记全部词（已在词库的自动跳过，幂等）
  2. 只对本次新登记的词 --card 存词卡：释义 + 文章原句例句（存卡即锚点）；
     重跑不会覆盖已有词卡（包括 agent 后来改写的 quirky 例句）
  3. 重渲染 dashboard 并打开
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOCAB_MJS = HERE.parent / "vocab-drill" / "vocab.mjs"
DEFAULT_JSON = Path.home() / "Desktop" / "English Learning" / "review-vocab.json"


def run(args):
    return subprocess.run(["node", str(VOCAB_MJS), *args],
                          capture_output=True, text=True)


def main():
    if not VOCAB_MJS.exists():
        sys.exit(f"找不到 vocab.mjs：{VOCAB_MJS}\n"
                 "(应与 english-reading-exercises 同级安装在 english-learning-tools 下)")

    argv = sys.argv[1:]
    core_only = "--core" in argv
    src = Path(next((a for a in argv if not a.startswith("--")), DEFAULT_JSON))
    raw = src.read_text("utf-8")

    if raw.lstrip().startswith("{"):
        # review-vocab.json（build 导出）：带释义+例句，登记并存词卡
        data = json.loads(raw)
        entries = data["core"] if core_only else data["all"]
        have_cards = True
    else:
        # 纯词单（复习页导出的 wordbank-export.txt 三列取首列，或逗号/换行分隔）：
        # 只登记，词卡留到 vocab-drill 首批测时按正常流程生成
        entries, seen = [], set()
        for ln in raw.splitlines():
            first_col = ln.strip().split("\t")[0]
            for w in first_col.split(","):
                w = w.strip().lower()
                if w and w not in seen:
                    seen.add(w)
                    entries.append({"word": w})
        have_cards = False

    words = [e["word"].strip().lower() for e in entries if e["word"].strip()]
    print(f"{src}\n{len(words)} 词，开始登记…")

    res = run(["--add", ",".join(words)])
    if res.returncode:
        sys.exit(res.stderr)
    # stdout 第一行是「已登记 N 个新词…」汇总，其后每行一个新词
    added = {ln.strip() for ln in res.stdout.splitlines()[1:] if ln.strip()}
    print(res.stdout.splitlines()[0])

    n_card = 0
    for i, e in enumerate(entries, 1):
        if not have_cards:
            break
        w = e["word"].strip().lower()
        if w not in added:
            continue
        card = {"word": w, "meaning": e.get("meaning", ""),
                "example": e.get("example", "")}
        r = run(["--card", w, "--json",
                 json.dumps(card, ensure_ascii=False)])
        if r.returncode:
            print(f"  词卡失败 {w}: {r.stderr.strip()}")
        else:
            n_card += 1
        if i % 200 == 0:
            print(f"  …{i}/{len(entries)}")

    out = Path.home() / "Downloads" / "vocab-dashboard.html"
    r = run(["--render", "--type", "dashboard", "--out", str(out)])
    if r.returncode:
        print(r.stderr)
    else:
        subprocess.run(["open", str(out)])
    print(f"\n✓ 完成：新登记 {len(added)}，存词卡 {n_card}，dashboard: {out}")


if __name__ == "__main__":
    main()
