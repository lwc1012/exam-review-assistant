# 📚 期末复习助手 — Exam Review Assistant

> 基于 MCP 协议 + 向量检索的智能期末复习工具  
> 把 PPT、课本、作业、试卷扔进去 → 自动出复习提纲、变体练习题、模拟卷

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-1.0+-orange)](https://modelcontextprotocol.io/)

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📥 一键导入 | 放入 PPT/PDF/DOCX/TXT/图片，自动解析、向量化、分类 |
| 🔍 语义搜索 | 用自然语言搜索课程知识库，精准定位到 PPT 页码 |
| ⭐ 重点标记 | 标注老师划的重点，搜索时自动加权 |
| 📋 复习提纲 | 按章节生成详细知识点 + 流程图 + 经典例题 |
| ✏️ 变体练习 | 基于原题生成同知识点新题（改数值/改场景） |
| 📝 模拟试卷 | 按往年题型比例出卷，附答案 + 评分标准 + 知识点覆盖表 |
| 📄 多格式 | 同时输出 Markdown（带 Mermaid 流程图）和 Word(.docx) |

## 🏗 架构

```
┌────────────────────────────────────────────┐
│  Claude Code / VS Code MCP Host            │
│  /review-summary  /generate-practice  ...  │  ← Skill 层
└──────────────┬─────────────────────────────┘
               │ MCP 协议
┌──────────────▼─────────────────────────────┐
│  MCP Server (10 个工具)                     │  ← 数据层
│  ┌──────────┬───────────┬────────────────┐ │
│  │ 文档解析  │ TF-IDF    │ numpy 向量存储  │ │
│  │ PPT/PDF   │ 向量化    │ 余弦相似度搜索  │ │
│  │ DOCX/OCR  │           │                │ │
│  └──────────┴───────────┴────────────────┘ │
│  ┌──────────────────────────────────────┐   │
│  │ SQLite 元数据（课程/章节/重点/题库） │    │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 环境要求

- Python **3.10+**（推荐 3.12）
- Windows / macOS / Linux
- 无需 GPU，纯 CPU 即可运行

### 2. 安装

```bash
git clone https://github.com/lwc1012/exam-review-assistant.git
cd exam-review-assistant

# 安装依赖
pip install -r requirements.txt

# （可选）提升中文分词精度
pip install jieba
```

### 3. 准备资料

把你的课程资料按以下结构放到任意位置：

```
你的资料目录/
└── 高等数学/              ← 文件夹名 = 课程名
    ├── ppt/               ← 老师课件（.ppt/.pptx）
    │   ├── 第一章.pptx
    │   └── 第二章.pptx
    ├── 课本/               ← 教材（.pdf）
    │   └── 高等数学上册.pdf
    ├── 作业题/             ← 平时作业（.pdf/.docx）
    │   └── 作业汇总.docx
    ├── 往年题/             ← 历年试卷（.pdf/.docx）
    │   ├── 2023期末.pdf
    │   └── 2024期末.docx
    └── 个人笔记/           ← 你的笔记（.txt/.md/.docx）
        └── 复习笔记.docx
```

> 子文件夹名可中文可英文，程序会自动识别并打上来源标签。

### 4. 导入资料

```bash
python import_materials.py "你的资料目录/高等数学" "高等数学"
```

输出示例：
```
课程: 高等数学
[1/4] 扫描文件... 发现 35 个文件
[2/4] 解析文件...
  [PPT] [PPT课件] ppt/第一章.pptx (52 chunks)
  [TXT] [课本] 课本/教材.pdf (120 chunks)
  ...
[3/4] 向量化存储... 存储完成: 1500 个向量块
[4/4] 创建课程结构... 自动识别 5 个章节
导入完成!
```

### 5. 使用 Skill

在 Claude Code 或支持 MCP 的 AI 对话中：

| 命令 | 效果 |
|------|------|
| `/review-summary 高等数学` | 生成详细复习提纲（含流程图） |
| `/generate-practice 高等数学` | 生成各题型的变体练习题 |
| `/mock-exam 高等数学` | 生成完整模拟试卷 |

### 6. 格式转换

```bash
# Markdown → Word 文档
python md2docx.py 复习资料.md
```

---

## 🔌 配置到 Claude Code

在项目根目录的 `.claude/settings.json` 中添加：

```json
{
  "mcpServers": {
    "exam-review-assistant": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "你的路径/exam-review-assistant"
    }
  }
}
```

> 也可以用 `python` 的全路径，如 `"C:/Python312/python.exe"`

---

## 📂 项目结构

```
exam-review-assistant/
├── mcp_server/                # MCP Server（数据层）
│   ├── server.py              #   主入口，10 个 MCP 工具
│   ├── document_parser.py     #   文档解析（PPT/PDF/DOCX/图片/文本）
│   ├── embedding.py           #   TF-IDF 向量化引擎
│   ├── vector_store.py        #   numpy 向量存储 + 余弦搜索
│   └── metadata_store.py      #   SQLite 结构化数据（课程/章节/重点/题库）
├── skills/                    # Skill 定义（业务层）
│   ├── review_summary.py      #   复习提纲 Skill
│   ├── generate_practice.py   #   变体练习题 Skill
│   └── mock_exam.py           #   模拟试卷 Skill
├── import_materials.py        # 一键导入脚本
├── md2docx.py                 # Markdown → Word 转换
├── requirements.txt           # 依赖清单
├── .gitignore                 # Git 忽略规则
├── CLAUDE.md                  # Claude Code 项目指南
├── README.md                  # 本文件
├── LICENSE                    # 开源协议
└── data/                      # （运行时生成，不上传 Git）
    ├── chroma_db/             # 向量数据库
    ├── metadata.db            # SQLite 数据库
    ├── courses/               # 课程向量数据
    ├── model_cache/           # 模型缓存
    └── materials/             # 原始资料
