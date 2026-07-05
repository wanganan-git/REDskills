"""
compile_wiki.py — Wiki 编译辅助脚本

用法：
  python scripts/compile_wiki.py --action create --wiki-path wiki/xxx.md --notes notes/a.md notes/b.md
  python scripts/compile_wiki.py --action update --wiki-path wiki/xxx.md --notes notes/new.md

功能：
- create: 读取所有源笔记，输出编译上下文（JSON），供 Claude 写 wiki 页
- update: 读取现有 wiki 页 + 新笔记，输出更新上下文（JSON），供 Claude 重写

实际的语义编译由 Claude 完成，此脚本只做机械的文件读取和上下文准备。
"""

import sys
import os
import re
import json
import yaml
import argparse
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent


def parse_frontmatter(filepath):
    """解析 frontmatter，返回 (frontmatter_dict, body_text)"""
    text = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, match.group(2)


def read_note_content(note_path):
    """读取笔记全文，返回结构化内容"""
    path = ROOT / note_path if not Path(note_path).is_absolute() else Path(note_path)
    if not path.exists():
        return {"path": note_path, "error": "文件不存在"}

    fm, body = parse_frontmatter(path)
    return {
        "path": note_path,
        "title": fm.get("title", ""),
        "date": str(fm.get("date", "")),
        "tags": fm.get("tags", []),
        "source_type": fm.get("source_type", ""),
        "body": body.strip(),
    }


def prepare_create_context(wiki_path, note_paths):
    """准备创建 wiki 页的上下文"""
    notes = [read_note_content(p) for p in note_paths]

    # 收集所有标签取交集
    all_tag_sets = [set(n.get("tags", [])) for n in notes if "error" not in n]
    common_tags = sorted(set.intersection(*all_tag_sets)) if all_tag_sets else []

    context = {
        "action": "create",
        "wiki_path": wiki_path,
        "today": str(date.today()),
        "common_tags": common_tags,
        "notes": notes,
        "instructions": (
            "根据以下笔记内容，创建一篇 wiki 编译页。要求：\n"
            "1. 综合所有笔记得出结论，不是逐篇复述\n"
            "2. 标出不同笔记之间的矛盾点（如有）\n"
            "3. 包含：一段话结论摘要、核心结论列表、详细分析、开放问题、来源表\n"
            "4. 判断 type（theme=概念/方法论主题，entity=具体产品/人物/组织）\n"
            "5. 判断 confidence（low/medium/high）\n"
            "6. status: stub（2篇源）或 active（3+篇源）"
        ),
    }
    return context


def prepare_update_context(wiki_path, new_note_paths):
    """准备更新 wiki 页（往回织）的上下文"""
    wiki_full_path = ROOT / wiki_path
    if not wiki_full_path.exists():
        return {"error": f"Wiki 页不存在: {wiki_path}"}

    wiki_fm, wiki_body = parse_frontmatter(wiki_full_path)
    new_notes = [read_note_content(p) for p in new_note_paths]

    context = {
        "action": "update",
        "wiki_path": wiki_path,
        "today": str(date.today()),
        "existing_wiki": {
            "frontmatter": wiki_fm,
            "body": wiki_body.strip(),
        },
        "new_notes": new_notes,
        "instructions": (
            "有新笔记加入，请重写这篇 wiki 编译页。要求：\n"
            "1. 将新笔记的信息融入现有结论\n"
            "2. 如果新笔记与现有结论矛盾，添加 '⚠️ 矛盾点' 章节\n"
            "3. 根据新信息调整 confidence 级别\n"
            "4. 更新来源表，加入新笔记\n"
            "5. 保持综合分析风格，不要变成笔记罗列\n"
            "6. frontmatter 中 sources 要包含所有笔记路径，date_updated 设为今天"
        ),
    }
    return context


def write_wiki_page(wiki_path, frontmatter, body):
    """写入 wiki 页文件"""
    full_path = ROOT / wiki_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    fm_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False)
    content = f"---\n{fm_str}---\n{body}\n"
    full_path.write_text(content, encoding="utf-8")
    return str(full_path)


def main():
    parser = argparse.ArgumentParser(description="Wiki 编译辅助脚本")
    parser.add_argument("--action", required=True, choices=["create", "update", "context"])
    parser.add_argument("--wiki-path", required=True, help="wiki 页相对路径")
    parser.add_argument("--notes", nargs="+", required=True, help="笔记相对路径列表")
    args = parser.parse_args()

    if args.action == "create":
        context = prepare_create_context(args.wiki_path, args.notes)
    elif args.action == "update":
        context = prepare_update_context(args.wiki_path, args.notes)
    else:
        # context 模式：只输出上下文供调试
        context = prepare_create_context(args.wiki_path, args.notes)

    print(json.dumps(context, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
