"""
GBrain RRF 融合模块
"""

from typing import List

from .config import RRF_K


def rrf_fuse(vector_results: List[dict],
             bm25_results: List[dict],
             top_k: int = 5) -> List[dict]:
    """
    RRF (Reciprocal Rank Fusion) 融合向量搜索和 BM25 搜索结果

    RRF 公式: score(d) = Σ 1/(k + rank(d))
    其中 k 是融合参数（默认60）
    """
    if not vector_results and not bm25_results:
        return []

    scores = {}

    # 处理向量搜索结果
    for rank, result in enumerate(vector_results):
        page_id = result['page_id']
        rrf_score = 1.0 / (RRF_K + rank + 1)
        if page_id in scores:
            scores[page_id]['rrf_score'] += rrf_score
            scores[page_id]['vector_rank'] = rank + 1
        else:
            scores[page_id] = {
                'page_id': page_id,
                'title': result['title'],
                'snippet': result['snippet'],
                'rrf_score': rrf_score,
                'vector_score': result['score'],
                'vector_rank': rank + 1,
                'bm25_rank': None,
                'bm25_score': 0
            }

    # 处理 BM25 结果
    for rank, result in enumerate(bm25_results):
        page_id = result['page_id']
        rrf_score = 1.0 / (RRF_K + rank + 1)
        if page_id in scores:
            scores[page_id]['rrf_score'] += rrf_score
            scores[page_id]['bm25_rank'] = rank + 1
            scores[page_id]['bm25_score'] = result['score']
        else:
            scores[page_id] = {
                'page_id': page_id,
                'title': result['title'],
                'snippet': result['snippet'],
                'rrf_score': rrf_score,
                'vector_score': 0,
                'vector_rank': None,
                'bm25_rank': rank + 1,
                'bm25_score': result['score']
            }

    # 按 RRF 分数排序
    sorted_results = sorted(scores.values(),
                          key=lambda x: x['rrf_score'],
                          reverse=True)[:top_k]

    final_results = []
    for r in sorted_results:
        final_results.append({
            'page_id': r['page_id'],
            'title': r['title'],
            'snippet': r['snippet'],
            'score': r['rrf_score'],
            'source': 'rrf',
            'vector_rank': r['vector_rank'],
            'bm25_rank': r['bm25_rank']
        })

    return final_results
