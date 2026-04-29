"""
对话引擎 - 培训场景下的 AI 对话交互
"""

import re
import json
from typing import Optional

from gbrain.plugins.training.course_gen import call_llm


# ========== 系统提示词模板 ==========

SYSTEM_PROMPT_TEMPLATE = """你是一个友善的企业培训教练，风格特点：
- 鼓励式、耐心、案例丰富
- 善于用具体例子解释抽象概念
- 轻松愉快的氛围，但专业可靠
- 适时肯定员工的思考和提问

当前培训阶段：{stage}
课程内容：
{content}
"""


# ========== ChatEngine 基类 ==========

class ChatEngine:
    """对话引擎基类"""

    def __init__(self, content: str, stage: str):
        """
        初始化对话引擎

        Args:
            content: 课件内容
            stage: 培训阶段 (tour | q_and_a | quiz)
        """
        self.content = content
        self.stage = stage
        self.messages: list[dict] = []
        self.system_prompt = self.build_system_prompt()

    def build_system_prompt(self) -> str:
        """构建系统提示词"""
        return SYSTEM_PROMPT_TEMPLATE.format(
            stage=self.stage,
            content=self.content[:2000]  # 限制长度避免上下文溢出
        )

    def add_message(self, role: str, content: str) -> None:
        """
        添加对话历史

        Args:
            role: 角色 (user | assistant)
            content: 消息内容
        """
        self.messages.append({"role": role, "content": content})

    async def chat(self, user_input: str) -> str:
        """
        处理用户输入并返回 AI 回复

        Args:
            user_input: 用户输入

        Returns:
            AI 回复内容
        """
        self.add_message("user", user_input)

        response = call_llm(
            prompt=user_input,
            system_prompt=self.system_prompt
        )

        self.add_message("assistant", response)
        return response


# ========== TourEngine - 导览引擎 ==========

