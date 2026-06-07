# pdfedit vibe coding log

## 2026-06-07 — 16 天后回访：smoke test + save_pdf incremental 修复

### 背景
距上次提交（2026-05-22 22:13）已过 16 天。期间 STATUS.md、vibe-coding-log.md、handoff 均未更新，AGENTS.md 收尾 Checklist 全部过期。本次回来重跑真实案例确认核心功能是否仍可用。

### Smoke test 结果
| 用例 | 旧文字 | 新文字 | 结果 |
|------|--------|--------|------|
| `test_replace.py` | `535-168=` | `999-111=` | ✓ 1 处命中替换 |
| `cmd_replace_成绩.py` | `成绩` | `学号` | ✓ 30/30 页 |
| `cmd_replace_套数编号.py` | `30套` | `1~30套` | ✓ 30/30 页 |
| `produce_合并版.py`（新）| 两项合并 | 一次性输出 | ✓ p1=1套+p15=15套+p30=30套 |

### Bug：save_pdf incremental=True 路径死锁
**症状**：`save_pdf(doc, "/tmp/xxx.pdf")` 抛 `ValueError: incremental needs original file`
**根因**：commit `aa76541`（5-22 16:24）将 `save_pdf` 改成 `incremental=True`，但 PyMuPDF 的 incremental 模式要求**输出路径必须等于源文件路径**——本质上是 PDF 增量更新协议。
**为什么 5-22 当时没炸**：d9a33c1（5-22 16:11）生成合并版 PDF 时，core.py 还是 `incremental=False`；`aa76541` 改 incremental=True 的 commit 在 16:24 推送，d9a33c1 的合并版跑在 incremental=False 路径上。回归窗口为 5-22 16:24 ~ 6-07 这 16 天。
**修复**：`save_pdf` 检查 `str(path) == doc.name`，相等才用 incremental，不等则 fallback 到非 incremental。
**commit**: 见下一步 git log。

### 教训
- 修改 `save_pdf` 这种"全局默认"时，先在调用方对比参数验证，5-22 那次应该是漏了
- 冒烟跑要覆盖**所有调用方**（test_replace.py / cmd_*.py / 真实合并脚本），不能只测其中一个
- 16 天空窗期——AGENTS.md 收尾 Checklist 应该 cron 化提醒，而不是靠人工

### 新坑点：incremental 也救不了"大文件"问题
**实测**：30 处替换 + 30 处 fallback 后，incremental 模式输出 62MB（vs 原始 570KB）——膨胀 110 倍。
**根因**：每次 `replace_span` 的 `apply_redactions` 都会生成 overlay 注释 + 新字体子集，incremental 只追加不重写，但每次替换产生的新 xref 都留在文件里。
**结论**：incremental 在这个工作量下**没有体积优势**，且会**单向追加无法回滚**——production 路径反而应该走 non-incremental + 显式指定输出路径。
**已用方案**：`produce_合并版.py` 输出到 `/tmp/pdfedit_合并版.pdf`（新路径 → non-incremental），再 copy 到 `output/`，**不覆盖源文件**。

### 新增 / 改动文件
- `src/pdfedit/core.py` — `save_pdf` 增量/全量分支
- `produce_合并版.py` — 端到端冒烟脚本（取代 d9a33c1 的一次性合并版产物）

### 输出成品
- `output/pdfedit_合并版.pdf` (60.6 MB) — 本地保留，已 .gitignore
- `/tmp/pdfedit_original_backup.pdf` — 源文件备份（避免 smoke test 误改原 PDF）

### Wiki 沉淀（待办）
- 把"incremental 不能解决大文件问题"加进 `hermes-base/concepts/pdfedit-pitfalls.md`
- 16 天空窗期经验建议加进 `hermes-base/projects/project-pdfedit.md` 的 maintenance 章节

### commit（见 git log 同步确认）
- 待 push：`fix: save_pdf — incremental fallback to non-incremental when path != doc.name`
- 待 push：`feat: produce_合并版.py — end-to-end smoke test script`

---

## 2026-05-22 — Git 仓库初始化

### 完成
- `git init` 初始化仓库
- 添加 remote origin（HTTPS pushurl 绕过 SSH 代理）
- 推送所有 commit 到 GitHub

### commit
- `7c6f5c0` - docs: add AGENTS.md
- `9b5a9b1` - docs: add vibe-coding-log.md

---

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
