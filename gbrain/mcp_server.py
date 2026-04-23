"""
GBrain MCP Server - 标准 MCP 协议实现

提供工具接口:
- search: 三层检索
- add_page: 添加页面
- get_page: 获取页面
- list_pages: 列出页面
- analyze: 知识库分析
- ask: 问答
- get_graph_stats: 图谱统计
"""

import sys
import json
from typing import Optional

from .config import ensure_dirs
from .database import Database
from .graph import KnowledgeGraph
from .vector_search import VectorSearcher
from .bm25_search import BM25Searcher
from .fusion import rrf_fuse
from .evolver import Evolver
from .classifier import Classifier
from .vector_search import get_embedding


class GBrainMCP:
    """GBrain MCP 工具接口"""

    def __init__(self):
        ensure_dirs()
        self.db = Database()
        self.graph = KnowledgeGraph(self.db)
        self.vector_searcher = VectorSearcher(self.db)
        self.bm25_searcher = BM25Searcher(self.db)
        self.evolver = Evolver(self.db, self.graph)
        self.classifier = Classifier()

    # =====================================================================
    # 工具方法
    # =====================================================================

    def search(self, query: str, top_k: int = 5) -> list:
        """三层检索：向量 + BM25 + RRF 融合"""
        vector_results = self.vector_searcher.search(query, top_k)
        bm25_results = self.bm25_searcher.search(query, top_k)
        results = rrf_fuse(vector_results, bm25_results, top_k)
        return results

    def add_page(self, title: str, content: str,
                 category: str = None, tags: list = None) -> dict:
        """添加页面"""
        import hashlib
        page_id = hashlib.md5(title.encode()).hexdigest()[:12]

        if category is None:
            category, confidence = self.classifier.classify(content, title)
        else:
            confidence = 1.0

        import re
        links = re.findall(r'\[\[([^\]]+)\]\]', content)

        self.db.insert_page(
            page_id=page_id,
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            links=links
        )

        self.graph.add_page(page_id, title, content)

        embedding = get_embedding(f"{title}\n{content}")
        if embedding:
            self.vector_searcher.add_vector(page_id, embedding)

        self.bm25_searcher.rebuild()

        return {
            "page_id": page_id,
            "category": category,
            "confidence": confidence,
            "links": links
        }

    def get_page(self, page_id: str) -> Optional[dict]:
        """获取页面"""
        return self.db.get_page(page_id)

    def list_pages(self, category: str = None) -> list:
        """列出页面"""
        pages = self.db.get_all_pages()
        if category:
            pages = [p for p in pages if p.get('category') == category]
        return pages

    def analyze(self) -> dict:
        """知识库分析"""
        return self.evolver.analyze()

    def get_graph_stats(self) -> dict:
        """图谱统计"""
        return self.graph.get_stats()

    def ask(self, question: str) -> str:
        """问答"""
        results = self.search(question, top_k=3)

        if not results:
            context = "（知识库为空）"
        else:
            context = "\n\n".join([
                f"### {r['title']}\n{r['snippet']}"
                for r in results
            ])

        system_prompt = f"""你是一个知识渊博的助手，基于用户的个人知识库回答问题。

规则：
1. 如果知识库中有相关内容，优先使用知识库回答
2. 如果没有相关内容，使用你的知识回答，但说明"知识库中没有相关内容"
3. 回答要清晰、有条理
4. 用中文回答

相关知识库内容：
{context}

用户的问题："""

        return call_minimax(question, system_prompt)

    def find_related(self, page_id: str, depth: int = 2) -> list:
        """查找相关页面"""
        return self.graph.get_neighbors(page_id, depth)

    def get_communities(self) -> list:
        """发现社区"""
        return self.graph.get_communities()

    def get_centrality(self) -> dict:
        """获取中心性"""
        return self.graph.get_centrality()


def call_minimax(prompt: str, system_prompt: str = "") -> str:
    """调用 MiniMax API"""
    import os
    import requests

    api_key = os.environ.get(
        "MINIMAX_API_KEY",
        "sk-cp-kDCyY6jjZ6FyV_NvT7VhIHwO-InBEmc7hah1iL4hUl4X9PBhq0A6DPJV61C3F7RlWfpSukXtSYJ39oImP7Mzoe2_ryCmZEcmLJIJMYhszLhpyOfmaVk7Auc"
    )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "MiniMax-M2.7",
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.7
    }

    response = requests.post(
        "https://api.minimax.chat/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120
    )

    if response.status_code != 200:
        raise Exception(f"API 错误: {response.status_code}")

    result = response.json()
    return result["choices"][0]["message"]["content"]


# ============================================================================
# MCP STDIO Server
# ============================================================================

