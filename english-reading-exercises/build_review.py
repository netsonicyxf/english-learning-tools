#!/usr/bin/env python3
"""
Build review HTML from all *-reading.html files.
Scans Desktop (or specified directory) for reading HTML files,
extracts ARTICLE_DATA from each, aggregates into a review page.
"""
import json
import re
import sys
import glob
import subprocess
from pathlib import Path
from datetime import datetime

TEMPLATE = Path(__file__).resolve().parent / "review-template.html"
DEFAULT_DIR = str(Path.home() / "Desktop" / "English Learning")


def list_reading_files(directory):
    """Enumerate *-reading.html in directory.

    macOS TCC can block directory listing (glob silently returns nothing)
    while read/write by exact path still works — e.g. ~/Desktop for agents
    without Full Disk Access. Fall back to borrowing Finder's permission.
    """
    files = sorted(glob.glob(str(Path(directory) / "*-reading.html")))
    if files:
        return files
    if sys.platform == "darwin":
        script = (
            'tell application "Finder" to get name of every file of '
            f'(POSIX file "{directory}" as alias)'
        )
        try:
            res = subprocess.run(["osascript", "-e", script],
                                 capture_output=True, text=True, timeout=30)
            names = [n.strip() for n in res.stdout.split(",")
                     if n.strip().endswith("-reading.html")]
            if names:
                return sorted(str(Path(directory) / n) for n in names)
        except Exception:
            pass
    return []


