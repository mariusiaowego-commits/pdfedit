"""
Replace "30套" with sequential numbers on each page (1套, 2套, ..., 30套).
Uses fallback font since '套' might be missing from the 方正 subset too.
"""
import sys
sys.path.insert(0, "src")

from pdfedit.core import load_pdf, save_pdf
from pdfedit.core import find_spans, replace_span, FontCache

PDF = "/Users/mt16/Documents/TQ/01-Personal/0101-Family/010102-Song/260522-改pdf/0511二下数学三位数进退位加减法竖式计算30套30页(1).pdf"
OUT = "/tmp/pdfedit_改套数.pdf"

doc = load_pdf(PDF)
font_cache = FontCache(doc)

total = len(doc)
replaced = 0

for page_idx in range(total):
    page = doc[page_idx]

    # Find the title span containing "30套"
    from pdfedit.core import find_spans
    spans = find_spans(doc, "二年级数学下册三位数进退位加减法竖式计算30套", page_idx=page_idx)

    if not spans:
        print(f"Page {page_idx+1}: title span not found, skipping")
        continue

    p_idx, span = spans[0]
    seq_num = page_idx + 1
    new_title = f"二年级数学下册三位数进退位加减法竖式计算{seq_num}套"

    print(f"Page {page_idx+1}: '{span['text'][:30]}...' → '{new_title[:30]}...'")
    replace_span(doc, page_idx, span, new_title, font_cache=font_cache)
    replaced += 1

print(f"\nReplaced {replaced} title(s)")
save_pdf(doc, OUT)
print(f"Saved: {OUT}")
