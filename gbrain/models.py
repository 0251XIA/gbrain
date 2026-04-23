"""
GBrain 数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Page:
    """知识库页面"""
    id: str
    title: str
    content: str
    category: str = "通用"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)  # [[链接]] 格式
    embedding: Optional[list[float]] = None

    @property
    def file_path(self) -> str:
        return f"{KB_PATH}/{self.id}.md"


@dataclass
class Entity:
    """知识图谱实体"""
    id: str
    name: str
    entity_type: str  # person/concept/org/topic
    properties: dict = field(default_factory=dict)


@dataclass
class Relation:
    """知识图谱关系"""
    source: str  # 源实体 ID
    target: str  # 目标实体 ID
    relation_type: str  # works_at/founded/attended/related_to
    properties: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    """搜索结果"""
    page_id: str
    title: str
    snippet: str
    score: float
    source: str = "mixed"  # vector/bm25/rrf


@dataclass
class QARecord:
    """问答记录"""
    id: str
    question: str
    answer: str
    created_at: datetime = field(default_factory=datetime.now)
    archived: bool = False
    pending: bool = False  # 待跟进
