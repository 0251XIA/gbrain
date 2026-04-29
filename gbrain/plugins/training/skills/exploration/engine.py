"""
探索引擎 - 自由问答模式
"""

import re
from typing import Optional

from .models import ExplorationResult, ExplorationContext
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


class ExplorationEngine:
    """
    探索引擎

    特点：
    - 自由问答，不限制问题格式
    - 基于课件内容智能回答
    - 提供相关知识点和建议
    - 不记录学习进度
    """

    def __init__(self, content: str, topic: str = ""):
        """
        初始化探索引擎

        Args:
            content: 课件内容
            topic: 培训主题
        """
        self.content = content
        self.topic = topic
        self.history: list[dict] = []  # 对话历史
        self.context_stack: list[ExplorationContext] = []

    def chat(self, question: str) -> ExplorationResult:
        """
        处理用户问题

        Args:
            question: 用户问题

        Returns:
            ExplorationResult: 探索结果
        """
        # 添加到历史
        self.history.append({"role": "user", "content": question})

        # 构建 prompt
        system_prompt = SYSTEM_PROMPT.format(
            topic=self.topic or "培训内容",
            content=self._prepare_content()
        )

        user_prompt = USER_PROMPT_TEMPLATE.format(question=question)

        # 调用 LLM
        response = self._call_llm(system_prompt, user_prompt)

        # 移除思考过程标签
        response = re.sub(r'<think>[\s\S]*?</think>', '', response).strip()

        # 提取相关知识点
        related = self._extract_related_knowledge(question, response)

        # 添加到历史
        self.history.append({"role": "assistant", "content": response})

        return ExplorationResult(
            content=response,
            related_knowledge=related,
            suggestions=self._generate_suggestions(question)
        )

    def _prepare_content(self) -> str:
        """准备内容（限制长度）"""
        # 限制内容长度避免上下文溢出
        if len(self.content) > 3000:
            return self.content[:3000] + "\n...\n（内容已截断）"
        return self.content

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用 LLM"""
        from gbrain.plugins.training.course_gen import call_llm
        return call_llm(user_prompt, system_prompt)

    def _extract_related_knowledge(self, question: str, response: str) -> list[str]:
        """从内容和响应中提取相关知识点"""
        related = []

        # 提取内容中的章节标题
        section_pattern = r'^##\s+(.+?)$'
        matches = re.findall(section_pattern, self.content, re.MULTILINE)

        # 简单的关键词匹配
        question_keywords = self._extract_keywords(question)
        for section in matches:
            section_keywords = self._extract_keywords(section)
            if any(kw in section_keywords for kw in question_keywords):
                related.append(section)

        return related[:5]  # 最多返回5个

    def _extract_keywords(self, text: str) -> list[str]:
        """提取关键词"""
        # 提取中文词
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        # 提取英文词
        english_words = re.findall(r'[a-zA-Z0-9]{3,}', text)
        return chinese_words + english_words

    def _generate_suggestions(self, question: str) -> list[str]:
        """生成建议"""
        suggestions = []

        # 基于问题类型生成建议
        question_lower = question.lower()

        if any(kw in question_lower for kw in ['什么是', '定义', '解释']):
            suggestions.append("💡 你可以进入学习模式，系统地了解这个知识点")

        if any(kw in question_lower for kw in ['为什么', '原因', '原理']):
            suggestions.append("📖 建议查看培训中的案例，加深理解")

        if any(kw in question_lower for kw in ['怎么做', '如何', '方法', '步骤']):
            suggestions.append("🎯 可以进入考核模式，检验你是否掌握了操作方法")

        if not suggestions:
            suggestions.append("📚 如果想深入学习，可以输入「学习模式」进入系统学习")
            suggestions.append("✅ 或者输入「考核模式」检验学习效果")

        return suggestions

    def get_welcome_message(self) -> str:
        """获取欢迎消息"""
        return """🔍 **探索模式**

欢迎使用探索模式！我可以帮你：

• 解答关于培训内容的问题
• 解释专业术语和概念
• 提供具体的例子和案例
• 引导你深入理解知识点

**使用方式：**
- 直接输入你的问题，我会尽力解答
- 输入「学习模式」切换到场景学习
- 输入「考核模式」切换到测验考核
- 输入「帮助」查看更多命令

有什么想问的吗？"""

    def get_history(self) -> list[dict]:
        """获取对话历史"""
        return self.history.copy()

    def clear_history(self) -> None:
        """清空对话历史"""
        self.history = []
