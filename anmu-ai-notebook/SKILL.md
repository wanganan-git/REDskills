---
name: anmu-ai-notebook
description: 初始化 Anmu AI 本地知识库 — 自动创建目录结构、脚本、配置，一步到位
trigger: 用户说"初始化知识库"、"搭建知识库"、"setup anmu"、"init anmu"
---

# Anmu AI Notebook 初始化

你正在为用户搭建一个 AI Native 本地知识库。这个知识库的核心理念是**编译 > 检索**——不是堆笔记搜索，而是把同主题笔记自动编译成可直接使用的结论页。

## 初始化步骤

严格按以下顺序执行，不要跳步。

### Step 0: 定位资源文件

本 skill 的资源文件位于 `.claude/skills/anmu-ai-notebook/` 目录下。后续步骤中需要从该目录读取文件并写入用户项目。

如果该目录不存在，提示用户：
> 资源文件未找到。请确保已将 anmu-ai-notebook 整个文件夹复制到项目的 `.claude/skills/` 目录下。

### Step 1: 检查 Python 环境

运行以下命令检查 Python 是否可用：

```bash
python --version 2>/dev/null || python3 --version 2>/dev/null
```

如果都不可用，提示用户安装 Python 3.10+，然后停止。

如果 Python 可用，检查 pyyaml：

```bash
python -c "import yaml; print('pyyaml OK')" 2>/dev/null || python3 -c "import yaml; print('pyyaml OK')" 2>/dev/null
```

如果 pyyaml 未安装，提示用户：
> 需要安装 pyyaml 依赖。请运行：`pip install pyyaml`
> 安装完成后重新执行本 skill。

确认 Python 和 pyyaml 都可用后继续。记录用户环境中可用的 Python 命令（`python` 或 `python3`），后续步骤统一使用。

### Step 2: 创建目录结构

在当前项目根目录下创建以下目录：

```
raw/
notes/
wiki/
scripts/
```

### Step 3: 写入文件

从 `.claude/skills/anmu-ai-notebook/` 读取以下文件，写入项目对应位置：

| 源文件（skill 目录下） | 目标位置（项目根目录下） |
|----------------------|----------------------|
| `scripts/build_index.py` | `scripts/build_index.py` |
| `scripts/search.py` | `scripts/search.py` |
| `scripts/update_related.py` | `scripts/update_related.py` |
| `scripts/find_compilable.py` | `scripts/find_compilable.py` |
| `scripts/compile_wiki.py` | `scripts/compile_wiki.py` |
| `tags.md` | `tags.md` |
| `CLAUDE.md` | `CLAUDE.md` |

使用 Read 工具读取源文件，使用 Write 工具写入目标文件。逐个文件操作，不要跳过任何一个。

然后创建一个空的 `INDEX.md`：

```markdown
# Anmu 知识库索引

> 本文件由 `scripts/build_index.py` 自动生成，请勿手动编辑。

---

*知识库暂无内容。使用 `/anmu <链接或想法>` 开始入库。*
```

### Step 4: 验证环境

运行索引脚本验证一切正常：

```bash
cd <项目根目录> && python scripts/build_index.py
```

（使用 Step 1 中确认的 Python 命令）

如果报错，根据错误信息排查并修复。常见问题：
- `ModuleNotFoundError: No module named 'yaml'` → 需要 `pip install pyyaml`
- 编码错误 → 确认文件以 UTF-8 写入

### Step 5: 输出初始化报告

初始化成功后，输出以下报告：

```
✅ Anmu 知识库初始化完成！

📁 目录结构：
   raw/          — 原料层（抓取的原文）
   notes/        — 笔记层（AI 带立场笔记）
   wiki/         — 编译层（结论页）
   scripts/      — 自动化脚本

📄 已写入文件：
   CLAUDE.md     — 项目规范（可自定义）
   tags.md       — 标签体系（可增删）
   INDEX.md      — 索引（自动生成）
   scripts/      — 5 个 Python 脚本

🚀 开始使用：
   给我一个链接或想法，我会帮你入库。
   例如："帮我把 https://example.com 存入知识库"

💡 自定义：
   - 编辑 tags.md 增删标签
   - 编辑 CLAUDE.md 调整笔记规范
```

