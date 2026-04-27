"""
LearningAgent - 引导式学习智能体

状态机：tour -> quiz -> completed
"""

from typing import Optional

from .chat_engine import TourEngine, QAEngine, QuizEngine


# ========== 状态定义 ==========

VALID_STAGES = ["tour", "quiz", "completed"]

STAGE_DESCRIPTIONS = {
    "tour": "课程学习",
    "quiz": "考核阶段",
    "completed": "已完成",
}

WELCOME_MESSAGES = {
    "tour": """欢迎开始学习！

我将带你学习这份课件。输入任意内容推进到下一个知识点。

📖 输入"开始"启动学习！""",

    "quiz": """考核环节开始！

准备好接受考核了吗？
- 选择题请输入 A/B/C/D
- 判断题请输入 对/错
- 简答题请直接输入你的答案

输入"开始考核"或任意内容开始第一题。""",

    "completed": """恭喜完成学习和考核！

学习已完成，感谢你的参与！

如果需要重新学习，请输入"重新开始"。""",
}


# ========== 特殊指令 ==========

QUIZ_TRIGGER_KEYWORDS = ["开始考核", "考核", "考试"]


# ========== LearningAgent 类 ==========

class LearningAgent:
    """
    引导式学习智能体

    负责协调学习引擎和考核引擎，管理学习状态流转。
    """

    def __init__(self, task_id: str, content: str, task_title: str, progress_id: str = None) -> None:
        """
        初始化 LearningAgent

        Args:
            task_id: 培训任务 ID
            content: 课件内容
            task_title: 培训任务标题
            progress_id: 学习进度 ID（用于保存考核记录）
        """
        self.task_id = task_id
        self.content = content
        self.task_title = task_title
        self.progress_id = progress_id

        # 状态机
        self._stage: str = "tour"

        # 初始化引擎
        self.tour_engine = TourEngine(content)
        self.quiz_engine = QuizEngine(content)

        # 考核相关状态
        self._quiz_attempts: int = 0  # 考核次数
        self._needs_relearn: bool = False  # 是否需要重新学习

        # 当前活跃引擎
        self._current_engine = self.tour_engine

    @property
    def stage(self) -> str:
        """获取当前阶段"""
        return self._stage

    def set_stage(self, stage: str) -> None:
        """
        切换学习阶段

        Args:
            stage: 目标阶段 (tour | quiz | completed)

        Raises:
            ValueError: 无效的阶段名称
        """
        if stage not in VALID_STAGES:
            raise ValueError(f"Invalid stage: {stage}. Must be one of {VALID_STAGES}")

        self._stage = stage

        # 更新当前引擎
        if stage == "tour":
            self._current_engine = self.tour_engine
        elif stage == "quiz":
            self._current_engine = self.quiz_engine
        else:
            # completed 阶段不涉及引擎对话
            self._current_engine = None

    def get_welcome_message(self) -> dict:
        """
        获取当前阶段的欢迎消息

        Returns:
            响应格式的 dict
        """
        content = WELCOME_MESSAGES.get(self._stage, "未知阶段")

        return {
            "type": self._get_response_type(),
            "content": content,
            "metadata": {
                "stage": self._stage,
                "stage_description": STAGE_DESCRIPTIONS.get(self._stage, ""),
                "engine": self._get_engine_name(),
            }
        }

    async def chat(self, message: str) -> dict:
        """
        处理员工消息，根据当前阶段调用对应引擎

        Args:
            message: 员工输入

        Returns:
            响应格式的 dict
        """
        # 检查是否需要重新学习
        if self._needs_relearn and message in ["重新学习", "重新开始", "重新开始学习"]:
            self._needs_relearn = False
            self._quiz_attempts = 0
            self.tour_engine.reset()
            self.set_stage("tour")
            return self._build_response(
                message_type="message",
                content="好的，让我们重新开始学习！\n\n输入任意内容开始学习第一个知识点。"
            )

        # 检查是否触发考核
        if self._is_quiz_trigger(message) and self._stage == "tour":
            return self._start_quiz()

        # 根据当前阶段处理对话
        if self._stage == "tour":
            return await self._handle_tour(message)
        elif self._stage == "quiz":
            return await self._handle_quiz(message)
        elif self._stage == "completed":
            if message in ["重新学习", "重新开始", "重新开始学习"]:
                self._needs_relearn = False
                self._quiz_attempts = 0
                self.tour_engine.reset()
                self.set_stage("tour")
                return self._build_response(
                    message_type="message",
                    content="好的，让我们重新开始学习！\n\n输入任意内容开始学习第一个知识点。"
                )
            return self._build_response(
                message_type="message",
                content="学习已完成。如果需要重新学习，请输入\"重新开始\"。",
            )
        else:
            return self._build_response(
                message_type="message",
                content="未知阶段，请联系管理员。",
            )

    async def _start_quiz(self) -> dict:
        """开始考核"""
        # 基于知识点生成考核题
        quiz_items = self.tour_engine.generate_quiz_items(
            num_choice=3, num_judge=2, num_short=2
        )

        if not quiz_items:
            return self._build_response(
                message_type="message",
                content="抱歉，无法生成考核题，请联系管理员。"
            )

        # 设置考核题
        self.quiz_engine.set_quiz_items(quiz_items)
        self.set_stage("quiz")

        # 获取第一题
        first_question = self.quiz_engine.get_current_question()
        if not first_question:
            return self._build_response(
                message_type="message",
                content="抱歉，无法获取考核题。"
            )

        response = "📋 考核开始！\n\n"
        response += f"共 {len(quiz_items)} 道题：3道选择题 + 2道判断题 + 2道简答题\n"
        response += f"满分100分，70分及格。\n\n"
        response += f"第一题：\n{first_question['question']}\n"

        if first_question['question_type'] == 'choice':
            for i, opt in enumerate(first_question['options']):
                response += f"  {'ABCD'[i]}. {opt}\n"
        elif first_question['question_type'] == 'judge':
            response += "  A. 对  B. 错\n"

        return self._build_response(
            message_type="quiz",
            content=response,
            metadata={"quiz_started": True, "question_index": 0}
        )

    async def _handle_tour(self, message: str) -> dict:
        """处理导览阶段对话"""
        response = await self.tour_engine.chat(message)

        # 检查是否学习完成
        if "学习完成" in response:
            # 自动进入考核
            return await self._start_quiz()

        return self._build_response(
            message_type="message",
            content=response,
        )

    def get_progress(self) -> dict:
        """
        获取学习进度

        Returns:
            进度信息 dict
        """
        stage_index = VALID_STAGES.index(self._stage) if self._stage in VALID_STAGES else 0
        total_stages = len(VALID_STAGES) - 1  # 减去 completed

        return {
            "task_id": self.task_id,
            "task_title": self.task_title,
            "current_stage": self._stage,
            "stage_description": STAGE_DESCRIPTIONS.get(self._stage, ""),
            "stage_index": stage_index,
            "total_stages": total_stages,
            "progress_percent": int((stage_index / total_stages) * 100),
        }

    # ========== 内部方法 ==========

    def _is_quiz_trigger(self, message: str) -> bool:
        """检查是否是触发测验的指令"""
        return any(keyword in message for keyword in QUIZ_TRIGGER_KEYWORDS)

    def _get_response_type(self) -> str:
        """获取当前阶段对应的响应类型"""
        type_mapping = {
            "tour": "tour_end",
            "quiz": "quiz",
            "completed": "message",
        }
        return type_mapping.get(self._stage, "message")

    def _get_engine_name(self) -> Optional[str]:
        """获取当前引擎名称"""
        engine_mapping = {
            "tour": "TourEngine",
            "quiz": "QuizEngine",
        }
        return engine_mapping.get(self._stage)

    def _build_response(
        self,
        message_type: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        构建标准响应格式

        Args:
            message_type: 消息类型
            content: 消息内容
            metadata: 元数据

        Returns:
            标准响应格式 dict
        """
        base_metadata = {
            "stage": self._stage,
            "engine": self._get_engine_name(),
        }
        if metadata:
            base_metadata.update(metadata)

        return {
            "type": message_type,
            "content": content,
            "metadata": base_metadata,
        }

    async def _handle_quiz(self, message: str) -> dict:
        """处理考核阶段对话"""
        response = await self.quiz_engine.chat(message)

        # 检查是否考核结束
        current_q = self.quiz_engine.get_current_question()
        if current_q is None:
            # 考核结束，处理结果
            score = self.quiz_engine.get_score()
            passed = self.quiz_engine.is_passed()
            self._quiz_attempts += 1

            # 保存考核记录
            self._save_quiz_record(score, passed)

            if passed:
                self.set_stage("completed")
                return self._build_response(
                    message_type="quiz",
                    content=response,
                    metadata={"quiz_completed": True, "passed": True, "score": score}
                )
            else:
                if self._quiz_attempts >= 2:
                    # 重考2次都不通过，需要重新学习
                    self._needs_relearn = True
                    self.set_stage("completed")
                    return self._build_response(
                        message_type="quiz",
                        content=response + "\n\n⚠️ 考核未通过，且已达到最大重考次数（2次）。\n请重新学习后再参加考核。\n\n输入\"重新学习\"开始。",
                        metadata={"quiz_completed": True, "passed": False, "score": score, "needs_relearn": True}
                    )
                else:
                    # 还有重考机会
                    return self._build_response(
                        message_type="quiz",
                        content=response + f"\n\n📚 还有 {2 - self._quiz_attempts} 次补考机会。\n输入\"重新考核\"或任意内容再次参加考核。",
                        metadata={"quiz_completed": True, "passed": False, "score": score, "attempts_left": 2 - self._quiz_attempts}
                    )

        return self._build_response(
            message_type="quiz",
            content=response,
            metadata={"quiz_in_progress": True}
        )

    def _save_quiz_record(self, score: float, passed: bool) -> None:
        """保存考核记录"""
        try:
            from gbrain.database import Database
            from gbrain.plugins.training.models import QuizRecord
            import uuid

            db = Database()
            record = QuizRecord(
                id=str(uuid.uuid4()),
                progress_id=self.progress_id or "",
                task_id=self.task_id,
                total_score=score,
                passed=passed,
                attempts=self._quiz_attempts,
                answers=self.quiz_engine.get_answers()
            )

            db.insert_quiz_record({
                'id': record.id,
                'progress_id': record.progress_id,
                'task_id': record.task_id,
                'total_score': record.total_score,
                'passed': record.passed,
                'attempts': record.attempts,
                'answers': record.answers
            })
        except Exception as e:
            print(f"保存考核记录失败: {e}")
