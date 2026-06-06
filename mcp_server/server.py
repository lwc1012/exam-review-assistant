"""
期末复习助手 — MCP Server 主入口

向 AI 助手提供以下工具：

  数据导入层：
    1. ingest_material        — 导入课程资料（PPT/PDF/DOCX/图片/文本）
    2. import_directory       — 批量导入整个目录

  知识检索层：
    3. search_knowledge       — 语义搜索知识点
    4. get_course_overview    — 查看课程数据结构概览
    5. get_chapter_list       — 获取章节列表

  重点管理层：
    6. mark_key_point         — 标记老师划的重点
    7. get_key_points         — 查询已标记的重点

  题目管理层：
    8. add_exam_question      — 添加题目（作业/期中/期末）
    9. get_questions          — 按条件查询题目
   10. get_question_stats     — 查看题目统计（题型分布、来源分布）

运行方式：
    python mcp_server/server.py
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from mcp_server.document_parser import parse_file, parse_directory
from mcp_server.vector_store import VectorStore
from mcp_server.metadata_store import MetadataStore
from mcp_server.embedding import get_embedding_model

# =========================================================================
# 全局实例（懒加载）
# =========================================================================

_vector_store: Optional[VectorStore] = None
_metadata_store: Optional[MetadataStore] = None


def get_vs() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def get_ms() -> MetadataStore:
    global _metadata_store
    if _metadata_store is None:
        _metadata_store = MetadataStore()
    return _metadata_store


# =========================================================================
# 创建 MCP Server
# =========================================================================

mcp = FastMCP(
    "exam-review-assistant",
    instructions=(
        "期末复习助手 — 帮助大学生高效复习的智能工具。\n\n"
        "核心能力：\n"
        "1. 导入课程资料（PPT、PDF课本、作业题、试卷图片等）\n"
        "2. 语义搜索知识点，精准定位相关内容\n"
        "3. 标记和管理老师划的重点\n"
        "4. 管理题库（作业题、期中考试、往年期末题）\n"
        "5. 配合 AI 生成复习资料、变体练习题和模拟试卷\n\n"
        "典型使用流程：\n"
        "  ① 用 ingest_material / import_directory 导入所有资料\n"
        "  ② 用 mark_key_point 标注老师划的重点\n"
        "  ③ 用 add_exam_question 录入题目\n"
        "  ④ 用 search_knowledge 检索知识点，让 AI 总结复习提纲\n"
        "  ⑤ 用 get_questions 获取题目，让 AI 生成模拟卷"
    )
)


# =========================================================================
#  工具 1：ingest_material — 导入单个资料文件
# =========================================================================

@mcp.tool(
    description=(
        "导入一份课程资料（PPT课件、PDF课本、Word文档、图片笔记、文本文件）。"
        "支持格式：.ppt/.pptx, .pdf, .doc/.docx, .png/.jpg/.jpeg/.bmp/.tiff, .txt/.md"
        "导入后自动向量化存储，支持后续语义搜索。"
        "参数 is_key_point=True 可标记该资料整体为重点（所有内容权重提升）。"
    )
)
def ingest_material(
    file_path: str,
    course_name: str,
    is_key_point: bool = False,
) -> str:
    """导入单份课程资料"""
    if not os.path.exists(file_path):
        return json.dumps({"error": f"文件不存在：{file_path}"}, ensure_ascii=False)

    try:
        chunks = parse_file(file_path, is_key_point=is_key_point)
        if not chunks:
            return json.dumps({
                "warning": f"文件解析后无有效文本内容：{file_path}",
                "chunk_count": 0,
            }, ensure_ascii=False)

        # 确保课程存在于元数据库
        ms = get_ms()
        course = ms.get_course(course_name)
        if not course:
            ms.add_course(course_name)

        # 写入向量库
        vs = get_vs()
        added = vs.add_chunks(chunks, course_name=course_name)

        return json.dumps({
            "success": True,
            "file": os.path.basename(file_path),
            "course": course_name,
            "chunk_count": added,
            "source_types": list(set(c.source_type for c in chunks)),
            "is_key_point": is_key_point,
            "hint": "资料已就绪，可使用 search_knowledge 检索内容",
        }, ensure_ascii=False, indent=2)

    except FileNotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except ImportError as e:
        return json.dumps({"error": f"缺少依赖：{e}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"导入失败：{str(e)}"}, ensure_ascii=False)


# =========================================================================
#  工具 2：import_directory — 批量导入目录
# =========================================================================

@mcp.tool(
    description=(
        "批量导入一个目录下的所有课程资料。递归扫描子目录，自动识别文件类型并解析。"
        "适合一次导入整个课程的 PPT 文件夹或资料包。"
    )
)
def import_directory(
    directory_path: str,
    course_name: str,
) -> str:
    """批量导入目录"""
    if not os.path.exists(directory_path):
        return json.dumps({"error": f"目录不存在：{directory_path}"}, ensure_ascii=False)

    try:
        chunks = parse_directory(directory_path, recursive=True)
        if not chunks:
            return json.dumps({
                "warning": f"目录下未找到支持的文件：{directory_path}",
                "supported_formats": "ppt/pptx, pdf, doc/docx, png/jpg/bmp/tiff, txt/md",
                "chunk_count": 0,
            }, ensure_ascii=False)

        # 确保课程存在
        ms = get_ms()
        course = ms.get_course(course_name)
        if not course:
            ms.add_course(course_name)

        # 写入向量库
        vs = get_vs()
        added = vs.add_chunks(chunks, course_name=course_name)

        # 按文件来源分组统计
        source_files = {}
        for c in chunks:
            fname = c.source_file
            if fname not in source_files:
                source_files[fname] = {"file": fname, "chunks": 0, "type": c.source_type}
            source_files[fname]["chunks"] += 1

        return json.dumps({
            "success": True,
            "directory": directory_path,
            "course": course_name,
            "total_chunks": added,
            "files_imported": len(source_files),
            "file_details": list(source_files.values()),
            "hint": f"已导入 {added} 个文本块，覆盖 {len(source_files)} 个文件。可使用 search_knowledge 检索。",
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": f"批量导入失败：{str(e)}"}, ensure_ascii=False)


# =========================================================================
#  工具 3：search_knowledge — 语义搜索
# =========================================================================

@mcp.tool(
    description=(
        "语义搜索课程知识库。输入自然语言查询，返回最相关的知识点和资料片段。\n"
        "支持过滤条件：按课程、文件类型、章节筛选；自动提升老师划重点的内容权重。\n"
        "典型用法：'微积分中值定理'、'线性代数矩阵运算例题'"
    )
)
def search_knowledge(
    query: str,
    course_name: str,
    top_k: int = 10,
    source_type: str = "",
    chapter: str = "",
) -> str:
    """语义搜索课程知识"""
    try:
        vs = get_vs()

        results = vs.search(
            query=query,
            top_k=top_k,
            course_filter=course_name,
            source_type_filter=source_type if source_type else None,
            chapter_filter=chapter if chapter else None,
            boost_key_points=True,
        )

        if not results:
            return json.dumps({
                "query": query,
                "course": course_name,
                "results": [],
                "hint": "未找到匹配内容。建议：1) 确认课程资料已导入 2) 尝试更宽泛的搜索词 3) 检查 course_name 是否正确",
            }, ensure_ascii=False, indent=2)

        return json.dumps({
            "query": query,
            "course": course_name,
            "total_results": len(results),
            "results": [
                {
                    "rank": i + 1,
                    "score": round(r["score"], 4),
                    "text": r["text"],
                    "source_file": r["metadata"].get("source_file", ""),
                    "source_type": r["metadata"].get("source_type", ""),
                    "chapter": r["metadata"].get("chapter_hint", ""),
                    "is_key_point": r["metadata"].get("is_key_point", False),
                    "boosted": r.get("boosted", False),
                }
                for i, r in enumerate(results)
            ],
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": f"搜索失败：{str(e)}"}, ensure_ascii=False)


# =========================================================================
#  工具 4：get_course_overview — 课程概览
# =========================================================================

@mcp.tool(
    description=(
        "查看课程的完整数据概览：已导入的文件列表、总文档块数、"
        "章节数量、题目数量、重点标记数等。帮助了解当前课程的知识库规模。"
    )
)
def get_course_overview(course_name: str) -> str:
    """获取课程数据结构概览"""
    try:
        ms = get_ms()
        vs = get_vs()

        course = ms.get_course(course_name)

        # 向量库统计
        sources = vs.list_sources(course_filter=course_name)
        total_chunks = vs.count()
        chapters_list = vs.list_chapters(course_filter=course_name)

        # 元数据库统计
        q_types = []
        source_stats = []
        key_points = []
        if course:
            course_id = course["id"]
            q_types = ms.get_question_types(course_id)
            source_stats = ms.get_source_stats(course_id)
            key_points = ms.get_key_points(course_id)

        return json.dumps({
            "course_name": course_name,
            "course_info": course,
            "vector_store": {
                "total_chunks": total_chunks,
                "source_files": len(sources),
                "file_list": sources,
                "auto_detected_chapters": chapters_list,
            },
            "questions": {
                "types": q_types,
                "source_stats": source_stats,
            },
            "key_points_count": len(key_points),
            "hint": (
                "数据概览如上。\n"
                "- 如果文件列表为空，请先用 ingest_material 导入资料\n"
                "- 如果题目为空，请用 add_exam_question 录入题目\n"
                "- 如果重点为空，请用 mark_key_point 标注重点"
            ),
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# =========================================================================
#  工具 5：get_chapter_list — 获取章节
# =========================================================================

@mcp.tool(
    description="获取课程已建的所有章节/知识点列表（从元数据库和自动识别中汇总）。"
)
def get_chapter_list(course_name: str) -> str:
    """获取课程章节列表"""
    try:
        ms = get_ms()
        vs = get_vs()

        course = ms.get_course(course_name)

        # 元数据库中手动创建的章节
        manual_chapters = []
        if course:
            manual_chapters = ms.get_chapters(course["id"])

        # 向量库中自动识别的章节
        auto_chapters = vs.list_chapters(course_filter=course_name)

        return json.dumps({
            "course": course_name,
            "manual_chapters": [
                {"id": c["id"], "title": c["title"], "weight": c["weight"],
                 "description": c.get("description", "")}
                for c in manual_chapters
            ],
            "auto_detected_chapters": auto_chapters,
            "hint": "可对自动识别的章节使用 mark_key_point 标注重点，或使用 add_exam_question 为章节添加题目。",
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# =========================================================================
#  工具 6：mark_key_point — 标记重点
# =========================================================================

@mcp.tool(
    description=(
        "标记老师划的重点内容。可指定关联章节。\n"
        "标记后：1) 关联章节权重提升至 3.0 2) 语义搜索时重点内容排名靠前。\n"
        "source 参数记录信息来源（如'老师口述'、'PPT 标红'、'期末复习课'）。"
    )
)
def mark_key_point(
    course_name: str,
    content: str,
    chapter_title: str = "",
    source: str = "手动标记",
) -> str:
    """标记重点内容"""
    try:
        ms = get_ms()
        vs = get_vs()

        # 确保课程存在
        course = ms.get_course(course_name)
        if not course:
            course_id = ms.add_course(course_name)
        else:
            course_id = course["id"]

        # 查找或创建章节
        chapter_id = None
        if chapter_title:
            chapters = ms.get_chapters(course_id)
            for ch in chapters:
                if ch["title"] == chapter_title:
                    chapter_id = ch["id"]
                    break
            if chapter_id is None:
                chapter_id = ms.add_chapter(course_id, chapter_title)

        # 添加重点
        kp_id = ms.add_key_point(course_id, content, chapter_id, source)

        # 同时在向量库中标记相关内容（搜索并提升权重）
        search_results = vs.search(
            query=content,
            top_k=5,
            course_filter=course_name,
            boost_key_points=False,
        )
        for r in search_results:
            # 在向量库 metadata 中标记 is_key_point
            if r["metadata"].get("chapter_hint") == chapter_title or not chapter_title:
                try:
                    vs.update_metadata(course_name, r["id"],
                                       {"is_key_point": True})
                except Exception:
                    pass  # 更新失败不影响主流程

        return json.dumps({
            "success": True,
            "key_point_id": kp_id,
            "course": course_name,
            "chapter": chapter_title or "无指定章节",
            "content": content[:100] + ("..." if len(content) > 100 else ""),
            "boosted_chunks": len(search_results),
            "hint": "重点已标记，后续搜索将自动提升相关内容的权重。",
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# =========================================================================
#  工具 7：get_key_points — 查询重点
# =========================================================================

@mcp.tool(
    description="查询课程所有已标记的重点内容，按时间倒序排列。"
)
def get_key_points(course_name: str) -> str:
    """查询重点"""
    try:
        ms = get_ms()
        course = ms.get_course(course_name)
        if not course:
            return json.dumps({
                "course": course_name,
                "key_points": [],
                "hint": f"课程 '{course_name}' 不存在，请先导入资料或创建课程。",
            }, ensure_ascii=False, indent=2)

        points = ms.get_key_points(course["id"])

        return json.dumps({
            "course": course_name,
            "total": len(points),
            "key_points": [
                {
                    "id": p["id"],
                    "content": p["content"],
                    "chapter": p.get("chapter_title", ""),
                    "source": p.get("source", ""),
                }
                for p in points
            ],
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# =========================================================================
#  工具 8：add_exam_question — 添加题目
# =========================================================================

@mcp.tool(
    description=(
        "添加一道考试题目到题库。\n"
        "q_type 题型：选择题/填空题/计算题/证明题/简答题/编程题 等\n"
        "source 来源：作业/期中考试/期末考试/往年期末/模拟题\n"
        "difficulty 难度：1(简单)-5(困难)\n"
        "tags 标签：逗号分隔，如 '中值定理,罗尔定理'"
    )
)
def add_exam_question(
    course_name: str,
    question: str,
    answer: str = "",
    q_type: str = "计算题",
    chapter_title: str = "",
    difficulty: int = 3,
    source: str = "作业",
    source_year: str = "",
    tags: str = "",
) -> str:
    """添加题目"""
    try:
        ms = get_ms()

        # 确保课程存在
        course = ms.get_course(course_name)
        if not course:
            course_id = ms.add_course(course_name)
        else:
            course_id = course["id"]

        # 查找或创建章节
        chapter_id = None
        if chapter_title:
            chapters = ms.get_chapters(course_id)
            for ch in chapters:
                if ch["title"] == chapter_title:
                    chapter_id = ch["id"]
                    break
            if chapter_id is None:
                chapter_id = ms.add_chapter(course_id, chapter_title)

        qid = ms.add_question(
            course_id=course_id,
            q_type=q_type,
            question=question,
            answer=answer,
            chapter_id=chapter_id,
            difficulty=max(1, min(5, difficulty)),
            source=source,
            source_year=source_year,
            tags=tags,
        )

        return json.dumps({
            "success": True,
            "question_id": qid,
            "course": course_name,
            "type": q_type,
            "chapter": chapter_title or "无指定章节",
            "source": source,
            "difficulty": difficulty,
            "hint": "题目已录入题库，可使用 get_questions 查询。",
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# =========================================================================
#  工具 9：get_questions — 查询题目
# =========================================================================

@mcp.tool(
    description=(
        "按条件查询题库中的题目。支持按题型、章节、来源、难度过滤。\n"
        "典型用法：\n"
        "  - 获取所有往年期末题：source='往年期末'\n"
        "  - 获取某章节的作业题：chapter_title='第三章', source='作业'\n"
        "  - 获取所有选择题：q_type='选择题'"
    )
)
def get_questions(
    course_name: str,
    q_type: str = "",
    chapter_title: str = "",
    source: str = "",
    difficulty: str = "",
    limit: int = 50,
) -> str:
    """查询题目"""
    try:
        ms = get_ms()
        course = ms.get_course(course_name)
        if not course:
            return json.dumps({
                "course": course_name,
                "questions": [],
                "hint": f"课程 '{course_name}' 不存在",
            }, ensure_ascii=False, indent=2)

        # 解析难度参数
        diff_int = int(difficulty) if difficulty.isdigit() else None

        # 解析章节 ID
        chapter_id = None
        if chapter_title:
            chapters = ms.get_chapters(course["id"])
            for ch in chapters:
                if ch["title"] == chapter_title:
                    chapter_id = ch["id"]
                    break

        questions = ms.get_questions(
            course_id=course["id"],
            q_type=q_type if q_type else None,
            chapter_id=chapter_id,
            source=source if source else None,
            difficulty=diff_int,
            limit=limit,
        )

        return json.dumps({
            "course": course_name,
            "filters": {
                "type": q_type or "全部",
                "chapter": chapter_title or "全部",
                "source": source or "全部",
                "difficulty": difficulty or "全部",
            },
            "total": len(questions),
            "questions": [
                {
                    "id": q["id"],
                    "type": q["q_type"],
                    "question": q["question"],
                    "answer": q.get("answer", ""),
                    "chapter": q.get("chapter_title", ""),
                    "source": q.get("source", ""),
                    "source_year": q.get("source_year", ""),
                    "difficulty": q["difficulty"],
                    "tags": q.get("tags", ""),
                }
                for q in questions
            ],
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# =========================================================================
#  工具 10：get_question_stats — 题目统计分析
# =========================================================================

@mcp.tool(
    description=(
        "统计课程的题目分布：各题型数量、各来源（作业/期中/期末）数量、"
        "难度分布。用于生成模拟卷时参考题型比例。"
    )
)
def get_question_stats(course_name: str) -> str:
    """题目统计分析"""
    try:
        ms = get_ms()
        course = ms.get_course(course_name)
        if not course:
            return json.dumps({
                "error": f"课程 '{course_name}' 不存在",
            }, ensure_ascii=False, indent=2)

        course_id = course["id"]
        source_stats = ms.get_source_stats(course_id)
        q_types = ms.get_question_types(course_id)

        # 按题型 + 来源交叉统计
        type_source_stats = {}
        for qt in q_types:
            questions = ms.get_questions(course_id, q_type=qt, limit=1000)
            type_source_stats[qt] = {}
            for q in questions:
                src = q.get("source", "未知")
                type_source_stats[qt][src] = type_source_stats[qt].get(src, 0) + 1

        # 难度统计
        all_qs = ms.get_questions(course_id, limit=10000)
        diff_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for q in all_qs:
            d = q.get("difficulty", 3)
            diff_dist[d] = diff_dist.get(d, 0) + 1

        return json.dumps({
            "course": course_name,
            "total_questions": len(all_qs),
            "by_source": source_stats,
            "by_type_and_source": type_source_stats,
            "by_difficulty": [
                {"difficulty": d, "count": c, "label": ["", "很简单", "简单", "中等", "困难", "很难"][d]}
                for d, c in sorted(diff_dist.items())
            ],
            "hint": (
                "这些统计数据可以帮助 AI 生成模拟卷时匹配往年考试的题型比例和难度分布。"
                "题型分布用于确定试卷结构，难度分布用于控制试卷难度与往年一致。"
            ),
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# =========================================================================
#  入口
# =========================================================================

if __name__ == "__main__":
    print("=" * 55)
    print("  期末复习助手 MCP Server — Exam Review Assistant")
    print("=" * 55)
    print()
    print("  提供以下工具：")
    print("    数据导入：ingest_material / import_directory")
    print("    知识检索：search_knowledge / get_course_overview")
    print("    重点管理：mark_key_point / get_key_points")
    print("    题目管理：add_exam_question / get_questions")
    print("    统计分析：get_question_stats")
    print()
    print("  启动中...")
    mcp.run()
