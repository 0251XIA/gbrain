"""
GBrain 进化模块 - 知识库结构分析与自动进化
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List

from .graph import KnowledgeGraph


class Evolver:
    """知识库进化引擎"""

    def __init__(self, db=None, graph: KnowledgeGraph = None):
        self.db = db
        self.graph = graph or KnowledgeGraph(db)

    def analyze(self) -> Dict:
        """运行完整分析"""
        print("=" * 50)
        print("GBrain 知识库分析")
        print("=" * 50)

        graph_stats = self.graph.get_stats()
        print(f"\n📊 图谱统计：")
        print(f"   节点数：{graph_stats['node_count']}")
        print(f"   边数：{graph_stats['edge_count']}")
        print(f"   孤立节点：{graph_stats['orphan_count']}")

        if self.db:
            pages = self.db.get_all_pages()
            print(f"\n📄 页面统计：")
            print(f"   总页面数：{len(pages)}")

            categories = {}
            for page in pages:
                cat = page.get('category', '通用')
                categories[cat] = categories.get(cat, 0) + 1

            for cat, count in categories.items():
                print(f"   {cat}: {count}")

        return {
            'graph': graph_stats,
            'timestamp': datetime.now().isoformat()
        }

    def find_gaps(self) -> List[Dict]:
        """发现缺失"""
        gaps = []

        orphans = self.graph.find_orphans()
        for orphan in orphans:
            gaps.append({
                'type': 'orphan',
                'node': orphan,
                'suggestion': f"'{orphan}' 是孤立节点，建议添加关联"
            })

        return gaps

    def generate_report(self, result: Dict) -> str:
        """生成报告"""
        report = f"""# GBrain 知识库分析报告

**生成时间**：{result['timestamp']}

---

## 图谱统计

| 指标 | 数值 |
|------|------|
| 节点数 | {result['graph']['node_count']} |
| 边数 | {result['graph']['edge_count']} |
| 孤立节点 | {result['graph']['orphan_count']} |

---

## 建议

"""
        gaps = self.find_gaps()
        if gaps:
            for i, gap in enumerate(gaps[:5], 1):
                report += f"{i}. {gap['suggestion']}\n"
        else:
            report += "未发现明显问题。\n"

        return report
