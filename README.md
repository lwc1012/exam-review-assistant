# 📚 Exam Review Assistant — 期末复习助手（完整版）

> 把 PPT、课本、作业、试卷扔进去，AI 帮你出复习提纲、练习题、模拟卷。
>
> 基于 **MCP 协议**（Model Context Protocol），在 Claude Code / VS Code 里直接对话就能用。

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-orange)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🤔 这玩意儿能干什么？

期末考试前，你有一堆资料：老师 PPT、课本 PDF、平时作业、往年试卷…… 这个工具帮你：

1. **导入**所有资料（PPT/PDF/Word/图片），自动识别章节和内容
2. **检索**任意知识点，秒级定位到 PPT 原文、课本摘录
3. **标记**老师划的重点，搜索时自动加权靠前
4. **管理**题库（选择题/计算题/证明题…），支持按来源、难度、章节筛选
5. 配合 AI **生成**复习提纲、变体练习题、模拟试卷

**一句话：把资料扔进去，告诉 AI 你想要什么，剩下的它来干。**

---

## 🧠 MCP 是什么？

MCP（Model Context Protocol）是 Anthropic 发布的开放协议，让 AI 模型能**直接调用你电脑上的工具**。就像给 AI 装了一只手，它能自己翻你的资料、搜你的题库。

```
你在 IDE 里说：「帮我生成操作系统的复习提纲」
    ↓
AI 自动调用 MCP 工具：
  ① get_course_overview("操作系统")        ← 看看有哪些资料
  ② search_knowledge("进程调度算法")         ← 检索第2章
  ③ search_knowledge("死锁银行家算法")       ← 检索第3章
  ④ get_key_points("操作系统")             ← 提取老师划的重点
  ⑤ get_questions("操作系统", source="往年期末") ← 匹配历年考题
    ↓
AI 综合所有数据 → 生成一份结构化的复习提纲（含 Mermaid 流程图）
```

---

## 🚀 5 分钟上手

### 第 0 步：你需要有

