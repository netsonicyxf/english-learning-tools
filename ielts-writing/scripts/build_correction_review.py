#!/usr/bin/env python3
"""
Build correction review HTML from all *-correction.html files and corrections-log.jsonl.
Generates a summary page with band-score trends and high-frequency error analysis.
"""
import json, re, sys, glob
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "templates" / "review-corrections.html"
DEFAULT_DIR = Path.home() / "Desktop" / "IELTS Writing"
LOG_FILE = Path.home() / "Documents" / "ielts-writing" / "corrections-log.jsonl"

# Error-classification keywords (order matters — first match wins)
ERROR_KEYWORDS = [
    ("grammar", "语法", [
        "tense", "subject-verb", "agreement", "article", "dangling modifier",
        "run-on", "comma splice", "fragments", "parallel", "pronoun",
        "passive", "word order", "missing", "incorrect", "tense shift",
        "grammar", "grammatical",
    ]),
    ("vocabulary", "词汇", [
        "collocation", "wrong word", "inappropriate", "vague", "repetitive",
        "awkward", "informal", "register", "precise", "lexical",
        "vocabulary", "word choice", "repetition",
    ]),
    ("structure", "结构", [
        "coherence", "cohesion", "paragraph", "topic sentence", "support",
        "logical", "development", "off-topic", "task response", "relevance",
        "structure", "organization",
    ]),
    ("expression", "搭配/表达", [
        "idiom", "phrasal verb", "collocation", "unnatural", "chinese english",
        "translation", "make", "do", "take", "give",
    ]),
]


def classify_error(comment):
    """Classify an error annotation into a category based on keyword matching."""
    lower = (comment or "").lower()
    for cat_id, cat_name, keywords in ERROR_KEYWORDS:
        for kw in keywords:
            if kw in lower:
                return cat_id, cat_name
    return "other", "其他"


def extract_correction_data(html_text):
    """Extract CORRECTION_DATA JSON from a correction HTML file."""
    m = re.search(
        r'const CORRECTION_DATA\s*=\s*(\{.*\});\s*\n\s*(?:function|const|var|let)',
        html_text, re.DOTALL)
    if not m:
        m = re.search(
            r'const CORRECTION_DATA\s*=\s*(\{.*?\});',
            html_text, re.DOTALL)
    if not m:
        return None
    raw = m.group(1).replace('<\\/', '</')
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def load_log():
    """Load band-score history from corrections-log.jsonl."""
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


def build_review(correction_dir=DEFAULT_DIR, output=None):
    correction_dir = Path(correction_dir)
    # 1. Collect correction data from HTML files
    files = sorted(glob.glob(str(correction_dir / "*-correction.html")))
    if not files:
        print(f"No *-correction.html files found in {correction_dir}")
        sys.exit(1)

    print(f"Found {len(files)} correction file(s):")
    corrections = []
    all_errors = []  # {keyword, category, slug, comment}

    for fpath in files:
        html = Path(fpath).read_text("utf-8")
        data = extract_correction_data(html)
        if not data:
            print(f"  SKIP (no data): {Path(fpath).name}")
            continue

        slug = data.get("id", Path(fpath).stem)
        topic = data.get("topic", "")
        band = data.get("band", {})
        annotations = data.get("annotations", [])
        print(f"  ✓ {topic or slug} (overall={band.get('overall', '?')}, "
              f"{len(annotations)} annotations)")

        corrections.append({
            "slug": slug,
            "topic": topic,
            "band": band,
            "annotations": annotations,
        })

        for a in annotations:
            if a.get("severity") == "error":
                cat_id, cat_name = classify_error(a.get("comment", ""))
                # Extract a keyword from the comment (first few words)
                comment = a.get("comment", "")
                keyword = _extract_keyword(comment, cat_id)
                all_errors.append({
                    "keyword": keyword,
                    "category": cat_name,
                    "slug": topic or slug,
                    "comment": comment,
                })

    # 2. Load log for time-series band scores
    log_records = load_log()
    # Merge: log has timestamps, corrections have richer data.
    # Use log as the time-series source, match by slug.
    logged_slugs = set()
    history = []
    for rec in log_records:
        slug = rec.get("slug", "")
        logged_slugs.add(slug)
        # Find matching correction for topic name
        matching = next((c for c in corrections if c["slug"] == slug), None)
        history.append({
            "ts": rec.get("ts", ""),
            "slug": slug,
            "topic": rec.get("topic") or (matching["topic"] if matching else ""),
            "band": rec.get("band", {}),
            "errorCount": rec.get("errorCount", 0),
            "improveCount": rec.get("improveCount", 0),
        })

    # Supplement with corrections that have no log entry (generated before logging was added)
    for c in corrections:
        if c["slug"] not in logged_slugs:
            history.append({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "slug": c["slug"],
                "topic": c["topic"],
                "band": c["band"],
                "errorCount": sum(1 for a in c["annotations"] if a.get("severity") == "error"),
                "improveCount": sum(1 for a in c["annotations"] if a.get("severity") == "improve"),
            })

    # 3. Aggregate error groups
    error_groups = _group_errors(all_errors)

    # 4. Build review data
    review_data = {
        "history": history,
        "errorGroups": error_groups,
        "correctionCount": len(corrections),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # 5. Fill template
    template = TEMPLATE.read_text("utf-8")
    data_json = json.dumps(review_data, ensure_ascii=False).replace("</", "<\\/")
    html_output = template.replace("{{REVIEW_DATA_JSON}}", data_json)
    html_output = html_output.replace("{{TIMESTAMP}}", review_data["generated"])

    if output is None:
        output = str(correction_dir / "review-corrections.html")
    Path(output).write_text(html_output, "utf-8")

    print(f"\n✓ Review page: {output}")
    print(f"  Corrections: {len(corrections)}")
    print(f"  History records: {len(history)}")
    print(f"  Error groups: {len(error_groups)}")


def _extract_keyword(comment, category):
    """Extract a short keyword from an error comment for grouping."""
    if not comment:
        return "unknown"
    # Try to get the main issue (usually before the first period or colon)
    for sep in [".", "，", "：", ":"]:
        if sep in comment:
            comment = comment.split(sep)[0]
    # Take first ~30 chars
    keyword = comment.strip()[:30]
    if len(comment.strip()) > 30:
        keyword += "…"
    return keyword


def _group_errors(errors):
    """Group errors by keyword, count occurrences, collect slugs."""
    groups = {}
    for e in errors:
        kw = e["keyword"]
        if kw not in groups:
            groups[kw] = {"keyword": kw, "category": e["category"], "count": 0, "slugs": [], "comments": []}
        groups[kw]["count"] += 1
        if e["slug"] not in groups[kw]["slugs"]:
            groups[kw]["slugs"].append(e["slug"])
        if len(groups[kw]["comments"]) < 2:
            groups[kw]["comments"].append(e["comment"])
    # Sort by count descending
    return sorted(groups.values(), key=lambda g: -g["count"])


if __name__ == "__main__":
    correction_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    output = sys.argv[2] if len(sys.argv) > 2 else None
    build_review(correction_dir, output)
