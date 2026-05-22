# pdfedit

**在 PDF 中精准替换文字，保留原始排版和字体。**

支持内嵌子集字体（如方正黑体）的缺失字形 fallback、多页批量替换、以及同一页多次替换。

---

## 功能特性

- **精准文字替换** — 通过 PyMuPDF 定位文字 bbox，redaction 涂掉旧文字后注入新文字
- **内嵌字体 fallback** — 当 PDF 内嵌的子集字体缺少目标字符（如方正黑体缺"号"）时，自动 fallback 到系统汉字字体
- **多页批量** — 一次处理所有页面，自动匹配相同文字
- **同页多次替换** — 支持对同一页执行多个不同的替换操作
- **字体 buffer 复用** — 避免 apply_redactions 后的 xref stream 缓存失效问题

---

## 安装

```bash
pip install pymupdf
```

或者直接从源码运行：

```bash
git clone https://github.com/mariusiaowego-commits/pdfedit.git
cd pdfedit
```

---

## 快速开始

### Python API

```python
import sys
sys.path.insert(0, 'src')

from pdfedit.core import load_pdf, find_spans, replace_span, FontCache, save_pdf

doc = load_pdf('input.pdf')
fc = FontCache(doc)

for page_idx in range(len(doc)):
    spans = find_spans(doc, '旧文字', page_idx=page_idx)
    if spans:
        _, span = spans[0]
        replace_span(doc, page_idx, span, '新文字', font_cache=fc)

save_pdf(doc, 'output.pdf')
```

### 命令行示例

```python
# cmd_replace_成绩.py
from pdfedit.core import load_pdf, find_spans, replace_span, FontCache, save_pdf

PDF = 'input.pdf'
doc = load_pdf(PDF)
fc = FontCache(doc)

for page_idx in range(len(doc)):
    spans = find_spans(doc, ' 班级: ___________ 姓名: ___________ 成绩: ___________', page_idx=page_idx)
    if spans:
        _, span = spans[0]
        replace_span(doc, page_idx, span, ' 班级: ___________ 姓名: ___________ 学号: ___________', font_cache=fc)

save_pdf(doc, 'output.pdf')
```

---

## 项目结构

```
pdfedit/
├── src/
│   └── pdfedit/
│       ├── __init__.py
│       └── core.py          # 核心替换逻辑
├── cmd_replace_成绩.py       # 替换表头"成绩→学号"
├── cmd_replace_套数编号.py   # 替换标题"30套→1~30套"
├── test_replace.py          # 最小化测试
└── output/                   # 输出成品（本地保留）
```

---

## 效果示例

以一份 30 页数学练习 PDF 为例，执行两处替换：

| 替换项 | 原始 | 替换后 |
|--------|------|--------|
| 表头字段 | `成绩: ___________` | `学号: ___________` |
| 标题 | `三位数进退位加减法竖式计算30套` | `三位数进退位加减法竖式计算1~30套` |

> **原始 PDF 保留**：原始文件原样不动，修改结果输出到新文件。

### 截图

**第 1 页 — 替换后**（标题显示"1套"，表头显示"学号"）
![Page 1 Header](screenshots/p1_header.png)

**第 15 页 — 替换后**（标题显示"15套"）
![Page 15 Header](screenshots/p15_header.png)

**第 30 页 — 替换后**（标题显示"30套"）
![Page 30 Header](screenshots/p30_header.png)

---

## 已知限制

- **输出文件偏大**：每次 `insert_font` 都会创建新的字体对象，PyMuPDF 没有合并重复字体的 API。大量替换时输出文件可能显著大于原始文件。建议后续用外部工具（如 Ghostscript）压缩。
- **仅支持文字替换**：图片、矢量图形、表格结构暂不支持。
- **依赖特定字体路径**：fallback 字体默认使用 macOS 的 `/System/Library/Fonts/STHeiti Medium.ttc`，Linux/Windows 用户需自行配置。

---

## 相关概念

- [[pdfedit-pitfalls]] — PyMuPDF 文字替换的核心坑点记录

---

## License

MIT
