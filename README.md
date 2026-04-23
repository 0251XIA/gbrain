# GBrain

> AI Agent 的记忆与知识管理系统 - 让私有知识成为 AI 的上下文

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 定位

GBrain 不是另一个笔记应用或企业 wiki，而是 **AI 应用的记忆层组件**。

```
AI 应用 ─── MCP ───► GBrain ───► 私有知识
                              (向量 + BM25 + RRF)
```

**核心场景:**
- 为 AI Agent 添加私有知识检索能力
- 构建本地 RAG 系统的知识底座
- 打造私人 AI 助手的记忆模块

---

## 特性

| 特性 | 说明 |
|------|------|
| **三层检索** | 向量搜索 + BM25 关键词 + RRF 融合，兼顾语义和精确匹配 |
| **知识图谱** | 自动从 [[链接]] 构建知识关系图 |
| **MCP 协议** | 标准化的 STDIO/HTTP 接口，AI 应用即插即用 |
| **本地优先** | SQLite 存储，数据完全可控 |
| **中文优化** | 中文 2-gram 分词 + 千问 Embedding |
| **自动分类** | 销售/服务/技术/通用 自动归类 |
| **轻量快速** | 无外部依赖（除可选向量 API） |

---

## 快速开始

### 安装

```bash
cd /Users/forxia/gbrain
source .venv/bin/activate
```

依赖已安装：`networkx`, `rank-bm25`, `requests`

### 5 分钟入门

```python
from gbrain import GBrain
from gbrain.config import ensure_dirs

# 初始化
ensure_dirs()
kb = GBrain()

# 添加知识
kb.add_page(
    title="销售报价流程",
    content="客户开发是销售的第一步，需要了解预算和需求，然后进行商务报价[[销售流程]]"
)

kb.add_page(
    title="售后服务标准",
    content="客户服务包括问题解答、技术支持和售后维护"
)

# 检索
results = kb.search("如何给客户报价")
print(results)

# 问答
answer = kb.ask("客户要求报价应该怎么回复？")
print(answer)

# 分析
kb.analyze()
```

### MCP STDIO 模式

```bash
# 启动 MCP STDIO 服务器
python -m gbrain.mcp_server --stdio
```

MCP 工具列表:

| 工具 | 功能 |
|------|------|
| `search` | 三层检索 |
| `add_page` | 添加页面 |
| `get_page` | 获取页面 |
| `list_pages` | 列出页面 |
| `ask` | 问答 |
| `get_graph_stats` | 图谱统计 |
| `find_related` | 查找相关页面 |
| `get_communities` | 发现社区 |

### HTTP API 模式

```bash
# 启动 HTTP 服务器
python -m gbrain.mcp_server --port 8765
```

```bash
# 搜索
curl "http://localhost:8765/search?q=销售&top_k=5"

# 添加
curl -X POST http://localhost:8765/add \
  -H "Content-Type: application/json" \
  -d '{"title":"标题","content":"内容"}'

# 问答
curl "http://localhost:8765/ask?q=如何报价"
```

---

## 架构设计

### 三层检索流程

```
用户查询
    │
    ├──► 向量搜索 ──► 余弦相似度计算
    │                      │
    ├──► BM25 搜索 ──► 关键词匹配
    │                      │
    └──► RRF 融合 ◄────────┘
             │
             ▼
        综合排名结果
```

**RRF 公式:**
```python
score(d) = Σ 1/(k + rank_i)
# k = 60 (融合参数)
```

### 知识图谱

```python
# 添加页面时自动提取 [[链接]]
kb.add_page("A", "内容包含[[B]]和[[C]]")

# 自动构建关系
# A ─links_to──► B
# A ─links_to──► C
```

---

## API 参考

### GBrain 主类

```python
from gbrain import GBrain

kb = GBrain()

# 添加入知识库
page_id = kb.add_page(title, content, category=None, tags=None)

# 三层检索
results = kb.search(query, top_k=5)
# 返回: [{'page_id', 'title', 'snippet', 'score', 'source', 'vector_rank', 'bm25_rank'}]

# 问答（调用 LLM）
answer = kb.ask(question)

# 获取页面
page = kb.get_page(page_id)

# 列出页面
pages = kb.list_pages(category=None)

# 知识图谱统计
stats = kb.get_graph_stats()

# 知识库分析
kb.analyze()
```

### 配置

`gbrain/config.py`:

```python
# API 配置
MINIMAX_API_KEY = "your-key"  # LLM 调用
QWEN_API_KEY = "your-key"     # Embedding

# 路径配置
DATA_PATH = "./data"  # 数据存储
KB_PATH = "./data/kb"

# 搜索配置
VECTOR_DIM = 1024      # Embedding 维度
TOP_K = 5             # 默认返回数量
RRF_K = 60            # RRF 融合参数
```

---

## 项目结构

```
gbrain/
├── gbrain/
│   ├── __init__.py        # 包入口
│   ├── config.py          # 配置
│   ├── database.py        # SQLite 数据库
│   ├── models.py          # 数据模型
│   ├── vector_search.py   # 向量搜索
│   ├── bm25_search.py     # BM25 搜索
│   ├── fusion.py          # RRF 融合
│   ├── graph.py           # 知识图谱
│   ├── classifier.py       # 分类器
│   ├── evolver.py         # 进化引擎
│   └── mcp_server.py      # MCP Server
├── data/                  # 数据存储
├── tests/                 # 测试
└── .venv/                 # 虚拟环境
```

---

## 与竞品对比

| 项目 | 定位 | 优势 | 劣势 |
|------|------|------|------|
| **GBrain** | AI 记忆组件 | 轻量/MCP/开源 | 无 UI |
| AnythingLLM | AI 知识库 | 开箱即用 | 闭源/无 MCP |
| Dify | AI 应用平台 | 功能完整 | 太重 |
| LangChain | 开发框架 | 灵活 | 偏底层 |
| Notion AI | 笔记 + AI | 用户多 | 不开源 |

**GBrain 差异化:**
- 专注 AI 应用的记忆层，而非 ToC 笔记
- MCP 协议原生支持，AI 应用即插即用
- 轻量可嵌入，5 行代码集成

---

## 适用场景

✅ **适合:**
- AI Agent 的知识检索组件
- RAG 系统的知识底座
- 私人 AI 助手的记忆模块
- 小团队知识管理

❌ **不适合:**
- 需要复杂权限的企业 wiki
- 需要协作编辑的文档系统
- 需要 99.9% SLA 的生产环境

---

## 技术栈

- **运行时:** Python 3.10+
- **数据库:** SQLite
- **向量:** 千问 Embedding API (可选本地计算)
- **图谱:** NetworkX
- **搜索:** rank-bm25
- **协议:** MCP (STDIO + HTTP)

---

## 贡献

欢迎提交 Issue 和 PR！

---

## 许可

MIT License

---

**GBrain = 让 AI 更懂你的知识**
