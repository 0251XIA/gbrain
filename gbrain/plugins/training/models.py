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
    PUBLISHING = "publishing"     # 发布中
    PUBLISHED = "published"       # 已发布
    ARCHIVED = "archived"         # 已归档


class LearningState(Enum):
    """学习状态"""
    NOT_STARTED = "not_started"    # 未开始
    LEARNING = "learning"          # 进行中（场景学习中）
    LEARNING_COMPLETED = "learning_completed"  # 学习完成（可参加考核）
    READY_TO_QUIZ = "ready_to_quiz"  # 准备就绪（学习完成，可参加考核）
    QUIZ_COMPLETED = "quiz_completed"  # 考核完成
    COMPLETED = "completed"        # 全部完成（学习+考核都通过）
    FAILED = "failed"             # 考核未通过（不可重考，需重新学习）


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
    question_type: str = "choice"  # choice | judge | short_answer
    options: list[str] = field(default_factory=list)  # 选择题选项
    correct_index: int = 0  # 选择题正确答案索引
    correct_answer: str = ""  # 判断题答案 (true/false) | 简答题参考答案
    explanation: str = ""  # 题解
    keywords: list[str] = field(default_factory=list)  # 简答题评分关键词


@dataclass
class TrainingTask:
    """培训任务"""
    id: str
    title: str
    description: str
    task_type: TaskType
    content_source: list[str]     # 关联的 gbrain 知识库页面 ID
    quiz_items: list[QuizItem] = field(default_factory=list)
    scene_chain: list = field(default_factory=list)  # 预生成的学习场景链
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
    passed: bool                  # >= 70% 为通过
    answers: list[int]            # 员工答案列表
    submitted_at: datetime = field(default_factory=datetime.now)


@dataclass
class QuizRecord:
    """考核记录（详细）"""
    id: str
    progress_id: str
    task_id: str
    total_score: float  # 总分 0-100
    passed: bool  # >= 70% 为通过
    attempts: int = 0  # 第几次考核
    answers: list[dict] = field(default_factory=list)  # 每题答案详情
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Scene:
    """学习场景"""
    index: int                    # 场景索引（从1开始）
    title: str                    # 场景标题，如"场景1：客户基础接待"
    description: str              # 场景描述（具体工作情境）
    knowledge_points: list[str]  # 本场景涉及的知识点
    correct_answer: str           # 标准答案/正确做法
    explanation: str              # 讲解要点（用户答错时展示）
    hint: str = ""               # 提示信息


@dataclass
class SceneChain:
    """场景链（一个任务的所有场景）"""
    task_id: str
    scenes: list[Scene]           # 场景列表
    weak_points: list[str] = field(default_factory=list)  # 全局薄弱知识点


@dataclass
class LearningSession:
    """一次学习会话"""
    id: str
    employee_id: str
    task_id: str
    scene_index: int = 0         # 当前场景索引（0表示未开始）
    total_scenes: int = 0        # 总场景数
    status: str = "active"       # active | completed | abandoned
    scene_responses: list[dict] = field(default_factory=list)  # 每个场景的用户回答
    weak_points: list[str] = field(default_factory=list)  # 本会话中暴露的薄弱点
    learning_score: float = 0.0  # 学习得分（0-100）
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class SceneResponse:
    """用户对单个场景的响应"""
    scene_index: int
    user_response: str           # 用户回答
    ai_evaluation: str          # AI评价
    is_correct: bool            # 是否正确
    score: float                # 本场景得分
    knowledge_learned: list[str] = field(default_factory=list)  # 本场景涉及的知识点
