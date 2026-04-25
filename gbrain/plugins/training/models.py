"""
培训插件数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class TaskType(Enum):
    """任务类型"""
    ONBOARDING = "onboarding"      # 入职培训
    SKILL = "skill"               # 技能提升


class TaskStatus(Enum):
    """任务状态"""
    DRAFT = "draft"               # 草稿
    PUBLISHED = "published"       # 已发布
    ARCHIVED = "archived"         # 已归档


class LearningState(Enum):
    """学习状态"""
    NOT_STARTED = "not_started"    # 未开始
    LEARNING = "learning"          # 进行中
    QUIZ_FAILED = "quiz_failed"    # 测验不及格
    COMPLETED = "completed"        # 已完成
    MASTERED = "mastered"          # 已掌握


class EmployeeRole(Enum):
    """员工角色"""
    ADMIN = "admin"               # 管理员
    HR = "hr"                     # HR
    EMPLOYEE = "employee"          # 普通员工


@dataclass
class Employee:
    """员工"""
    id: str
    name: str
    department: str
    position: str
    join_date: datetime
    role: EmployeeRole = EmployeeRole.EMPLOYEE
    wecom_openid: str = ""
    dingtalk_userid: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class QuizItem:
    """测验题"""
    id: str
    question: str
    options: list[str]           # 选项列表
    correct_index: int            # 正确答案索引
    explanation: str = ""         # 题解


@dataclass
class TrainingTask:
    """培训任务"""
    id: str
    title: str
    description: str
    task_type: TaskType
    content_source: list[str]     # 关联的 gbrain 知识库页面 ID
    quiz_items: list[QuizItem] = field(default_factory=list)
    content: str = ""             # 课件正文内容
    deadline: datetime = None
    priority: int = 1             # 1=高，2=中，3=低
    status: TaskStatus = TaskStatus.DRAFT
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class LearningProgress:
    """学习进度"""
    id: str
    employee_id: str
    task_id: str
    state: LearningState = LearningState.NOT_STARTED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    quiz_score: float = 0.0
    quiz_attempts: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class QuizResult:
    """测验结果"""
    id: str
    progress_id: str
    employee_id: str
    task_id: str
    score: float                  # 0-100
    passed: bool                  # >= 60% 为通过
    answers: list[int]            # 员工答案列表
    submitted_at: datetime = field(default_factory=datetime.now)