class TourEngine(ChatEngine):
    """
    导览引擎 - 逐步引导式学习

    学习流程：
    1. 分析课件内容，拆成知识点
    2. 每个知识点按"是什么→为什么→怎么样"引导
    3. 讲完即提问，用户回答后评估
    4. 回答太简略 → 引导详细回答
    5. 回答正确 → 推进下一知识点
    """

    def __init__(self, content: str):
        super().__init__(content, stage="tour")
        self._knowledge_points: list[dict] = []  # 知识点列表
        self._current_point_index: int = 0
        self._current_step: str = "what"  # what | why | how | quiz
        self._is_first_run: bool = True
        self._scores: list[dict] = []

        # 用于判断用户是否在回答问题
        self._awaiting_answer: bool = False
        self._last_question: str = ""

    def _extract_knowledge_points(self) -> list[dict]:
        """
        分析课件内容，拆成知识点

        使用 LLM 分析内容结构，提取关键知识点
        """
        prompt = f"""你是一个企业培训专家，请分析以下课件内容，提取出关键知识点。

课件内容：
{self.content[:4000]}

请将内容拆成3-6个核心知识点，每个知识点需要包含：

1. **title**：简洁的知识点名称
2. **what**：核心概念的定义/说明（50-100字）
3. **why**：讲解原因、原理、重要性（50-100字）
4. **how**：实际应用、方法、案例（50-100字）
5. **quiz**：一个简答题，用于检验学习效果

请用以下JSON格式返回（不要有其他内容）：
{{
  "knowledge_points": [
    {{
      "title": "知识点标题",
      "what": "是什么的说明",
      "why": "为什么的说明",
      "how": "怎么样的说明",
      "quiz": "验证简答题"
    }}
  ]
}}

要求：
- 知识点数量3-6个，不要太少也不要太多
- 每个知识点的 what/why/how 要简洁，50-100字
- quiz 问题要具体，能检验用户是否真正理解"""

        try:
            response = call_llm(prompt, "")
            # 提取JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group(0))
                points = result.get('knowledge_points', [])
                if points:
                    return points
        except Exception as e:
            print(f"LLM 解析失败: {e}")

        # 备用方案：简单按段落拆分
        return self._fallback_split()

    def _fallback_split(self) -> list[dict]:
        """备用拆分方案（当LLM不可用时）"""
        sections = []
        pattern = r'^(##\s+.+)$'
        lines = self.content.split('\n')

        current_title = "主要内容"
        current_lines = []

        for line in lines:
            if re.match(pattern, line):
                if current_lines:
                    content = '\n'.join(current_lines).strip()
                    if len(content) > 50:
                        sections.append({
                            'title': current_title,
                            'what': content[:200],
                            'why': '这是理解这个主题的关键。',
                            'how': content[200:400] if len(content) > 200 else content,
                            'quiz': f'请用自己的话解释一下"{current_title}"的核心含义？'
                        })
                    current_lines = []
                current_title = line.lstrip('#').strip()
            else:
                current_lines.append(line)

        if current_lines:
            content = '\n'.join(current_lines).strip()
            if len(content) > 50:
                sections.append({
                    'title': current_title,
                    'what': content[:200],
                    'why': '这是理解这个主题的关键。',
                    'how': content[200:400] if len(content) > 200 else content,
                    'quiz': f'请用自己的话解释一下"{current_title}"的核心含义？'
                })

        return sections[:6]  # 最多6个

    def _get_current_point(self) -> Optional[dict]:
        """获取当前知识点"""
        if self._knowledge_points and self._current_point_index < len(self._knowledge_points):
            return self._knowledge_points[self._current_point_index]
        return None

    async def chat(self, user_input: str) -> str:
        """
        处理对话，根据当前步骤决定输出

        改进的学习流程：
        1. 展示知识点标题 + 是什么
        2. 用户输入"继续" → 展示为什么
        3. 用户输入"继续" → 展示怎么样
        4. 用户输入"继续" → 提问检验
        5. 评估回答 → 下一知识点
        """
        # 检查是否是"开始学习"触发词
        is_start_trigger = user_input.strip() in ['开始', '开始学习', 'start', '学习']

        # 首次调用 或 收到开始触发词：分析内容
        if self._is_first_run or is_start_trigger:
            if self._is_first_run:
                self._knowledge_points = self._extract_knowledge_points()
                self._is_first_run = False

            if not self._knowledge_points:
                return "抱歉，无法分析课件内容，请联系管理员。"

            # 从第一个知识点开始，展示"是什么"
            self._current_step = "what"
            self._awaiting_answer = False
            return self._teach_what()

        # 用户输入"继续"时推进
        user_contiune = user_input.strip() in ['继续', 'next', '继续学习']
        user_start_point = user_input.strip() in ['回答', '答', '我知道了']

        # 如果用户在回答问题
        if self._awaiting_answer:
            if self._current_step == "quiz":
                return await self._handle_answer(user_input)
            elif user_contiune:
                # 用户说"继续"，推进到下一步
                return self._advance_to_next_step()
            else:
                # 其他输入作为回答
                return await self._handle_answer(user_input)

        # 根据当前步骤讲解
        if self._current_step == "what":
            return self._teach_what()
        elif self._current_step == "why":
            return self._teach_why()
        elif self._current_step == "how":
            return self._teach_how()
        elif self._current_step == "quiz":
            return self._ask_quiz()
        else:
            return self._teach_what()

    def _teach_current_point(self) -> str:
        """一次性输出当前知识点的完整内容（是什么+为什么+怎么样）"""
        point = self._get_current_point()
        if not point:
            return self._next_point_or_finish()

        self._awaiting_answer = True

        response = f"📖 【{point['title']}】\n\n"
        response += f"**是什么：**\n{point.get('what', '')}\n\n"
        response += f"**为什么：**\n{point.get('why', '')}\n\n"
        response += f"**怎么样：**\n{point.get('how', '')}"

        return response

    def _teach_what(self) -> str:
        """讲解当前知识点的'是什么'"""
        point = self._get_current_point()
        if not point:
            return self._next_point_or_finish()

        self._current_step = "why"
        self._awaiting_answer = True

        # 直接输出知识点内容，不带引导性问题
        response = f"📖 【{point['title']}】\n\n"
        response += f"{point.get('what', '')}"

        return response

    def _teach_why(self) -> str:
        """讲解当前知识点的'为什么'"""
        point = self._get_current_point()
        if not point:
            return self._next_point_or_finish()

        self._current_step = "how"
        self._awaiting_answer = True

        # 直接输出知识点内容
        response = f"❓ 【{point['title']} - 为什么】\n\n"
        response += f"{point.get('why', '')}"

        return response

    def _teach_how(self) -> str:
        """讲解当前知识点的'怎么样'"""
        point = self._get_current_point()
        if not point:
            return self._next_point_or_finish()

        self._current_step = "quiz"
        self._awaiting_answer = True

        # 直接输出知识点内容
        response = f"⚡ 【{point['title']} - 怎么样】\n\n"
        response += f"{point.get('how', '')}"

        return response

    def _ask_quiz(self) -> str:
        """提问验证"""
        point = self._get_current_point()
        if not point:
            return self._next_point_or_finish()

        self._awaiting_answer = True
        self._last_question = point.get('quiz', f'请回答：{point["title"]}的核心要点是什么？')

        return self._last_question

    def _advance_to_next_step(self) -> str:
        """推进到当前知识点的下一步"""
        point = self._get_current_point()
        if not point:
            return self._next_point_or_finish()

        if self._current_step == "what":
            self._current_step = "why"
            self._awaiting_answer = False
            return self._teach_why()
        elif self._current_step == "why":
            self._current_step = "how"
            self._awaiting_answer = False
            return self._teach_how()
        elif self._current_step == "how":
            self._current_step = "quiz"
            self._awaiting_answer = False
            return self._ask_quiz()
        else:
            return self._ask_quiz()

    async def _handle_answer(self, user_input: str) -> str:
        """处理用户回答"""
        point = self._get_current_point()
        if not point:
            return self._next_point_or_finish()

        # 评估回答质量
        evaluation = self._evaluate_answer(user_input, point)

        # 记录分数
        self._scores.append({
            'point': point['title'],
            'score': evaluation['score'],
            'level': evaluation['level']
        })

        # 根据评估结果决定下一步
        if evaluation['level'] == 'needs_review':
            # 回答不够详细，引导重新回答
            self._awaiting_answer = True
            return self._build_retry_message(evaluation, point)
        else:
            # 回答合格，推进到下一步
            return self._build_success_and_advance(evaluation, point)

    def _evaluate_answer(self, answer: str, point: dict) -> dict:
        """
        评估用户回答质量

        Returns:
            {score: 0-100, level: 'excellent'|'good'|'needs_review', feedback: str}
        """
        # 答案太短，认为不够详细
        if len(answer.strip()) < 10:
            return {
                'score': 0,
                'level': 'needs_review',
                'feedback': '回答太简略了，请详细描述一下。'
            }

        prompt = f"""你是企业培训教练，评估学员对知识点的理解程度。

知识点：{point['title']}
知识点内容：
- 是什么：{point.get('what', '')}
- 为什么：{point.get('why', '')}
- 怎么样：{point.get('how', '')}

学员回答：
{answer}

评估标准：
1. 是否用自己的话描述（30%）
2. 是否抓住了核心要点（40%）
3. 表达是否清晰（30%）

请用以下JSON格式返回：
{{"score": 分数, "level": "excellent"/"good"/"needs_review", "feedback": "简短反馈"}}

- 85-100分：excellent（理解深刻，表达清晰）
- 60-84分：good（理解基本正确）
- 60分以下：needs_review（理解不够，需要补充）"""

        try:
            response = call_llm(prompt, "")
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group(0))
                return {
                    'score': result.get('score', 0),
                    'level': result.get('level', 'needs_review'),
                    'feedback': result.get('feedback', '')
                }
        except Exception:
            pass

        # 备用评估：基于长度
        if len(answer) > 100:
            return {'score': 75, 'level': 'good', 'feedback': '回答得不错！'}
        return {'score': 50, 'level': 'needs_review', 'feedback': '请更详细地描述一下。'}

    def _build_retry_message(self, evaluation: dict, point: dict) -> str:
        """构建重新回答的引导消息"""
        response = f"💪 {evaluation['feedback']}\n\n"
        response += f"提示：可以从以下角度描述「{point['title']}」\n"
        response += f"- 这个概念**是什么**？\n"
        response += f"- 它**为什么**重要？\n"
        response += f"- 工作中**怎么**应用？\n\n"
        response += f"请详细说说你的理解："

        return response

    def _build_success_and_advance(self, evaluation: dict, point: dict) -> str:
        """构建成功消息并推进"""
        level_emoji = {'excellent': '🌟', 'good': '👍'}
        emoji = level_emoji.get(evaluation['level'], '👍')

        response = f"{emoji} {evaluation['feedback']}\n\n"

        # 推进到下一知识点或步骤
        if self._current_step == "what":
            self._current_step = "why"
            self._awaiting_answer = True
            response += f"接下来我们看看**为什么**...\n\n"
            response += f"❓ **为什么：**\n{point.get('why', '')}\n\n"
            response += f"---\n请说说你的理解："
        elif self._current_step == "why":
            self._current_step = "how"
            self._awaiting_answer = True
            response += f"很好！再看看**怎么样**应用...\n\n"
            response += f"⚡ **怎么样：**\n{point.get('how', '')}\n\n"
            response += f"---\n这对你有什么启发？"
        elif self._current_step == "how" or self._current_step == "quiz":
            response += self._next_point_or_finish()

        return response

    def _next_point_or_finish(self) -> str:
        """推进到下一知识点或结束"""
        self._current_point_index += 1
        self._current_step = "what"
        self._awaiting_answer = False

        if self._current_point_index >= len(self._knowledge_points):
            # 学习完成，直接结束
            return "✅ 学习完成！"
        else:
            # 输出下一知识点的完整内容
            return self._teach_current_point()

    def _start_new_point(self, point: dict) -> str:
        """开始新知识点"""
        self._awaiting_answer = True

        response = f"\n{'='*40}\n"
        response += f"📚 第 {self._current_point_index + 1}/{len(self._knowledge_points)} 个知识点：{point['title']}\n"
        response += f"{'='*40}\n\n"
        response += f"📖 **是什么：**\n{point.get('what', '')}\n\n"
        response += f"---\n请用自己的话说说这个概念是什么意思？"

        return response

    def _build_summary(self) -> str:
        """构建学习总结"""
        if not self._scores:
            return "🎉 恭喜完成学习！"

        total = sum(s['score'] for s in self._scores)
        avg = total / len(self._scores)

        excellent_count = sum(1 for s in self._scores if s['level'] == 'excellent')
        good_count = sum(1 for s in self._scores if s['level'] == 'good')

        response = f"\n{'='*40}\n"
        response += f"🎉 恭喜完成全部 {len(self._scores)} 个知识点的学习！\n"
        response += f"{'='*40}\n\n"
        response += f"📊 学习统计：\n"
        response += f"- 平均得分：{avg:.0f}分\n"
        response += f"- 🌟 优秀：{excellent_count}个\n"
        response += f"- 👍 良好：{good_count}个\n\n"
        response += f"📝 知识点回顾：\n"
        for s in self._scores:
            emoji = '🌟' if s['level'] == 'excellent' else '👍'
            response += f"{emoji} {s['point']}（{s['score']}分）\n"

        response += f"\n💬 进入问答环节，有问题随时问我！"

        return response

    def get_progress(self) -> dict:
        """获取学习进度"""
        if not self._knowledge_points:
            return {'current': 0, 'total': 0, 'percent': 0}

        total = len(self._knowledge_points)
        current = self._current_point_index + 1
        percent = int((self._current_point_index / total) * 100)

        return {
            'current': current,
            'total': total,
            'percent': min(percent, 100),
            'current_point': self._get_current_point()['title'] if self._get_current_point() else ''
        }

    def reset(self) -> None:
        """重置学习状态，支持重新开始学习"""
        self._knowledge_points = []
        self._current_point_index = 0
        self._current_step = "what"
        self._is_first_run = True
        self._scores = []
        self._awaiting_answer = False
        self._last_question = ""
        self.messages = []  # 清空对话历史

    def generate_quiz_items(self, num_choice: int = 3, num_judge: int = 2, num_short: int = 2) -> list[dict]:
        """
        基于知识点生成考核题

        Args:
            num_choice: 选择题数量
            num_judge: 判断题数量
            num_short: 简答题数量

        Returns:
            考核题列表
        """
        if not self._knowledge_points:
            return []

        # 构建知识点摘要用于生成考核题
        points_summary = "\n".join([
            f"- {p['title']}: {p.get('what', '')[:100]}"
            for p in self._knowledge_points
        ])

        prompt = f"""基于以下知识点，生成考核题目。

知识点：
{points_summary}

要求：
1. 选择题 {num_choice} 道：单选题，4个选项，标注正确答案索引
2. 判断题 {num_judge} 道：判断对错，标注正确答案
3. 简答题 {num_short} 道：需要简答，提供参考答案和评分关键词

请用以下JSON格式返回：
{{
  "quiz_items": [
    {{
      "id": "q1",
      "question": "题目内容",
      "question_type": "choice",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "correct_index": 0,
      "explanation": "题解"
    }},
    {{
      "id": "q{num_choice + 1}",
      "question": "判断题题目",
      "question_type": "judge",
      "correct_answer": "true",
      "explanation": "题解"
    }},
    {{
      "id": "q{num_choice + num_judge + 1}",
      "question": "简答题题目",
      "question_type": "short_answer",
      "correct_answer": "参考答案",
      "keywords": ["关键词1", "关键词2"],
      "explanation": "评分标准"
    }}
  ]
}}

注意：
- 选择题 correct_index: 0=A, 1=B, 2=C, 3=D
- 判断题 correct_answer: "true" 或 "false"
- 简答题 keywords 是评分关键词，用户回答包含越多得分越高"""

        try:
            response = call_llm(prompt, "")
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group(0))
                items = result.get('quiz_items', [])
                # 确保有 id
                for i, item in enumerate(items):
                    if not item.get('id'):
                        item['id'] = f"q{i+1}"
                return items
        except Exception as e:
            print(f"生成考核题失败: {e}")

        return []


