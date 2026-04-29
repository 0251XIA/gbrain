"""
场景学习数据模型
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Scene:
    """学习场景"""
    index: int
    title: str
    description: str
    knowledge_points: list[str] = field(default_factory=list)
    correct_answer: str = ""
    explanation: str = ""
    hint: str = ""


@dataclass
class SceneChain:
    """场景链"""
    task_id: str
    scenes: list[Scene]
    weak_points: list[str] = field(default_factory=list)


@dataclass
class SceneLearningResult:
    """场景学习结果"""
    content: str
    scene_index: int = 0
    total_scenes: int = 0
    scene_title: str = ""
    is_completed: bool = False
    awaiting_answer: bool = True
    evaluation: Optional[dict] = None
