"""
期末复习提纲 Skill — /review-summary

用法：
    /review-summary <课程名>                    → MCP Skill 模式（Claude Code 中）
    python skills/review_summary.py <课程名>    → 独立运行模式（命令行直接调用）
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcp_server.vector_store import VectorStore
from mcp_server.metadata_store import MetadataStore


SKILL_INSTRUCTION = """
你是一个专业的大学课程复习助手。用户当前正在使用 /review-summary 命令。

## 核心原则

1. **深度而非概括**：每个知识点必须包含定义、原理、示例、辨析、考试要点
2. **流程图要求**：流程类知识必须附带 Mermaid 图表（stateDiagram/flowchart/sequenceDiagram）
3. **多格式输出**：先生成 .md（含流程图），再运行 md2docx.py 转 .docx

## 执行步骤

### Step 1：获取全貌
调用 get_course_overview(course_name="{课程名}") 了解数据规模。

### Step 2：获取重点
调用 get_key_points(course_name="{课程名}") 获取老师划的重点。

### Step 3：获取章节
调用 get_chapter_list(course_name="{课程名}") 获取所有章节。

### Step 4：逐章深度检索（关键步骤）
对每个章节，至少发起 3-4 次不同角度的搜索，每次 top_k>=12：
- 概念定义：search_knowledge("{核心概念} 定义 特点", course_name="{课程名}", top_k=12)
- 工作原理：search_knowledge("{核心概念} 原理 流程 步骤", course_name="{课程名}", top_k=12)
- 对比辨析：search_knowledge("{概念A} {概念B} 区别 对比", course_name="{课程名}", top_k=12)
- 考试题型：search_knowledge("{章节} 考题 计算", course_name="{课程名}", top_k=12, source_tag_filter="往年期末")

### Step 5：获取题目
调用 get_questions + get_question_stats 获取往届真题和题型分布。

### Step 6：综合生成
按章节输出，每章不少于 500 字详细讲解，附带 Mermaid 流程图和对比表格。

## 注意事项
- 重点内容突出标注
- 流程图用 Mermaid 语法
- 同时生成 .md 和 .docx
"""

# =====================================================================
# 独立运行入口（无需 MCP Server）
# =====================================================================

def run_standalone(course_name: str, output_dir: str = None):
    """
    不依赖 MCP Server，直接调用底层模块生成复习提纲。

    参数
    ----
    course_name : 课程名（需已导入资料）
    output_dir : 输出目录（默认为项目根目录）
    """
    vs = VectorStore()
    ms = MetadataStore()

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..')

    print(f"[1/5] 课程概览...")
    sources = vs.list_sources(course_filter=course_name)
    total = vs.count(course_filter=course_name)
    chapters = vs.list_chapters(course_filter=course_name)
    print(f"  文件: {len(sources)}, 文档块: {total}, 章节: {len(chapters)}")

    print(f"[2/5] 获取重点...")
    course = ms.get_course(course_name)
    key_points = ms.get_key_points(course["id"]) if course else []
    print(f"  重点: {len(key_points)} 条")

    print(f"[3/5] 获取题库统计...")
    if course:
        q_types = ms.get_question_types(course["id"])
        source_stats = ms.get_source_stats(course["id"])
        print(f"  题型: {q_types}, 来源: {len(source_stats)} 类")

    print(f"[4/5] 逐章深度检索...")
    topic_queries = [
        ("进程 概念 状态 PCB 线程 调度", "进程管理"),
        ("CPU 调度 FCFS SJF RR 优先级 多级 反馈", "处理器调度"),
        ("死锁 条件 银行家 算法 预防 避免 检测", "死锁"),
        ("内存 分页 分段 虚拟 页表 置换 FIFO LRU", "内存管理"),
        ("文件 系统 FCB inode 目录 磁盘", "文件系统"),
        ("I/O 控制 中断 DMA 通道 缓冲 spooling", "I/O管理"),
        ("临界区 同步 互斥 信号量 PV 管程", "进程同步"),
        ("进程 通信 管道 共享 内存 消息 socket", "进程通信"),
    ]

    search_results = {}
    for query, topic in topic_queries:
        results = vs.search(query=query, course_filter=course_name, top_k=12, boost_key_points=True)
        search_results[topic] = results
        print(f"  {topic}: {len(results)} 条结果")

    print(f"\n[5/5] 生成复习资料...")
    print(f"  已检索 {len(topic_queries)} 个知识领域，每个深度搜索 12 条")
    print(f"  接下来请 AI 基于以上数据生成详细复习提纲")
    print(f"  包含: 概念定义 + 原理流程 + Mermaid 图表 + 对比表格 + 真题例题")
    print(f"\n  >>> 将以上检索结果提供给 AI 即可生成完整复习资料 <<<")

    return {
        "course": course_name,
        "chunks": total,
        "files": len(sources),
        "chapters": len(chapters),
        "key_points": len(key_points),
        "search_results": search_results,
    }


# =====================================================================
# 命令行入口
# =====================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python skills/review_summary.py <课程名>")
        print("示例: python skills/review_summary.py 操作系统")
        sys.exit(1)

    course_name = sys.argv[1]
    result = run_standalone(course_name)
