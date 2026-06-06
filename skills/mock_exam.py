"""
模拟试卷生成 Skill — /mock-exam

用法：
    /mock-exam <课程名>                                  → MCP Skill 模式
    python skills/mock_exam.py <课程名>                   → 独立运行模式
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcp_server.vector_store import VectorStore
from mcp_server.metadata_store import MetadataStore


SKILL_INSTRUCTION = """
你是一个专业的大学考试命题专家。用户当前正在使用 /mock-exam 命令。

## 核心原则
1. **题型严格匹配**：基于 get_question_stats 返回的实际数据确定题型/数量/分值
2. **题目全新**：所有题目不能与题库中任何原题重复
3. **重点覆盖**：get_key_points 中标记的重点章节出题量翻倍
4. **难度梯度**：从易到难排列（名词解释→选择→简答→计算→综合/PV）
5. **完整配套**：答题卡 + 答案 + 评分标准 + 知识点覆盖表
6. **多格式输出**：生成 .md 后运行 md2docx.py 转 .docx

## 执行步骤
### Step 1：get_question_stats(course_name="{课程名}") — 确定题型/数量/分值
### Step 2：get_key_points(course_name="{课程名}") — 重点章节出题加权
### Step 3：get_questions(course_name="{课程名}", source="往年期末") — 参考结构，避免重复
### Step 4：get_chapter_list(course_name="{课程名}") — 知识点覆盖
### Step 5：逐题型命题（名词解释/选择/简答/计算/综合）
### Step 6：生成配套材料（答题卡+答案+评分标准+知识点覆盖表）
"""


def run_standalone(course_name: str):
    """
    独立运行 — 直接读取题库分析往年试卷结构，给出命题蓝图。
    """
    vs = VectorStore()
    ms = MetadataStore()

    print(f"课程: {course_name}")
    print(f"{'='*50}")

    course = ms.get_course(course_name)
    if not course:
        print(f"[ERROR] 课程 '{course_name}' 不存在，请先导入资料")
        return None

    cid = course["id"]

    # 1. 题型分析
    print(f"\n[1/5] 题型分布...")
    q_types = ms.get_question_types(cid)
    source_stats = ms.get_source_stats(cid)
    print(f"  题型: {q_types}")
    print(f"  来源分布:")
    for s in source_stats:
        print(f"    {s['source']} ({s['source_year']}): {s['count']} 题")

    # 2. 重点标记
    print(f"\n[2/5] 重点章节...")
    key_points = ms.get_key_points(cid)
    chapters = ms.get_chapters(cid)
    for ch in chapters:
        if ch["weight"] > 1.0:
            print(f"  {ch['title']}: 权重 {ch['weight']} (重点)")
    print(f"  重点标记: {len(key_points)} 条")

    # 3. 往年期末题参考
    print(f"\n[3/5] 往年期末题参考...")
    finals = ms.get_questions(cid, source="往年期末", limit=50)
    # 统计题型和难度
    type_dist = {}
    diff_dist = {}
    for q in finals:
        qt = q["q_type"]
        d = q["difficulty"]
        type_dist[qt] = type_dist.get(qt, 0) + 1
        diff_dist[d] = diff_dist.get(d, 0) + 1
    print(f"  往年题型分布: {type_dist}")
    print(f"  往年难度分布: {diff_dist}")

    # 4. 搜索各章节的考试热点
    print(f"\n[4/5] 各章节考试热点...")
    chapter_topics = [
        ("进程 PCB 状态 线程", "进程管理"),
        ("CPU 调度 FCFS SJF RR 算法", "处理器调度"),
        ("死锁 银行家 条件 安全 序列", "死锁"),
        ("分页 分段 虚拟 内存 页面 置换", "内存管理"),
        ("文件 系统 FCB inode 磁盘", "文件系统"),
        ("I/O 控制 中断 DMA spooling", "I/O管理"),
        ("同步 互斥 信号量 PV 临界区", "进程同步"),
        ("进程 通信 管道 共享 内存 IPC", "进程通信"),
    ]

    for query, topic in chapter_topics:
        results = vs.search(query=query, course_filter=course_name, top_k=3,
                            source_tag_filter="往年期末", boost_key_points=True)
        if results:
            print(f"  {topic}: 有往年题覆盖 ✓")

    # 5. 确定试卷蓝图
    print(f"\n[5/5] 试卷蓝图...")
    print(f"  试卷总分: 100 分")
    print(f"  建议结构:")
    print(f"    名词解释: 4-5 题 × 4-5 分 = 20 分")
    print(f"    选择题:   10-15 题 × 2 分 = 20-30 分")
    print(f"    简答题:   3-4 题 × 6-8 分 = 24 分")
    print(f"    计算题:   3-4 题 × 7-9 分 = 27-30 分")
    print(f"    综合题:   1 题 × 10 分 = 10 分")
    print(f"\n  配套输出: .md + .docx")
    print(f"  附带: 答题卡 + 答案 + 评分标准 + 知识点覆盖表")
    print(f"\n  >>> 将以上数据提供给 AI 即可生成完整模拟试卷 <<<")

    return {
        "course": course_name,
        "type_distribution": type_dist,
        "difficulty_distribution": diff_dist,
        "key_points": len(key_points),
        "final_count": len(finals),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python skills/mock_exam.py <课程名>")
        print("示例: python skills/mock_exam.py 操作系统")
        sys.exit(1)

    course_name = sys.argv[1]
    run_standalone(course_name)
