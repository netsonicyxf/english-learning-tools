#!/usr/bin/env python3
"""
Build correction review HTML: band-score trends + error analysis by IELTS dimension.

Primary data source is corrections-log.jsonl (appended by build_correction.py,
contains scores AND annotations). *-correction.html files are only scanned as a
fallback for corrections built before logging existed — their timeline entry
uses the file's mtime, which stays stable across rebuilds of this page.
"""
import json, re, sys, glob, argparse
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "templates" / "review-corrections.html"
DEFAULT_DIR = Path.home() / "Desktop" / "IELTS Writing"
LOG_FILE = Path.home() / "Documents" / "ielts-writing" / "corrections-log.jsonl"

# Errors are grouped by the annotation's IELTS band dimension. Comments are
# mostly Chinese, so keyword matching on comment text does not work — and the
# band field (TA/CC/LR/GRA) is exactly the categorisation an IELTS learner wants.
BAND_CATEGORIES = [
    ("GRA", "语法 (GRA)"),
    ("LR", "词汇 (LR)"),
    ("CC", "结构与衔接 (CC)"),
    ("TA", "任务回应 (TA)"),
]


def category_for(band):
    for code, name in BAND_CATEGORIES:
        if (band or "").strip().upper() == code:
            return name
    return "其他"


def extract_correction_data(html_text):
    """Extract CORRECTION_DATA JSON from a correction HTML file (legacy fallback).

    Greedy match anchored on the statement that follows the assignment, so a
    `};` occurring inside a string can't truncate the JSON; non-greedy pass as
    a second chance. json.loads is the final validator.
    """
    m = re.search(
        r'const CORRECTION_DATA\s*=\s*(\{.*\});\s*\n\s*(?:function|const|var|let)',
        html_text, re.DOTALL)
    if not m:
        m = re.search(r'const CORRECTION_DATA\s*=\s*(\{.*?\});', html_text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1).replace('<\\/', '</'))
    except json.JSONDecodeError:
        return None


def load_log():
    """Load correction records from corrections-log.jsonl."""
    if not LOG_FILE.exists():
        return []
    records = []
    for line in LOG_FILE.read_text("utf-8").strip().split("\n"):
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def normalize_record(rec):
    """Unify a log record or an HTML-extracted correction into one shape."""
    annos = rec.get("annotations", [])
    return {
        "ts": rec.get("ts", ""),
        "slug": rec.get("slug") or rec.get("id", ""),
        "topic": rec.get("topic", ""),
        "band": rec.get("band", {}),
        "errorCount": sum(1 for a in annos if a.get("severity") == "error"),
        "improveCount": sum(1 for a in annos if a.get("severity") == "improve"),
        "annotations": annos,
    }


def group_errors(history):
    """Group error annotations by IELTS band dimension, count + sample comments."""
    groups = {}
    for rec in history:
        for a in rec["annotations"]:
            if a.get("severity") != "error":
                continue
            cat = category_for(a.get("band", ""))
            g = groups.setdefault(
                cat, {"category": cat, "count": 0, "slugs": [], "comments": []})
            g["count"] += 1
            if rec["slug"] not in g["slugs"]:
                g["slugs"].append(rec["slug"])
            if a.get("comment") and len(g["comments"]) < 3:
                g["comments"].append(a["comment"])
    return sorted(groups.values(), key=lambda g: -g["count"])


def build_review(correction_dir=DEFAULT_DIR, output=None):
    correction_dir = Path(correction_dir)

    # 1. History from the log — the durable source (one entry per correction build).
    history = []
    logged_slugs = set()
    for rec in load_log():
        if not rec.get("slug"):
            continue
        logged_slugs.add(rec["slug"])
        history.append(normalize_record(rec))

    # 2. Legacy fallback: correction HTMLs built before logging existed.
    #    mtime is the best available timestamp — and unlike datetime.now(),
    #    it doesn't drift forward on every rebuild of this page.
    for fpath in sorted(glob.glob(str(correction_dir / "*-correction.html"))):
        data = extract_correction_data(Path(fpath).read_text("utf-8"))
        if not data or not data.get("id") or data["id"] in logged_slugs:
            continue
        rec = normalize_record(data)
        rec["ts"] = datetime.fromtimestamp(
            Path(fpath).stat().st_mtime).isoformat(timespec="seconds")
        print(f"  ⚠ {Path(fpath).name}: 无 log 记录，按文件修改时间 {rec['ts']} 收录")
        history.append(rec)

    if not history:
        sys.exit(f"❌ 没有可用的批改记录（log: {LOG_FILE}；目录: {correction_dir}）")

    # 3. Chronological order — the template reads the last entry as “最新”.
    history.sort(key=lambda r: r["ts"])

    # 4. Error analysis + slim history for embedding (drop annotations —
    #    the page only needs scores/counts; keeps the file small).
    review_data = {
        "history": [
            {k: r[k] for k in ("ts", "slug", "topic", "band", "errorCount", "improveCount")}
            for r in history
        ],
        "errorGroups": group_errors(history),
        "correctionCount": len(history),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    template = TEMPLATE.read_text("utf-8")
    data_json = json.dumps(review_data, ensure_ascii=False).replace("</", "<\\/")
    html_output = template.replace("{{REVIEW_DATA_JSON}}", data_json)
    html_output = html_output.replace("{{TIMESTAMP}}", review_data["generated"])

    if output is None:
        output = str(correction_dir / "review-corrections.html")
    Path(output).write_text(html_output, "utf-8")

    print(f"\n✓ 汇总页: {output}")
    print(f"  批改记录: {len(history)} 条")
    print(f"  问题分组: {len(review_data['errorGroups'])} 组")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="生成雅思批改进度汇总页（log 为主数据源，HTML 兜底）")
    ap.add_argument("--dir", default=str(DEFAULT_DIR),
                    help="批改 HTML 所在目录（仅用于兜底扫描无 log 的旧文件）")
    ap.add_argument("--out", default=None, help="输出 HTML 路径")
    args = ap.parse_args()
    build_review(args.dir, args.out)
