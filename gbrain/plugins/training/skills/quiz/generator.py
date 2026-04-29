"""
考核题生成器
"""

import re
import json
from typing import Optional

from .models import QuizItem
from .prompts import QUIZ_GENERATION_PROMPT


class QuizGenerator:
    """考核题生成器"""

    def __init__(self):
        pass

    def generate_quiz(
        self,
        lecture_content: str,
        num_questions: int = 5,
        topic: str = ""
    ) -> list[QuizItem]:
        """
        生成考核题目

        Args:
            lecture_content: 讲义内容
            num_questions: 题目数量
            topic: 培训主题

        Returns:
            list[QuizItem]: 题目列表
        """
        cleaned_content = self._clean_content(lecture_content)

        try:
            from gbrain.plugins.training.course_gen import call_llm

            prompt = QUIZ_GENERATION_PROMPT.format(
                content=cleaned_content[:3000],
                num_questions=num_questions
            )

            response = call_llm(prompt, "")

            # 解析 JSON
            quiz_data = self._parse_json_response(response)

            if quiz_data and 'questions' in quiz_data:
                items = []
                for i, q in enumerate(quiz_data['questions']):
                    item = QuizItem(
                        id=i + 1,
                        type=q.get('type', 'choice'),
                        question=q.get('question', ''),
                        options=q.get('options', []),
                        correct_answer=str(q.get('correct_answer', '')),
                        explanation=q.get('explanation', '')
                    )
                    items.append(item)
                return items

        except Exception as e:
            print(f"生成题目失败: {e}")

        # 生成默认题目
        return self._generate_default_quiz(cleaned_content, num_questions)

    def _clean_content(self, content: str) -> str:
        """清理讲义内容"""
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()

    def _parse_json_response(self, response: str) -> Optional[dict]:
        """解析 JSON 响应"""
        try:
            return json.loads(response)
        except:
            pass

        # 尝试提取 JSON 块
        match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except:
                pass

        match = re.search(r'```\s*([\s\S]*?)\s*```', response)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except:
                pass

        start = response.find('{')
        if start == -1:
            return None

        for end in range(len(response) - 1, start - 1, -1):
            if response[end] == '}':
                try:
                    return json.loads(response[start:end + 1])
                except:
                    continue

        return None

    def _generate_default_quiz(self, content: str, num_questions: int) -> list[QuizItem]:
        """生成默认题目"""
        items = []

        # 提取章节标题作为题目
        sections = re.findall(r'^##\s+(.+?)$', content, re.MULTILINE)

        for i, section in enumerate(sections[:num_questions]):
            items.append(QuizItem(
                id=i + 1,
                type='choice',
                question=f"关于「{section}」，以下说法正确的是？",
                options=[
                    f"A. 这是{sections[i % len(sections)]}的重要内容",
                    "B. 这与培训内容无关",
                    "C. 这是可选内容",
                    "D. 这不是考核重点"
                ],
                correct_answer="A",
                explanation=f"根据培训内容，「{section}」是重要知识点"
            ))

        # 如果不够，添加通用题目
        while len(items) < num_questions:
            idx = len(items)
            items.append(QuizItem(
                id=idx + 1,
                type='true_false',
                question=f"本题考察你对培训内容的理解程度（第{idx + 1}题）",
                correct_answer="true",
                explanation="请根据培训内容作答"
            ))

        return items


def generate_quiz(
    lecture_content: str,
    num_questions: int = 5,
    topic: str = ""
) -> list[QuizItem]:
    """便捷函数"""
    generator = QuizGenerator()
    return generator.generate_quiz(lecture_content, num_questions, topic)
