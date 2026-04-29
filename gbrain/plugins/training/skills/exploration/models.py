"""
探索模式数据模型
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExplorationResult:
    """探索结果"""
    content: str  # 回复内容
    related_knowledge: list[str] = None  # 相关知识点
    suggestions: list[str] = None  # 建议探索的方向

    def __post_init__(self):
        if self.related_knowledge is None:
            self.related_knowledge = []
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class ExplorationContext:
    """探索上下文"""
    topic: str  # 当前话题
    related_sections: list[str] = None  # 相关章节
    difficulty: str = "normal"  # 难度：easy/normal/advanced
