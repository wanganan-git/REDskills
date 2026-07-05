#!/usr/bin/env python3
"""Anmu 知识库 - 自动索引生成器（v2: 含 wiki 编译页）

扫描 wiki/ 和 notes/ 下所有 .md 文件的 frontmatter，生成 INDEX.md。
视图顺序：wiki 编译页（置顶）→ 按标签分组 → 按时间倒序。
"""

import re
import yaml
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
WIKI_DIR = ROOT / "wiki"
NOTES_DIR = ROOT / "notes"
INDEX_FILE = ROOT / "INDEX.md"


def parse_frontmatter(filepath: Path) -> dict | None:
    """解析 Markdown 文件的 YAML frontmatter。"""
    text = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def build_wiki_section() -> list[str]:
    """生成 wiki 编译页索引区块"""
    if not WIKI_DIR.exists():
        return []

    wikis = []
    for f in sorted(WIKI_DIR.glob("*.md")):
        fm = parse_frontmatter(f)
        if fm:
            fm["_filename"] = f.name
            wikis.append(fm)

    if not wikis:
        return []

    # 按 date_updated 倒序
    wikis.sort(key=lambda w: w.get("date_updated", ""), reverse=True)

    # 分类：theme vs entity
    themes = [w for w in wikis if w.get("type") == "theme"]
    entities = [w for w in wikis if w.get("type") == "entity"]

    lines = [
        "## Wiki 编译页",
        "",
    ]

    if themes:
        lines.append("### 主题页")
        lines.append("")
        for w in themes:
            title = w.get("title", w["_filename"])
            sources_count = len(w.get("sources", []))
            confidence = w.get("confidence", "")
            status = w.get("status", "")
            status_badge = f" [{status}]" if status == "stub" else ""
            lines.append(
                f"- [{title}](wiki/{w['_filename']}) — "
                f"{sources_count} sources, confidence: {confidence}{status_badge}"
            )
        lines.append("")

    if entities:
        lines.append("### 实体页")
        lines.append("")
        for w in entities:
            title = w.get("title", w["_filename"])
            sources_count = len(w.get("sources", []))
            confidence = w.get("confidence", "")
            status = w.get("status", "")
            status_badge = f" [{status}]" if status == "stub" else ""
            lines.append(
                f"- [{title}](wiki/{w['_filename']}) — "
                f"{sources_count} sources, confidence: {confidence}{status_badge}"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    return lines


def build_index():
    if not NOTES_DIR.exists():
        NOTES_DIR.mkdir(parents=True, exist_ok=True)

    # 收集所有笔记的 frontmatter
    notes = []
    for f in sorted(NOTES_DIR.glob("*.md")):
        fm = parse_frontmatter(f)
        if fm:
            fm["_filename"] = f.name
            notes.append(fm)

    # 收集 wiki 统计
    wiki_count = 0
    if WIKI_DIR.exists():
        wiki_count = len(list(WIKI_DIR.glob("*.md")))

    if not notes and wiki_count == 0:
        INDEX_FILE.write_text(
            "# Anmu 知识库索引\n\n"
            "> 本文件由 `scripts/build_index.py` 自动生成，请勿手动编辑。\n\n"
            "---\n\n"
            "*知识库暂无内容。使用 `/anmu <链接或想法>` 开始入库。*\n",
            encoding="utf-8",
        )
        print("INDEX.md 已更新（空索引）")
        return

    # 按日期倒序排
    notes.sort(key=lambda n: n.get("date", ""), reverse=True)

    # 按标签分组
    tag_groups = defaultdict(list)
    for n in notes:
        for tag in n.get("tags", []):
            tag_groups[tag].append(n)

    # 生成 INDEX.md
    lines = [
        "# Anmu 知识库索引",
        "",
        "> 本文件由 `scripts/build_index.py` 自动生成，请勿手动编辑。",
        "",
        f"共 **{len(notes)}** 篇笔记，**{wiki_count}** 篇编译页，覆盖 **{len(tag_groups)}** 个标签。",
        "",
        "---",
        "",
    ]

    # Wiki 编译页区块（置顶）
    wiki_lines = build_wiki_section()
    lines.extend(wiki_lines)

    # 笔记按标签分组
    lines.append("## 笔记（按标签分组）")
    lines.append("")

    for tag in sorted(tag_groups.keys()):
        items = tag_groups[tag]
        lines.append(f"### `{tag}`（{len(items)} 篇）")
        lines.append("")
        for n in items:
            title = n.get("title", n["_filename"])
            date = n.get("date", "")
            lines.append(f"- [{title}](notes/{n['_filename']}) — {date}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 笔记（按时间倒序）")
    lines.append("")
    lines.append("| 日期 | 标题 | 类型 | 标签 |")
    lines.append("|------|------|------|------|")

    for n in notes:
        title = n.get("title", n["_filename"])
        date = n.get("date", "")
        stype = n.get("source_type", "")
        tags = ", ".join(f"`{t}`" for t in n.get("tags", []))
        lines.append(f"| {date} | [{title}](notes/{n['_filename']}) | {stype} | {tags} |")

    lines.append("")

    INDEX_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"INDEX.md 已更新（{len(notes)} 篇笔记，{wiki_count} 篇编译页，{len(tag_groups)} 个标签）")


if __name__ == "__main__":
    build_index()
