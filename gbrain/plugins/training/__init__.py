"""
培训插件模块

子模块：
- models: 数据模型
- events: 事件总线
- course_gen: 课件生成器
- state_machine: 学习状态机
- quiz_engine: 考核引擎
- task_pusher: 任务推送器
- dashboard: 数据看板
"""

from gbrain.plugins.training.models import (
    TaskType, TaskStatus, LearningState, EmployeeRole,
    Employee, QuizItem, TrainingTask, LearningProgress, QuizResult
)
from gbrain.plugins.training.learning_agent import LearningAgent
from gbrain.plugins.training.chat_engine import TourEngine, QAEngine, QuizEngine

__all__ = [
    "TaskType", "TaskStatus", "LearningState", "EmployeeRole",
    "Employee", "QuizItem", "TrainingTask", "LearningProgress", "QuizResult",
    "LearningAgent", "TourEngine", "QAEngine", "QuizEngine"
]
