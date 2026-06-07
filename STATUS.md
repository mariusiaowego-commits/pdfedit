# pdfedit — 当前开发状态

**最后更新**: 2026-06-07
**当前阶段**: v1.0 核心功能完成 + 16 天后回归测试通过 + save_pdf 修复

## 阶段记录

**2026-06-07 — 16 天后冒烟回归 + save_pdf 修复**:
- **背景**: 距上次提交（5-22）已 16 天，期间无任何改动。AGENTS.md 收尾 Checklist 全部过期
- **smoke test**: test_replace.py + cmd_replace_成绩.py + cmd_replace_套数编号.py + 新 produce_合并版.py 全部通过
- **Bug 发现**: `save_pdf` 在 `path != doc.name` 时报 `ValueError: incremental needs original file`（commit aa76541 引入的回归，5-22 之后未有人跑过）
- **修复**: `save_pdf` 增加分支——`path == doc.name` 才 incremental，否则 non-incremental
- **新坑点**: incremental 模式并不能解决"输出文件偏大"问题（实测 570KB → 62MB），且单向追加无法回滚；改为统一输出到 /tmp/... 路径 + copy 到 output/
- **新增**: `produce_合并版.py` 端到端冒烟脚本
- **commit**: 待 push

**2026-05-22 — FontCache 重构 + 同页多次替换支持**:
- **Bug**: 同一页做两次 `replace_span` 时，第二次报错 `need font file or buffer`
- **根因**: PyMuPDF `apply_redactions()` 使内部 xref stream 缓存失效；字体 name→buffer 映射也在 redaction 后失效
- **修复**:
  - `get_registered_name()`: 每次调用 `doc.extract_font()` 获取 buffer（redaction 后仍有效）+ uuid 唯一字体名
  - `get_fallback_name()`: 直接读取文件 + uuid 名，不复用
  - 去掉 `preload_page()` 机制（第一次 redaction 后即失效）
- **commit**: `88dcc97` → **已合并 main**

**2026-05-22 — 方正子集字体缺字 fallback**:
- **Bug**: 新文字含"号"字时渲染空白（tofu）
- **根因**: `fangzheng` subset 只有用到的字形，罕见字不在子集中
- **修复**: `_needs_fallback()` 检测字体名含 `B01S`/`fangzheng` 且文字含 `{"号","龍","龟",...}` 时，fallback 到 STHeiti
- **commit**: `0e14a8a` → **已合并 main**

**2026-05-22 — 合并版 PDF 输出**:
- **完成**: `成绩→学号` + `30套→1~30套编号` 两个替换合并到单个输出
- **成品**: `/Users/mt16/dev/pdfedit/output/pdfedit_合并版.pdf`（28MB）
- **验证**: vision AI 确认第1/15/30页标题和表头文字正确
- **commit**: `d9a33c1` → **已合并 main**

**2026-05-22 — 项目初始化**:
- `src/pdfedit/core.py` — `FontCache`、`find_spans`、`replace_span`、`save_pdf`
- `cmd_replace_成绩.py` / `cmd_replace_套数编号.py` — 独立替换命令
- GitHub: https://github.com/mariusiaowego-commits/pdfedit
