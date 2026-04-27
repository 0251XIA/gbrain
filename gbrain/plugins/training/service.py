"""
培训模块服务层 - 核心业务逻辑
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Optional

from gbrain.database import Database
from gbrain.plugins.training.models import (
    Employee, TrainingTask, LearningProgress, QuizItem, QuizResult,
    TaskType, TaskStatus, LearningState, EmployeeRole
)


class TrainingService:
    """培训服务"""

    def __init__(self):
        self.db = Database()

    # ========== 员工管理 ==========

    def create_employee(self, name: str, department: str, position: str,
                       role: str = "employee", join_date: str = None) -> Employee:
        """创建员工"""
        employee = Employee(
            id=str(uuid.uuid4()),
            name=name,
            department=department,
            position=position,
            join_date=datetime.fromisoformat(join_date) if join_date else datetime.now(),
            role=EmployeeRole(role),
            created_at=datetime.now()
        )
        self.db.insert_employee({
            'id': employee.id,
            'name': employee.name,
            'department': employee.department,
            'position': employee.position,
            'join_date': employee.join_date.isoformat(),
            'role': employee.role.value,
        })
        return employee

    def get_employee(self, employee_id: str) -> Optional[Employee]:
        """获取员工"""
        data = self.db.get_employee(employee_id)
        if not data:
            return None
        return self._dict_to_employee(data)

    def get_all_employees(self) -> list[Employee]:
        """获取所有员工"""
        return [self._dict_to_employee(d) for d in self.db.get_all_employees()]

    def _dict_to_employee(self, data: dict) -> Employee:
        return Employee(
            id=data['id'],
            name=data['name'],
            department=data['department'],
            position=data['position'],
            join_date=datetime.fromisoformat(data['join_date']) if data.get('join_date') else datetime.now(),
            role=EmployeeRole(data.get('role', 'employee')),
            wecom_openid=data.get('wecom_openid', ''),
            dingtalk_userid=data.get('dingtalk_userid', ''),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )

    # ========== 任务管理 ==========

    def create_task(self, title: str, description: str, task_type: str,
                   content_source: list = None, deadline: str = None,
                   priority: int = 2, created_by: str = None,
                   content: str = "", quiz_items: list = None) -> TrainingTask:
        """创建培训任务"""
        task = TrainingTask(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            task_type=TaskType(task_type),
            content_source=content_source or [],
            quiz_items=quiz_items or [],
            content=content,
            deadline=datetime.fromisoformat(deadline) if deadline else datetime.now() + timedelta(days=7),
            priority=priority,
            status=TaskStatus.DRAFT,
            created_by=created_by or "",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.insert_training_task({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'task_type': task.task_type.value,
            'content_source': task.content_source,
            'quiz_items': [q.__dict__ if hasattr(q, '__dict__') else q for q in (quiz_items or [])],
            'content': task.content,
            'deadline': task.deadline.isoformat(),
            'priority': task.priority,
            'status': task.status.value,
            'created_by': task.created_by,
        })
        return task

    def get_task(self, task_id: str) -> Optional[TrainingTask]:
        """获取任务"""
        data = self.db.get_training_task(task_id)
        if not data:
            return None
        return self._dict_to_task(data)

    def get_all_tasks(self, status: str = None) -> list[TrainingTask]:
        """获取所有任务"""
        return [self._dict_to_task(d) for d in self.db.get_all_training_tasks(status)]

    def update_task_status(self, task_id: str, status: str) -> bool:
        """更新任务状态"""
        return self.db.update_training_task_status(task_id, status)

    def publish_task(self, task_id: str) -> bool:
        """发布任务"""
        return self.update_task_status(task_id, TaskStatus.PUBLISHED.value)

    def archive_task(self, task_id: str) -> bool:
        """归档任务"""
        return self.update_task_status(task_id, TaskStatus.ARCHIVED.value)

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        return self.db.delete_training_task(task_id)

    def update_task(self, task_id: str, **kwargs) -> bool:
        """更新任务内容"""
        allowed = ['content', 'description', 'title', 'deadline', 'priority']
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        updates['updated_at'] = datetime.now().isoformat()
        return self.db.update_training_task(task_id, updates)

    def _dict_to_task(self, data: dict) -> TrainingTask:
        quiz_items = []
        if data.get('quiz_items'):
            for q in data['quiz_items']:
                if isinstance(q, dict):
                    quiz_items.append(QuizItem(
                        id=q.get('id', ''),
                        question=q.get('question', ''),
                        options=q.get('options', []),
                        correct_index=q.get('correct_index', 0),
                        explanation=q.get('explanation', '')
                    ))

        return TrainingTask(
            id=data['id'],
            title=data['title'],
            description=data.get('description', ''),
            task_type=TaskType(data.get('task_type', 'onboarding')),
            content_source=data.get('content_source', []),
            quiz_items=quiz_items,
            content=data.get('content', ''),
            deadline=datetime.fromisoformat(data['deadline']) if data.get('deadline') else datetime.now(),
            priority=data.get('priority', 2),
            status=TaskStatus(data.get('status', 'draft')),
            created_by=data.get('created_by', ''),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now()
        )

    # ========== 学习进度 ==========

    def assign_task_to_employee(self, task_id: str, employee_id: str) -> LearningProgress:
        """分配任务给员工"""
        progress = LearningProgress(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            task_id=task_id,
            state=LearningState.NOT_STARTED,
            created_at=datetime.now()
        )
        self.db.insert_learning_progress({
            'id': progress.id,
            'employee_id': progress.employee_id,
            'task_id': progress.task_id,
            'state': progress.state.value,
        })
        return progress

    def get_progress(self, progress_id: str) -> Optional[LearningProgress]:
        """获取学习进度"""
        data = self.db.get_learning_progress(progress_id)
        if not data:
            return None
        return self._dict_to_progress(data)

    def get_employee_progress(self, employee_id: str) -> list[LearningProgress]:
        """获取员工所有学习进度"""
        return [self._dict_to_progress(d) for d in self.db.get_employee_progress(employee_id)]

    def get_task_progress(self, task_id: str) -> list[LearningProgress]:
        """获取任务的所有学习进度"""
        return [self._dict_to_progress(d) for d in self.db.get_task_progress(task_id)]

    def start_learning(self, progress_id: str) -> bool:
        """开始学习"""
        return self.db.update_learning_progress(progress_id, {
            'state': LearningState.LEARNING.value,
            'started_at': datetime.now().isoformat()
        })

    def submit_quiz(self, progress_id: str, answers: list[dict]) -> QuizResult:
        """提交测验并评分"""
        progress_data = self.db.get_learning_progress(progress_id)
        if not progress_data:
            raise ValueError("Progress not found")

        task = self.get_task(progress_data['task_id'])
        if not task:
            raise ValueError("Task not found")

        # 评分
        correct_count = 0
        for i, q in enumerate(task.quiz_items):
            if i < len(answers) and answers[i].get('answer') == q.correct_index:
                correct_count += 1

        score = (correct_count / len(task.quiz_items) * 100) if task.quiz_items else 0
        passed = score >= 60

        # 记录结果
        result = QuizResult(
            id=str(uuid.uuid4()),
            progress_id=progress_id,
            employee_id=progress_data['employee_id'],
            task_id=progress_data['task_id'],
            score=score,
            passed=passed,
            answers=[a.get('answer', -1) for a in answers],
            submitted_at=datetime.now()
        )

        self.db.insert_quiz_result({
            'id': result.id,
            'progress_id': result.progress_id,
            'employee_id': result.employee_id,
            'task_id': result.task_id,
            'score': result.score,
            'passed': result.passed,
            'answers': result.answers
        })

        # 更新进度
        current_attempts = progress_data.get('quiz_attempts', 0)
        new_state = LearningState.COMPLETED.value if passed else LearningState.QUIZ_FAILED.value
        updates = {
            'quiz_score': score,
            'quiz_attempts': current_attempts + 1,
            'state': new_state
        }
        if passed:
            updates['completed_at'] = datetime.now().isoformat()

        self.db.update_learning_progress(progress_id, updates)

        return result

    def _dict_to_progress(self, data: dict) -> LearningProgress:
        return LearningProgress(
            id=data['id'],
            employee_id=data['employee_id'],
            task_id=data['task_id'],
            state=LearningState(data.get('state', 'not_started')),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            quiz_score=data.get('quiz_score', 0.0),
            quiz_attempts=data.get('quiz_attempts', 0),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now()
        )

    # ========== 数据看板 ==========

    def get_dashboard_stats(self) -> dict:
        """获取看板统计数据"""
        return self.db.get_dashboard_stats()

    def get_task_stats(self) -> list[dict]:
        """获取各任务统计"""
        tasks = self.get_all_tasks(status='published')
        stats = []
        for task in tasks:
            progress_list = self.db.get_task_progress(task.id)
            total = len(progress_list)
            completed = len([p for p in progress_list if p.get('state') in ('completed', 'mastered')])
            stats.append({
                'task_id': task.id,
                'task_title': task.title,
                'task_type': task.task_type.value,
                'total': total,
                'completed': completed,
                'completion_rate': f"{(completed/total*100):.1f}%" if total > 0 else "0%"
            })
        return stats

    def get_incomplete_employees(self) -> list[dict]:
        """获取未完成员工列表"""
        employees = self.get_all_employees()
        incomplete = []
        for emp in employees:
            progress_list = self.get_employee_progress(emp.id)
            for p in progress_list:
                if p.state in (LearningState.NOT_STARTED, LearningState.LEARNING, LearningState.QUIZ_FAILED):
                    task = self.get_task(p.task_id)
                    if task:
                        incomplete.append({
                            'employee_id': emp.id,
                            'name': emp.name,
                            'department': emp.department,
                            'task_id': task.id,
                            'task_title': task.title,
                            'state': p.state.value
                        })
        return incomplete


# 全局服务实例
_service: Optional[TrainingService] = None


def get_training_service() -> TrainingService:
    global _service
    if _service is None:
        _service = TrainingService()
    return _service
