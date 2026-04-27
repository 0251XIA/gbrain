"""
LearningAgent - 引导式学习智能体

状态机：learning -> ready_to_quiz -> quiz -> completed/failed
学习70% + 考核30%，考核不可重考
"""

from typing import Optional

from .chat_engine import QuizEngine, SceneLearningEngine


# ========== 状态定义 ==========

VALID_STAGES = ["learning", "ready_to_quiz", "quiz", "completed", "failed"]

STAGE_DESCRIPTIONS = {
    "learning": "场景学习中",
    "ready_to_quiz": "准备考核",
    "quiz": "参加考核",
    "completed": "全部完成",
    "failed": "考核未通过"
}

WELCOME_MESSAGES = {
    "learning": """欢迎开始学习！

我将带你通过真实工作场景来学习这份培训内容。
每个场景先让你思考如何处理，然后再给出正确答案和讲解。

准备好开始第一个场景了吗？

输入"开始"启动学习！""",

    "ready_to_quiz": """恭喜完成所有场景学习！

你已经掌握了培训的核心内容。
准备好参加考核了吗？

输入"开始考核"进入考核环节。""",

    "quiz": """考核环节开始！

准备好接受考核了吗？
- 选择题请输入 A/B/C/D
- 判断题请输入 对/错
- 简答题请直接输入你的答案

注意：考核只有一次机会，请认真作答。

输入"开始考核"或任意内容开始第一题。""",

    "completed": """🎉 恭喜完成学习和考核！

学习已完成，感谢你的参与！
希望这些内容对你有帮助。""",

    "failed": """很遗憾，本次考核未通过。

由于考核只有一次机会，你需要重新学习整个培训内容后，才能再次参加考核。

输入"重新学习"开始新一轮学习。""",
}


# ========== 特殊指令 ==========

QUIZ_TRIGGER_KEYWORDS = ["开始考核", "考核", "考试"]
RESTART_KEYWORDS = ["重新学习", "重新开始"]


# ========== LearningAgent 类 ==========

