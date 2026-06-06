# 期末复习助手 — Claude Code 项目指南

## 项目概述
基于 MCP 协议的智能期末复习工具。导入课程资料（PPT/课本/作业/试卷），
通过 TF-IDF 向量搜索 + AI 推理，自动生成复习提纲、变体练习题和模拟试卷。

## 架构

```
用户 ↔ Claude Code Skill ↔ MCP Server ↔ 数据层
                                 ├── numpy 向量存储（语义搜索）
                                 └── SQLite（结构化数据）
```

---

## 用户偏好（使用 Skill 时自动生效）

### 资料导入
- 推荐目录结构：`{课程名}/ppt/` `{课程名}/课本/` `{课程名}/作业题/` `{课程名}/往年题/` `{课程名}/个人笔记/`
- 子文件夹自动识别为来源标签
- 导入命令：`python import_materials.py "资料路径" "课程名"`

### 复习资料生成标准
1. **深度内容**：每个知识点 top_k>=12 条深度检索，提取 PPT 完整教学内容
2. **流程图**：流程类知识必须附带 Mermaid 图表（stateDiagram/flowchart/sequenceDiagram）
3. **多格式**：先生成 .md（含流程图），再运行 `python md2docx.py {文件}` 转 .docx
4. **练习题**：覆盖所有题型，每题附带完整答案 + 分步解析 + 易错提醒
5. **模拟卷**：题型比例与往年一致，附带答题卡 + 答案 + 评分标准 + 知识点覆盖表

### 工作时使用的 Python
- 使用项目中的 `python` 或系统默认 Python 3.10+
- 命令在 `exam_review_assistant/` 目录下执行

---

## 关键文件

- [mcp_server/server.py](mcp_server/server.py) — MCP Server 主入口，10个工具
- [mcp_server/document_parser.py](mcp_server/document_parser.py) — 文档解析（PPT/PDF/DOCX/OCR）
- [mcp_server/vector_store.py](mcp_server/vector_store.py) — numpy 向量存储
- [mcp_server/metadata_store.py](mcp_server/metadata_store.py) — SQLite 元数据管理
- [mcp_server/embedding.py](mcp_server/embedding.py) — TF-IDF 向量化
- [skills/review_summary.py](skills/review_summary.py) — 复习提纲 Skill
- [skills/generate_practice.py](skills/generate_practice.py) — 变体练习 Skill
- [skills/mock_exam.py](skills/mock_exam.py) — 模拟试卷 Skill
- [import_materials.py](import_materials.py) — 一键导入脚本
- [md2docx.py](md2docx.py) — Markdown → Word 转换工具

## 常用命令

```bash
# 导入资料
python import_materials.py "D:/课程资料/操作系统" "操作系统"

# Markdown → Word 转换
python md2docx.py 操作系统_详细复习资料.md

# 启动 MCP Server
python -m mcp_server.server
```

## 编码规范
- Python 3.10+ 兼容
- 所有 MCP 工具返回 JSON 字符串
- 文档解析输出统一的 ParsedChunk 结构
- 错误处理：捕获具体异常，返回 { "error": "..." } JSON
- 输出避免 GBK 不兼容的 Unicode 字符
