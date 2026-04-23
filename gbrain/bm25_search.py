"""
GBrain BM25 关键词搜索模块
"""

import re
from typing import Optional

try:
    import rank_bm25
    HAS_RANK_BM25 = True
except ImportError:
    HAS_RANK_BM25 = False


def _tokenize_chinese(text: str, n: int = 2) -> list[str]:
    """简单中文分词 - 字符级 n-gram"""
    text = text.lower()
    text = re.sub(r'[^\w\u4e00-\u9fff]', ' ', text)
    tokens = []

    # 处理英文词
    english_words = re.findall(r'[a-z0-9]+', text)
    tokens.extend([w for w in english_words if len(w) > 1])

    # 处理中文字符 - 2-gram
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    for i in range(len(chinese_chars) - n + 1):
        tokens.append(''.join(chinese_chars[i:i+n]))

    return tokens


class BM25Searcher:
    """BM25 关键词搜索引擎"""

    def __init__(self, db):
        self.db = db
        self.index = None
        self.corpus = []
        self.page_ids = []
        self._build_index()

    def _tokenize(self, text: str) -> list[str]:
        """分词 - 支持中英文"""
        return _tokenize_chinese(text, n=2)

    def _build_index(self):
        """构建 BM25 索引"""
        if not HAS_RANK_BM25:
            print("rank_bm25 未安装，BM25 搜索降级")
            return

        pages = self.db.get_all_pages()
        self.corpus = []
        self.page_ids = []

        for page in pages:
            text = f"{page['title']} {page['content']}"
            tokens = self._tokenize(text)
            self.corpus.append(tokens)
            self.page_ids.append(page['id'])

        if self.corpus:
            self.index = rank_bm25.BM25Okapi(self.corpus)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """BM25 搜索"""
        if not self.index:
            return []

        query_tokens = self._tokenize(query)
        scores = self.index.get_scores(query_tokens)

        # 排序获取 top_k（不按分数过滤，BM25 分数可正可负）
        top_indices = sorted(range(len(scores)),
                           key=lambda i: scores[i],
                           reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            page = self.db.get_page(self.page_ids[idx])
            if page:
                results.append({
                    'page_id': self.page_ids[idx],
                    'title': page['title'],
                    'snippet': page['content'][:200],
                    'score': scores[idx],
                    'source': 'bm25'
                })

        return results

    def rebuild(self):
        """重建索引"""
        self._build_index()
