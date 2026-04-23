"""
GBrain 知识图谱模块
"""

import re
import networkx as nx
from typing import Optional

from .config import GRAPH_PATH


class KnowledgeGraph:
    """知识图谱"""

    def __init__(self, db=None):
        self.db = db
        self.graph = nx.DiGraph()
        self._load_from_db()

    def _load_from_db(self):
        """从数据库加载图数据"""
        if not self.db:
            return

        # 加载实体
        entities = self.db.get_all_entities()
        for entity in entities:
            self.graph.add_node(
                entity['id'],
                name=entity['name'],
                type=entity['entity_type'],
                properties=entity.get('properties', {})
            )

        # 加载关系
        relations = self.db.get_relations()
        for rel in relations:
            self.graph.add_edge(
                rel['source_id'],
                rel['target_id'],
                relation_type=rel['relation_type'],
                properties=rel.get('properties', {})
            )

    def extract_links(self, content: str) -> list[str]:
        """从内容中提取 [[链接]] 格式的链接"""
        return re.findall(r'\[\[([^\]]+)\]\]', content)

    def add_page(self, page_id: str, title: str, content: str):
        """添加页面到图谱"""
        # 添加页面节点
        self.graph.add_node(page_id, title=title, type='page')

        # 提取并添加链接关系
        links = self.extract_links(content)
        for link in links:
            link_id = link.split('|')[0].strip()
            if link_id != page_id:  # 避免自环
                self.graph.add_node(link_id, title=link_id, type='page')
                self.graph.add_edge(page_id, link_id, relation_type='links_to')

    def add_entity(self, entity_id: str, name: str,
                   entity_type: str, properties: dict = None):
        """添加实体"""
        self.graph.add_node(
            entity_id,
            name=name,
            type=entity_type,
            properties=properties or {}
        )

    def add_relation(self, source_id: str, target_id: str,
                     relation_type: str, properties: dict = None):
        """添加关系"""
        self.graph.add_edge(
            source_id,
            target_id,
            relation_type=relation_type,
            properties=properties or {}
        )

    def get_neighbors(self, node_id: str, depth: int = 1) -> list[dict]:
        """获取节点邻居"""
        if node_id not in self.graph:
            return []

        neighbors = []
        for neighbor in nx.single_source_shortest_path_length(
            self.graph, node_id, cutoff=depth
        ):
            if neighbor != node_id:
                node_data = self.graph.nodes[neighbor]
                neighbors.append({
                    'id': neighbor,
                    'name': node_data.get('name', neighbor),
                    'type': node_data.get('type', 'unknown'),
                    'distance': neighbors[neighbor] if isinstance(neighbors, dict) else 1
                })
        return neighbors

    def find_orphans(self) -> list[str]:
        """找出孤立节点"""
        return [n for n in self.graph.nodes()
                if self.graph.degree(n) == 0]

    def find_shortest_paths(self, source: str, target: str) -> list[list]:
        """找出两个节点之间的最短路径"""
        if source not in self.graph or target not in self.graph:
            return []

        try:
            return list(nx.all_shortest_paths(self.graph, source, target))
        except nx.NetworkXNoPath:
            return []

    def get_centrality(self) -> dict:
        """获取节点中心性"""
        if len(self.graph.nodes()) == 0:
            return {}

        try:
            return nx.degree_centrality(self.graph)
        except:
            return {}

    def get_communities(self) -> list[list]:
        """发现社区"""
        if len(self.graph.nodes()) < 2:
            return []

        try:
            undirected = self.graph.to_undirected()
            return list(nx.community.greedy_modularity_communities(undirected))
        except:
            return []

    def save(self):
        """保存图到文件"""
        if not self.graph:
            return

        # 保存为 GraphML 格式
        graph_file = GRAPH_PATH / "knowledge_graph.graphml"
        nx.write_graphml(self.graph, str(graph_file))

    def load(self):
        """从文件加载图"""
        graph_file = GRAPH_PATH / "knowledge_graph.graphml"
        if graph_file.exists():
            self.graph = nx.read_graphml(str(graph_file))

    def get_stats(self) -> dict:
        """获取图统计信息"""
        return {
            'node_count': self.graph.number_of_nodes(),
            'edge_count': self.graph.number_of_edges(),
            'orphan_count': len(self.find_orphans()),
            'density': nx.density(self.graph) if self.graph else 0
        }