# ========== QAEngine - 问答引擎 ==========

class QAEngine(ChatEngine):
    """问答引擎 - 回答员工关于课程的问题"""

    def __init__(self, content: str):
        super().__init__(content, stage="q_and_a")

    async def chat(self, user_input: str) -> str:
        """
        结合课件内容回答员工问题

        Args:
            user_input: 员工问题

        Returns:
            AI 回答
        """
        prompt = f"""员工问题：{user_input}

请结合以下课件内容回答员工的问题。如果课件中没有直接相关内容，请基于培训主题给出合理回答，并注明这是基于通用知识而非课件内容。

课件内容：
{self.content[:3000]}
"""
        response = call_llm(prompt, self.system_prompt)
        self.add_message("user", user_input)
        self.add_message("assistant", response)
        return response


# ========== QuizEngine - 考核引擎 ==========

class QuizEngine(ChatEngine):
    """考核引擎 - 支持选择题、判断题、简答题"""

    def __init__(self, content: str, quiz_items: list = None):
        super().__init__(content, stage="quiz")
        self._quiz_items: list[dict] = quiz_items or []
        self._current_index: int = 0
        self._answers: list[dict] = []  # {"question_id": "", "answer": "", "correct": bool, "score": float}
        self._total_score: float = 0.0

    def set_quiz_items(self, items: list[dict]) -> None:
        """设置考核题"""
        self._quiz_items = items or []
        self._current_index = 0
        self._answers = []
        self._total_score = 0.0

    def get_current_question(self) -> Optional[dict]:
        """获取当前题目"""
        if self._current_index >= len(self._quiz_items):
            return None

        item = self._quiz_items[self._current_index]
        return {
            "index": self._current_index,
            "total": len(self._quiz_items),
            "id": item.get('id', f'q{self._current_index + 1}'),
            "question": item.get('question', ''),
            "question_type": item.get('question_type', 'choice'),
            "options": item.get('options', []),
            "explanation": item.get('explanation', '')
        }

    async def chat(self, user_input: str) -> str:
        """处理用户回答"""
        if self._current_index >= len(self._quiz_items):
            return self._generate_result()

        current_item = self._quiz_items[self._current_index]
        q_type = current_item.get('question_type', 'choice')

        # 评分
        result = await self._grade_answer(user_input, current_item, q_type)
        self._answers.append(result)
        self._total_score += result['score']

        # 构建反馈
        feedback = self._build_feedback(result, current_item, q_type)

        # 推进到下一题
        self._current_index += 1

        if self._current_index < len(self._quiz_items):
            feedback += self._build_next_question()
        else:
            feedback += self._generate_result()

        self.add_message("user", user_input)
        self.add_message("assistant", feedback)
        return feedback

    async def _grade_answer(self, user_input: str, item: dict, q_type: str) -> dict:
        """评分"""
        answer = user_input.strip()
        question_id = item.get('id', f'q{self._current_index + 1}')

        if q_type == 'choice':
            # 选择题
            answer_upper = answer.upper()
            if answer_upper in ['A', 'B', 'C', 'D']:
                selected = ['A', 'B', 'C', 'D'].index(answer_upper)
            elif answer.isdigit() and 0 <= int(answer) <= 3:
                selected = int(answer)
            else:
                return {"question_id": question_id, "answer": answer, "correct": False, "score": 0}

            correct = item.get('correct_index', 0)
            is_correct = selected == correct
            return {
                "question_id": question_id,
                "answer": answer,
                "correct": is_correct,
                "score": 20.0 if is_correct else 0  # 选择题 20 分
            }

        elif q_type == 'judge':
            # 判断题
            answer_lower = answer.lower()
            is_correct = answer_lower in ['对', '错', 'true', 'false', 't', 'f', '1', '0', 'a', 'b']
            correct_answer = item.get('correct_answer', 'true')
            expected = '对' if correct_answer == 'true' else '错'
            actual = answer
            if answer_lower in ['true', 't', '1', 'a']:
                actual = '对'
            elif answer_lower in ['false', 'f', '0', 'b']:
                actual = '错'

            is_correct = actual == expected
            return {
                "question_id": question_id,
                "answer": answer,
                "correct": is_correct,
                "score": 10.0 if is_correct else 0  # 判断题 10 分
            }

        elif q_type == 'short_answer':
            # 简答题 - AI 评估
            score = await self._grade_short_answer(answer, item)
            is_correct = score >= 10  # 简答题 10 分以上算正确
            return {
                "question_id": question_id,
                "answer": answer,
                "correct": is_correct,
                "score": score
            }

        return {"question_id": question_id, "answer": answer, "correct": False, "score": 0}

    async def _grade_short_answer(self, user_answer: str, item: dict) -> float:
        """AI 评估简答题"""
        keywords = item.get('keywords', [])
        question = item.get('question', '')
        correct_answer = item.get('correct_answer', '')

        # 标准化用户回答：去空格、去标点、转小写
        normalized = re.sub(r'[\s\，。、！？：；""''（）【】]+', '', user_answer.lower())

        if not keywords:
            return 7.5  # 默认给 7.5 分

        # 先尝试 AI 评估
        prompt = f"""评估学员简答题回答。

题目：{question}
参考答案：{correct_answer}
评分关键词：{', '.join(keywords)}

学员回答：{user_answer}

评估标准：
- 包含全部关键词：15分
- 包含大部分关键词（>=60%）：10-14分
- 包含部分关键词（>=30%）：5-9分
- 较少或没有关键词：0-4分

请直接给出一个0-15的分数，只输出数字："""

        try:
            response = call_llm(prompt, "")
            match = re.search(r'\d+', response.strip())
            if match:
                score = float(match.group())
                return min(score, 15.0)
        except Exception:
            pass

        # 改进的关键词匹配
        matched = 0
        for kw in keywords:
            kw_norm = re.sub(r'[\s\，。、！？：；""''（）【】]+', '', kw.lower())
            if kw_norm and kw_norm in normalized:
                matched += 1
            elif len(kw_norm) >= 2:
                kw_chars = set(kw_norm)
                answer_chars = set(normalized)
                overlap = len(kw_chars & answer_chars)
                if overlap >= len(kw_chars) * 0.7:
                    matched += 0.5

        ratio = matched / len(keywords) if keywords else 0

        # 基于匹配率计算分数
        if ratio >= 1.0:
            base_score = 15.0
        elif ratio >= 0.6:
            base_score = 10.0 + (ratio - 0.6) / 0.4 * 4
        elif ratio >= 0.3:
            base_score = 5.0 + (ratio - 0.3) / 0.3 * 5
        elif ratio > 0:
            base_score = ratio / 0.3 * 5
        else:
            base_score = 0

        # 答案长度奖励（详细程度）
        min_len = len(correct_answer) * 0.5 if correct_answer else 20
        len_ratio = min(len(user_answer) / max(min_len, 1), 1.5)
        length_bonus = (len_ratio - 1) * 2 if len_ratio > 1 else 0

        final_score = min(base_score + length_bonus, 15.0)
        return max(final_score, 0)

    def _build_feedback(self, result: dict, item: dict, q_type: str) -> str:
        """构建单题反馈"""
        feedback = f"第 {self._current_index + 1} 题：{'✅ 正确！' if result['correct'] else '❌ 错误！'}\n"
        feedback += f"你的回答：{result['answer']}\n"

        if q_type == 'choice':
            correct = item.get('correct_index', 0)
            feedback += f"正确答案：{'ABCD'[correct]}\n"
        elif q_type == 'judge':
            correct_answer = item.get('correct_answer', 'true')
            expected = '对' if correct_answer == 'true' else '错'
            feedback += f"正确答案：{expected}\n"

        feedback += f"得分：{result['score']:.0f} 分\n"
        feedback += f"题解：{item.get('explanation', '')}\n\n"

        return feedback

    def _build_next_question(self) -> str:
        """构建下一题"""
        next_item = self.get_current_question()
        if not next_item:
            return ""

        q_type = next_item['question_type']
        feedback = f"📝 下一题（{self._current_index + 1}/{len(self._quiz_items)}）：\n"
        feedback += f"{next_item['question']}\n"

        if q_type == 'choice':
            for i, opt in enumerate(next_item['options']):
                feedback += f"  {'ABCD'[i]}. {opt}\n"
        elif q_type == 'judge':
            feedback += "  A. 对  B. 错\n"
        elif q_type == 'short_answer':
            feedback += "  （请简述你的答案）\n"

        return feedback

    def _generate_result(self) -> str:
        """生成考核结果"""
        score = self._total_score
        passed = score >= 70

        feedback = f"\n{'='*40}\n"
        feedback += f"🎉 考核完成！\n"
        feedback += f"{'='*40}\n\n"
        feedback += f"📊 总分：{score:.0f} 分\n"
        feedback += f"📝 题数：{len(self._quiz_items)} 题\n"
        feedback += f"✅ 正确：{sum(1 for a in self._answers if a['correct'])} 题\n"
        feedback += f"📌 结果：{'🎊 合格！' if passed else '📚 不合格，需重新学习'}\n"

        return feedback

    def get_score(self) -> float:
        """获取总分"""
        return self._total_score

    def is_passed(self) -> bool:
        """是否通过"""
        return self._total_score >= 70

    def get_answers(self) -> list[dict]:
        """获取所有答案"""
        return self._answers


