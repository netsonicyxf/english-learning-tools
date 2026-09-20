#!/usr/bin/env python3
"""Validate IELTS skill data before injecting into templates."""
import json, re, sys, argparse
from pathlib import Path

BANDS = ("overall", "ta", "cc", "lr", "gra")
# must match the template's split(/\n\s*\n/) exactly, or paragraph indices
# validated here won't be the ones the page renders.
PARA_SPLIT = re.compile(r"\n\s*\n")


def _overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


def check_marks(paras, annos):
    """Replay the template's buildMarks(): within a paragraph, longer text wins
    the span and any annotation fully covered by it is silently dropped — the
    page renders no highlight and files it under 未定位. Report those here."""
    errs = []
    for pi, para in enumerate(paras):
        low = para.lower()
        target = [(i, a) for i, a in enumerate(annos) if a.get("paragraph") == pi]
        marks = []
        for i, a in sorted(target, key=lambda x: -len(x[1].get("text") or "")):
            t = (a.get("text") or "").lower()
            if not t:
                continue
            idx, placed, guard = low.find(t), False, 0
            while idx != -1 and guard < 50:
                guard += 1
                cand = (idx, idx + len(t))
                if not any(_overlap(m[:2], cand) for m in marks):
                    marks.append((cand[0], cand[1], i))
                    placed = True
                    break
                idx = low.find(t, idx + len(t))
            if not placed:
                first = low.find(t)
                blockers = [m[2] for m in marks
                            if _overlap(m[:2], (first, first + len(t)))]
                errs.append(
                    f"批注#{i} 会渲染成「未定位」：片段被批注#{blockers} 的更长片段整段覆盖"
                    f"，页面无处高亮 — 换一个不重叠的片段: {a.get('text')[:40]}"
                )
    return errs


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
    # only worth replaying the marks when every text already sits in its paragraph
    if not errs:
        errs += check_marks(paras, d.get("annotations", []))
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
