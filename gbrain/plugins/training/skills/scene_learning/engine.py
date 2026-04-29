"""
场景学习引擎
"""

import re
from typing import Optional

from .models import Scene, SceneLearningResult
from .prompts import SYSTEM_PROMPT, EVALUATION_PROMPT


class SceneLearningEngine:
    """
    场景学习引擎

    特点：
    - 基于场景链的引导式学习
    - 先展示场景，学员尝试回答
    - AI 评估回答并给出反馈
    - 记录薄弱点用于考核
    """

    def __init__(self, content: str, topic: str = "", scene_chain: list = None):
        """
        初始化场景学习引擎

        Args:
            content: 课件内容
            topic: 培训主题
            scene_chain: 场景链（可选）
        """
        self.content = content
        self.topic = topic
        self.scene_chain = scene_chain or []
        self.current_scene_index = 0
        self.scene_responses = []  # 每个场景的响应记录
        self.weak_points = []  # 薄弱知识点
        self.learning_score = 0.0  # 学习得分
        self.status = "active"  # active | completed

    def set_scene_chain(self, scene_chain: list) -> None:
        """设置场景链"""
        self.scene_chain = scene_chain
        self.current_scene_index = 0
        self.scene_responses = []
        self.weak_points = []
        self.learning_score = 0.0
        self.status = "active"

    def get_current_scene(self) -> Optional[dict]:
        """获取当前场景"""
        if self.current_scene_index >= len(self.scene_chain):
            return None
        return self.scene_chain[self.current_scene_index]

    def get_progress(self) -> dict:
        """获取学习进度"""
        total = len(self.scene_chain)
        current = self.current_scene_index + 1 if self.current_scene_index < total else total
        percent = int((self.current_scene_index / total) * 100) if total > 0 else 0

        scene = self.get_current_scene()
        # 清理标题
        scene_title = scene.get('title', '') if scene else ''
        scene_title = re.sub(r'^场景?\d+[.：:]\s*', '', scene_title)
        scene_title = re.sub(r'^[一二三四五六七八九十0-9]+[.、)）\s]+', '', scene_title)
        scene_title = re.sub(r'^\([一二三四五六七八九十0-9]+\)\s*', '', scene_title)

        return {
            'current_scene': self.current_scene_index + 1,
            'total_scenes': total,
            'percent': min(percent, 100),
            'scene_title': scene_title,
            'learning_score': self.learning_score,
            'status': self.status
        }

    def _show_current_scene(self) -> SceneLearningResult:
        """展示当前场景，等待用户回答"""
        scene = self.get_current_scene()
        if not scene:
            return self._build_learning_complete()

        # 清理标题
        title = scene.get('title', '')
        title = re.sub(r'^场景?\d+[.：:]\s*', '', title)
        title = re.sub(r'^[一二三四五六七八九十0-9]+[.、)）\s]+', '', title)
        title = re.sub(r'^\([一二三四五六七八九十0-9]+\)\s*', '', title)

        return SceneLearningResult(
            content=f"📋 【场景 {self.current_scene_index + 1}】{title}\n\n"
                    f"{scene.get('description', '')}\n\n"
                    f"💡 提示：{scene.get('hint', '请结合培训内容回答')}\n\n"
                    f"请输入您的回答：",
            scene_index=self.current_scene_index + 1,
            total_scenes=len(self.scene_chain),
            scene_title=title,
            is_completed=False,
            awaiting_answer=True
        )

    def _advance_to_next_scene(self) -> SceneLearningResult:
        """推进到下一场景"""
        self.current_scene_index += 1

        if self.current_scene_index >= len(self.scene_chain):
            return self._build_learning_complete()

        scene = self.get_current_scene()
        # 清理标题
        scene_title = scene.get('title', '')
        scene_title = re.sub(r'^场景?\d+[.：:]\s*', '', scene_title)
        scene_title = re.sub(r'^[一二三四五六七八九十0-9]+[.、)）\s]+', '', scene_title)
        scene_title = re.sub(r'^\([一二三四五六七八九十0-9]+\)\s*', '', scene_title)

        return SceneLearningResult(
            content=f"📋 【场景 {self.current_scene_index + 1}】{scene_title}\n\n"
                    f"{scene.get('description', '')}\n\n"
                    f"💡 提示：{scene.get('hint', '请结合培训内容回答')}\n\n"
                    f"请输入您的回答：",
            scene_index=self.current_scene_index + 1,
            total_scenes=len(self.scene_chain),
            scene_title=scene_title,
            is_completed=False,
            awaiting_answer=True
        )

    async def chat(self, user_response: str) -> SceneLearningResult:
        """
        处理用户对当前场景的回答

        Args:
            user_response: 用户回答

        Returns:
            SceneLearningResult: 包含评估结果和下一场景
        """
        # 检查是否是"继续"指令
        if user_response.strip() in ['继续', 'next', '下一题']:
            return self._advance_to_next_scene()

        # 检查是否是"开始学习"触发词
        is_start_trigger = user_response.strip() in ['开始', '开始学习', 'start', '学习']

        # 如果是第一次输入或收到开始触发词，展示场景
        if is_start_trigger and self.current_scene_index == 0:
            return self._show_current_scene()

        current_scene = self.get_current_scene()
        if not current_scene:
            return self._build_learning_complete()

        # 评估用户回答
        evaluation = await self._evaluate_response(user_response, current_scene)

        # 记录响应
        self.scene_responses.append({
            'scene_index': self.current_scene_index,
            'user_response': user_response,
            'evaluation': evaluation
        })

        # 更新学习得分
        self.learning_score = (self.learning_score * len(self.scene_responses) + evaluation.get('score', 0)) / (len(self.scene_responses) + 1)

        # 记录薄弱点
        if evaluation.get('score', 0) < 7:
            for point in current_scene.get('knowledge_points', []):
                if point not in self.weak_points:
                    self.weak_points.append(point)

        # 构建响应
        response = self._build_scene_response(evaluation, current_scene)

        # 推进到下一场景
        remaining = len(self.scene_chain) - self.current_scene_index - 1
        if remaining > 0:
            response.content += f"\n📍 还剩 {remaining} 个场景\n"
            response.content += f"输入「继续」进入下一场景"
        else:
            response.is_completed = True
            self.status = "completed"
            response.content += f"\n🎉 您已完成所有场景学习！\n\n"
            response.content += f"📊 学习得分：{self.learning_score:.1f}/10\n\n"
            response.content += f"输入「考核模式」检验学习效果，或继续探索其他问题。"

        return response

    async def _evaluate_response(self, user_response: str, scene: dict) -> dict:
        """评估用户回答"""
        prompt = EVALUATION_PROMPT.format(
            scene_description=scene.get('description', ''),
            user_answer=user_response
        )

        try:
            from gbrain.plugins.training.course_gen import call_llm_async
            response_text = await call_llm_async(prompt, "")

            # 解析 JSON
            import json
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"评估失败: {e}")

        # 默认评估
        return {
            'score': 5,
            'strengths': ['有参与学习'],
            'weaknesses': ['需要更多信息'],
            'correct_action': scene.get('correct_answer', ''),
            'explanation': scene.get('explanation', '')
        }

    def _build_scene_response(self, evaluation: dict, scene: dict) -> SceneLearningResult:
        """构建场景响应"""
        score = evaluation.get('score', 0)

        if score >= 9:
            emoji = "✅"
            comment = "回答非常准确！"
        elif score >= 7:
            emoji = "👍"
            comment = "回答基本正确！"
        else:
            emoji = "📝"
            comment = "还有提升空间"

        response_text = f"{emoji} {comment}\n\n"

        if evaluation.get('strengths'):
            response_text += f"✨ 优点：{', '.join(evaluation['strengths'][:2])}\n"

        if evaluation.get('weaknesses'):
            response_text += f"📌 不足：{', '.join(evaluation['weaknesses'][:2])}\n"

        response_text += f"\n💡 正确答案：{evaluation.get('correct_action', scene.get('correct_answer', ''))}\n"

        if evaluation.get('explanation'):
            response_text += f"\n📖 讲解：{evaluation['explanation']}\n"

        return SceneLearningResult(
            content=response_text,
            scene_index=self.current_scene_index,
            total_scenes=len(self.scene_chain),
            scene_title=scene.get('title', ''),
            is_completed=False,
            awaiting_answer=False,
            evaluation=evaluation
        )

    def _build_learning_complete(self) -> SceneLearningResult:
        """构建学习完成响应"""
        self.status = "completed"
        return SceneLearningResult(
            content=f"🎉 恭喜完成所有场景学习！\n\n"
                    f"📊 学习得分：{self.learning_score:.1f}/10\n\n"
                    f"📌 薄弱环节：{', '.join(self.weak_points) if self.weak_points else '无'}\n\n"
                    f"你可以：\n"
                    f"• 输入「继续」重新学习\n"
                    f"• 输入「考核模式」检验学习效果\n"
                    f"• 输入「探索模式」自由提问",
            scene_index=self.current_scene_index,
            total_scenes=len(self.scene_chain),
            scene_title="",
            is_completed=True,
            awaiting_answer=False
        )

    def reset(self) -> None:
        """重置学习进度"""
        self.current_scene_index = 0
        self.scene_responses = []
        self.weak_points = []
        self.learning_score = 0.0
        self.status = "active"

    def get_welcome_message(self) -> str:
        """获取欢迎消息"""
        return """🎯 **学习模式**

欢迎进入学习模式！我将通过真实工作场景带你学习培训内容。

学习流程：
1. 📋 展示工作场景
2. 💭 你思考如何处理
3. ✅ 我评估你的回答并讲解
4. ➡️ 进入下一场景

**使用方式：**
- 输入「开始」启动学习
- 输入「继续」进入下一场景
- 输入「探索模式」切换到自由问答
- 输入「考核模式」切换到测验考核

准备好了吗？输入「开始」开始学习！"""

    def get_weak_points(self) -> list[str]:
        """获取薄弱点列表"""
        return self.weak_points.copy()

    def get_learning_score(self) -> float:
        """获取学习得分"""
        return self.learning_score

    def generate_quiz_items(self, num_questions: int = 7) -> list[dict]:
        """
        基于场景链和薄弱点生成考核题

        Args:
            num_questions: 考核题数量

        Returns:
            考核题列表
        """
        if not self.scene_chain:
            return []

        # 构建场景摘要
        scenes_summary = "\n".join([
            f"场景{i+1}：{s.get('title', '')}\n"
            f"  描述：{s.get('description', '')}\n"
            f"  正确答案：{s.get('correct_answer', '')}"
            for i, s in enumerate(self.scene_chain)
        ])

        weak_points_str = ', '.join(self.weak_points) if self.weak_points else '无'

        prompt = f"""基于以下培训场景，生成考核题目。

场景内容：
{scenes_summary}

用户薄弱环节：{weak_points_str}

要求：
1. 生成 {num_questions} 道考核题
2. 题型包括：场景应用题（考察在实际情境中应用知识）、概念题（考察对知识点的理解）
3. 场景应用题要基于上述场景改编，考察相同知识点
4. 每题提供：题目、选项（如有）、正确答案、解析

请用以下JSON格式返回：
{{
    "quiz_items": [
        {{
            "id": "q1",
            "question": "题目内容",
            "question_type": "choice",
            "options": ["A. 选项", "B. 选项", "C. 选项", "D. 选项"],
            "correct_index": 0,
            "explanation": "解析",
            "related_scene": "关联场景"
        }}
    ]
}}

注意：选择题 correct_index 是 0=A, 1=B, 2=C, 3=D"""

        try:
            from gbrain.plugins.training.course_gen import call_llm
            import re
            import json

            response_text = call_llm(prompt, "")
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group(0))
                items = result.get('quiz_items', [])
                for i, item in enumerate(items):
                    if not item.get('id'):
                        item['id'] = f'q{i+1}'
                return items
        except Exception as e:
            print(f"生成考核题失败: {e}")

        return []