# ========== SceneLearningEngine - 场景驱动学习引擎 ==========

class SceneLearningEngine:
    """
    场景驱动学习引擎

    学习流程：
    1. 基于讲义内容生成场景链
    2. 每个场景让用户先尝试解决
    3. 用户回答后 AI 评估，给出反馈
    4. 记录薄弱点，用于后续考核
    """

    def __init__(self, content: str, scene_chain: list = None):
        """
        初始化场景学习引擎

        Args:
            content: 讲义内容
            scene_chain: 场景链（如果为 None，会自动生成）
        """
        self.content = content
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

        return {
            'current': current,
            'total': total,
            'percent': min(percent, 100),
            'scene_title': self.get_current_scene().get('title', '') if self.get_current_scene() else ''
        }

    def _show_current_scene(self) -> dict:
        """展示当前场景，等待用户回答"""
        scene = self.get_current_scene()
        if not scene:
            return self._build_learning_complete()

        # 获取场景标题（去掉可能重复的前缀和冗余序号）
        title = scene.get('title', '')
        # 去掉开头的"场景X："或"场景 X"
        title = re.sub(r'^场景?\d+[.：:]\s*', '', title)
        # 去掉开头多余的序号如"2. "、"二、"、"（二）"等
        title = re.sub(r'^[一二三四五六七八九十0-9]+[.、)）\s]+', '', title)
        title = re.sub(r'^\([一二三四五六七八九十0-9]+\)\s*', '', title)

        response = {
            'content': f"📋 【场景 {self.current_scene_index + 1}】{title}\n\n"
                      f"{scene.get('description', '')}\n\n"
                      f"💡 提示：{scene.get('hint', '请结合培训内容回答')}\n\n"
                      f"请输入您的回答：",
            'scene_index': self.current_scene_index + 1,
            'total_scenes': len(self.scene_chain),
            'scene_title': title,
            'is_completed': False,
            'awaiting_answer': True
        }

        return response

    def _advance_to_next_scene(self) -> dict:
        """推进到下一场景"""
        self.current_scene_index += 1

        if self.current_scene_index >= len(self.scene_chain):
            # 学习完成
            return self._build_learning_complete()

        # 展示下一场景
        scene = self.get_current_scene()
        # 清理标题
        scene_title = scene.get('title', '')
        scene_title = re.sub(r'^场景?\d+[.：:]\s*', '', scene_title)
        scene_title = re.sub(r'^[一二三四五六七八九十0-9]+[.、)）\s]+', '', scene_title)
        scene_title = re.sub(r'^\([一二三四五六七八九十0-9]+\)\s*', '', scene_title)

        return {
            'content': f"📋 【场景 {self.current_scene_index + 1}】{scene_title}\n\n"
                      f"{scene.get('description', '')}\n\n"
                      f"💡 提示：{scene.get('hint', '请结合培训内容回答')}\n\n"
                      f"请输入您的回答：",
            'scene_index': self.current_scene_index + 1,
            'total_scenes': len(self.scene_chain),
            'scene_title': scene.get('title', ''),
            'is_completed': False,
            'awaiting_answer': True
        }

    async def chat(self, user_response: str) -> dict:
        """
        处理用户对当前场景的回答

        Args:
            user_response: 用户回答

        Returns:
            包含评估结果和下一场景的 dict
        """
        # 检查是否是"继续"指令（用于推进到下一场景）
        if user_response.strip() in ['继续', 'next', '下一题']:
            return self._advance_to_next_scene()

        # 检查是否是"开始学习"触发词
        is_start_trigger = user_response.strip() in ['开始', '开始学习', 'start', '学习']

        # 如果是第一次输入或收到开始触发词，展示场景而非评估
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

        # 更新薄弱点
        if not evaluation['is_correct']:
            for kw in current_scene.get('knowledge_points', []):
                if kw not in self.weak_points:
                    self.weak_points.append(kw)

        # 更新学习得分（答对得20分，答错但理解到位得10分）
        if evaluation['is_correct']:
            self.learning_score += 20
        elif evaluation['score'] >= 10:
            self.learning_score += 10

        # 构建响应（不自动推进，等待用户输入"继续"）
        response = self._build_scene_response(evaluation, current_scene)

        # 不再自动推进，保持当前场景，等待用户输入"继续"
        return response

    async def _evaluate_response(self, user_response: str, scene: dict) -> dict:
        """
        评估用户回答

        Args:
            user_response: 用户回答
            scene: 当前场景

        Returns:
            评估结果 dict
        """
        correct_answer = scene.get('correct_answer', '')
        knowledge_points = scene.get('knowledge_points', [])

        prompt = f"""评估学员对以下培训场景的回答。

场景描述：{scene.get('description', '')}
正确答案：{correct_answer}
考察知识点：{', '.join(knowledge_points)}

学员回答：
{user_response}

请评估学员的回答，给出 JSON 格式：
{{
    "is_correct": true或false,
    "score": 0-20的分数,
    "feedback": "具体的反馈意见",
    "missing_knowledge": ["如果回答不正确，列出缺失的知识点"]
}}

注意：
- score 根据回答质量给分，不是简单对错
- 回答正确但不完整给15分左右
- 回答部分正确给10分左右
- 回答完全错误但态度认真给5分
- 敷衍或不相关回答给0-3分"""

        try:
            response = call_llm(prompt, "")
            # 提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group(0))
                return {
                    'is_correct': result.get('is_correct', False),
                    'score': float(result.get('score', 0)),
                    'feedback': result.get('feedback', ''),
                    'missing_knowledge': result.get('missing_knowledge', [])
                }
        except Exception as e:
            print(f"评估回答失败: {e}")

        # 默认评估
        return {
            'is_correct': False,
            'score': 0,
            'feedback': '无法评估你的回答，请联系管理员。',
            'missing_knowledge': knowledge_points
        }

    def _build_scene_response(self, evaluation: dict, scene: dict) -> dict:
        """构建场景响应"""
        response = {
            'scene_index': self.current_scene_index + 1,
            'total_scenes': len(self.scene_chain),
            'scene_title': scene.get('title', ''),
            'evaluation': evaluation,
            'is_completed': False
        }

        # 反馈内容
        if evaluation['is_correct']:
            response['content'] = f"✅ {evaluation['feedback']}\n\n"
        else:
            response['content'] = f"📝 {evaluation['feedback']}\n\n"
            response['content'] += f"📚 知识点：{', '.join(scene.get('knowledge_points', []))}\n\n"
            response['content'] += f"💡 参考答案：{scene.get('correct_answer', '')}\n\n"
            if scene.get('explanation'):
                response['content'] += f"📖 讲解：{scene.get('explanation', '')}\n\n"

        # 添加下一步引导
        remaining = len(self.scene_chain) - self.current_scene_index - 1
        if remaining > 0:
            response['content'] += f"━━━━━━━━━━━━━━━\n"
            response['content'] += f"📍 还剩 {remaining} 个场景\n"
            response['content'] += f"输入「继续」进入下一场景"
        else:
            response['content'] += f"━━━━━━━━━━━━━━━\n"
            response['content'] += f"🎉 您已完成所有场景学习！\n"
            response['content'] += f"输入「继续」准备考核"

        return response

    def _build_learning_complete(self) -> dict:
        """构建学习完成响应"""
        return {
            'content': f"🎉 恭喜完成所有场景学习！\n\n" +
                      f"学习得分：{self.learning_score} 分\n" +
                      f"薄弱环节：{', '.join(self.weak_points) if self.weak_points else '无'}\n\n" +
                      f"准备好参加考核了吗？",
            'is_completed': True,
            'learning_score': self.learning_score,
            'weak_points': self.weak_points,
            'total_scenes': len(self.scene_chain),
            'scenes_completed': len(self.scene_responses)
        }

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
            "question_type": "scenario 或 concept",
            "options": ["A. 选项", "B. 选项", "C. 选项", "D. 选项"],
            "correct_index": 0,
            "explanation": "解析",
            "related_scene": "关联场景"
        }}
    ]
}}

注意：选择题 correct_index 是 0=A, 1=B, 2=C, 3=D"""

        try:
            response = call_llm(prompt, "")
            json_match = re.search(r'\{{[\s\S]*\}}', response)
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

    def reset(self) -> None:
        """重置学习状态"""
        self.current_scene_index = 0
        self.scene_responses = []
        self.weak_points = []
        self.learning_score = 0.0
        self.status = "active"


# ========== 工厂函数 ==========

def create_chat_engine(content: str, stage: str, quiz_items: list = None) -> ChatEngine:
    """
    创建对话引擎实例

    Args:
        content: 课件内容
        stage: 培训阶段 (tour | q_and_a | quiz)
        quiz_items: 已有测验题列表（QuizEngine 用）

    Returns:
        ChatEngine 子类实例
    """
    if stage == "tour":
        return TourEngine(content)
    elif stage == "q_and_a":
        return QAEngine(content)
    elif stage == "quiz":
        return QuizEngine(content, quiz_items)
    else:
        raise ValueError(f"Unknown stage: {stage}")
