"""
find_compilable.py — 检测新笔记是否触发 wiki 编译

用法：python scripts/find_compilable.py notes/2026-06-14-xxx.md
输出：JSON 格式的编译动作列表

逻辑：
1. 解析新笔记 tags
2. 扫描 wiki/ 找 tag 重叠 ≥1 且新笔记不在 sources 中的 → update
3. 若无匹配 wiki 页：扫描 notes/ 找共享 ≥2 tags 的笔记群 ≥2 篇 → create
"""

import sys
import os
import re
import json
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = ROOT / "wiki"
NOTES_DIR = ROOT / "notes"


def parse_frontmatter(filepath):
    """解析 markdown 文件的 YAML frontmatter"""
    text = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def find_wiki_updates(new_note_path, new_tags):
    """找到需要更新的 wiki 页（tag 重叠 ≥1 且新笔记不在 sources 中）"""
    actions = []
    if not WIKI_DIR.exists():
        return actions

    # 新笔记的相对路径（相对于项目根目录）
    new_note_rel = str(new_note_path.relative_to(ROOT)).replace("\\", "/")

    for wiki_file in WIKI_DIR.glob("*.md"):
        fm = parse_frontmatter(wiki_file)
        wiki_tags = set(fm.get("tags", []))
        sources = fm.get("sources", [])

        # 检查新笔记是否已编入
        if new_note_rel in sources:
            continue

        # 计算 tag 重叠
        overlap = new_tags & wiki_tags
        if len(overlap) >= 1:
            wiki_rel = str(wiki_file.relative_to(ROOT)).replace("\\", "/")
            all_notes = sources + [new_note_rel]
            actions.append({
                "action": "update",
                "wiki_path": wiki_rel,
                "notes": all_notes,
                "overlap_tags": sorted(overlap),
            })

    return actions


def find_new_clusters(new_note_path, new_tags):
    """在 notes/ 中找共享 ≥2 tags 的笔记群，判断是否应创建新 wiki 页"""
    actions = []
    new_note_rel = str(new_note_path.relative_to(ROOT)).replace("\\", "/")

    # 收集所有笔记的 tags
    note_tags_map = {}
    for note_file in NOTES_DIR.glob("*.md"):
        fm = parse_frontmatter(note_file)
        tags = set(fm.get("tags", []))
        note_rel = str(note_file.relative_to(ROOT)).replace("\\", "/")
        note_tags_map[note_rel] = tags

    # 确保新笔记也在 map 中
    note_tags_map[new_note_rel] = new_tags

    # 找与新笔记共享 ≥2 tags 的笔记
    cluster = [new_note_rel]
    shared_tags_all = set(new_tags)  # 用于生成 slug

    for note_rel, tags in note_tags_map.items():
        if note_rel == new_note_rel:
            continue
        overlap = new_tags & tags
        if len(overlap) >= 2:
            cluster.append(note_rel)
            shared_tags_all &= tags  # 取交集作为主题标签

    # 需要 ≥2 篇笔记才触发创建
    if len(cluster) >= 2:
        # 检查这些笔记是否已经被某个 wiki 页覆盖
        if not _cluster_already_covered(cluster):
            # 用共享 tag 生成 slug
            slug_tags = sorted(shared_tags_all) if shared_tags_all else sorted(new_tags)[:2]
            slug = "-".join(slug_tags[:3])
            actions.append({
                "action": "create",
                "wiki_path": f"wiki/{slug}.md",
                "notes": sorted(cluster),
                "overlap_tags": slug_tags,
            })

    return actions


def _cluster_already_covered(cluster):
    """检查笔记群是否已被现有 wiki 页覆盖（>50% 的笔记已编入同一 wiki 页）"""
    if not WIKI_DIR.exists():
        return False

    cluster_set = set(cluster)
    for wiki_file in WIKI_DIR.glob("*.md"):
        fm = parse_frontmatter(wiki_file)
        sources = set(fm.get("sources", []))
        overlap = cluster_set & sources
        if len(overlap) > len(cluster_set) * 0.5:
            return True
    return False


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/find_compilable.py <note_path>")
        sys.exit(1)

    note_path = Path(sys.argv[1])
    if not note_path.is_absolute():
        note_path = ROOT / note_path

    if not note_path.exists():
        print(json.dumps({"error": f"文件不存在: {note_path}"}, ensure_ascii=False))
        sys.exit(1)

    fm = parse_frontmatter(note_path)
    new_tags = set(fm.get("tags", []))

    if not new_tags:
        print(json.dumps({"actions": [], "message": "笔记无标签，跳过编译检测"}, ensure_ascii=False))
        return

    actions = []

    # 优先检查是否有 wiki 页需要更新
    update_actions = find_wiki_updates(note_path, new_tags)
    actions.extend(update_actions)

    # 如果没有需要更新的 wiki 页，检查是否应创建新页
    if not update_actions:
        create_actions = find_new_clusters(note_path, new_tags)
        actions.extend(create_actions)

    result = {"actions": actions}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
