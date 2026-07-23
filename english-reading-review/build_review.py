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
from pathlib import Path
from datetime import datetime

TEMPLATE = Path.home() / ".workbuddy/skills/english-reading-review/template.html"
DEFAULT_DIR = str(Path.home() / "Desktop" / "English Learning")


def extract_article_data(html_text):
    """Extract ARTICLE_DATA JSON from a reading HTML file."""
    # Match: const ARTICLE_DATA = {...};
    m = re.search(r'const ARTICLE_DATA\s*=\s*(\{.*?\});', html_text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def strip_html(html_text):
    """Strip HTML tags, return plain text."""
    # Replace block tags with spaces for sentence splitting
    text = re.sub(r'<(?:p|div|h\d|blockquote|br)[^>]*>', ' ', html_text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def find_example_sentence(word, article_content):
    """Find a sentence from the article containing this word."""
    plain = strip_html(article_content)
    sentences = re.findall(r'[^.!?]+[.!?]+', plain)
    lower = word.lower()
    for s in sentences:
        if lower in s.lower():
            s = s.strip()
            if len(s) > 120:
                # Trim around the word
                idx = s.lower().index(lower)
                start = max(0, idx - 50)
                end = min(len(s), idx + len(word) + 60)
                s = ("..." if start > 0 else "") + s[start:end] + ("..." if end < len(s) else "")
            return s
    return ""


def build_review(directory=DEFAULT_DIR, output=None):
    """Build review HTML from all reading files in directory."""
    files = sorted(glob.glob(str(Path(directory) / "*-reading.html")))
    if not files:
        print(f"No *-reading.html files found in {directory}")
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

        # Extract example sentences (one per article to keep it fast)
        plain = strip_html(content)
        sentences = re.findall(r'[^.!?]+[.!?]+', plain)
        for w, entry in master_vocab.items():
            if art_id in entry["articles"] and not entry["example"]:
                wl = w.lower()
                for s in sentences:
                    if wl in s.lower():
                        s = s.strip()
                        if len(s) > 120:
                            idx = s.lower().index(wl)
                            start = max(0, idx - 40)
                            end = min(len(s), idx + len(w) + 50)
                            s = ("..." if start > 0 else "") + s[start:end] + ("..." if end < len(s) else "")
                        entry["example"] = s
                        break

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
    data_json = json.dumps(review_data, ensure_ascii=False)
    html_output = template.replace("{{REVIEW_DATA_JSON}}", data_json)

    if output is None:
        output = str(Path(directory) / "review-all.html")
    Path(output).write_text(html_output, "utf-8")

    print(f"\n✓ Review page: {output}")
    print(f"  Articles: {len(articles_meta)}")
    print(f"  Unique words: {len(master_vocab)}")
    print(f"  Shared words: {shared_words}")
    print(f"  Patterns: {len(all_patterns)}")


if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    output = sys.argv[2] if len(sys.argv) > 2 else None
    build_review(directory, output)
