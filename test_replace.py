"""
Test: replace "535-168=" with "999-111=" on page 1.
"""
import sys
sys.path.insert(0, "src")

from pdfedit.core import load_pdf, find_spans, replace_span, save_pdf, FontCache

PDF = "/Users/mt16/Documents/TQ/01-Personal/0101-Family/010102-Song/260522-改pdf/0511二下数学三位数进退位加减法竖式计算30套30页(1).pdf"
OUT = "/tmp/pdfedit_test_out.pdf"

doc = load_pdf(PDF)

# Find
spans = find_spans(doc, "535-168=", page_idx=0, font="fangzheng", size=42.5)
print(f"Found: {len(spans)}")
if not spans:
    sys.exit(1)

p_idx, span = spans[0]
print(f"  bbox: {span['bbox']}")

# Replace
font_cache = FontCache(doc)
replace_span(doc, p_idx, span, "999-111=", font_cache=font_cache)
print("Replaced OK")

# Verify: reload and check
doc.save(OUT)
doc2 = load_pdf(OUT)
spans2 = find_spans(doc2, "535-168=", page_idx=0)
spans3 = find_spans(doc2, "999-111=", page_idx=0)
print(f"Old text still present: {len(spans2) > 0}")
print(f"New text present: {len(spans3) > 0}")
print(f"Output: {OUT}")
