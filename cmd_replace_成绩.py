"""
Replace "成绩" with "学号" in the header row of every page.
The header is a single span: " 班级: ___________ 姓名: ___________ 成绩: ___________"
"""
import sys
sys.path.insert(0, "src")

from pdfedit.core import load_pdf, find_spans, replace_span, save_pdf, FontCache

PDF = "/Users/mt16/Documents/TQ/01-Personal/0101-Family/010102-Song/260522-改pdf/0511二下数学三位数进退位加减法竖式计算30套30页(1).pdf"
OUT = "/tmp/pdfedit_成绩改学号.pdf"

doc = load_pdf(PDF)
font_cache = FontCache(doc)
count = 0

for p_idx in range(len(doc)):
    # Find spans containing "成绩" on this page
    page = doc[p_idx]
    raw = page.get_text("dict")
    for block in raw["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if "成绩" in span["text"]:
                    print(f"Page {p_idx+1}: replacing '成绩' in span: {span['text'][:40]!r}...")
                    new_text = span["text"].replace("成绩", "学号")
                    replace_span(doc, p_idx, span, new_text, font_cache=font_cache)
                    count += 1

print(f"\nReplaced {count} span(s)")
save_pdf(doc, OUT)
print(f"Saved: {OUT}")
