#!/usr/bin/env python3
"""Batch-parsing step 1: extract plain text from a user-supplied document
(pdf/docx/doc/rtf/html/txt/md) into a temp text file the agent then reads
and splits into essays.

- PDF → PyPDF2, with "===== PAGE N =====" markers so per-essay boundaries
  (often one essay per page) stay visible. Scanned PDFs have no text layer;
  PyPDF2 then returns little/no text — the agent should fall back to reading
  the PDF with its Read tool (visual, page by page) instead.
- docx → Python stdlib zipfile + XML (cross-platform, zero dependencies;
  textutil fallback for files the stdlib path can't read).
- doc/rtf/html → macOS built-in `textutil -convert txt -stdout`.
- txt/md → passthrough (utf-8, gbk, latin-1 fallback).
"""
import argparse, re, subprocess, sys
from pathlib import Path

SUPPORTED = {".pdf", ".doc", ".docx", ".rtf", ".html", ".htm", ".txt", ".md", ".markdown"}


def default_out(path: Path) -> Path:
    stem = re.sub(r"[^0-9A-Za-z]+", "-", path.stem).strip("-").lower() or "doc"
    return Path(f"/tmp/english-{stem}-raw.txt")


def extract_pdf(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        sys.exit("❌ 未安装 PyPDF2（pip3 install PyPDF2）。也可以不用本脚本："
                 "agent 直接用 Read 工具按页读 PDF 即可。")
    reader = PdfReader(str(path))
    parts = []
    for i, page in enumerate(reader.pages):
        parts.append(f"===== PAGE {i + 1} =====\n" + (page.extract_text() or ""))
    text = "\n\n".join(parts)
    body = re.sub(r"===== PAGE \d+ =====", "", text).strip()
    if len(body) < 50:
        print("⚠ 提取到的文本极少——可能是扫描版 PDF（无文字层）。"
              "请改用 Read 工具按页读取该 PDF。", file=sys.stderr)
    return text


def extract_docx(path: Path) -> str:
    # docx = zip containing word/document.xml; each <w:p> is a paragraph.
    # stdlib-only on purpose: the skill must work on any OS without
    # textutil (macOS) or python-docx. Paragraphs joined with blank lines
    # so multi-essay boundaries stay visible.
    import zipfile
    import xml.etree.ElementTree as ET
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    paras = ["".join(t.text or "" for t in p.iter(W + "t"))
             for p in root.iter(W + "p")]
    return "\n\n".join(paras)


def extract_textutil(path: Path) -> str:
    try:
        out = subprocess.run(
            ["textutil", "-convert", "txt", "-stdout", str(path)],
            capture_output=True, text=True, check=True,
        )
        return out.stdout
    except FileNotFoundError:
        sys.exit("❌ 找不到 textutil（macOS 自带；其他系统请转存为 docx/txt）。")
    except subprocess.CalledProcessError as e:
        sys.exit(f"❌ textutil 转换失败: {(e.stderr or '').strip()}")


def read_plain(path: Path) -> str:
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return path.read_text(enc)
        except UnicodeDecodeError:
            continue
    return ""  # latin-1 never fails; unreachable


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", required=True, help="用户文档路径 (pdf/docx/txt/md/...)")
    ap.add_argument("--out", help="输出文本路径（默认 /tmp/english-<stem>-raw.txt）")
    args = ap.parse_args()

    path = Path(args.file).expanduser()
    if not path.is_file():
        sys.exit(f"❌ 文件不存在: {path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED:
        sys.exit(f"❌ 不支持的类型 {suffix}，支持: {', '.join(sorted(SUPPORTED))}")

    if suffix == ".pdf":
        text = extract_pdf(path)
    elif suffix == ".docx":
        try:
            text = extract_docx(path)
        except Exception:
            text = extract_textutil(path)  # fallback for odd docx files
    elif suffix in {".txt", ".md", ".markdown"}:
        text = read_plain(path)
    else:
        text = extract_textutil(path)

    out = Path(args.out) if args.out else default_out(path)
    out.write_text(text, "utf-8")
    pages = text.count("===== PAGE")
    note = f"，{pages} 页" if pages else ""
    print(f"✅ 已抽取 {len(text)} 字符{note} → {out}")


if __name__ == "__main__":
    main()
