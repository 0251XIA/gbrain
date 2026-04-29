"""
学习助手 Skill 协调器

统一管理探索、学习、考核三种模式
"""

from .exploration import ExplorationEngine
from .scene_learning import SceneLearningEngine
from .quiz import QuizEngine
from .scene_learning.generator import generate_scene_chain


class LearningCoordinator:
    """
    学习协调器

    管理三种模式的切换和执行：
    1. 探索模式 - 自由问答
    2. 学习模式 - 场景引导学习
    3. 考核模式 - 测验考核
    """

    MODES = ["exploration", "learning", "quiz"]

    MODE_TRIGGERS = {
        "exploration": ["探索", "问答", "提问", "不懂", "解释", "探索模式"],
        "learning": ["学习", "场景学习", "开始学习", "学习模式", "场景模式"],
        "quiz": ["考核", "考试", "测验", "答题", "考核模式"]
    }

    def __init__(self, content: str, topic: str = ""):
        """
        初始化协调器

        Args:
            content: 课件内容
            topic: 培训主题
        """
        self.content = content
        self.topic = topic
        self.current_mode = "exploration"  # 默认探索模式

        # 初始化三个引擎
        self.exploration_engine = ExplorationEngine(content, topic)
        self.scene_learning_engine = SceneLearningEngine(content, topic)
        self.quiz_engine = QuizEngine(content, topic)

        # 当前引擎
        self._current_engine = self.exploration_engine

    def detect_mode_switch(self, message: str) -> str:
        """
        检测是否要切换模式

        Args:
            message: 用户消息

        Returns:
            str: 模式名称，如果不需要切换返回 None
        """
        msg_lower = message.lower().strip()

        # 检查是否精确匹配模式名称
        if msg_lower in ["探索模式", "学习模式", "考核模式"]:
            return msg_lower.replace("模式", "")

        # 检查触发词
        for mode, triggers in self.MODE_TRIGGERS.items():
            for trigger in triggers:
                if trigger in msg_lower:
                    return mode

        return None

    def switch_mode(self, mode: str) -> str:
        """
        切换模式

        Args:
            mode: 模式名称

        Returns:
            str: 欢迎消息
        """
        if mode not in self.MODES:
            return f"未知模式：{mode}"

        self.current_mode = mode

        # 更新当前引擎
        if mode == "exploration":
            self._current_engine = self.exploration_engine
        elif mode == "learning":
            self._current_engine = self.scene_learning_engine
        else:
            self._current_engine = self.quiz_engine

        return self._current_engine.get_welcome_message()

    async def chat(self, message: str) -> dict:
        """
        处理用户消息

        Args:
            message: 用户消息

        Returns:
            dict: 响应
        """
        # 检测模式切换
        new_mode = self.detect_mode_switch(message)

        if new_mode and new_mode != self.current_mode:
            welcome = self.switch_mode(new_mode)
            return {
                "type": "mode_switch",
                "mode": new_mode,
                "content": welcome
            }

        # 执行当前模式
        if self.current_mode == "exploration":
            return await self._handle_exploration(message)
        elif self.current_mode == "learning":
            return await self._handle_learning(message)
        else:
            return await self._handle_quiz(message)

    async def _handle_exploration(self, message: str) -> dict:
        """处理探索模式"""
        # 检查是否是开始触发
        if message.strip() in ["开始", "探索", "开始探索"]:
            result = self.exploration_engine.get_welcome_message()
        else:
            result = self.exploration_engine.chat(message)

        return {
            "type": "exploration",
            "mode": "exploration",
            "content": result.content if hasattr(result, 'content') else result,
            "suggestions": result.suggestions if hasattr(result, 'suggestions') else []
        }

    async def _handle_learning(self, message: str) -> dict:
        """处理学习模式"""
        # 检查是否是第一次进入
        if message.strip() in ["开始", "开始学习", "学习"]:
            result = self.scene_learning_engine.get_welcome_message()
        else:
            result = await self.scene_learning_engine.chat(message)

        return {
            "type": "learning",
            "mode": "learning",
            "content": result.content if hasattr(result, 'content') else result,
            "scene_index": result.scene_index if hasattr(result, 'scene_index') else 0,
            "total_scenes": result.total_scenes if hasattr(result, 'total_scenes') else 0,
            "is_completed": result.is_completed if hasattr(result, 'is_completed') else False
        }

    async def _handle_quiz(self, message: str) -> dict:
        """处理考核模式"""
        # 检查是否是开始
        is_start = message.strip() in ["开始", "开始考核", "考核", "考试"]

        if is_start and not hasattr(self.quiz_engine.state, 'current_question'):
            result = await self.quiz_engine.start_quiz()
        elif is_start and self.quiz_engine.state.is_completed:
            self.quiz_engine.reset()
            result = await self.quiz_engine.start_quiz()
        else:
            result = await self.quiz_engine.submit_answer(message)

        return {
            "type": "quiz",
            "mode": "quiz",
            "content": result,
            "is_completed": self.quiz_engine.state.is_completed if hasattr(self.quiz_engine.state, 'is_completed') else False,
            "score": self.quiz_engine.state.score if hasattr(self.quiz_engine.state, 'score') else 0
        }

    def get_current_mode(self) -> str:
        """获取当前模式"""
        return self.current_mode

    def get_progress(self) -> dict:
        """获取进度"""
        return {
            "mode": self.current_mode,
            "learning": self.scene_learning_engine.get_progress() if hasattr(self.scene_learning_engine, 'get_progress') else {},
            "quiz": {
                "completed": self.quiz_engine.state.is_completed,
                "score": self.quiz_engine.state.score
            } if hasattr(self.quiz_engine, 'state') else {}
        }

    def get_welcome_message(self) -> str:
        """获取欢迎消息"""
        return self.exploration_engine.get_welcome_message()