MCP_TOOLS = [
    {
        "name": "search",
        "description": "三层检索：向量 + BM25 + RRF 融合搜索",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索查询"},
                "top_k": {"type": "integer", "default": 5, "description": "返回数量"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_page",
        "description": "添加页面到知识库（自动分类+建图+建向量）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "页面标题"},
                "content": {"type": "string", "description": "页面内容"},
                "category": {"type": "string", "description": "分类（可选，自动分类）"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "标签"}
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "get_page",
        "description": "获取页面详情",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "页面 ID"}
            },
            "required": ["page_id"]
        }
    },
    {
        "name": "list_pages",
        "description": "列出所有页面",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "按分类筛选"}
            }
        }
    },
    {
        "name": "analyze",
        "description": "运行知识库分析",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_graph_stats",
        "description": "获取知识图谱统计",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "ask",
        "description": "基于知识库问答",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "问题"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "find_related",
        "description": "查找相关页面",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "页面 ID"},
                "depth": {"type": "integer", "default": 2, "description": "深度"}
            },
            "required": ["page_id"]
        }
    },
    {
        "name": "get_communities",
        "description": "发现知识图谱中的社区",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_centrality",
        "description": "获取节点中心性排名",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
]


def run_stdio_server():
    """MCP STDIO 服务器"""
    gb = GBrainMCP()

    def send_response(response):
        print(json.dumps(response), flush=True)

    while True:
        line = sys.stdin.readline()
        if not line:
            break

        try:
            request = json.loads(line)
            method = request.get("method", "")
            params = request.get("params", {})
            request_id = request.get("id")

            if method == "initialize":
                send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "gbrain", "version": "0.1.0"}
                    }
                })

            elif method == "tools/list":
                send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": MCP_TOOLS}
                })

            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})

                try:
                    if tool_name == "search":
                        result = gb.search(**tool_args)
                    elif tool_name == "add_page":
                        result = gb.add_page(**tool_args)
                    elif tool_name == "get_page":
                        result = gb.get_page(**tool_args)
                    elif tool_name == "list_pages":
                        result = gb.list_pages(**tool_args)
                    elif tool_name == "analyze":
                        result = gb.analyze()
                    elif tool_name == "get_graph_stats":
                        result = gb.get_graph_stats()
                    elif tool_name == "ask":
                        result = gb.ask(**tool_args)
                    elif tool_name == "find_related":
                        result = gb.find_related(**tool_args)
                    elif tool_name == "get_communities":
                        result = gb.get_communities()
                    elif tool_name == "get_centrality":
                        result = gb.get_centrality()
                    else:
                        result = {"error": f"未知工具: {tool_name}"}

                    send_response({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]
                        }
                    })

                except Exception as e:
                    send_response({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32603, "message": str(e)}
                    })

            elif method == "notifications/initialized":
                pass  # 握手完成

        except Exception as e:
            send_response({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)}
            })


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GBrain MCP Server")
    parser.add_argument("--stdio", action="store_true", help="STDIO 传输模式")
    parser.add_argument("--port", type=int, default=8765, help="HTTP 端口")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")

    args = parser.parse_args()

    if args.stdio:
        run_stdio_server()
    else:
        run_http_server(args.host, args.port)


def run_http_server(host: str, port: int):
    """HTTP 服务器"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse

    gb = GBrainMCP()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                info = {
                    "name": "gbrain",
                    "version": "0.1.0",
                    "endpoints": ["/search", "/pages", "/stats", "/graph-stats"]
                }
                self.wfile.write(json.dumps(info, ensure_ascii=False).encode())

            elif self.path == "/stats":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                pages = gb.list_pages()
                self.wfile.write(json.dumps({
                    "total_pages": len(pages),
                    "graph": gb.get_graph_stats()
                }, ensure_ascii=False).encode())

            elif self.path == "/graph-stats":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(gb.get_graph_stats(), ensure_ascii=False).encode())

            elif self.path.startswith("/search?"):
                query = urllib.parse.parse_qs(self.path[8:]).get("q", [""])[0]
                top_k = int(urllib.parse.parse_qs(self.path[8:]).get("top_k", ["5"])[0])
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                results = gb.search(query, top_k)
                self.wfile.write(json.dumps(results, ensure_ascii=False).encode())

            elif self.path.startswith("/pages"):
                category = urllib.parse.parse_qs(self.path[7:] if len(self.path) > 7 else "").get("category", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                pages = gb.list_pages(category)
                self.wfile.write(json.dumps(pages, ensure_ascii=False).encode())

            elif self.path.startswith("/ask?"):
                question = urllib.parse.parse_qs(self.path[5:]).get("q", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                result = gb.ask(question)
                self.wfile.write(result.encode("utf-8"))

            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if self.path == "/add":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode()
                data = json.loads(body)
                result = gb.add_page(
                    title=data.get("title", ""),
                    content=data.get("content", ""),
                    category=data.get("category"),
                    tags=data.get("tags")
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode())

            elif self.path == "/analyze":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                result = gb.analyze()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode())

            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass

    server = HTTPServer((host, port), Handler)
    print(f"GBrain MCP Server 运行在 http://{host}:{port}")
    print(f"可用端点: /search?q=..., /pages, /stats, /graph-stats, /ask?q=..., /add")
    server.serve_forever()


if __name__ == "__main__":
    main()
