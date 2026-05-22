# pdfedit AGENTS

PDF 文字 in-place 替换工具，保留原始排版和字体。

## 项目路径
`/Users/mt16/dev/pdfedit`

## 技术栈
- Python 3（`python3`，系统默认）
- PyMuPDF 1.27.1
- 无数据库，纯文件处理

## 核心模块
- `src/pdfedit/core.py` — `FontCache`、`find_spans`、`replace_span`、`save_pdf`
- `cmd_replace_成绩.py` — 替换表头"成绩→学号"
- `cmd_replace_套数编号.py` — 替换标题"30套→1~30套"
- `test_replace.py` — 最小化测试

## 输出成品
- `output/` — 本地保留，不上传 Git
- `/tmp/pdfedit_合并版.pdf` — 30页数学练习替换成品

## GitHub
- https://github.com/mariusiaowego-commits/pdfedit
- push 用 HTTPS：`git config --local remote.origin.pushurl https://github.com/mariusiaowego-commits/pdfedit.git`

## 关键坑点（必读）

### apply_redactions() 后 xref stream 缓存失效
- `doc.xref_stream(xref)` 在 redaction 后返回 None
- 解法：用 `doc.extract_font(xref)` 获取字体 buffer（仍然有效）
- PyMuPDF name→buffer 映射在 redaction 后也失效，必须用 uuid 生成唯一字体名

### 方正子集字体缺字
- `fangzheng` subset 字体缺少"号"等罕见汉字
- 解法：检测到 `B01S`/`fangzheng` 且文字含 `{"号","龍","龟",...}` 时 fallback 到 STHeiti

### 字体名不能复用
- `page.insert_font(fontname='fz_v1', ...)` 第二次调用失败
- 解法：每次替换用 `uuid.uuid4().hex[:8]` 生成唯一名字

### 输出文件偏大
- `insert_font()` 每次创建新字体对象，无法复用
- 原始 557KB → 输出 ~28MB（30页×2处替换）
- 解法：已用 `incremental=True` 保存，后续可加 post-process 去重

详见：`hermes-base/concepts/pdfedit-pitfalls.md`

## 用户偏好
- 输出 PDF 视觉效果必须与原文件一模一样
- 主要改文字内容，不改排版/样式
- 字体 fallback 优先使用 STHeiti

## 收尾 Checklist
□ STATUS.md — 本次修改涉及的功能，对应条目是否更新（日期 + 阶段描述）
□ vibe-coding-log.md — 新增当日记录，append 到文件开头
□ handoff-YYYY-MM-DD.md — 完整记录含待办清单，写入项目根目录
□ README — 改动需要同步更新
□ 成品 — 放在 output/，不上传 Git
□ Wiki沉淀 — 发现新模式/踩坑记录/项目惯例，同步到obsidian vault='hermes-base' 路径`/projects/project-pdfedit`