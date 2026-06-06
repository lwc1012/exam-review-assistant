"""
Embedding / 文本向量化模块

默认策略：TF-IDF（纯 numpy 实现，零额外依赖，32位 Windows 兼容）
可选升级：ONNX Runtime 模型（需手动配置）

TF-IDF 在课程知识检索场景下表现良好：
  - 学生搜索 "中值定理" → 精准匹配包含该术语的 PPT/课本片段
  - 搜索 "导数定义" → 找到所有包含该概念的章节
  - 比纯关键词搜索更能区分术语重要性
"""

import os
import json
import re
import math
from typing import List, Optional
from collections import Counter

import numpy as np


# 模型缓存路径
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME",
                      os.path.join(os.path.dirname(__file__), "..", "data", "model_cache"))


class TfidfVectorizer:
    """
    纯 numpy 实现的 TF-IDF 向量化器。

    特点：
      - 中文分词：混合 jieba（如已安装）+ 字符级 n-gram 回退
      - IDF 平滑：防止除零
      - L2 归一化输出
    """

    def __init__(self, max_features: int = 5000):
        self.max_features = max_features
        self._vocab: dict = {}          # word → index
        self._idf: np.ndarray = None    # IDF 向量
        self._fitted = False

    # ------------------------------------------------------------------
    # 分词
    # ------------------------------------------------------------------

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """
        中文文本分词。
        优先使用 jieba（如果已安装），否则使用字符级 bigram + trigram。
        """
        try:
            import jieba
            return list(jieba.cut(text))
        except ImportError:
            pass

        # 回退方案：字符 n-gram（兼容中文）
        # 先提取中文字段和英文单词
        tokens = []
        # 英文单词
        eng_words = re.findall(r'[a-zA-Z]+', text)
        tokens.extend(w.lower() for w in eng_words)

        # 数字
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        tokens.extend(numbers)

        # 中文字符 bigram (更好的语义捕获)
        chinese_chars = re.findall(r'[一-鿿]', text)
        for i in range(len(chinese_chars)):
            tokens.append(chinese_chars[i])  # 单字
            if i < len(chinese_chars) - 1:
                tokens.append(chinese_chars[i] + chinese_chars[i + 1])  # bigram
            if i < len(chinese_chars) - 2:
                tokens.append(chinese_chars[i] + chinese_chars[i + 1] + chinese_chars[i + 2])  # trigram

        return tokens

    # ------------------------------------------------------------------
    # 拟合 & 转换
    # ------------------------------------------------------------------

    def fit(self, documents: List[str]) -> "TfidfVectorizer":
        """
        在文档集上拟合 IDF。
        """
        N = len(documents)
        doc_freq = Counter()

        for doc in documents:
            tokens = set(self.tokenize(doc))
            for t in tokens:
                doc_freq[t] += 1

        # 按频率排序，取 top max_features
        top_terms = [t for t, _ in doc_freq.most_common(self.max_features)]
        self._vocab = {t: i for i, t in enumerate(top_terms)}
        vocab_size = len(self._vocab)

        # 计算 IDF: log((N + 1) / (df + 1)) + 1
        self._idf = np.ones(vocab_size, dtype=np.float32)
        for term, idx in self._vocab.items():
            df = doc_freq.get(term, 0)
            self._idf[idx] = math.log((N + 1) / (df + 1)) + 1.0

        self._fitted = True
        return self

    def transform(self, documents: List[str]) -> np.ndarray:
        """
        将文档转换为 TF-IDF 矩阵（L2 归一化）。
        返回 shape = (len(documents), vocab_size)
        """
        if not self._fitted:
            raise RuntimeError("请先调用 fit() 拟合向量化器")

        matrix = np.zeros((len(documents), len(self._vocab)), dtype=np.float32)

        for i, doc in enumerate(documents):
            tokens = self.tokenize(doc)
            tf = Counter(tokens)
            for term, count in tf.items():
                if term in self._vocab:
                    idx = self._vocab[term]
                    # TF sublinear: 1 + log(tf)
                    matrix[i, idx] = 1.0 + math.log(count)

            # 乘以 IDF
            matrix[i] *= self._idf

            # L2 归一化
            norm = np.linalg.norm(matrix[i])
            if norm > 0:
                matrix[i] /= norm

        return matrix

    def save(self, path: str) -> None:
        """保存拟合好的向量化器"""
        data = {
            "vocab": self._vocab,
            "idf": self._idf.tolist() if self._idf is not None else None,
            "max_features": self.max_features,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def load(self, path: str) -> bool:
        """加载之前拟合的向量化器"""
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._vocab = data["vocab"]
        self._idf = np.array(data["idf"], dtype=np.float32) if data["idf"] else None
        self.max_features = data.get("max_features", 5000)
        self._fitted = True
        return True

    @property
    def dimension(self) -> int:
        return len(self._vocab) if self._fitted else 0

    @property
    def is_fitted(self) -> bool:
        return self._fitted


# =========================================================================
# 统一 Embedding 接口（兼容原 ChromaDB 调用的 API）
# =========================================================================

class EmbeddingModel:
    """
    Embedding 模型统一封装。

    兼容 32 位 Windows：
      - 默认使用 TF-IDF（纯 numpy）
      - 可选升级为 ONNX 模型（需手动配置模型文件）
    """

    _instance: Optional["EmbeddingModel"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = None):
        if self._initialized:
            return

        self.model_name = model_name or "tfidf"
        self._vectorizer = TfidfVectorizer()
        self._dimension = None
        self._onnx_session = None
        self._using_tfidf = True
        self._initialized = True

    # ------------------------------------------------------------------
    # 加载
    # ------------------------------------------------------------------

    def load(self, quiet: bool = False) -> bool:
        """
        加载/拟合向量化器。
        会尝试从缓存加载已有拟合数据。
        返回 True 表示就绪。
        """
        # 尝试从缓存加载
        cache_path = os.path.join(
            os.path.dirname(__file__), "..", "data",
            "tfidf_vectorizer.json"
        )
        if self._vectorizer.load(cache_path):
            self._dimension = self._vectorizer.dimension
            self._using_tfidf = True
            if not quiet:
                print(f"[Embedding] Loaded TF-IDF from cache (dim={self._dimension})")
            return True

        if not quiet:
            print("[Embedding] TF-IDF 向量化器尚未拟合，将在首次导入文档时自动拟合。")
        return False

    def fit_on_documents(self, documents: List[str], quiet: bool = False) -> None:
        """在文档集上拟合 TF-IDF"""
        if not quiet:
            print(f"[Embedding] 正在拟合 TF-IDF 向量化器 (文档数={len(documents)}) ...")
        self._vectorizer.fit(documents)
        self._dimension = self._vectorizer.dimension
        self._using_tfidf = True

        # 保存到缓存
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, "tfidf_vectorizer.json")
        self._vectorizer.save(cache_path)

        if not quiet:
            print(f"[Embedding] TF-IDF fitted (vocab={self._dimension})")

    # ------------------------------------------------------------------
    # 编码
    # ------------------------------------------------------------------

    def encode(self, texts: List[str], batch_size: int = 32,
               normalize_embeddings: bool = True) -> np.ndarray:
        """
        将文本列表转换为向量矩阵。
        返回 shape = (len(texts), dimension)
        """
        if not self._vectorizer.is_fitted:
            # 尝试从缓存加载
            if not self.load(quiet=True):
                # 缓存未命中，拟合新向量化器
                self.fit_on_documents(texts)

        return self._vectorizer.transform(texts)

    def encode_single(self, text: str) -> List[float]:
        """单条文本转向量"""
        vec = self.encode([text])
        return vec[0].tolist()

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def dimension(self) -> int:
        if self._dimension is None and self._vectorizer.is_fitted:
            self._dimension = self._vectorizer.dimension
        return self._dimension or 0

    @property
    def is_loaded(self) -> bool:
        return True  # TF-IDF 总是可用

    # ------------------------------------------------------------------
    # 诊断
    # ------------------------------------------------------------------

    def info(self) -> dict:
        return {
            "model_name": self.model_name,
            "backend": "tfidf (numpy)",
            "dimension": self.dimension or "需先导入文档拟合",
            "vectorizer_fitted": self._vectorizer.is_fitted,
            "device": "cpu",
        }


# =========================================================================
# 单例获取
# =========================================================================

_global_embedding: Optional[EmbeddingModel] = None


def get_embedding_model(model_name: str = None) -> EmbeddingModel:
    """获取全局 embedding 实例"""
    global _global_embedding
    if _global_embedding is None:
        _global_embedding = EmbeddingModel(model_name)
    return _global_embedding
