"""
LearningAgent - 引导式学习智能体

状态机：tour -> q_and_a -> quiz -> summary -> completed
"""

from typing import Optional

from .chat_engine import TourEngine, QAEngine, QuizEngine


# ========== 状态定义 ==========

VALID_STAGES = ["tour", "q_and_a", "quiz", "summary", "completed"]

STAGE_DESCRIPTIONS = {
    "tour": "课程导览",
    "q_and_a": "问答环节",
    "quiz": "测验考核",
    "summary": "学习总结",
    "completed": "已完成",
}

WELCOME_MESSAGES = {
    "tour": """欢迎开始学习之旅！

我将带你逐步学习这份课件。每个知识点按"是什么→为什么→怎么样"的顺序引导你理解。

📖 输入"开始"启动学习！""",

    "q_and_a": """现在进入问答环节！

你可以随时提问关于课程内容的问题，我会结合课件内容为你解答。

输入"开始测验"可以提前进入测验环节。""",

    "quiz": """测验环节开始！

准备好了吗？让我们通过几个问题检验你的学习成果。

注意：请使用 A/B/C/D 或 0/1/2/3 格式回答。""",

    "summary": """恭喜完成学习！

让我们回顾一下今天的学习内容...（此处由 AI 自动生成总结）""",

    "completed": """学习已完成，感谢你的参与！

如果需要重新学习，请输入"重新开始"。""",
}


# ========== 特殊指令 ==========

QUIZ_TRIGGER_KEYWORDS = ["开始测验", "我想测验", "测验"]


# ========== LearningAgent 类 ==========

class LearningAgent:
    """
    引导式学习智能体

    负责协调三个对话引擎（导览、问答、测验），
    管理学习状态流转，处理员工对话。
    """

    def __init__(self, task_id: str, content: str, task_title: str) -> None:
        """
        初始化 LearningAgent

        Args:
            task_id: 培训任务 ID
            content: 课件内容
            task_title: 培训任务标题
        """
        self.task_id = task_id
        self.content = content
        self.task_title = task_title

        # 状态机
        self._stage: str = "tour"

        # 初始化三个引擎
        self.tour_engine = TourEngine(content)
        self.qa_engine = QAEngine(content)
        self.quiz_engine = QuizEngine(content)

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
            stage: 目标阶段 (tour | q_and_a | quiz | summary | completed)

        Raises:
            ValueError: 无效的阶段名称
        """
        if stage not in VALID_STAGES:
            raise ValueError(f"Invalid stage: {stage}. Must be one of {VALID_STAGES}")

        self._stage = stage

        # 更新当前引擎
        if stage == "tour":
            self._current_engine = self.tour_engine
        elif stage == "q_and_a":
            self._current_engine = self.qa_engine
        elif stage == "quiz":
            self._current_engine = self.quiz_engine
        else:
            # summary / completed 阶段不涉及引擎对话
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
        # 检查特殊指令
        if self._is_quiz_trigger(message):
            if self._stage != "quiz":
                self.set_stage("quiz")
                return self._build_response(
                    message_type="message",
                    content="好的，现在开始测验环节！",
                )

        # 根据当前阶段处理对话
        if self._stage == "tour":
            return await self._handle_tour(message)
        elif self._stage == "q_and_a":
            return await self._handle_qa(message)
        elif self._stage == "quiz":
            return await self._handle_quiz(message)
        elif self._stage == "summary":
            return await self._handle_summary(message)
        elif self._stage == "completed":
            return self._build_response(
                message_type="message",
                content="学习已完成。如果需要重新学习，请输入\"重新开始\"。",
            )
        else:
            return self._build_response(
                message_type="message",
                content="未知阶段，请联系管理员。",
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
            "q_and_a": "q_and_a_end",
            "quiz": "quiz",
            "summary": "summary",
            "completed": "message",
        }
        return type_mapping.get(self._stage, "message")

    def _get_engine_name(self) -> Optional[str]:
        """获取当前引擎名称"""
        engine_mapping = {
            "tour": "TourEngine",
            "q_and_a": "QAEngine",
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

    async def _handle_tour(self, message: str) -> dict:
        """处理导览阶段对话"""
        response = await self.tour_engine.chat(message)

        return self._build_response(
            message_type="message",
            content=response,
        )

    async def _handle_qa(self, message: str) -> dict:
        """处理问答阶段对话"""
        response = await self.qa_engine.chat(message)

        return self._build_response(
            message_type="message",
            content=response,
        )

    async def _handle_quiz(self, message: str) -> dict:
        """处理测验阶段对话"""
        response = await self.quiz_engine.chat(message)

        # 检查是否测验结束
        current_q = self.quiz_engine.get_current_question()
        if current_q is None:
            self.set_stage("summary")
            return self._build_response(
                message_type="quiz",
                content=response,
                metadata={"quiz_completed": True}
            )

        return self._build_response(
            message_type="quiz",
            content=response,
            metadata={"quiz_in_progress": True}
        )

    async def _handle_summary(self, message: str) -> dict:
        """处理总结阶段对话"""
        prompt = f"""请为以下培训内容生成学习总结：

任务标题：{self.task_title}

课件内容：
{self.content[:2000]}

请用简洁的语言概括：
1. 主要学习内容
2. 关键知识点
3. 后续建议"""
        from .course_gen import call_llm
        response = call_llm(prompt, "")

        self.set_stage("completed")

        return self._build_response(
            message_type="summary",
            content=response,
        )