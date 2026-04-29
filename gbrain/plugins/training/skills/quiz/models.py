"""
考核模式数据模型
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QuizItem:
    """测验题目"""
    id: int
    type: str  # choice/true_false/blank
    question: str
    options: list[str] = field(default_factory=list)
    correct_answer: str = ""
    explanation: str = ""


@dataclass
class QuizResult:
    """考核结果"""
    score: float  # 得分 0-100
    passed: bool  # 是否通过（>=60）
    total_questions: int
    correct_count: int
    wrong_count: int
    answers: list[dict] = field(default_factory=list)


@dataclass
class QuizState:
    """考核状态"""
    current_question: int = 0
    total_questions: int = 0
    answers: list[str] = field(default_factory=list)
    score: float = 0.0
    is_completed: bool = False