- **Python 3.10 或以上** — [python.org 下载](https://www.python.org/downloads/)（安装时勾选 ✅ "Add Python to PATH"）
- **一个支持 MCP 的 AI 工具**（任选一个）：
  - [Claude Code](https://claude.ai/code)（推荐，零配置）
  - VS Code + MCP 插件
  - Claude Desktop

打开终端验证：

```bash
python --version   # 应该显示 3.10 或以上
```

### 第 1 步：下载项目

```bash
git clone https://github.com/lwc1012/exam-review-assistant.git
cd exam-review-assistant
pip install -r requirements.txt
```

> 💡 `git clone` 报错？点 GitHub 上的绿色 **Code** 按钮 → **Download ZIP**，解压后进目录。

### 第 2 步：连接 AI 工具

MCP Server 需要配合支持 MCP 的 AI 工具使用。选一个你已经在用的：

| 方式 | 工具名 | 怎么安装 | 配置文件 |
|------|--------|----------|----------|
| **推荐** | **Claude Code**（Anthropic 官方） | VS Code 按 `Ctrl+Shift+X`，搜索 **Claude Code**（2M+ 安装） | 项目根目录创建 `.mcp.json` |
| 方案 B | **GitHub Copilot Chat**（Microsoft） | VS Code 按 `Ctrl+Shift+X`，搜索 **GitHub Copilot Chat**（需 Copilot 订阅） | 项目根目录创建 `.vscode/mcp.json` |
| 方案 C | **Claude Code CLI**（终端版） | `npm install -g @anthropic-ai/claude-code`（需 Node 18+） | 项目根目录创建 `.mcp.json` |

在项目根目录创建配置文件（以 Claude Code 为例）：

```json
{
  "mcpServers": {
    "exam-review-assistant": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "你解压的完整路径/exam-review-assistant"
    }
  }
}
```

> 🔧 `python` 命令不行就换成完整路径，如 `C:/Users/你的用户名/AppData/Local/Programs/Python/Python312/python.exe`

**重启** VS Code / AI 工具，看到工具列表出现即成功。

### 第 3 步：整理资料

把一门课的资料按类型放到文件夹里：

```
📁 操作系统/
├── 📁 ppt/             ← 课件 (.ppt/.pptx)
├── 📁 课本/            ← 教材 (.pdf)
├── 📁 作业题/          ← 平时作业 (.docx/.pdf)
├── 📁 往年题/          ← 历年试卷 (.pdf/.docx)
└── 📁 个人笔记/         ← 你的笔记 (.txt/.md/.docx)
```

> 📌 至少要有 `ppt` 和 `往年题` 两个文件夹，效果最好。子文件夹名中英文都行。

### 第 4 步：导入资料

```bash
python import_materials.py "你的资料路径/操作系统" "操作系统"
```

看到 `导入完成!` 就 OK 了。

### 第 5 步：开始对话！

在 Claude Code / VS Code 的 AI 对话中直接说：

| 对话内容 | 效果 |
|----------|------|
| "帮我生成操作系统的复习提纲" | AI 检索所有资料 → 生成详细复习文档 |
| "生成第三章的变体练习题" | AI 提取该章题目 → 生成同类变体题（含答案+解析） |
| "出一份操作系统期末模拟卷" | AI 分析往年题型分布 → 命题蓝图 → 完整试卷 |
| "搜索死锁的四个必要条件" | AI 调用 search_knowledge 精准定位 PPT/课本原文 |
| "老师划了第三章是重点，标记一下" | AI 调用 mark_key_point 提升该章权重 |
| "把 2024 年期末第 3 题加进去" | AI 调用 add_exam_question 录入题库 |

---

## 🛠 10 个 MCP 工具详解

MCP Server 暴露了 10 个精细控制工具，你也可以在对话中精确操作：

### 📥 数据导入

| 工具 | 参数 | 干什么 |
|------|------|--------|
| `ingest_material` | `file_path`, `course_name`, `is_key_point` | 导入单个文件（PPT/PDF/Word/图片） |
| `import_directory` | `directory_path`, `course_name` | 批量导入整个文件夹 |

### 🔍 知识检索

| 工具 | 参数 | 干什么 |
|------|------|--------|
| `search_knowledge` | `query`, `course_name`, `top_k`, `source_type`, `chapter` | 语义搜索知识点（自动加权重点内容） |
| `get_course_overview` | `course_name` | 查看课程数据全景（文件/章节/题目/重点统计） |
| `get_chapter_list` | `course_name` | 获取章节列表（手动+自动识别） |

### ⭐ 重点管理

| 工具 | 参数 | 干什么 |
|------|------|--------|
| `mark_key_point` | `course_name`, `content`, `chapter_title`, `source` | 标记老师划的重点（搜索时自动靠前） |
| `get_key_points` | `course_name` | 查询所有已标记的重点 |

### 📝 题目管理

| 工具 | 参数 | 干什么 |
|------|------|--------|
| `add_exam_question` | `course_name`, `question`, `answer`, `q_type`, `chapter_title`, `difficulty`, `source`, `tags` | 添加一道题目 |
| `get_questions` | `course_name`, `q_type`, `chapter_title`, `source`, `difficulty`, `limit` | 按条件筛选题目 |
| `get_question_stats` | `course_name` | 题目统计分析（题型/来源/难度分布） |

---

## 📂 项目结构

```
exam-review-assistant/
├── import_materials.py            ← 一键导入资料
├── md2docx.py                     ← Markdown → Word 转换
├── requirements.txt               ← Python 依赖
├── CLAUDE.md                      ← Claude Code 自动读取
├── README.md                      ← 你在看的这个文件
│
├── mcp_server/                    ← MCP Server（底层引擎）
│   ├── server.py                  ←   主入口，10 个 MCP 工具
│   ├── document_parser.py         ←   PPT/PDF/DOCX/图片解析
│   ├── embedding.py               ←   TF-IDF 文本向量化
│   ├── vector_store.py            ←   numpy 向量存储 + 搜索
│   └── metadata_store.py          ←   SQLite 题库/重点管理
│
├── skills/                        ← 一键生成 Skill
│   ├── review_summary.py          ←   复习提纲
│   ├── generate_practice.py       ←   变体练习题
│   └── mock_exam.py               ←   模拟试卷
│
└── data/                          ← 运行时数据（自动生成）
    ├── courses/                   ←   课程向量数据
    ├── metadata.db                ←   题库/重点数据库
    └── tfidf_vectorizer.json      ←   TF-IDF 模型
```

---

## 🔧 遇到问题？

### Python 版本不对

```bash
python --version   # 必须是 3.10 或以上
```

如果显示 3.8 或 3.9，去 [python.org](https://www.python.org/downloads/) 下载最新版，安装时勾选 "Add Python to PATH"。

### MCP 配置后工具没出现

1. 确认 `pip install mcp` 已执行
2. 确认 `.claude/mcp.json` 里的 `cwd` 路径是**完整绝对路径**
3. 确认路径里没有中文乱码
4. **重启** Claude Code / VS Code

### 文件导入失败

| 问题 | 解决 |
|------|------|
| `.doc` 格式 | 用 Word 打开 → 另存为 `.docx` |
| PDF 是扫描版（图片） | `pip install paddlepaddle paddleocr` |
| 图片不清晰 | 先用微信/QQ 截图识字转成文本 |

### 搜索不到内容

1. 确认资料已导入（运行 `import_materials.py` 看到 "导入完成"）
2. 安装 jieba 提升中文搜索精度：`pip install jieba`
3. 尝试更宽泛的搜索词

### 想用自己的 Python 程序调用？

参考 [mcp_llm_client.py](mcp_llm_client.py) — 一个通用的 MCP + LLM 集成客户端：

```python
from mcp_llm_client import MCPClient

mcp = MCPClient("mcp_server/server.py")
mcp.start()

# 获取工具
tools = mcp.to_openai_tools()  # OpenAI 格式
tools = mcp.to_anthropic_tools()  # Anthropic 格式

# 调用工具
result = mcp.call_tool("search_knowledge", {
    "query": "死锁",
    "course_name": "操作系统"
})

mcp.close()
```

---

## ❓ 常见问题

**Q: 和独立版有什么区别？**
A: 完整版多了 10 个细粒度 MCP 工具 + Skill 一键生成，适合在 IDE 里精细控制每一步。独立版只有 3 个高级工具，适合命令行一把梭。

**Q: 要联网吗？我的资料会被上传吗？**
A: 不需要。所有数据都在你电脑的 `data/` 目录里。TF-IDF 向量化也是本地计算。只有当你用 AI 对话时，AI 工具（Claude/GPT）会收到检索结果。

**Q: 能同时处理多门课吗？**
A: 能。每门课一个文件夹，分别 `import_materials.py` 导入，数据自动按课程名隔离。

**Q: 需要 GPU 吗？**
A: 不需要。纯 CPU 运行，普通笔记本就能跑。

**Q: 支持哪些文件格式？**
A: `.ppt/.pptx`（课件）、`.pdf`（电子版+扫描版）、`.docx`（Word）、`.txt/.md`（文本）、`.png/.jpg/.bmp/.tiff`（图片OCR）。

---

## 📄 License

MIT
