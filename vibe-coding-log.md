# pdfedit vibe coding log

## 2026-05-22 — FontCache 重构 + 同页多次替换 + 合并版 PDF

### Bug
同一页做两次 `replace_span` 时，第二次报错 `need font file or buffer`。

### 根因
1. PyMuPDF `apply_redactions()` 使内部 xref stream 缓存失效，`doc.xref_stream(xref)` 返回 None
2. PyMuPDF name→buffer 映射也在 redaction 后失效，同名字体无法复用

### 调试过程
- 发现 `doc.extract_font(xref)` 在 redaction 后仍然有效（与 `xref_stream()` 不同）
- 测试发现：同一个 buffer 用不同名字注册可以，用同名字注册失败
- 最终方案：`get_registered_name()` 每次 `extract_font()` + uuid 唯一名；去掉 preload 机制

### 教训
- 不能相信 PyMuPDF 的内部缓存，xref stream 缓存和 name 映射都会因 redaction 失效
- `extract_font()` 比 `xref_stream()` 可靠
- 每次替换用 uuid 名绕过 name→buffer 映射失效问题

### 成品
- `/tmp/pdfedit_合并版.pdf` — vision AI 确认"学号"/"1套~30套"全部正确

### Wiki 沉淀
- `hermes-base/concepts/pdfedit-pitfalls.md` — 核心坑点
- `hermes-base/projects/project-pdfedit.md` — 项目 wiki

### commit
- `88dcc97` - fix: FontCache — no preload, uuid names, extract_font() per call
- `d9a33c1` - output: 合并版 PDF（本地）
- `aa76541` - fix: .gitignore — ignore output/ and *.pyc

---

## 2026-05-22 — 项目初始化

### 技术方案
- PyMuPDF + redaction + insert_text 路线
- 字体预提取：`doc.extract_font(xref)` → `insert_font(fontbuffer=)`
- fallback：`fangzheng` subset 缺字时用 STHeiti

### 坑点
- `color` 是 int 不是 tuple（PyMuPDF 内部 RGB888 整数）
- 方正子集字体缺少"号"等罕见汉字（不在 subset 中）

### commit
- `0e14a8a` - feat: pdfedit core — text replacement with font fallback
