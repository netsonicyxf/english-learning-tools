#!/usr/bin/env python3
"""把 vocab-drill 词库一键导入个人库（library.json）。

只**读** vocab-drill 的 state 文件（红线：state 只由 vocab.mjs 写），把每个有词卡
的词经 manage_library.merge() 并入个人库，复用其「同义组归并 + 组内去重」规则，
重复导入安全。词卡的中文释义 meaning 同时充当 group_meaning_zh：相同释义的词
自动聚成同义组，之后范文入库遇到同释义也会并进同一组。

用法：
  python3 import_vocab_drill.py            # 导入
  python3 import_vocab_drill.py --dry-run  # 只预览要导什么，不写盘
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import manage_library  # noqa: E402  同目录复用合并/去重逻辑

POS_MAP = {"n": "noun", "v": "verb", "adj": "adj", "adv": "adv"}


def vocab_state_path():
    """与 vocab.mjs 同一套定位规则：VOCAB_DRILL_HOME 可重定向，
    ~/.ai-tutoring-config.json 的 student 决定文件名后缀。"""
    home = Path(os.environ.get("VOCAB_DRILL_HOME", str(Path.home())))
    student = "default"
    cfg = home / ".ai-tutoring-config.json"
    if cfg.exists():
        try:
            student = json.loads(cfg.read_text("utf-8")).get("student") or "default"
        except (json.JSONDecodeError, OSError):
            pass  # 配置坏了就按 default，与 vocab.mjs 行为一致
    name = ".vocab-drill-state.json" if student == "default" else f".vocab-drill-state-{student}.json"
    return home / name


def map_pos(pos, term):
    """vocab-drill 的 'n.' / 'adj.' / 'n.&v.' → schema 的 adj|verb|noun|adv|phrase|other。"""
    if " " in term.strip() or "phr" in (pos or "").lower():
        return "phrase"
    for tok in re.split(r"[.&\s]+", (pos or "").lower().replace(".", "")):
        if tok in POS_MAP:
            return POS_MAP[tok]  # 复合词性（n.&v.）取第一个
    return "other"


def collect(state_path):
    """state → 待入库 items。无词卡或词卡无释义的词跳过（没有释义没法归同义组）。"""
    state = json.loads(state_path.read_text("utf-8"))
    items, skipped = [], []
    for key, entry in state.get("words", {}).items():
        card = entry.get("card") or {}
        term = (card.get("word") or key).strip()
        meaning = (card.get("meaning") or "").split("｜")[0].strip()
        if not card or not meaning:
            skipped.append(term)
            continue
        items.append({
            "term": term,
            "pos": map_pos(card.get("pos"), term),
            "translation": meaning,
            "group_meaning_zh": meaning,
            "example": card.get("example", ""),
            "source": "vocab-drill",
        })
    return items, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只预览，不写盘")
    args = ap.parse_args()

    state_path = vocab_state_path()
    if not state_path.exists():
        sys.exit(f"❌ 找不到 vocab-drill 词库：{state_path}（先在 vocab-drill 里 --add 登记词）")

    items, skipped = collect(state_path)
    print(f"📖 {state_path.name}：共 {len(items) + len(skipped)} 个词，"
          f"{len(items)} 个有词卡可导入" + (f"，跳过 {len(skipped)} 个无词卡/无释义（{', '.join(skipped[:5])}…）" if skipped else ""))

    if args.dry_run:
        print("（dry-run）前 5 条预览：")
        for it in items[:5]:
            print(f"  {it['term']} [{it['pos']}] {it['translation']} → 组「{it['group_meaning_zh']}」")
        return

    added = manage_library.merge({"items": items})
    print(f"↔️ 其中新收录 {added} 条，其余为组内重复已跳过。")
    print("💡 想刷新浏览页：python3 %s/build_library_view.py" % SCRIPT_DIR)


if __name__ == "__main__":
    main()
