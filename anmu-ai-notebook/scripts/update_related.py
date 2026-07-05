#!/usr/bin/env python3
"""Anmu 知识库 - 关联更新器

对指定笔记与 notes/ 下所有其他笔记计算关联分：
  score = (共同标签数 × 2) + (标题关键词重叠数 × 1)
阈值 ≥ 2 的写入双方 related 字段。

用法：python scripts/update_related.py notes/2026-06-14-xxx.md
"""

import os
import re
import sys
import yaml
from pathlib import Path

NOTES_DIR = Path(__file__).parent.parent / "notes"
THRESHOLD = 2


def parse_frontmatter_and_body(filepath: Path) -> tuple[dict, str] | tuple[None, str]:
    """返回 (frontmatter_dict, body_text)。"""
    text = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return None, text
    try:
        fm = yaml.safe_load(match.group(1))
        return fm, match.group(2)
    except yaml.YAMLError:
        return None, text


def write_frontmatter_and_body(filepath: Path, fm: dict, body: str):
    """将 frontmatter + body 写回文件。"""
    fm_str = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    filepath.write_text(f"---\n{fm_str}---\n{body}", encoding="utf-8")


def extract_keywords(title: str) -> set[str]:
    """从标题中提取关键词（简单分词：按非字母数字中文切割，去短词）。"""
    # 按非字母数字中文字符分割
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", title.lower())
    # 过滤掉太短的词（英文 ≤2 字符，中文单字保留）
    stopwords = {"the", "a", "an", "of", "in", "on", "for", "and", "or", "is", "are", "to", "with", "from", "by"}
    result = set()
    for t in tokens:
        if t in stopwords:
            continue
        # 中文字符：每个字都算关键词
        if re.search(r"[\u4e00-\u9fff]", t):
            for ch in t:
                if "\u4e00" <= ch <= "\u9fff":
                    result.add(ch)
        elif len(t) > 2:
            result.add(t)
    return result


def compute_score(fm_a: dict, fm_b: dict) -> int:
    """计算两篇笔记的关联分。"""
    tags_a = set(fm_a.get("tags", []))
    tags_b = set(fm_b.get("tags", []))
    tag_overlap = len(tags_a & tags_b)

    kw_a = extract_keywords(fm_a.get("title", ""))
    kw_b = extract_keywords(fm_b.get("title", ""))
    kw_overlap = len(kw_a & kw_b)

    return tag_overlap * 2 + kw_overlap * 1


def update_related(target_path: str):
    target = Path(target_path)
    if not target.exists():
        print(f"错误：文件不存在 {target_path}")
        sys.exit(1)

    target_fm, target_body = parse_frontmatter_and_body(target)
    if target_fm is None:
        print(f"错误：无法解析 frontmatter {target_path}")
        sys.exit(1)

    # 收集所有其他笔记
    others = []
    for f in NOTES_DIR.glob("*.md"):
        if f.name == target.name:
            continue
        fm, body = parse_frontmatter_and_body(f)
        if fm:
            others.append((f, fm, body))

    # 计算关联
    new_related = []
    updated_others = []

    for other_path, other_fm, other_body in others:
        score = compute_score(target_fm, other_fm)
        if score >= THRESHOLD:
            new_related.append(other_path.name)
            # 双向：把 target 也加到 other 的 related 里
            other_related = other_fm.get("related", []) or []
            if target.name not in other_related:
                other_related.append(target.name)
                other_fm["related"] = other_related
                updated_others.append((other_path, other_fm, other_body))

    # 更新 target 的 related（合并已有的，去重）
    existing_related = target_fm.get("related", []) or []
    merged = list(dict.fromkeys(existing_related + new_related))  # 保序去重
    target_fm["related"] = merged
    write_frontmatter_and_body(target, target_fm, target_body)

    # 写回被关联的其他笔记
    for other_path, other_fm, other_body in updated_others:
        write_frontmatter_and_body(other_path, other_fm, other_body)

    if new_related:
        print(f"关联更新完成：{target.name} ↔ {', '.join(new_related)}")
    else:
        print(f"关联更新完成：{target.name} 暂无关联笔记")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scripts/update_related.py notes/文件名.md")
        sys.exit(1)
    update_related(sys.argv[1])
