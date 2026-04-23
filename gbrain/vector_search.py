"""
GBrain 向量搜索模块 - 纯 Python 实现
"""

import json
import math
import requests
from typing import Optional, List

from .config import (
    QWEN_API_KEY, QWEN_EMBEDDING_URL, EMBEDDING_MODEL,
    VECTOR_DIM, TOP_K
)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_embedding(text: str) -> Optional[list[float]]:
    """获取文本的 embedding"""
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": EMBEDDING_MODEL,
        "input": {"texts": [text[:8192]]}
    }

    try:
        response = requests.post(
            QWEN_EMBEDDING_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            print(f"Embedding API 错误: {response.status_code} - {response.text}")
            return None

        result = response.json()

        embeddings = None
        if "data" in result and "embeddings" in result.get("data", {}):
            embeddings = result["data"]["embeddings"]
        elif "output" in result and "embeddings" in result.get("output", {}):
            embeddings = result["output"]["embeddings"]

        if embeddings and len(embeddings) > 0:
            embedding = embeddings[0].get("embedding") or embeddings[0]
            if isinstance(embedding, list):
                if len(embedding) == VECTOR_DIM:
                    return embedding
                elif len(embedding) > VECTOR_DIM:
                    return embedding[:VECTOR_DIM]
                else:
                    return (embedding + [0.0] * VECTOR_DIM)[:VECTOR_DIM]
        return None

    except Exception as e:
        print(f"Embedding 获取失败: {e}")
        return None


class VectorSearcher:
    """向量搜索器 - 纯 Python 实现"""

    def __init__(self, db):
        self.db = db
        self._vector_cache: dict[str, list[float]] = {}
        self._load_vectors()

    def _load_vectors(self):
        """从数据库加载向量到内存"""
        try:
            with self.db.get_cursor() as c:
                c.execute("SELECT page_id, embedding FROM page_vectors")
                for row in c.fetchall():
                    page_id = row[0]
                    embedding_str = row[1]
                    if isinstance(embedding_str, str):
                        self._vector_cache[page_id] = json.loads(embedding_str)
                    elif isinstance(embedding_str, bytes):
                        import struct
                        count = len(embedding_str) // 4
                        self._vector_cache[page_id] = list(
                            struct.unpack(f'{count}f', embedding_str)
                        )
        except Exception as e:
            print(f"加载向量缓存失败: {e}")

    def add_vector(self, page_id: str, embedding: list[float]):
        """添加向量到缓存和数据库"""
        self._vector_cache[page_id] = embedding
        # 存储为 JSON 格式
        try:
            with self.db.get_cursor() as c:
                c.execute(
                    """INSERT OR REPLACE INTO page_vectors (page_id, embedding)
                       VALUES (?, ?)""",
                    (page_id, json.dumps(embedding))
                )
        except Exception as e:
            print(f"存储向量失败: {e}")

    def search(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """向量相似度搜索"""
        query_embedding = get_embedding(query)
        if not query_embedding:
            return []

        # 计算与所有向量的相似度
        scores = []
        for page_id, embedding in self._vector_cache.items():
            sim = cosine_similarity(query_embedding, embedding)
            scores.append((page_id, sim))

        # 排序并取 top_k
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for page_id, score in scores[:top_k]:
            page = self.db.get_page(page_id)
            if page:
                results.append({
                    'page_id': page_id,
                    'title': page['title'],
                    'snippet': page['content'][:200],
                    'score': score,
                    'source': 'vector'
                })

        return results
