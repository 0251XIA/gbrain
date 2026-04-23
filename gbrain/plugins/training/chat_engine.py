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
    """导览引擎 - 带领员工浏览课件内容"""

    def __init__(self, content: str):
        super().__init__(content, stage="tour")
        self._sections: list[dict] = self._split_content()
        self._current_index: int = 0

    def _split_content(self) -> list[dict]:
        """
        将课件按 ## 标题分段

        Returns:
            [{title, content, start_pos, end_pos}, ...]
        """
        sections = []
        # 匹配 ## 标题
        pattern = r'^(##\s+.+)$'
        lines = self.content.split('\n')

        current_section = None
        current_lines = []

        for line in lines:
            if re.match(pattern, line):
                # 保存上一个 section
                if current_section is not None:
                    current_section['content'] = '\n'.join(current_lines).strip()
                    sections.append(current_section)

                # 开始新 section
                current_section = {
                    'title': line.lstrip('#').strip(),
                    'content': '',
                    'start_pos': 0,
                    'end_pos': 0
                }
                current_lines = []
            else:
                current_lines.append(line)

        # 保存最后一个 section
        if current_section is not None:
            current_section['content'] = '\n'.join(current_lines).strip()
            sections.append(current_section)

        # 计算位置信息
        pos = 0
        for section in sections:
            section['start_pos'] = pos
            pos += len(section['title']) + 1 + len(section['content']) + 1
            section['end_pos'] = pos

        return sections

    def get_section_intro(self) -> str:
        """
        获取当前章节介绍

        Returns:
            当前章节的标题和简介
        """
        if self._current_index >= len(self._sections):
            return "课程内容已全部浏览完毕！"

        section = self._sections[self._current_index]
        intro = f"【{self._current_index + 1}/{len(self._sections)}】{section['title']}\n\n"
        intro += section['content'][:300]
        if len(section['content']) > 300:
            intro += "..."
        return intro

    def advance_section(self) -> bool:
        """
        推进到下一章节

        Returns:
            是否还有下一章节
        """
        if self._current_index < len(self._sections) - 1:
            self._current_index += 1
            return True
        return False

    async def chat(self, user_input: str) -> str:
        """
        处理员工回答，判断是否理解，推进章节

        Args:
            user_input: 员工输入

        Returns:
            AI 反馈和章节推进信息
        """
        current_title = self._sections[self._current_index]['title'] if self._current_index < len(self._sections) else "未知章节"

        prompt = f"""当前章节：{current_title}
员工回复：{user_input}

请评估员工对当前章节内容的理解程度：
1. 是否理解了核心概念？
2. 回答是否正确反映了学习内容？
3. 是否需要进一步解释？

请用鼓励性的语言给予反馈，并判断是否可以进入下一章节（回复"继续"或"再讲一遍"）。"""

        response = call_llm(prompt, self.system_prompt)

        # 检查是否理解（简单判断关键词）
        understood_keywords = ['理解', '懂了', '明白', '正确', '继续', '下一章']
        needs_review = not any(kw in user_input for kw in understood_keywords)

        if not needs_review:
            # 可以推进
            has_next = self.advance_section()
            if has_next:
                response += f"\n\n📖 让我们进入下一章节：{self._sections[self._current_index]['title']}"
            else:
                response += "\n\n🎉 恭喜！你已完成全部课程内容的学习。"

        self.add_message("user", user_input)
        self.add_message("assistant", response)
        return response


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
            user_input: 员工回答（如 "A" 或 "1"）

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