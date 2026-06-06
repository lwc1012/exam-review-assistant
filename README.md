# 📚 Exam Review Assistant（完整版）

> 基于 MCP 协议的智能期末复习工具  
> 在 IDE 里对话就能出复习提纲、变体练习题、模拟卷

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-1.0+-orange)](https://modelcontextprotocol.io/)

---

## 🚀 5 分钟快速上手

### 前提条件

- [ ] **Python 3.10+**（终端输入 `python --version` 检查）
- [ ] **Git**（终端输入 `git --version` 检查）
- [ ] **Claude Code** 或 支持 MCP 的 VS Code 插件

### 第 1 步：下载安装

```bash
git clone https://github.com/lwc1012/exam-review-assistant.git
cd exam-review-assistant
pip install -r requirements.txt
```

> 📌 `git clone` 报错的话，点 GitHub 上绿色 "Code" 按钮 → Download ZIP，解压后进入目录。

### 第 2 步：配置到 IDE

在项目根目录创建 `.claude/settings.json`（如果用的是 VS Code MCP 插件，配置方式类似）：

```json
{
  "mcpServers": {
    "exam-review-assistant": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "你解压的路径/exam-review-assistant"
    }
  }
}
```

> 🔧 如果 `python` 命令不行，换成 Python 的完整路径，如 `C:/Python312/python.exe`

重启 Claude Code 或 VS Code，让配置生效。

### 第 3 步：整理资料

把你的课程资料按类型放到一个文件夹里：

```
📁 操作系统/
├── 📁 ppt/          ← 课件 (.ppt/.pptx)
├── 📁 课本/          ← 教材 (.pdf)
├── 📁 作业题/        ← 作业 (.docx/.pdf)
├── 📁 往年题/        ← 历年试卷 (.pdf/.docx)
└── 📁 个人笔记/       ← 你的笔记 (.txt/.md/.docx)
```

### 第 4 步：导入资料

```bash
python import_materials.py "你的资料路径/操作系统" "操作系统"
```

### 第 5 步：在 IDE 里对话

直接在 Claude Code 对话中说：

> "/review-summary 操作系统"

AI 会自动调用 MCP 工具完成：全貌扫描 → 逐章深度检索 → 提取重点 → 匹配题目 → 生成复习资料。

也支持这些命令：

| 命令 | 效果 |
|------|------|
| `/review-summary 操作系统` | 生成详细复习提纲（含流程图 + Word） |
| `/generate-practice 操作系统` | 生成变体练习题（含答案和解析） |
| `/mock-exam 操作系统` | 生成模拟试卷（含答题卡 + 评分标准） |
| "搜索操作系统中进程和线程的区别" | AI 自动调用 search_knowledge |
| "标记第三章中值定理为重点" | AI 自动调用 mark_key_point |
| "往操作系统题库加一道题" | AI 自动调用 add_exam_question |

---

## 🛠 如果你想手动控制每一步

MCP Server 暴露了 10 个工具，除了 Skill 一键生成，你也可以在对话中精细控制：

| 工具 | 干什么用 | 对话示例 |
|------|----------|----------|
| `ingest_material` | 导入单个文件 | "帮我导入这份 PPT" |
| `import_directory` | 批量导入文件夹 | "把操作系统文件夹全部导入" |
| `search_knowledge` | 搜索知识点 | "搜索所有关于死锁的内容" |
| `get_course_overview` | 查看数据概况 | "操作系统导入了多少资料" |
| `get_chapter_list` | 查看章节列表 | "操作系统有哪些章节" |
| `mark_key_point` | 标记重点 | "标记老师说的罗尔定理重点" |
| `get_key_points` | 查看所有重点 | "操作系统有哪些重点标注" |
| `add_exam_question` | 添加题目 | "添加 2024 年期末第 3 题" |
| `get_questions` | 查询题目 | "找出所有往年期末计算题" |
| `get_question_stats` | 题目统计 | "往年题型分布是怎样的" |

---

## 📂 项目文件说明

```
exam-review-assistant/
├── import_materials.py            ← 把资料导入系统
├── md2docx.py                     ← Markdown → Word 转换
├── requirements.txt               ← Python 依赖清单
├── CLAUDE.md                      ← Claude Code 自动读取的配置
├── LICENSE                        ← MIT 协议
├── README.md                      ← 你现在看的这个文件
│
├── mcp_server/                    ← MCP Server（底层引擎）
│   ├── server.py                  ←   主入口，10 个 MCP 工具
│   ├── document_parser.py         ←   PPT/PDF/DOCX/图片解析
│   ├── embedding.py               ←   TF-IDF 向量化
│   ├── vector_store.py            ←   numpy 向量搜索
│   └── metadata_store.py          ←   SQLite 题库/重点管理
│
├── skills/                        ← 三个 Skill 定义
│   ├── review_summary.py          ←   复习提纲
│   ├── generate_practice.py       ←   变体练习题
│   └── mock_exam.py               ←   模拟试卷
│
└── data/                          ← 运行时生成，不上传 Git
    ├── courses/                   ←   向量数据
    ├── metadata.db                ←   数据库
    └── tfidf_vectorizer.json      ←   搜索模型
```

---

## 🔧 遇到问题

### `'python' 不是内部或外部命令`
Python 没装或没加 PATH。去 [python.org](https://python.org) 下载安装，勾选 "Add Python to PATH"。

### MCP 配置后工具没出现
1. 确认 `pip install mcp` 已执行
2. 确认 `.claude/settings.json` 里的 `cwd` 路径正确
3. 重启 Claude Code

### 文件导入失败
- `.doc` 格式：用 Word 另存为 `.docx`
- PDF 扫描件：安装 `pip install paddlepaddle paddleocr`
- 图片：安装 PaddleOCR 获取文字

### 搜索不到内容
- 确认资料已导入（运行 `import_materials.py` 看到 "导入完成"）
- 安装 jieba：`pip install jieba`

---

## 📄 License

MIT
