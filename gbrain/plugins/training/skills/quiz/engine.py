"""
考核引擎
"""

import asyncio
from typing import Optional

from .models import QuizItem, QuizResult, QuizState
from .generator import QuizGenerator
from .prompts import ANSWER_EVALUATION_PROMPT


class QuizEngine:
    """
    考核引擎

    特点：
    - 基于题目的测验考核
    - 支持选择题、判断题、简答题
    - 实时评分和反馈
    - 记录考核结果
    """

    def __init__(self, content: str, topic: str = ""):
        """
        初始化考核引擎

        Args:
            content: 课件内容
            topic: 培训主题
        """
        self.content = content
        self.topic = topic
        self.generator = QuizGenerator()
        self.questions: list[QuizItem] = []
        self.state = QuizState()
        self.answers: list[dict] = []  # 学员答案记录

    async def start_quiz(self, num_questions: int = 5) -> str:
        """
        开始考核

        Args:
            num_questions: 题目数量

        Returns:
            str: 欢迎消息和第一题
        """
        # 生成题目
        self.questions = self.generator.generate_quiz(
            self.content,
            num_questions,
            self.topic
        )

        # 初始化状态
        self.state = QuizState(
            current_question=0,
            total_questions=len(self.questions),
            answers=[],
            score=0.0,
            is_completed=False
        )
        self.answers = []

        # 返回第一题
        return self._format_question(0)

    def _format_question(self, index: int) -> str:
        """格式化题目"""
        if index >= len(self.questions):
            return self._format_result()

        q = self.questions[index]

        if q.type == 'choice':
            options_text = '\n'.join(q.options)
            return (f"📝 第 {index + 1} 题（选择题）\n\n"
                    f"{q.question}\n\n"
                    f"{options_text}\n\n"
                    f"请输入 A/B/C/D 作答")

        elif q.type == 'true_false':
            return (f"📝 第 {index + 1} 题（判断题）\n\n"
                    f"{q.question}\n\n"
                    f"请输入 对/错 作答")

        else:  # blank
            return (f"📝 第 {index + 1} 题（简答题）\n\n"
                    f"{q.question}\n\n"
                    f"请输入你的答案")

    async def chat(self, user_answer: str) -> str:
        """
        处理用户回答（chat 接口）

        Args:
            user_answer: 学员答案

        Returns:
            str: 反馈和下一题或结果
        """
        return await self.submit_answer(user_answer)

    async def submit_answer(self, user_answer: str) -> str:
        """
        提交答案

        Args:
            user_answer: 学员答案

        Returns:
            str: 反馈和下一题或结果
        """
        if self.state.is_completed:
            return self._format_result()

        current_q = self.questions[self.state.current_question]

        # 评估答案
        evaluation = await self._evaluate_answer(current_q, user_answer)

        # 记录答案
        self.answers.append({
            'question_id': current_q.id,
            'question': current_q.question,
            'user_answer': user_answer,
            'correct_answer': current_q.correct_answer,
            'is_correct': evaluation.get('correct', False),
            'score': evaluation.get('score', 0),
            'explanation': evaluation.get('explanation', '')
        })

        # 更新状态
        self.state.current_question += 1

        # 构建反馈
        feedback = self._format_feedback(current_q, evaluation)

        # 检查是否完成
        if self.state.current_question >= len(self.questions):
            self.state.is_completed = True
            self.state.score = self._calculate_score()
            return feedback + "\n\n" + self._format_result()

        # 返回下一题
        return feedback + "\n\n" + self._format_question(self.state.current_question)

    async def _evaluate_answer(self, question: QuizItem, user_answer: str) -> dict:
        """评估答案"""
        # 标准化答案：去除空白、标点，转大写
        user_answer = user_answer.strip().upper()
        # 去除常见标点符号
        user_answer = user_answer.replace('。', '').replace('.', '').replace('，', '').replace(',', '')

        # 选择题直接比对
        if question.type == 'choice':
            # 支持 A/B/C/D 或 a/b/c/d
            correct = user_answer == question.correct_answer.upper()
            return {
                'correct': correct,
                'score': 100 if correct else 0,
                'explanation': question.explanation
            }

        # 判断题
        if question.type == 'true_false':
            # 对应 true, 错对应 false
            correct_map = {'对': 'true', '错': 'false', 'T': 'true', 'F': 'false', 'TRUE': 'true', 'FALSE': 'false'}
            normalized = correct_map.get(user_answer, '')
            correct = normalized == question.correct_answer.lower()
            return {
                'correct': correct,
                'score': 100 if correct else 0,
                'explanation': question.explanation
            }

        # 简答题用 LLM 评估
        try:
            prompt = ANSWER_EVALUATION_PROMPT.format(
                question_type=question.type,
                question=question.question,
                user_answer=user_answer
            )
            from gbrain.plugins.training.course_gen import call_llm_async
            response = await call_llm_async(prompt, "")

            import re
            import json
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    'correct': result.get('correct', False),
                    'score': result.get('score', 50),
                    'explanation': result.get('explanation', question.explanation)
                }
        except Exception as e:
            print(f"简答题评估失败: {e}")

        # 默认评估
        return {
            'correct': user_answer in question.correct_answer,
            'score': 50,
            'explanation': question.explanation
        }

    def _format_feedback(self, question: QuizItem, evaluation: dict) -> str:
        """格式化反馈"""
        if evaluation.get('correct'):
            feedback = "✅ 回答正确！"
        else:
            feedback = "❌ 回答错误"

        feedback += f"\n\n📖 解析：{evaluation.get('explanation', question.explanation)}"

        if not evaluation.get('correct'):
            # 将 correct_answer 转为字母显示
            correct = question.correct_answer
            if correct.isdigit():
                correct = chr(65 + int(correct))  # 0->A, 1->B, 2->C, 3->D
            feedback += f"\n\n正确答案：{correct}"

        return feedback

    def _calculate_score(self) -> float:
        """计算得分"""
        if not self.answers:
            return 0.0

        total = sum(a['score'] for a in self.answers)
        return total / len(self.answers)

    def _format_result(self) -> str:
        """格式化结果"""
        correct_count = sum(1 for a in self.answers if a.get('is_correct'))
        wrong_count = len(self.answers) - correct_count
        score = self.state.score

        result = "📊 **考核结果**\n\n"
        result += f"得分：{score:.1f}/100\n"
        result += f"正确：{correct_count} 题\n"
        result += f"错误：{wrong_count} 题\n\n"

        if score >= 90:
            result += "🎉 优秀！已经很好地掌握了培训内容！"
        elif score >= 60:
            result += "👍 合格！继续加油！"
        else:
            result += "📚 建议重新学习后再来考核"

        result += "\n\n你可以：\n"
        result += "• 输入「继续」重新考核\n"
        result += "• 输入「学习模式」巩固知识\n"
        result += "• 输入「探索模式」自由提问"

        return result

    def set_quiz_items(self, items: list) -> None:
        """设置考核题（用于外部传入）"""
        from .models import QuizItem
        self.questions = []
        for item in items:
            if isinstance(item, dict):
                # 转换 correct_index (0,1,2,3) 为字母 (A,B,C,D)
                correct_idx = item.get('correct_index', 0)

                # 尝试将 correct_idx 转为数字
                if isinstance(correct_idx, str):
                    # 尝试解析为数字
                    try:
                        correct_idx = int(correct_idx)
                    except ValueError:
                        # 如果是字母 A/B/C/D，转为数字
                        if correct_idx.upper() in ('A', 'B', 'C', 'D'):
                            correct_idx = ord(correct_idx.upper()) - ord('A')
                        else:
                            correct_idx = 0

                if isinstance(correct_idx, int) and correct_idx >= 0:
                    correct_answer = chr(65 + correct_idx)  # 0->A, 1->B, 2->C, 3->D
                else:
                    correct_answer = str(correct_idx)

                self.questions.append(QuizItem(
                    id=item.get('id', f'q{len(self.questions)+1}'),
                    type=item.get('question_type', 'choice'),
                    question=item.get('question', ''),
                    options=item.get('options', []),
                    correct_answer=correct_answer,
                    explanation=item.get('explanation', '')
                ))
            else:
                self.questions.append(item)
        self.state.current_question = 0
        self.state.total_questions = len(self.questions)
        self.state.answers = []
        self.state.score = 0.0
        self.state.is_completed = False
        self.answers = []

    def get_current_question(self) -> Optional[dict]:
        """获取当前题目"""
        if self.state.current_question >= len(self.questions):
            return None
        q = self.questions[self.state.current_question]
        return {
            'index': self.state.current_question,
            'total': len(self.questions),
            'id': q.id,
            'question': q.question,
            'question_type': q.type,
            'options': q.options,
            'explanation': q.explanation
        }

    def get_score(self) -> float:
        """获取考核得分"""
        return self.state.score

    def get_answers(self) -> list[dict]:
        """获取所有答案"""
        return self.answers.copy()

    def get_result(self) -> QuizResult:
        """获取考核结果"""
        correct_count = sum(1 for a in self.answers if a.get('is_correct'))
        wrong_count = len(self.answers) - correct_count

        return QuizResult(
            score=self.state.score,
            passed=self.state.score >= 60,
            total_questions=len(self.questions),
            correct_count=correct_count,
            wrong_count=wrong_count,
            answers=self.answers.copy()
        )

    def get_welcome_message(self) -> str:
        """获取欢迎消息"""
        return """📝 **考核模式**

欢迎进入考核模式！我将检验你对培训内容的学习效果。

考核说明：
• 题型包括：选择题、判断题、简答题
• 共 5 道题，请认真作答
• 考核只有一次机会

**使用方式：**
- 输入「开始考核」启动考核
- 输入「探索模式」切换到自由问答
- 输入「学习模式」切换到场景学习

准备好了吗？输入「开始考核」开始！"""

    def reset(self) -> None:
        """重置考核"""
        self.state = QuizState()
        self.answers = []