## 日常使用：Ingest 流程

初始化完成后，当用户提供链接或想法时，按以下流程入库：

1. **判断输入类型**：URL → 抓取；纯文字 → 想法笔记（无 raw 文件）
2. **生成文件名**：`YYYY-MM-DD-关键词slug.md`（英文短横线连接，3-5 个词）
3. **抓取原文**（仅 URL）：用 WebFetch 抓取内容，存入 `raw/`，frontmatter 只写 `source` 和 `fetched`
4. **写笔记**：读原文（或想法原文），从 `tags.md` 选 3-5 个标签，写一篇带立场的笔记，存入 `notes/`
5. **更新关联**：运行 `python scripts/update_related.py notes/新文件名.md`
6. **重建索引**：运行 `python scripts/build_index.py`
7. **Wiki 编译检测**：运行 `python scripts/find_compilable.py notes/新文件名.md`
   - 有 wiki 页需更新 → 往回织（重写结论页，标出矛盾）
   - 有足够笔记聚合 → 创建新 wiki 页
   - 无编译动作 → 跳过
8. **输出入库报告**：标题、标签、关联、编译结果

## 查询流程

用户提问时：
1. 运行 `python scripts/search.py "关键词"` 搜索（wiki 优先）
2. 如果有 wiki 命中 → 优先读取 wiki 编译页回答（结论级别）
3. 如果无 wiki 命中 → 读取匹配的笔记全文综合回答
4. 引用具体文件名作为来源

## 笔记规范

- 800-1500 字
- 必须包含：
  - **一句话总结**（放在正文最开头）
  - **核心观点**（带 AI 自己的判断或质疑，不是复述原文）
  - **对用户的启发**（跟用户的实际场景有什么关联）
- 语气：像写给未来的自己看的备忘录
- 有争议的观点要标出 AI 的独立判断，用 `> ⚡ AI 判断：` 前缀

## Wiki 编译页规范

### 触发条件

- **创建**：≥2 篇笔记共享 ≥2 个标签，且未被现有 wiki 页覆盖
- **更新（往回织）**：新笔记与已有 wiki 页 tag 重叠 ≥1，且未编入该页

### 内容结构

```markdown
# 标题

> 一段话结论摘要

## 核心结论
- 结论1（基于 [note-a], [note-b]）

## 详细分析
跨源综合，不逐篇复述

## ⚠️ 矛盾点（仅当源冲突时）
- **话题**: [note-a](日期) vs [note-c](日期)

## 开放问题

## 来源
| 笔记 | 日期 | 贡献 |
```

## Frontmatter Schema

### notes/ 笔记

```yaml
---
title: 文章标题
source: https://原始链接（想法类型为空）
source_type: web | github | wechat | youtube | x | pdf | idea
date: 2026-06-14
tags: [tag1, tag2, tag3]
related: []
---
```

### wiki/ 编译页

```yaml
---
title: 主题标题
type: theme | entity
date_created: 2026-06-14
date_updated: 2026-06-14
tags: [tag1, tag2]
sources:
  - notes/2026-06-10-xxx.md
  - notes/2026-06-12-yyy.md
confidence: low | medium | high
status: stub | active | stale
related: []
---
```

### raw/ 原文

```yaml
---
source: https://原始链接
fetched: 2026-06-14
---
```

## 禁止操作

- ❌ 不要修改 `raw/` 下的任何文件（只读层）
- ❌ 不要手动编辑 `INDEX.md`（由脚本生成）
- ❌ 不要在 ingest 时跳过 update_related、build_index、find_compilable 步骤
- ❌ 不要使用 tags.md 之外的标签（需要新标签先更新 tags.md）
- ❌ 不要在笔记中复述原文，要有自己的判断
- ❌ 不要在 wiki 页中逐篇罗列笔记内容，要综合编译为结论
