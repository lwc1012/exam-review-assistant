"""
变体练习题生成 Skill — /generate-practice

用法：
    /generate-practice <课程名> [章节名]                 → MCP Skill 模式
    python skills/generate_practice.py <课程名> [章节名]  → 独立运行模式
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcp_server.vector_store import VectorStore
from mcp_server.metadata_store import MetadataStore


SKILL_INSTRUCTION = """
你是一个专业的大学课程练习题生成器。用户当前正在使用 /generate-practice 命令。

## 核心原则
1. **全面覆盖**：基于 get_question_stats 分析出的题型分布，每种题型都要出变体题
2. **变体规则**：同知识点、同题型、同难度，数值/场景/参数不同，答案验算正确
3. **完整解析**：每道变体题附带 (1)完整答案 (2)逐步解析 (3)易错点提示
4. **多格式输出**：生成 .md 后用 md2docx.py 转 .docx

## 执行步骤
### Step 1：获取题型分布 — get_question_stats(course_name="{课程名}")
### Step 2：获取原题 — get_questions(course_name="{课程名}", limit=30)
### Step 3：逐题型生成变体题（选择/填空/简答/计算/PV操作）
### Step 4：生成参考答案（完整 + 分步 + 易错提醒）
"""


def run_standalone(course_name: str, chapter: str = None, num_per_type: int = 3):
    """
    独立运行 — 直接读取题库生成变体练习题建议。

    参数
    ----
    course_name : 课程名
    chapter : 章节名（可选，不传则覆盖全部章节）
    num_per_type : 每种题型生成几道变体题
    """
    vs = VectorStore()
    ms = MetadataStore()

    print(f"课程: {course_name}")
    if chapter:
        print(f"章节: {chapter}")
    print(f"{'='*50}")

    course = ms.get_course(course_name)
    if not course:
        print(f"[ERROR] 课程 '{course_name}' 不存在，请先导入资料")
        return None

    cid = course["id"]

    # 1. 题型分布
    print(f"\n[1/4] 题型分布...")
    q_types = ms.get_question_types(cid)
    source_stats = ms.get_source_stats(cid)
    print(f"  已有题型: {q_types}")
    print(f"  来源分布: {source_stats}")

    # 2. 获取原题（按来源分类）
    print(f"\n[2/4] 获取原题...")
    all_questions = {}
    for src in ["作业", "期中考试", "往年期末"]:
        qs = ms.get_questions(cid, source=src, limit=30)
        if qs:
            all_questions[src] = qs
            print(f"  {src}: {len(qs)} 道")

    # 3. 按题型分组
    print(f"\n[3/4] 题型分析...")
    questions_by_type = {}
    for src, qs in all_questions.items():
        for q in qs:
            qt = q["q_type"]
            if qt not in questions_by_type:
                questions_by_type[qt] = []
            questions_by_type[qt].append(q)

    for qt, qs in questions_by_type.items():
        print(f"  {qt}: {len(qs)} 道原题")

    # 4. 为每种题型提供变体建议
    print(f"\n[4/4] 变体建议...")
    print(f"  每种题型可生成 {num_per_type} 道变体题")
    print(f"  变体原则: 同知识点、同难度、不同数值/场景")
    print(f"  输出: .md（详细版）+ .docx（打印版）")
    print(f"\n  >>> 将以上原题提供给 AI 即可生成对应变体练习题 <<<")

    return {
        "course": course_name,
        "types": q_types,
        "questions_by_type": {qt: len(qs) for qt, qs in questions_by_type.items()},
        "all_questions": all_questions,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python skills/generate_practice.py <课程名> [章节名] [数量]")
        print("示例: python skills/generate_practice.py 操作系统 第三章 5")
        sys.exit(1)

    course_name = sys.argv[1]
    chapter = sys.argv[2] if len(sys.argv) > 2 else None
    num = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    run_standalone(course_name, chapter, num)
