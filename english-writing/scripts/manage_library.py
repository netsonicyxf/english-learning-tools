#!/usr/bin/env python3
"""Manage the personal IELTS library (library.json).

Modes:
  --data '<json>'       merge collected items into the library (agent does the
                        synonym clustering; each item carries group_meaning_zh)
  --print              print the current library as JSON (agent reads it for
                        correction suggestions)
  --init              create an empty library if missing
"""
import json, sys, argparse, datetime
from pathlib import Path

LIB = Path.home() / "Documents" / "ielts-writing" / "library.json"


def load():
    if LIB.exists():
        return json.loads(LIB.read_text("utf-8"))
    return {"version": 1, "updated_at": None, "groups": [], "ungrouped": []}


def save(lib):
    lib["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    LIB.parent.mkdir(parents=True, exist_ok=True)
    LIB.write_text(json.dumps(lib, ensure_ascii=False, indent=2), "utf-8")


def norm(s):
    return "".join(ch for ch in (s or "") if ch.isalnum()).lower()


def merge(data):
    lib = load()
    items = data.get("items", [])
    added = 0
    for it in items:
        term = (it.get("term") or "").strip()
        if not term:
            continue
        gkey = norm(it.get("group_meaning_zh", ""))
        group = None
        if gkey:
            for g in lib["groups"]:
                if norm(g.get("meaning_zh", "")) == gkey:
                    group = g
                    break
        if group is None:
            if gkey:
                gid = f"g{len(lib['groups']) + 1}"
                group = {"id": gid, "meaning_zh": it["group_meaning_zh"].strip(), "items": []}
                lib["groups"].append(group)
            else:
                lib.setdefault("ungrouped", []).append(_mk_item(it, term))
                added += 1
                continue
        # dedup within group (case-insensitive)
        exists = any(norm(x.get("term", "")) == norm(term) for x in group["items"])
        if exists:
            continue
        group["items"].append(_mk_item(it, term))
        added += 1
    save(lib)
    groups_n = len(lib["groups"])
    total = sum(len(g["items"]) for g in lib["groups"]) + len(lib.get("ungrouped", []))
    print(f"✅ 已收录 {added} 条；当前库共 {total} 条，分 {groups_n} 个语义组。")
    return added


def _mk_item(it, term):
    return {
        "term": term,
        "pos": it.get("pos", ""),
        "translation": it.get("translation", ""),
        "example": it.get("example", it.get("context", "")),
        "source": it.get("source", ""),
        "added_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data")
    ap.add_argument("--data-file")
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--init", action="store_true")
    args = ap.parse_args()

    if args.init:
        save(load())
        print(f"✅ 已初始化库: {LIB}")
        return
    if args.print:
        print(json.dumps(load(), ensure_ascii=False, indent=2))
        return
    if args.data_file:
        data = json.loads(Path(args.data_file).read_text("utf-8"))
    elif args.data:
        data = json.loads(args.data)
    else:
        sys.exit("❌ 需要 --data / --data-file / --print / --init 之一")
    merge(data)


if __name__ == "__main__":
    main()
