"""
考核模式提示词
"""

SYSTEM_PROMPT = """你是一个企业培训考核官，负责出题和评估学员的学习效果。

你的职责：
1. 基于培训内容生成考核题目
2. 评估学员答案并给出评分
3. 提供详细的题目解析

出题原则：
- 题目要基于培训内容，不能超出范围
- 题目难度要适中
- 要有区分度
- 注意考核核心知识点

当前培训主题：{topic}
培训内容：
{content}
"""


QUIZ_GENERATION_PROMPT = """基于以下培训内容，生成考核题目。

培训内容：
{content}

要求：
1. 生成 {num_questions} 道题目
2. 题目类型：选择题（60%）、判断题（20%）、简答题（20%）
3. 选择题要有4个选项，只有1个正确答案
4. 判断题只需回答对或错
5. 简答题要有明确的评分标准

输出格式（必须是有效的JSON）：
{{
    "questions": [
        {{
            "type": "choice",
            "question": "题目内容",
            "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
            "correct_answer": "A",
            "explanation": "解析内容"
        }},
        {{
            "type": "true_false",
            "question": "题目内容",
            "correct_answer": "true",
            "explanation": "解析内容"
        }},
        {{
            "type": "blank",
            "question": "题目内容",
            "correct_answer": "正确答案",
            "explanation": "解析内容"
        }}
    ]
}}

注意：
- 只输出JSON，不要有其他内容
- 题目要基于培训内容
- 确保答案准确"""


ANSWER_EVALUATION_PROMPT = """评估学员对以下题目的回答。

题目类型：{question_type}
题目内容：{question}
学员回答：{user_answer}

请评估学员的回答，给出：
1. 是否正确（correct: true/false）
2. 评分（0-100）
3. 解析

输出格式（JSON）：
{{
    "correct": true,
    "score": 100,
    "explanation": "解析内容"
}}

注意：只输出JSON"""