```

---

## 🛠 MCP 工具列表

| 工具 | 分类 | 功能 |
|------|------|------|
| `ingest_material` | 导入 | 导入单份资料文件 |
| `import_directory` | 导入 | 批量导入目录 |
| `search_knowledge` | 检索 | 语义搜索知识点 |
| `get_course_overview` | 检索 | 课程数据概览 |
| `get_chapter_list` | 检索 | 章节/知识点列表 |
| `mark_key_point` | 重点 | 标记老师划的重点 |
| `get_key_points` | 重点 | 查询已标记重点 |
| `add_exam_question` | 题库 | 添加题目 |
| `get_questions` | 题库 | 按条件查询题目 |
| `get_question_stats` | 题库 | 题目统计分布 |

---

## 🎓 支持的文件格式

| 格式 | 解析引擎 | 适用场景 |
|------|----------|----------|
| `.ppt` / `.pptx` | python-pptx | 老师课件 |
| `.pdf`（电子版） | PyMuPDF (fitz) | 电子课本、电子试卷 |
| `.pdf`（扫描件） | pdfplumber + PaddleOCR | 扫描版试卷 |
| `.docx` | python-docx | 复习提纲、习题集 |
| `.doc` | 需要先转为 .docx | 旧版 Word |
| `.png` / `.jpg` 等 | PaddleOCR + OpenCV | 手机拍的板书/笔记 |
| `.txt` / `.md` | 直接读取 | 自己整理的笔记 |

---

## 💡 常见问题

### Q: 为什么用 TF-IDF 而不是深度学习模型？
A: 纯 numpy 实现，零额外依赖，32位 Windows 也能跑。对课程知识检索场景（专业术语、概念名）效果足够好，不需要 GPU。

### Q: 能支持其他语言吗？
A: 目前中文搜中文效果最好。英文教材也能解析和搜索，TF-IDF 对英文分词天然友好。

### Q: 资料太多会不会慢？
A: 几千个文档块以内秒级响应。如果上万块，可以考虑改为 ChromaDB 或 FAISS（见 vector_store.py 注释）。

### Q: 怎么添加新课程？
A: 把新课程资料放到对应文件夹，再跑一次 `python import_materials.py "路径" "课程名"`，数据自动隔离。

### Q: .doc 格式不支持？
A: 旧版 .doc 需要先在 Word 中另存为 .docx，或者安装 `antiword`/`libreoffice` 做命令行转换。

---

## 🤝 贡献

欢迎提 Issue 和 PR！特别需要的贡献方向：

- [ ] 接入 ChromaDB / Milvus 作为可选的向量后端
- [ ] 接入 sentence-transformers / m3e 作为可选的 Embedding 后端
- [ ] Web UI 界面
- [ ] 支持更多文件格式（.epub、网页等）
- [ ] 公式 OCR 支持（LaTeX-OCR / Mathpix）

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)
