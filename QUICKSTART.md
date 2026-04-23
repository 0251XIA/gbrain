# GBrain 快速开始指南

## 环境要求

- Python 3.10+
- pip

## 安装

```bash
cd /Users/forxia/gbrain
source .venv/bin/activate
```

## 基本使用

### 1. 初始化知识库

```python
from gbrain import GBrain
from gbrain.config import ensure_dirs

ensure_dirs()
kb = GBrain()
```

### 2. 添加知识

```python
# 添加单条知识
kb.add_page(
    title="销售报价流程",
    content="客户开发是销售的第一步，需要了解客户预算和需求，然后进行商务报价"
)

# 添加更多知识
kb.add_page("售后服务标准", "客户服务包括问题解答、技术支持和售后维护")
kb.add_page("合同签署流程", "合同签署前需要确认对方资质，然后走法务审批流程[[销售流程]]")
```

### 3. 检索知识

```python
# 三层检索
results = kb.search("如何给客户报价")
print(results)

# 查看结果
for r in results:
    print(f"- {r['title']}: {r['snippet'][:50]}... (score: {r['score']:.3f})")
```

### 4. 问答

```python
# 基于知识库的问答
answer = kb.ask("客户要求报价应该怎么回复？")
print(answer)
```

### 5. 分析

```python
# 知识库分析
kb.analyze()
```

## MCP 接口

### STDIO 模式

```bash
python -m gbrain.mcp_server --stdio
```

### HTTP 模式

```bash
python -m gbrain.mcp_server --port 8765
```

## 目录结构

```
gbrain/
├── gbrain/          # 源代码
├── data/            # 数据存储
├── tests/           # 测试
├── README.md        # 说明文档
└── QUICKSTART.md   # 本文档
```

## 常见问题

**Q: 报错 "no module named 'xxx'"**
```bash
source .venv/bin/activate
pip install networkx rank-bm25 requests
```

**Q: 向量搜索返回空**
- 检查 Embedding API 配置是否正确
- 确认千问 API key 有效

**Q: BM25 搜索不工作**
- 检查 `rank-bm25` 是否安装
- 确认中文分词正常工作

## 下一步

- 阅读 [README.md](README.md) 了解完整架构
- 查看 `gbrain/` 目录下的源码
- 根据需要修改 `config.py` 配置
