#!/usr/bin/env python3
"""Anmu 知识库 - 关键词搜索（v2: wiki-first）

优先搜索 wiki/ 编译页，其次搜索 notes/。

用法：python scripts/search.py "关键词"
"""

import re
import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).parent.parent
WIKI_DIR = ROOT / "wiki"
NOTES_DIR = ROOT / "notes"


def parse_frontmatter_and_body(filepath: Path) -> tuple[dict, str] | tuple[None, str]:
    text = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return None, text
    try:
        fm = yaml.safe_load(match.group(1))
        return fm, match.group(2)
    except yaml.YAMLError:
        return None, text


def score_file(filepath: Path, keyword_lower: str) -> dict | None:
    """对单个文件进行关键词打分"""
    fm, body = parse_frontmatter_and_body(filepath)
    if fm is None:
        return None

    score = 0
    match_locations = []

    # 检查标题
    title = fm.get("title", "")
    if keyword_lower in title.lower():
        score += 3
        match_locations.append("标题")

    # 检查标签
    tags = fm.get("tags", [])
    for tag in tags:
        if keyword_lower in tag.lower():
            score += 2
            match_locations.append(f"标签:{tag}")

    # 检查正文
    body_lower = body.lower()
    count = body_lower.count(keyword_lower)
    if count > 0:
        score += min(count, 5)
        match_locations.append(f"正文({count}次)")

    if score <= 0:
        return None

    return {
        "file": str(filepath.relative_to(ROOT)).replace("\\", "/"),
        "title": title,
        "date": fm.get("date", ""),
        "tags": tags,
        "score": score,
        "match": ", ".join(match_locations),
        "sources": fm.get("sources", []),  # wiki 页特有
        "type": fm.get("type", ""),  # wiki 页特有
        "confidence": fm.get("confidence", ""),  # wiki 页特有
    }


def search(keyword: str):
    keyword_lower = keyword.lower()
    wiki_results = []
    note_results = []

    # 1. 先搜 wiki/
    if WIKI_DIR.exists():
        for f in sorted(WIKI_DIR.glob("*.md")):
            result = score_file(f, keyword_lower)
            if result:
                wiki_results.append(result)
        wiki_results.sort(key=lambda r: r["score"], reverse=True)

    # 2. 再搜 notes/
    if NOTES_DIR.exists():
        for f in sorted(NOTES_DIR.glob("*.md")):
            result = score_file(f, keyword_lower)
            if result:
                note_results.append(result)
        note_results.sort(key=lambda r: r["score"], reverse=True)

    if not wiki_results and not note_results:
        print(f"未找到与「{keyword}」相关的内容")
        return

    # 输出 wiki 结果（优先）
    if wiki_results:
        print(f"=== Wiki 编译页（优先阅读）===\n")
        for r in wiki_results:
            tags_str = ", ".join(r["tags"])
            source_count = len(r["sources"])
            print(f"  [{r['score']}分] {r['title']}")
            print(f"         文件: {r['file']}")
            print(f"         类型: {r['type']}  信心: {r['confidence']}  来源: {source_count}篇")
            print(f"         标签: {tags_str}")
            print(f"         匹配: {r['match']}")
            print()

    # 输出笔记结果
    if note_results:
        if wiki_results:
            print(f"=== 原始笔记（补充参考）===\n")
        else:
            print(f"=== 笔记 ===\n")

        for r in note_results:
            tags_str = ", ".join(r["tags"])
            print(f"  [{r['score']}分] {r['title']}")
            print(f"         文件: {r['file']}")
            print(f"         日期: {r['date']}  标签: {tags_str}")
            print(f"         匹配: {r['match']}")
            print()

    # 总结
    total = len(wiki_results) + len(note_results)
    print(f"共找到 {total} 条结果（wiki: {len(wiki_results)}, notes: {len(note_results)}）")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scripts/search.py \"关键词\"")
        sys.exit(1)
    search(sys.argv[1])
