#!/usr/bin/env python3
"""Validate IELTS skill data before injecting into templates."""
import json, re, sys, argparse
from pathlib import Path

BANDS = ("overall", "ta", "cc", "lr", "gra")
# must match the template's split(/\n\s*\n/) exactly, or paragraph indices
# validated here won't be the ones the page renders.
PARA_SPLIT = re.compile(r"\n\s*\n")


def validate_reader(d):
    errs = []
    for k in ("id", "title", "content"):
        if k not in d:
            errs.append(f"reader 缺少 {k}")
    if not isinstance(d.get("dictionary"), dict):
        errs.append("dictionary 不是对象")
    return errs


def validate_correction(d):
    errs = []
    if "essay" not in d:
        errs.append("correction 缺少 essay")
        return errs
    essay = d["essay"]
    paras = [p.strip() for p in PARA_SPLIT.split(essay) if p.strip()]
    flat = essay.lower()
    for i, a in enumerate(d.get("annotations", [])):
        for k in ("level", "paragraph", "text", "severity", "comment"):
            if k not in a:
                errs.append(f"批注#{i} 缺少 {k}")
        pi = a.get("paragraph")
        in_range = isinstance(pi, int) and 0 <= pi < len(paras)
        if pi is not None and not in_range:
            errs.append(f"批注#{i} 的 paragraph={pi} 超出段落范围 0-{len(paras) - 1}")
        t = (a.get("text") or "").lower()
        if t:
            # the template locates marks *within* the annotated paragraph, so
            # checking against the whole essay would pass data the page can't render.
            if in_range:
                if t not in paras[pi].lower():
                    where = "在别的段落里" if t in flat else "在正文中完全找不到"
                    errs.append(
                        f"批注#{i} 的 text 不在第 {pi} 段（{where}）: {a.get('text')[:50]}"
                    )
            elif t not in flat:
                errs.append(f"批注#{i} 的 text 在正文中找不到: {a.get('text')[:50]}")
        if a.get("severity") not in ("error", "improve", "good"):
            errs.append(f"批注#{i} severity 非法: {a.get('severity')}")
    band = d.get("band", {})
    for k in BANDS:
        v = band.get(k)
        if v is not None and not (0 <= float(v) <= 9):
            errs.append(f"band.{k}={v} 超出 0-9")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["reader", "correction"])
    ap.add_argument("--data")
    ap.add_argument("--data-file")
    args = ap.parse_args()
    if args.data_file:
        d = json.loads(Path(args.data_file).read_text("utf-8"))
    else:
        d = json.loads(args.data)
    errs = validate_reader(d) if args.kind == "reader" else validate_correction(d)
    if errs:
        print("❌ 校验失败:")
        for e in errs:
            print("  - " + e)
        sys.exit(1)
    print("✅ 校验通过")


if __name__ == "__main__":
    main()
