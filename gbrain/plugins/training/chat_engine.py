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

            # 如果是触发词，初始化状态并返回第一个知识点
            if is_start_trigger:
                self._awaiting_answer = True
                return self._teach_what()

            # 首次调用但不是触发词（不应该走到这里）
            return self._teach_what()

        # 如果在等待用户回答
        if self._awaiting_answer:
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
            return self._next_point_or_finish()

    def _teach_what(self) -> str:
        """讲解当前知识点的'是什么'"""
        point = self._get_current_point()
        if not point:
            return self._next_point_or_finish()

        self._current_step = "why"
        self._awaiting_answer = True
        self._last_question = f"请说说看，这个概念是什么意思？"

        response = f"📖 【{point['title']}】\n\n"
        response += f"**是什么：**\n{point.get('what', '')}\n\n"
        response += f"---\n{self._last_question}"

        return response

    def _teach_why(self) -> str:
        """讲解当前知识点的'为什么'"""
        point = self._get_current_point()
        if not point:
            return self._next_point_or_finish()

        self._current_step = "how"
        self._awaiting_answer = True
        self._last_question = f"为什么会这样？请谈谈你的理解。"

        response = f"❓ **为什么：**\n{point.get('why', '')}\n\n"
        response += f"---\n{self._last_question}"

        return response

    def _teach_how(self) -> str:
        """讲解当前知识点的'怎么样'"""
        point = self._get_current_point()
        if not point:
            return self._next_point_or_finish()

        self._current_step = "quiz"
        self._awaiting_answer = True
        self._last_question = point.get('quiz', f'学完了"{point["title"]}"，请用自己的话总结一下。')

        response = f"⚡ **怎么样：**\n{point.get('how', '')}\n\n"
        response += f"---\n{self._last_question}"

        return response

    def _ask_quiz(self) -> str:
        """提问验证"""
        point = self._get_current_point()
        if not point:
            return self._next_point_or_finish()

        self._awaiting_answer = True
        self._last_question = point.get('quiz', f'请回答：{point["title"]}的核心要点是什么？')

        return self._last_question

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
            # 学习完成
            return self._build_summary()
        else:
            # 下一知识点
            point = self._get_current_point()
            return self._start_new_point(point)

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


# ========== QuizEngine - 测验引擎 ==========

class QuizEngine(ChatEngine):
    """测验引擎 - 通过问答评估员工学习效果"""

    def __init__(self, content: str, existing_quiz_items: list = None):
        super().__init__(content, stage="quiz")
        self._quiz_items: list[dict] = existing_quiz_items or []
        self._current_index: int = 0
        self._answers: list[int] = []

    def _generate_quiz_items(self, num: int = 5) -> list[dict]:
        """
        调用 LLM 生成测验题

        Args:
            num: 题目数量

        Returns:
            [{question, options, correct_index, explanation}, ...]
        """
        prompt = f"""请根据以下课件内容生成 {num} 道单选题测验题。

课件内容：
{self.content[:4000]}

要求：
1. 每道题为单选题
2. 题目要测试学员对关键知识点的理解
3. 选项要有区分度，干扰项要合理
4. 必须明确标注正确答案（correct_index: 0=A, 1=B, 2=C, 3=D）
5. 输出 JSON 数组格式，不要有其他内容

格式：
[
  {{
    "question": "题目内容",
    "options": ["选项A", "选项B", "选项C", "选项D"],
    "correct_index": 0,
    "explanation": "题解"
  }}
]"""

        try:
            response = call_llm(prompt, "")
            # 提取 JSON
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                items = json.loads(json_match.group(0))
                return items
        except Exception:
            pass
        return []

    def get_current_question(self) -> Optional[dict]:
        """
        获取当前题目

        Returns:
            当前题目 dict 或 None（测验结束）
        """
        if self._current_index >= len(self._quiz_items):
            return None

        item = self._quiz_items[self._current_index]
        return {
            "index": self._current_index,
            "total": len(self._quiz_items),
            "id": item.get('id', f'q{self._current_index + 1}'),
            "question": item.get('question', ''),
            "options": item.get('options', []),
            "explanation": item.get('explanation', '')
        }

    async def chat(self, user_input: str) -> str:
        """
        评估员工回答，推进到下一题

        Args:
            user_input: 员工回答（如 "A" 或 "1" ）

        Returns:
            AI 反馈和下一题或结果
        """
        if self._current_index >= len(self._quiz_items):
            return "测验已完成，感谢参与！"

        current_item = self._quiz_items[self._current_index]

        # 解析答案
        answer = user_input.strip().upper()
        if answer in ['A', 'B', 'C', 'D']:
            selected = ['A', 'B', 'C', 'D'].index(answer)
        elif answer.isdigit() and 0 <= int(answer) <= 3:
            selected = int(answer)
        else:
            return f"请输入 A/B/C/D 或 0/1/2/3 格式的答案"

        correct = current_item.get('correct_index', 0)
        is_correct = selected == correct

        self._answers.append(selected)

        # 构建反馈
        feedback = f"第 {self._current_index + 1} 题：{'✅ 正确！' if is_correct else '❌ 错误！'}\n\n"
        feedback += f"你的答案：{answer}\n"
        feedback += f"正确答案：{['A', 'B', 'C', 'D'][correct]}\n\n"
        feedback += f"题解：{current_item.get('explanation', '')}"

        # 推进到下一题
        self._current_index += 1

        if self._current_index < len(self._quiz_items):
            next_item = self.get_current_question()
            feedback += f"\n\n📝 下一题（{self._current_index + 1}/{len(self._quiz_items)}）：\n"
            feedback += f"{next_item['question']}\n"
            for i, opt in enumerate(next_item['options']):
                feedback += f"  {'ABCD'[i]}. {opt}\n"
        else:
            # 测验结束
            correct_count = sum(1 for i, a in enumerate(self._answers) if i < len(self._quiz_items) and a == self._quiz_items[i].get('correct_index', 0))
            score = (correct_count / len(self._quiz_items) * 100) if self._quiz_items else 0
            passed = score >= 60

            feedback += f"\n\n🎉 测验完成！\n"
            feedback += f"得分：{score:.0f} 分（{correct_count}/{len(self._quiz_items)} 正确）\n"
            feedback += f"结果：{'🎊 合格！' if passed else '📚 继续加油！'}"

        self.add_message("user", user_input)
        self.add_message("assistant", feedback)
        return feedback


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
