"""
Produce the merged PDF: 成绩→学号 + 1~30套编号 in one pass.

This is the canonical end-to-end pipeline — same as the historical d9a33c1
artifact, but rebuilt now to verify the core still works after the 16-day pause
and to validate the save_pdf() incremental-mode fix.

Why this script instead of chaining cmd_replace_成绩.py + cmd_replace_套数编号.py:
- One FontCache / one doc / one save — avoids the "doc.name moves after save"
  gotcha when chaining two saves against different output paths.
- A single pass is also faster than opening/saving the document twice.

Output strategy:
- We do NOT overwrite the source file. Source PDFs are precious (e.g. the
  Song-family 数学练习册 is a unique 30-page worksheet) and an incremental
  save of 30+30 replacements balloons the file ~100x.
- Instead we save to a fresh /tmp path (triggers non-incremental fallback in
  save_pdf) and copy a snapshot to output/pdfedit_合并版.pdf for the user.
  output/ is gitignored — the snapshot is local-only.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "src")

from pdfedit.core import FontCache, find_spans, load_pdf, replace_span, save_pdf

SOURCE = Path("/Users/mt16/Documents/TQ/01-Personal/0101-Family/010102-Song/260522-改pdf/0511二下数学三位数进退位加减法竖式计算30套30页(1).pdf")
WORK_OUTPUT = Path("/tmp/pdfedit_合并版.pdf")
OUTPUT_DIR = Path("output")
OUTPUT_SNAPSHOT = OUTPUT_DIR / "pdfedit_合并版.pdf"

# Strings we know appear in the header
HEADER_OLD = " 班级: ___________ 姓名: ___________ 成绩: ___________"
HEADER_NEW = " 班级: ___________ 姓名: ___________ 学号: ___________"
TITLE_PREFIX = "二年级数学下册三位数进退位加减法竖式计算"


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: source PDF not found: {SOURCE}", file=sys.stderr)
        return 1

    doc = load_pdf(SOURCE)
    font_cache = FontCache(doc)

    header_count = 0
    title_count = 0

    for p_idx in range(len(doc)):
        # 1) header row: 成绩 → 学号
        header_spans = find_spans(doc, HEADER_OLD, page_idx=p_idx)
        for _, span in header_spans:
            replace_span(doc, p_idx, span, HEADER_NEW, font_cache=font_cache)
            header_count += 1

        # 2) title: 30套 → {p_idx+1}套
        title_spans = find_spans(doc, f"{TITLE_PREFIX}30套", page_idx=p_idx)
        if title_spans:
            _, span = title_spans[0]
            new_title = f"{TITLE_PREFIX}{p_idx + 1}套"
            replace_span(doc, p_idx, span, new_title, font_cache=font_cache)
            title_count += 1

    print(f"Header replacements (成绩→学号): {header_count}")
    print(f"Title replacements  (30套→1~30套): {title_count}")

    # Save to a fresh path → triggers the non-incremental fallback in save_pdf.
    # Source file is preserved untouched.
    save_pdf(doc, WORK_OUTPUT)
    print(f"Saved: {WORK_OUTPUT}")

    # Snapshot a copy to output/ for the user; this is local-only (gitignored).
    OUTPUT_DIR.mkdir(exist_ok=True)
    shutil.copy2(WORK_OUTPUT, OUTPUT_SNAPSHOT)
    size_kb = OUTPUT_SNAPSHOT.stat().st_size / 1024
    print(f"Snapshot: {OUTPUT_SNAPSHOT} ({size_kb:.0f} KB)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
