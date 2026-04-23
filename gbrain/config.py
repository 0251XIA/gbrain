"""
GBrain 配置模块
"""

import os
from pathlib import Path

# MiniMax API 配置
MINIMAX_API_KEY = os.environ.get(
    "MINIMAX_API_KEY",
    "sk-cp-kDCyY6jjZ6FyV_NvT7VhIHwO-InBEmc7hah1iL4hUl4X9PBhq0A6DPJV61C3F7RlWfpSukXtSYJ39oImP7Mzoe2_ryCmZEcmLJIJMYhszLhpyOfmaVk7Auc"
)
MINIMAX_BASE_URL = "https://api.minimax.chat/v1"
MODEL_NAME = "MiniMax-M2.7"

# 千问 Embedding API 配置
QWEN_API_KEY = os.environ.get(
    "QWEN_API_KEY",
    "sk-490b0bcca7fb4f3ba4fbfa3f9830b23b"
)
QWEN_EMBEDDING_URL = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
EMBEDDING_MODEL = "text-embedding-v1"

# 项目路径
BASE_PATH = Path(__file__).parent.parent
DATA_PATH = BASE_PATH / "data"
KB_PATH = DATA_PATH / "kb"  # 知识库存储
GRAPH_PATH = DATA_PATH / "graph"  # 图数据存储

# 向量搜索配置
VECTOR_DIM = 1024  # embedding 维度
TOP_K = 5

# RRF 融合参数
RRF_K = 60

# 分类配置
CATEGORY_RULES = {
    "销售": ["销售", "客户", "报价", "谈判", "成交", "续费", "漏斗"],
    "服务": ["服务", "售后", "客服", "问题", "支持"],
    "技术": ["技术", "功能", "API", "开发", "架构", "部署"],
    "通用": []
}

# MCP 配置
MCP_HOST = "0.0.0.0"
MCP_PORT = 8765

def ensure_dirs():
    """确保必要目录存在"""
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    KB_PATH.mkdir(parents=True, exist_ok=True)
    GRAPH_PATH.mkdir(parents=True, exist_ok=True)
