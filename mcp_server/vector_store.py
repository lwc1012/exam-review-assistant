"""
NumPy 向量存储 — 语义搜索核心（32位 Windows 兼容）

替代 ChromaDB，使用纯 numpy + JSON 实现：
  - 向量矩阵存储为 .npy 文件
  - 元数据存储为 .json 文件
  - 搜索使用 numpy 矩阵乘法（高效余弦相似度）
  - 支持：按课程隔离、按文件类型/章节过滤、重点加权

适用规模：数千 ~ 数万文档块（课设/毕设级别完全够用）
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Dict

import numpy as np

from .document_parser import ParsedChunk
from .embedding import get_embedding_model


DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data"
)


class VectorStore:
    """
    NumPy 向量存储 — API 兼容原 ChromaDB 版本。
    数据按课程分文件存储。
    """

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # 路径工具
    # ------------------------------------------------------------------

    def _course_path(self, course_name: str) -> str:
        """返回课程数据的目录路径"""
        safe_name = course_name.replace("/", "_").replace("\\", "_")
        return os.path.join(self.data_dir, "courses", safe_name)

    def _vectors_path(self, course_name: str) -> str:
        return os.path.join(self._course_path(course_name), "vectors.npy")

    def _metadata_path(self, course_name: str) -> str:
        return os.path.join(self._course_path(course_name), "metadata.json")

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def add_chunks(
        self,
        chunks: List[ParsedChunk],
        course_name: str = "default",
        batch_size: int = 32,
    ) -> int:
        """
        将文档块向量化并持久化存储。
        如果向量化器未拟合，先在整个文档集上拟合。
        """
        emb_model = get_embedding_model()

        # 如果向量化器未拟合，先拟合
        if not emb_model._vectorizer.is_fitted:
            all_texts = [c.text for c in chunks]
            # 同时加载已有文档用于拟合（如果有）
            existing = self.get_all(course_name)
            if existing:
                all_texts = [e["text"] for e in existing] + all_texts
            emb_model.fit_on_documents(all_texts)

        course_dir = self._course_path(course_name)
        os.makedirs(course_dir, exist_ok=True)

        # 加载已有数据（追加模式）
        existing_vectors = None
        existing_metadata = []
        if os.path.exists(self._vectors_path(course_name)):
            existing_vectors = np.load(self._vectors_path(course_name))
        if os.path.exists(self._metadata_path(course_name)):
            with open(self._metadata_path(course_name), "r", encoding="utf-8") as f:
                existing_metadata = json.load(f)

        # 向量化新数据
        texts = [c.text for c in chunks]
        new_vectors = emb_model.encode(texts)

        # 构造元数据
        new_metadata = []
        start_idx = len(existing_metadata)
        for j, chunk in enumerate(chunks):
            new_metadata.append({
                "id": f"{course_name}_{chunk.source_file}_{start_idx + j}",
                "source_file": chunk.source_file,
                "source_type": chunk.source_type,
                "source_tag": chunk.extra_metadata.get("source_tag", ""),
                "relative_path": chunk.extra_metadata.get("relative_path", ""),
                "page_number": chunk.page_number or 0,
                "slide_number": chunk.slide_number or 0,
                "chapter_hint": chunk.chapter_hint or "",
                "is_key_point": chunk.is_key_point,
                "course": course_name,
                "text": chunk.text,
                "text_preview": chunk.text[:200],
            })

        # 合并并保存
        if existing_vectors is not None:
            all_vectors = np.vstack([existing_vectors, new_vectors])
        else:
            all_vectors = new_vectors

        all_metadata = existing_metadata + new_metadata

        np.save(self._vectors_path(course_name), all_vectors)
        with open(self._metadata_path(course_name), "w", encoding="utf-8") as f:
            json.dump(all_metadata, f, ensure_ascii=False, indent=2)

        return len(chunks)

    # ------------------------------------------------------------------
    # 搜索
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 10,
        course_filter: Optional[str] = None,
        source_type_filter: Optional[str] = None,
        source_tag_filter: Optional[str] = None,
        chapter_filter: Optional[str] = None,
        boost_key_points: bool = True,
    ) -> List[dict]:
        """
        语义搜索（基于余弦相似度）。

        参数
        ----
        query : 查询文本
        top_k : 返回结果数量
        course_filter : 按课程过滤
        source_type_filter : 按文件类型过滤 (ppt/pdf/docx/image/text)
        source_tag_filter : 按来源标签过滤 (PPT课件/课本/作业/往年期末/期中考试)
        chapter_filter : 按章节过滤
        boost_key_points : 是否提升重点内容权重
        """
        course_name = course_filter or "default"
        vec_path = self._vectors_path(course_name)
        meta_path = self._metadata_path(course_name)

        if not os.path.exists(vec_path) or not os.path.exists(meta_path):
            return []

        # 加载数据
        vectors = np.load(vec_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        if len(vectors) == 0:
            return []

        # 向量化查询
        emb_model = get_embedding_model()
        query_vec = emb_model.encode([query])[0]

        # 计算余弦相似度（向量已 L2 归一化，直接点积即可）
        scores = np.dot(vectors, query_vec)

        # 构造结果
        items = []
        for i, score in enumerate(scores):
            meta = metadata[i]

            # 类型过滤
            if source_type_filter and meta.get("source_type") != source_type_filter:
                continue
            # 来源标签过滤（如"PPT课件"、"往年期末"）
            if source_tag_filter and meta.get("source_tag") != source_tag_filter:
                continue
            # 章节过滤
            if chapter_filter:
                ch = meta.get("chapter_hint", "")
                if chapter_filter.lower() not in ch.lower():
                    continue

            # 重点加权
            boosted = False
            if boost_key_points and meta.get("is_key_point"):
                score = min(float(score) * 1.3, 1.0)
                boosted = True

            items.append({
                "id": meta["id"],
                "text": meta.get("text", meta.get("text_preview", "")),
                "metadata": {k: v for k, v in meta.items() if k != "text"},
                "score": float(score),
                "boosted": boosted,
            })

        # 按分数降序
        items.sort(key=lambda x: -x["score"])

        return items[:top_k]

    # ------------------------------------------------------------------
    # 管理
    # ------------------------------------------------------------------

    def count(self, course_filter: str = None) -> int:
        """返回存储的文档块总数"""
        course_name = course_filter or "default"
        meta_path = self._metadata_path(course_name)
        if not os.path.exists(meta_path):
            return 0
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return len(metadata)

    def list_sources(self, course_filter: Optional[str] = None) -> List[dict]:
        """列出已导入的文件来源"""
        course_name = course_filter or "default"
        meta_path = self._metadata_path(course_name)
        if not os.path.exists(meta_path):
            return []
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        sources = {}
        for meta in metadata:
            fname = meta.get("source_file", "unknown")
            if fname not in sources:
                sources[fname] = {
                    "file": fname,
                    "type": meta.get("source_type", "unknown"),
                    "course": meta.get("course", course_name),
                    "chunk_count": 0,
                    "key_point_count": 0,
                }
            sources[fname]["chunk_count"] += 1
            if meta.get("is_key_point"):
                sources[fname]["key_point_count"] += 1

        return list(sources.values())

    def list_chapters(self, course_filter: Optional[str] = None) -> List[str]:
        """列出所有识别到的章节"""
        course_name = course_filter or "default"
        meta_path = self._metadata_path(course_name)
        if not os.path.exists(meta_path):
            return []
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        chapters = set()
        for meta in metadata:
            ch = meta.get("chapter_hint", "")
            if ch:
                chapters.add(ch)
        return sorted(chapters)

    def delete_course(self, course_name: str) -> int:
        """删除指定课程的所有数据"""
        import shutil
        course_dir = self._course_path(course_name)
        if os.path.exists(course_dir):
            # 计数
            count = self.count(course_name)
            shutil.rmtree(course_dir)
            return count
        return 0

    def get_all(self, course_filter: Optional[str] = None) -> List[dict]:
        """获取所有文档块"""
        course_name = course_filter or "default"
        meta_path = self._metadata_path(course_name)
        if not os.path.exists(meta_path):
            return []
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return [
            {
                "id": m["id"],
                "text": m.get("text", ""),
                "metadata": {k: v for k, v in m.items() if k != "text"},
            }
            for m in metadata
        ]

    def update_metadata(self, course_name: str, chunk_id: str,
                        updates: dict) -> bool:
        """更新指定文档块的元数据（用于标记重点等操作）"""
        meta_path = self._metadata_path(course_name)
        if not os.path.exists(meta_path):
            return False
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        for meta in metadata:
            if meta["id"] == chunk_id:
                meta.update(updates)
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                return True
        return False