class LearningAgent:
    """
    引导式学习智能体

    负责协调场景学习引擎和考核引擎，管理学习状态流转。
    学习70% + 考核30%，考核不可重考。
    """

    def __init__(self, task_id: str, content: str, task_title: str, progress_id: str = None,
                 scene_chain: list = None) -> None:
        """
        初始化 LearningAgent

        Args:
            task_id: 培训任务 ID
            content: 课件内容
            task_title: 培训任务标题
            progress_id: 学习进度 ID（用于保存考核记录）
            scene_chain: 场景链（可选，不提供则自动生成）
        """
        self.task_id = task_id
        self.content = content
        self.task_title = task_title
        self.progress_id = progress_id

        # 状态机
        self._stage: str = "learning"

        # 初始化场景学习引擎
        self.scene_engine = SceneLearningEngine(content, scene_chain)
        self.quiz_engine = QuizEngine(content)

        # 学习得分（来自场景学习）
        self._learning_score: float = 0.0

        # 当前活跃引擎
        self._current_engine = self.scene_engine

    def set_scene_chain(self, scene_chain: list) -> None:
        """设置场景链"""
        self.scene_engine.set_scene_chain(scene_chain)

    def get_scene_progress(self) -> dict:
        """获取场景学习进度"""
        return self.scene_engine.get_progress()

    @property
    def stage(self) -> str:
        """获取当前阶段"""
        return self._stage

    def set_stage(self, stage: str) -> None:
        """
        切换学习阶段

        Args:
            stage: 目标阶段 (learning | ready_to_quiz | quiz | completed | failed)

        Raises:
            ValueError: 无效的阶段名称
        """
        if stage not in VALID_STAGES:
            raise ValueError(f"Invalid stage: {stage}. Must be one of {VALID_STAGES}")

        self._stage = stage

        # 更新当前引擎
        if stage == "learning":
            self._current_engine = self.scene_engine
        elif stage == "quiz":
            self._current_engine = self.quiz_engine
        else:
            self._current_engine = None

    def get_welcome_message(self) -> dict:
        """
        获取当前阶段的欢迎消息

        Returns:
            响应格式的 dict
        """
        content = WELCOME_MESSAGES.get(self._stage, "未知阶段")

        # 如果是 learning 阶段，显示第一个场景
        metadata = {
            "stage": self._stage,
            "stage_description": STAGE_DESCRIPTIONS.get(self._stage, ""),
            "engine": self._get_engine_name(),
        }

        if self._stage == "learning":
            scene = self.scene_engine.get_current_scene()
            if scene:
                metadata["current_scene"] = {
                    "index": self.scene_engine.current_scene_index + 1,
                    "total": len(self.scene_engine.scene_chain),
                    "title": scene.get('title', ''),
                    "description": scene.get('description', ''),
                    "hint": scene.get('hint', '')
                }

        return {
            "type": self._get_response_type(),
            "content": content,
            "metadata": metadata
        }

    async def chat(self, message: str) -> dict:
        """
        处理员工消息，根据当前阶段调用对应引擎

        Args:
            message: 员工输入

        Returns:
            响应格式的 dict
        """
        # 检查是否触发考核
        if self._is_quiz_trigger(message) and self._stage in ["learning", "ready_to_quiz"]:
            return await self._start_quiz()

        # 检查是否需要重新学习
        if message in RESTART_KEYWORDS and self._stage in ["completed", "failed"]:
            return await self._restart_learning()

        # 根据当前阶段处理对话
        if self._stage == "learning":
            return await self._handle_learning(message)
        elif self._stage == "ready_to_quiz":
            return self._build_response(
                message_type="message",
                content=WELCOME_MESSAGES.get("ready_to_quiz", "")
            )
        elif self._stage == "quiz":
            return await self._handle_quiz(message)
        elif self._stage == "completed":
            return self._build_response(
                message_type="message",
                content=WELCOME_MESSAGES.get("completed", "")
            )
        elif self._stage == "failed":
            return self._build_response(
                message_type="message",
                content=WELCOME_MESSAGES.get("failed", "")
            )
        else:
            return self._build_response(
                message_type="message",
                content="未知阶段，请联系管理员。",
            )

    async def _start_quiz(self) -> dict:
        """开始考核"""
        # 基于场景学习结果生成考核题
        quiz_items = self.scene_engine.generate_quiz_items(num_questions=7)

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

        # 构建总分计算说明
        learning_score = self.scene_engine.learning_score
        response = "📋 考核开始！\n\n"
        response += f"共 {len(quiz_items)} 道题，满分100分。\n"
        response += f"其中学习得分占 {learning_score:.0f} 分（70%权重），\n"
        response += f"考核得分占 100 分（30%权重）。\n"
        response += f"70分及格。\n\n"
        response += f"第一题：\n{first_question['question']}\n"

        if first_question['question_type'] == 'choice':
            for i, opt in enumerate(first_question['options']):
                response += f"  {'ABCD'[i]}. {opt}\n"
        elif first_question['question_type'] == 'judge':
            response += "  A. 对  B. 错\n"

        return self._build_response(
            message_type="quiz",
            content=response,
            metadata={
                "quiz_started": True,
                "question_index": 0,
                "learning_score": learning_score,
                "learning_weight": 0.7,
                "quiz_weight": 0.3
            }
        )

    async def _restart_learning(self) -> dict:
        """重新开始学习"""
        self.scene_engine.reset()
        self._learning_score = 0.0
        self.set_stage("learning")

        scene = self.scene_engine.get_current_scene()
        if scene:
            content = "好的，让我们重新开始学习！\n\n"
            content += f"📋 当前场景：{scene.get('title', '')}\n{scene.get('description', '')}"
            if scene.get('hint'):
                content += f"\n\n💡 提示：{scene.get('hint', '')}"
        else:
            content = "抱歉，场景加载失败，请联系管理员。"

        return self._build_response(
            message_type="message",
            content=content
        )

    async def _handle_learning(self, message: str) -> dict:
        """处理场景学习"""
        result = await self.scene_engine.chat(message)

        # 更新学习得分
        self._learning_score = result.get('learning_score', 0)

        response_content = result.get('content', '')

        if result.get('is_completed'):
            # 学习完成，进入准备考核阶段
            self.set_stage("ready_to_quiz")
            response_content += f"\n\n{WELCOME_MESSAGES.get('ready_to_quiz', '')}"

        return self._build_response(
            message_type="scene",
            content=response_content,
            metadata={
                "scene_result": {
                    "is_correct": result.get('evaluation', {}).get('is_correct', False),
                    "score": result.get('evaluation', {}).get('score', 0),
                    "feedback": result.get('evaluation', {}).get('feedback', '')
                },
                "next_scene": result.get('next_scene'),
                "is_completed": result.get('is_completed', False),
                "learning_score": self._learning_score,
                "weak_points": result.get('weak_points', [])
            }
        )

    def get_progress(self) -> dict:
        """
        获取学习进度

        Returns:
            进度信息 dict
        """
        stage_index = VALID_STAGES.index(self._stage) if self._stage in VALID_STAGES else 0
        total_stages = len(VALID_STAGES)

        return {
            "task_id": self.task_id,
            "task_title": self.task_title,
            "current_stage": self._stage,
            "stage_description": STAGE_DESCRIPTIONS.get(self._stage, ""),
            "stage_index": stage_index,
            "total_stages": total_stages,
            "progress_percent": int((stage_index / total_stages) * 100),
            "scene_progress": self.get_scene_progress(),
            "learning_score": self._learning_score,
        }

    # ========== 内部方法 ==========

    def _is_quiz_trigger(self, message: str) -> bool:
        """检查是否是触发考核的指令"""
        return any(keyword in message for keyword in QUIZ_TRIGGER_KEYWORDS)

    def _get_response_type(self) -> str:
        """获取当前阶段对应的响应类型"""
        type_mapping = {
            "learning": "scene",
            "ready_to_quiz": "message",
            "quiz": "quiz",
            "completed": "message",
            "failed": "message",
        }
        return type_mapping.get(self._stage, "message")

    def _get_engine_name(self) -> Optional[str]:
        """获取当前引擎名称"""
        engine_mapping = {
            "learning": "SceneLearningEngine",
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
            quiz_score = self.quiz_engine.get_score()

            # 计算总分 = 学习得分(70%) + 考核得分(30%)
            # 但考核满分是100，学习满分是100，这里需要转换
            # 学习得分占 70 分，考核得分占 30 分
            total_score = self._learning_score * 0.7 + quiz_score * 0.3
            passed = total_score >= 70

            # 保存考核记录
            self._save_quiz_record(total_score, passed, quiz_score)

            if passed:
                self.set_stage("completed")
                return self._build_response(
                    message_type="quiz",
                    content=response,
                    metadata={
                        "quiz_completed": True,
                        "passed": True,
                        "total_score": total_score,
                        "learning_score": self._learning_score,
                        "quiz_score": quiz_score
                    }
                )
            else:
                # 考核未通过（不可重考）
                self.set_stage("failed")
                return self._build_response(
                    message_type="quiz",
                    content=response + "\n\n" + WELCOME_MESSAGES.get("failed", ""),
                    metadata={
                        "quiz_completed": True,
                        "passed": False,
                        "total_score": total_score,
                        "learning_score": self._learning_score,
                        "quiz_score": quiz_score,
                        "cannot_retry": True
                    }
                )

        return self._build_response(
            message_type="quiz",
            content=response,
            metadata={"quiz_in_progress": True}
        )

    def _save_quiz_record(self, total_score: float, passed: bool, quiz_score: float) -> None:
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
                total_score=total_score,
                passed=passed,
                attempts=1,  # 不可重考，所以总是1
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
