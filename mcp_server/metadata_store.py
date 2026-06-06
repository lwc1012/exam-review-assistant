"""
SQLite 元数据存储 — 结构化数据管理

表结构：
  ┌─ courses        课程信息
  ├─ chapters       章节/知识点层级
  ├─ key_points     老师划的重点标记
  ├─ exam_questions 题目库（作业、期中考、往年期末）
  └─ practice_log   刷题记录（错题本）
"""

import os
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from contextlib import contextmanager


DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "metadata.db"
)


class MetadataStore:
    """SQLite 元数据管理"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接（自动提交/关闭）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """创建表结构"""
        with self._get_conn() as conn:
            conn.executescript("""
                -- 课程表
                CREATE TABLE IF NOT EXISTS courses (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL UNIQUE,          -- 课程名称，如"高等数学"
                    semester    TEXT,                           -- 学期，如"2025春"
                    teacher     TEXT,                           -- 授课老师
                    created_at  TEXT DEFAULT (datetime('now'))
                );

                -- 章节/知识点表
                CREATE TABLE IF NOT EXISTS chapters (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id   INTEGER NOT NULL,
                    parent_id   INTEGER,                        -- 父章节（支持层级）
                    title       TEXT NOT NULL,                  -- 章节标题
                    description TEXT,                           -- 章节简介
                    weight      REAL DEFAULT 1.0,               -- 重要性权重（重点=3.0）
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_id) REFERENCES chapters(id) ON DELETE SET NULL
                );

                -- 重点标记表（老师划的重点）
                CREATE TABLE IF NOT EXISTS key_points (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id   INTEGER NOT NULL,
                    chapter_id  INTEGER,                        -- 关联章节
                    content     TEXT NOT NULL,                  -- 重点内容描述
                    source      TEXT,                           -- 来源（老师口述/PPT标注/word文档）
                    created_at  TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
                );

                -- 题目库
                CREATE TABLE IF NOT EXISTS exam_questions (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id   INTEGER NOT NULL,
                    chapter_id  INTEGER,                        -- 关联章节
                    q_type      TEXT NOT NULL,                  -- 题型（选择题/填空题/计算题/证明题/简答题）
                    question    TEXT NOT NULL,                  -- 题干
                    answer      TEXT,                           -- 答案/解析
                    difficulty  INTEGER DEFAULT 3,              -- 难度 1-5
                    source      TEXT,                           -- 来源（作业/期中考试/往年期末）
                    source_year TEXT,                           -- 来源年份
                    tags        TEXT,                           -- 标签（逗号分隔）
                    created_at  TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
                );

                -- 刷题记录（错题本）
                CREATE TABLE IF NOT EXISTS practice_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    is_correct  INTEGER DEFAULT 0,              -- 0=错, 1=对
                    user_answer TEXT,                           -- 用户作答
                    practiced_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (question_id) REFERENCES exam_questions(id) ON DELETE CASCADE
                );

                -- 索引
                CREATE INDEX IF NOT EXISTS idx_chapters_course ON chapters(course_id);
                CREATE INDEX IF NOT EXISTS idx_questions_course ON exam_questions(course_id);
                CREATE INDEX IF NOT EXISTS idx_questions_type ON exam_questions(q_type);
                CREATE INDEX IF NOT EXISTS idx_keypoints_course ON key_points(course_id);
            """)

    # ------------------------------------------------------------------
    # 课程 CRUD
    # ------------------------------------------------------------------

    def add_course(self, name: str, semester: str = "", teacher: str = "") -> int:
        """添加课程，返回 course_id"""
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO courses (name, semester, teacher) VALUES (?, ?, ?)",
                (name, semester, teacher)
            )
            if cur.lastrowid:
                return cur.lastrowid
            # 已存在，返回已有 ID
            row = conn.execute(
                "SELECT id FROM courses WHERE name = ?", (name,)
            ).fetchone()
            return row["id"] if row else 0

    def get_course(self, name: str) -> Optional[dict]:
        """按名称查询课程"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM courses WHERE name = ?", (name,)
            ).fetchone()
            return dict(row) if row else None

    def list_courses(self) -> List[dict]:
        """列出所有课程"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM courses ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # 章节 CRUD
    # ------------------------------------------------------------------

    def add_chapter(
        self, course_id: int, title: str,
        parent_id: int = None, description: str = "", weight: float = 1.0
    ) -> int:
        """添加章节/知识点"""
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO chapters (course_id, parent_id, title, description, weight) "
                "VALUES (?, ?, ?, ?, ?)",
                (course_id, parent_id, title, description, weight)
            )
            return cur.lastrowid

    def get_chapters(self, course_id: int) -> List[dict]:
        """获取课程的所有章节（树形结构）"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM chapters WHERE course_id = ? ORDER BY id",
                (course_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def update_chapter_weight(self, chapter_id: int, weight: float) -> None:
        """更新章节权重（标记重点时用）"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE chapters SET weight = ? WHERE id = ?",
                (weight, chapter_id)
            )

    # ------------------------------------------------------------------
    # 重点标记
    # ------------------------------------------------------------------

    def add_key_point(
        self, course_id: int, content: str,
        chapter_id: int = None, source: str = ""
    ) -> int:
        """
        添加重点标记。
        同时将关联章节的权重提升至 3.0。
        """
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO key_points (course_id, chapter_id, content, source) "
                "VALUES (?, ?, ?, ?)",
                (course_id, chapter_id, content, source)
            )
            if chapter_id:
                conn.execute(
                    "UPDATE chapters SET weight = 3.0 WHERE id = ?",
                    (chapter_id,)
                )
            return cur.lastrowid

    def get_key_points(self, course_id: int) -> List[dict]:
        """获取课程所有重点"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT kp.*, ch.title as chapter_title "
                "FROM key_points kp "
                "LEFT JOIN chapters ch ON kp.chapter_id = ch.id "
                "WHERE kp.course_id = ? "
                "ORDER BY kp.created_at DESC",
                (course_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # 题目管理
    # ------------------------------------------------------------------

    def add_question(
        self,
        course_id: int,
        q_type: str,
        question: str,
        answer: str = "",
        chapter_id: int = None,
        difficulty: int = 3,
        source: str = "",
        source_year: str = "",
        tags: str = "",
    ) -> int:
        """添加题目"""
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO exam_questions "
                "(course_id, chapter_id, q_type, question, answer, difficulty, source, source_year, tags) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (course_id, chapter_id, q_type, question, answer, difficulty,
                 source, source_year, tags)
            )
            return cur.lastrowid

    def get_questions(
        self,
        course_id: int,
        q_type: str = None,
        chapter_id: int = None,
        source: str = None,
        difficulty: int = None,
        limit: int = 50,
    ) -> List[dict]:
        """查询题目（支持多条件过滤）"""
        with self._get_conn() as conn:
            sql = "SELECT eq.*, ch.title as chapter_title FROM exam_questions eq " \
                  "LEFT JOIN chapters ch ON eq.chapter_id = ch.id " \
                  "WHERE eq.course_id = ?"
            params = [course_id]

            if q_type:
                sql += " AND eq.q_type = ?"
                params.append(q_type)
            if chapter_id is not None:
                sql += " AND eq.chapter_id = ?"
                params.append(chapter_id)
            if source:
                sql += " AND eq.source = ?"
                params.append(source)
            if difficulty is not None:
                sql += " AND eq.difficulty = ?"
                params.append(difficulty)

            sql += " ORDER BY eq.id LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def get_question_types(self, course_id: int) -> List[str]:
        """获取课程的题目类型分布"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT q_type FROM exam_questions WHERE course_id = ?",
                (course_id,)
            ).fetchall()
            return [r["q_type"] for r in rows]

    def get_source_stats(self, course_id: int) -> List[dict]:
        """按来源统计题目数量"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT source, source_year, COUNT(*) as count "
                "FROM exam_questions WHERE course_id = ? "
                "GROUP BY source, source_year ORDER BY source_year DESC",
                (course_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # 刷题记录
    # ------------------------------------------------------------------

    def log_practice(self, question_id: int, is_correct: bool, user_answer: str = "") -> int:
        """记录一次刷题"""
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO practice_log (question_id, is_correct, user_answer) "
                "VALUES (?, ?, ?)",
                (question_id, 1 if is_correct else 0, user_answer)
            )
            return cur.lastrowid

    def get_wrong_questions(self, course_id: int, limit: int = 50) -> List[dict]:
        """获取错题列表"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT eq.*, ch.title as chapter_title, pl.practiced_at as last_practice "
                "FROM practice_log pl "
                "JOIN exam_questions eq ON pl.question_id = eq.id "
                "LEFT JOIN chapters ch ON eq.chapter_id = ch.id "
                "WHERE eq.course_id = ? AND pl.is_correct = 0 "
                "ORDER BY pl.practiced_at DESC LIMIT ?",
                (course_id, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self, course_id: int) -> dict:
        """获取课程的练习统计"""
        with self._get_conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as c FROM practice_log pl "
                "JOIN exam_questions eq ON pl.question_id = eq.id "
                "WHERE eq.course_id = ?", (course_id,)
            ).fetchone()["c"]

            correct = conn.execute(
                "SELECT COUNT(*) as c FROM practice_log pl "
                "JOIN exam_questions eq ON pl.question_id = eq.id "
                "WHERE eq.course_id = ? AND pl.is_correct = 1", (course_id,)
            ).fetchone()["c"]

            return {
                "total_practice": total,
                "correct": correct,
                "wrong": total - correct,
                "accuracy": round(correct / max(total, 1) * 100, 1),
            }