def extract_article_data(html_text):
    """Extract ARTICLE_DATA JSON from a reading HTML file."""
    # Match: const ARTICLE_DATA = {...}; followed by const STORAGE_KEY.
    # Greedy .* + STORAGE_KEY anchor so a `};` inside content can't truncate early.
    m = re.search(
        r'const ARTICLE_DATA\s*=\s*(\{.*\});\s*\n\s*const STORAGE_KEY',
        html_text, re.DOTALL)
    if not m:
        # Fallback for templates without a STORAGE_KEY line right after.
        m = re.search(r'const ARTICLE_DATA\s*=\s*(\{.*?\});', html_text, re.DOTALL)
    if not m:
        return None
    # Undo the </ -> <\/ escaping applied when the file was generated.
    raw = m.group(1).replace('<\\/', '</')
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def strip_html(html_text):
    """Strip HTML tags, return plain text."""
    # Replace block tags with spaces for sentence splitting
    text = re.sub(r'<(?:p|div|h\d|blockquote|br)[^>]*>', ' ', html_text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def split_sentences(article_content):
    """Strip HTML and split into sentences (protecting abbreviations/decimals)."""
    plain = strip_html(article_content)
    plain = re.sub(r'([A-Z])\.', lambda m: m.group(1) + '\x00', plain)
    plain = re.sub(r'(\d)\.(\d)', lambda m: m.group(1) + '\x01' + m.group(2), plain)
    sentences = re.findall(r'[^.!?]+[.!?]+', plain)
    return [s.replace('\x00', '.').replace('\x01', '.') for s in sentences]


def find_example_sentence(word, sentences):
    """Find a sentence containing `word`, given pre-split sentences."""
    def clip(s, needle):
        s = s.strip()
        if len(s) > 120:
            idx = s.lower().index(needle)
            start = max(0, idx - 50)
            end = min(len(s), idx + len(needle) + 60)
            s = ("..." if start > 0 else "") + s[start:end] + ("..." if end < len(s) else "")
        return s

    lower = word.lower()
    # Exact word-boundary match first
    for s in sentences:
        if re.search(r'\b' + re.escape(lower) + r'\b', s, re.IGNORECASE):
            return clip(s, lower)
    # Stem fallback (e.g. "paradigm" -> "paradigms")
    stem = re.sub(r'(ing|ed|er|ers|es|s)$', '', lower)
    if len(stem) >= 4:
        for s in sentences:
            if stem in s.lower():
                return clip(s, stem)
    return ""


def build_review(directory=DEFAULT_DIR, output=None):
    """Build review HTML from all reading files in directory."""
    files = list_reading_files(directory)
    if not files:
        print(f"No *-reading.html files found in {directory}")
        print("(If this is ~/Desktop and the terminal lacks permission, "
              "grant Desktop access in System Settings > Privacy & Security, "
              "or approve the Finder automation prompt.)")
        sys.exit(1)

    print(f"Found {len(files)} reading file(s):")
    articles_meta = []
    master_vocab = {}  # word -> {meaning, articles, count, example}
    all_patterns = []

    for fpath in files:
        html = Path(fpath).read_text("utf-8")
        data = extract_article_data(html)
        if not data:
            print(f"  SKIP (no data): {fpath}")
            continue

        art_id = data.get("id", Path(fpath).stem)
        title = data.get("title", art_id)
        source = data.get("source", "")
        dictionary = data.get("dictionary", {})
        patterns = data.get("exercises", {}).get("sentencePatterns", [])
        content = data.get("content", "")
        mod_time = datetime.fromtimestamp(Path(fpath).stat().st_mtime).strftime("%Y-%m-%d")

        print(f"  ✓ {title} ({len(dictionary)} words, {len(patterns)} patterns)")

        articles_meta.append({
            "id": art_id,
            "title": title,
            "source": source,
            "vocabCount": len(dictionary),
            "patternCount": len(patterns),
            "date": mod_time,
            "fileName": Path(fpath).name,
        })

        # Aggregate vocabulary
        for word, meaning in dictionary.items():
            w = word.lower().strip()
            if w not in master_vocab:
                master_vocab[w] = {
                    "word": word,
                    "meaning": meaning,
                    "articles": [],
                    "count": 0,
                    "example": "",
                }
            if art_id not in master_vocab[w]["articles"]:
                master_vocab[w]["articles"].append(art_id)
                master_vocab[w]["count"] += 1

        # Extract example sentences (one per article, split once and reused)
        sentences = split_sentences(content)
        for w, entry in master_vocab.items():
            if art_id in entry["articles"] and not entry["example"]:
                entry["example"] = find_example_sentence(w, sentences)

        # Collect patterns
        for p in patterns:
            p_copy = json.loads(json.dumps(p))  # deep copy
            p_copy["articleId"] = art_id
            p_copy["articleTitle"] = title
            all_patterns.append(p_copy)

    # Build stats
    shared_words = sum(1 for v in master_vocab.values() if v["count"] > 1)
    review_data = {
        "articles": articles_meta,
        "masterVocab": list(master_vocab.values()),
        "allPatterns": all_patterns,
        "stats": {
            "totalArticles": len(articles_meta),
            "totalUniqueWords": len(master_vocab),
            "sharedWords": shared_words,
            "totalPatterns": len(all_patterns),
        },
    }

    # Fill template
    template = TEMPLATE.read_text("utf-8")
    # Escape </ so a stray </script> in any field can't break out of the tag.
    data_json = json.dumps(review_data, ensure_ascii=False).replace("</", "<\\/")
    html_output = template.replace("{{REVIEW_DATA_JSON}}", data_json)

    if output is None:
        output = str(Path(directory) / "review-all.html")
    Path(output).write_text(html_output, "utf-8")

    # Vocab export for the vocab-drill pipeline: raw material for --add/--card.
    # core = words appearing in >1 article (highest-value batch), all = everything.
    vocab_out = Path(output).with_name("review-vocab.json")

    def _entry(v):
        return {k: v[k] for k in ("word", "meaning", "example", "count", "articles")}

    ordered = sorted(master_vocab.values(),
                     key=lambda v: (-v["count"], v["word"].lower()))
    vocab_export = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "core": [_entry(v) for v in ordered if v["count"] > 1],
        "all": [_entry(v) for v in ordered],
    }
    vocab_out.write_text(
        json.dumps(vocab_export, ensure_ascii=False, indent=1), "utf-8")

    print(f"\n✓ Review page: {output}")
    print(f"  Articles: {len(articles_meta)}")
    print(f"  Unique words: {len(master_vocab)}")
    print(f"  Shared words: {shared_words}")
    print(f"  Patterns: {len(all_patterns)}")
    print(f"✓ Vocab export: {vocab_out} "
          f"(core {len(vocab_export['core'])} / all {len(vocab_export['all'])})")


if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    output = sys.argv[2] if len(sys.argv) > 2 else None
    build_review(directory, output)
