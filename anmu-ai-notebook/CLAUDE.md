# Anmu 知识库

## 项目简介

Anmu 是一个 AI Native 本地知识库。核心流程：手动丢链接/想法 → AI 抓取+写带立场笔记 → 自动编译为结论页 → 能问答。
设计原则：**编译 > 检索**——不是把笔记堆着搜索，而是把同主题笔记编译成可直接使用的结论。

## 目录结构

```
raw/          # 原料层：原文，只读不改，事实来源
notes/        # 笔记层：每条素材一篇带立场的 AI 笔记
wiki/         # 编译层：多篇同主题笔记编译为结论页（主题页/实体页）
scripts/      # Python 脚本（索引、关联、搜索、编译）
tags.md       # 预定义标签体系
INDEX.md      # 自动生成的索引（脚本维护，禁止手动编辑）
```

## Ingest 流程（/anmu Skill 触发）

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

### 往回织机制

新笔记入库后，如果与现有 wiki 页相关：
1. AI 读取现有 wiki 页 + 新笔记
2. 重写结论，融入新信息
3. 如有矛盾，添加「⚠️ 矛盾点」章节，标出新旧立场
4. 更新 confidence 级别
5. frontmatter 中 sources 加入新笔记，date_updated 刷新

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

## 查询流程

用户提问时：
1. 运行 `python scripts/search.py "关键词"` 搜索（wiki 优先）
2. **如果有 wiki 命中** → 优先读取 wiki 编译页回答（结论级别）
3. **如果无 wiki 命中** → 读取匹配的笔记全文综合回答
4. 引用具体文件名作为来源

## 脚本清单

| 脚本 | 用途 |
|------|------|
| `build_index.py` | 扫描 wiki/ + notes/ 生成 INDEX.md |
| `search.py` | 关键词搜索（wiki-first） |
| `update_related.py` | 笔记间双向关联 |
| `find_compilable.py` | 检测新笔记是否触发 wiki 编译 |
| `compile_wiki.py` | 准备编译上下文（供 Claude 执行编译） |

## 禁止操作

- ❌ 不要修改 `raw/` 下的任何文件（只读层）
- ❌ 不要手动编辑 `INDEX.md`（由脚本生成）
- ❌ 不要在 ingest 时跳过 update_related、build_index、find_compilable 步骤
- ❌ 不要使用 tags.md 之外的标签（需要新标签先更新 tags.md）
- ❌ 不要在笔记中复述原文，要有自己的判断
- ❌ 不要在 wiki 页中逐篇罗列笔记内容，要综合编译为结论

## 技术栈

- 存储：纯 Markdown 文件 + YAML frontmatter
- 抓取：Claude Code WebFetch
- 索引/关联/搜索/编译：Python 脚本（依赖 pyyaml）
- AI：Claude（当前会话）
