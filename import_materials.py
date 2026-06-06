"""
快速导入脚本 — 一键导入课程资料

支持自定义文件夹位置，自动识别子文件夹分类。

推荐目录结构：
    D:/你的课程资料/
    └── 高等数学/
        ├── ppt/          ← 老师课件 → 自动标记为 "PPT课件"
        ├── 课本/          ← 教材PDF   → 自动标记为 "课本"
        ├── 作业题/        ← 平时作业   → 自动标记为 "作业"
        └── 往年题/        ← 往年试卷   → 自动标记为 "往年期末"

用法：
    # 方式1：从文件夹名自动提取课程名
    python import_materials.py "D:/你的课程资料/高等数学"

    # 方式2：手动指定课程名
    python import_materials.py "D:/你的课程资料/高等数学" "高等数学"

    # 方式3：导入课程文件夹下的所有课程（每个子文件夹=一门课）
    python import_materials.py "D:/你的课程资料" --all
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server.document_parser import parse_file, ParsedChunk
from mcp_server.vector_store import VectorStore
from mcp_server.metadata_store import MetadataStore

# 子文件夹名 → 来源标签映射
FOLDER_TAG_MAP = {
    "ppt":      "PPT课件",
    "课件":     "PPT课件",
    "slides":   "PPT课件",
    "课本":     "课本",
    "教材":     "课本",
    "textbook": "课本",
    "作业":     "作业",
    "作业题":   "作业",
    "homework": "作业",
    "往年题":   "往年期末",
    "往年":     "往年期末",
    "期末":     "往年期末",
    "期中":     "期中考试",
    "exam":     "往年期末",
    "final":    "往年期末",
    "midterm":  "期中考试",
    "试卷":     "往年期末",
    "笔记":     "个人笔记",
    "个人笔记": "个人笔记",
    "notes":    "个人笔记",
}


def detect_source_tag(file_path: str) -> str:
    """根据文件所在子文件夹自动判定来源标签"""
    path_lower = file_path.lower().replace("\\", "/")
    parts = path_lower.split("/")

    # 从最近的子文件夹开始匹配
    for part in reversed(parts):
        part_clean = part.strip().lower()
        if part_clean in FOLDER_TAG_MAP:
            return FOLDER_TAG_MAP[part_clean]

    return "未知来源"


def import_course(root_dir: str, course_name: str = None) -> dict:
    """
    导入一门课程的所有资料。

    参数
    ----
    root_dir : 课程资料根目录（如 D:/courses/高等数学/）
    course_name : 课程名（不传则从文件夹名自动提取）

    返回
    ----
    dict : 导入统计
    """
    if not os.path.exists(root_dir):
        print(f"[ERROR] 目录不存在: {root_dir}")
        return {"error": "目录不存在"}

    if not os.path.isdir(root_dir):
        print(f"[ERROR] 不是目录: {root_dir}")
        return {"error": "不是目录"}

    # 自动提取课程名
    if course_name is None:
        course_name = os.path.basename(os.path.normpath(root_dir))
        if not course_name:
            course_name = "未命名课程"

    print(f"\n{'=' * 60}")
    print(f"  课程: {course_name}")
    print(f"  目录: {root_dir}")
    print(f"{'=' * 60}")

    # 1. 扫描所有文件
    print("\n[1/4] 扫描文件...")
    supported_exts = {".ppt", ".pptx", ".pdf", ".doc", ".docx",
                      ".png", ".jpg", ".jpeg", ".bmp", ".tiff",
                      ".txt", ".md", ".markdown"}

    file_list = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in supported_exts:
                file_list.append(os.path.join(dirpath, fname))

    if not file_list:
        print(f"  [ERROR] 未发现支持的文件！")
        print(f"  支持的格式: {', '.join(sorted(supported_exts))}")
        return {"error": "无支持的文件"}

    print(f"  发现 {len(file_list)} 个文件")

    # 2. 解析每个文件
    print("\n[2/4] 解析文件...")
    all_chunks = []
    file_stats = {}

    for file_path in file_list:
        rel_path = os.path.relpath(file_path, root_dir)
        source_tag = detect_source_tag(file_path)
        try:
            chunks = parse_file(file_path)
            if chunks:
                # 给每个 chunk 打上来源标签
                for c in chunks:
                    c.extra_metadata["source_tag"] = source_tag
                    c.extra_metadata["relative_path"] = rel_path

                all_chunks.extend(chunks)
                file_stats[rel_path] = {
                    "chunks": len(chunks),
                    "tag": source_tag,
                    "type": chunks[0].source_type,
                }

                # 显示进度
                icon = {"PPT课件": "[PPT]", "课本": "[TXT]", "作业": "[HW]", "往年期末": "[EXAM]",
                        "期中考试": "[MID]", "个人笔记": "[NOTE]", "未知来源": "[?]"}.get(source_tag, "[?]")
                chapter = chunks[0].chapter_hint or ""
                chapter_str = f" -> {chapter}" if chapter else ""
                print(f"  {icon} [{source_tag}] {rel_path} ({len(chunks)} chunks){chapter_str}")
            else:
                print(f"  [EMPTY] [{source_tag}] {rel_path} parsed but empty")
        except Exception as e:
            print(f"  [FAIL] [{source_tag}] {rel_path}: {e}")

    if not all_chunks:
        print("\n[ERROR] 所有文件解析均为空！")
        return {"error": "解析结果为空"}

    # 按来源标签统计
    tag_stats = {}
    for info in file_stats.values():
        tag = info["tag"]
        if tag not in tag_stats:
            tag_stats[tag] = {"files": 0, "chunks": 0}
        tag_stats[tag]["files"] += 1
        tag_stats[tag]["chunks"] += info["chunks"]

    print(f"\n  解析统计:")
    for tag, stats in sorted(tag_stats.items()):
        print(f"    {tag}: {stats['files']} 个文件, {stats['chunks']} 个文本块")
    print(f"    总计: {len(file_stats)} 个文件, {len(all_chunks)} 个文本块")

    # 3. 向量化存储
    print(f"\n[3/4] 向量化存储 (TF-IDF)...")
    vs = VectorStore()
    count = vs.add_chunks(all_chunks, course_name=course_name)
    print(f"  存储完成: {count} 个向量块")

    # 4. 元数据管理
    print(f"\n[4/4] 创建课程结构...")
    ms = MetadataStore()
    course = ms.get_course(course_name)
    if not course:
        course_id = ms.add_course(course_name)
    else:
        course_id = course["id"]

    # 自动识别章节
    chapters_seen = {}
    for c in all_chunks:
        if c.chapter_hint:
            ch = c.chapter_hint
            if ch not in chapters_seen:
                chapters_seen[ch] = []
            chapters_seen[ch].append(c.extra_metadata.get("source_tag", "未知来源"))

    for ch_title, tags in chapters_seen.items():
        ms.add_chapter(course_id, ch_title,
                       description=f"来源: {', '.join(set(tags))}")

    print(f"  自动识别 {len(chapters_seen)} 个章节:")
    for ch, tags in sorted(chapters_seen.items()):
        print(f"    - {ch} (来源: {', '.join(set(tags))})")

    # 汇总
    print(f"\n{'=' * 60}")
    print(f"  导入完成!")
    print(f"    课程: {course_name}")
    print(f"    文件: {len(file_stats)} 个")
    print(f"    文本块: {count} 个")
    print(f"    章节: {len(chapters_seen)} 个")
    print(f"    分类: {', '.join(tag_stats.keys())}")
    print(f"\n  接下来可以:")
    print(f"    1. 搜索: search_knowledge('{course_name}', '你的问题')")
    print(f"    2. 标记重点: mark_key_point('{course_name}', '重点内容')")
    print(f"    3. 录入题目: 把往年题的题目文本添加到题库")
    print(f"    4. 查看概览: get_course_overview('{course_name}')")
    print(f"    5. 生成复习提纲: /review-summary {course_name}")
    print(f"{'=' * 60}\n")

    return {
        "course": course_name,
        "files": len(file_stats),
        "chunks": count,
        "chapters": len(chapters_seen),
        "tags": list(tag_stats.keys()),
    }


# =========================================================================
# 入口
# =========================================================================

def main():
    if len(sys.argv) < 2:
        print("""
期末复习助手 — 资料导入工具

用法:
  python import_materials.py <资料目录> [课程名]

示例:
  # 自动从文件夹名提取课程名
  python import_materials.py "D:/课程资料/高等数学"

  # 手动指定课程名
  python import_materials.py "D:/课程资料/高数下" "高等数学（下）"

  # 使用默认 data/materials 目录
  python import_materials.py "data/materials/高等数学"

推荐目录结构:
  高等数学/
  ├── ppt/          ← 老师课件
  ├── 课本/          ← 教材PDF
  ├── 作业题/        ← 平时作业
  └── 往年题/        ← 期中期末卷
""")
        sys.exit(1)

    root_dir = sys.argv[1]
    course_name = sys.argv[2] if len(sys.argv) > 2 else None

    result = import_course(root_dir, course_name)
    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
