"""
GBrain 基本功能测试
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from gbrain import GBrain
from gbrain.config import ensure_dirs


@pytest.fixture
def kb():
    """创建测试用知识库"""
    ensure_dirs()
    return GBrain()


def test_add_page(kb):
    """测试添加页面"""
    result = kb.add_page("测试标题", "这是测试内容")
    assert result is not None
    # add_page 返回 dict: {'page_id': ..., 'category': ..., 'confidence': ..., 'links': ...}
    assert "page_id" in result
    assert len(result["page_id"]) == 12


def test_search(kb):
    """测试搜索"""
    kb.add_page("销售知识", "客户开发是销售的第一步")
    results = kb.search("销售")
    assert len(results) > 0
    assert results[0]["title"] == "销售知识"


def test_list_pages(kb):
    """测试列出页面"""
    kb.add_page("测试1", "内容1")
    kb.add_page("测试2", "内容2")
    pages = kb.list_pages()
    assert len(pages) >= 2


def test_graph_stats(kb):
    """测试图谱统计"""
    kb.add_page("测试", "内容[[链接]]")
    stats = kb.get_graph_stats()
    assert "node_count" in stats
    assert "edge_count" in stats
    assert "orphan_count" in stats


def test_mcp_tools(kb):
    """测试 MCP 工具接口"""
    from gbrain.mcp_server import MCP_TOOLS

    assert len(MCP_TOOLS) > 0

    tool_names = [t["name"] for t in MCP_TOOLS]
    assert "search" in tool_names
    assert "add_page" in tool_names
    assert "ask" in tool_names


def test_rrf_fusion():
    """测试 RRF 融合"""
    from gbrain.fusion import rrf_fuse

    vector_results = [
        {"page_id": "1", "title": "A", "snippet": "", "score": 0.9},
        {"page_id": "2", "title": "B", "snippet": "", "score": 0.8},
    ]

    bm25_results = [
        {"page_id": "2", "title": "B", "snippet": "", "score": 10.0},
        {"page_id": "3", "title": "C", "snippet": "", "score": 8.0},
    ]

    fused = rrf_fuse(vector_results, bm25_results, top_k=3)

    # 文档2同时在两个结果中，应该排名靠前
    assert len(fused) == 3
    page_ids = [r["page_id"] for r in fused]
    assert page_ids.index("2") < page_ids.index("1")
    assert page_ids.index("2") < page_ids.index("3")


def test_bm25_chinese():
    """测试中文分词"""
    from gbrain.bm25_search import _tokenize_chinese

    tokens = _tokenize_chinese("销售流程")
    assert "销售" in tokens
    assert "售流" in tokens
    assert "流程" in tokens

    tokens = _tokenize_chinese("API接口文档")
    assert "api" in tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
