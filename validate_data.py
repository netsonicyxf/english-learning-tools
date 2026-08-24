#!/usr/bin/env python3
"""Validate exercise data before template injection. Run after Step 5, before Step 6."""
import json, re, sys
from pathlib import Path

def validate(article_data):
    content = article_data["content"]
    exercises = article_data.get("exercises", {})
    errors = []

    # 1. sentence pattern sources must be verbatim in article content
    for i, p in enumerate(exercises.get("sentencePatterns", [])):
        if p["source"] not in content:
            errors.append(f"sentencePatterns[{i}].source not in article: {p['source'][:80]}...")

    # 2. sentence reorder: every sentence text must be in article
    for gi, group in enumerate(exercises.get("sentenceReorder", [])):
        for si, s in enumerate(group["sentences"]):
            if s["text"] not in content:
                errors.append(f"sentenceReorder[{gi}].sentences[{si}] not in article: {s['text'][:80]}...")

    # 3. recitation: every passage text must be in article
    for pi, passage in enumerate(exercises.get("recitation", {}).get("passages", [])):
        if passage["text"] not in content:
            errors.append(f"recitation.passages[{pi}] not in article: {passage['text'][:80]}...")

    # 4. sentence pattern Q&A: correct answer must not introduce new numbers
    for i, p in enumerate(exercises.get("sentencePatterns", [])):
        for j, q in enumerate(p.get("questions", [])):
            correct = q["options"][q["answer"]]
            # Extract numbers and strip trailing punctuation (comma in "when X, Y" clauses, etc.)
            input_nums = set(n.rstrip('.,;:!?)') for n in re.findall(r'\d[\d,.]*', q["input"]))
            answer_nums = set(n.rstrip('.,;:!?)') for n in re.findall(r'\d[\d,.]*', correct))
            new_nums = answer_nums - input_nums
            if new_nums:
                errors.append(
                    f"sentencePatterns[{i}].questions[{j}]: "
                    f"correct answer introduces numbers not in input: {new_nums}"
                )

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  {e}")
        return False
    print("VALIDATION PASSED")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_data.py <article_data.json>")
        sys.exit(1)

    data = json.loads(Path(sys.argv[1]).read_text("utf-8"))
    ok = validate(data)
    sys.exit(0 if ok else 1)
