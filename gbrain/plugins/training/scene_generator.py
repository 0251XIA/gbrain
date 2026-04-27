"""
场景生成器 - 根据讲义内容动态生成学习场景链
"""

import json
import re
import uuid
from typing import Optional

from .models import Scene, SceneChain


class SceneGenerator:
    """场景生成器"""

    def __init__(self):
        self.scene_prompt_template = """你是一个企业培训场景设计师。基于以下培训讲义内容，生成一个场景学习链。

讲义内容：
{content}

要求：
1. 将讲义内容拆解为 {num_scenes} 个核心场景
2. 每个场景对应1-2个核心知识点
3. 场景之间要有逻辑递进关系（入门→进阶→综合）
4. 每个场景要具体、可操作，包含明确的判断点或行动点
5. 每个场景的"正确答案"要简洁，50字以内

输出格式（必须是有效的JSON）：
{{
    "scenes": [
        {{
            "title": "场景1：[标题]",
            "description": "[具体工作情境，100字以内]",
            "knowledge_points": ["知识点1", "知识点2"],
            "correct_answer": "[标准答案，50字以内]",
            "explanation": "[讲解要点，用户答错时展示]",
            "hint": "[提示，10字以内]"
        }},
        ...
    ],
    "weak_points": ["在整个学习过程中需要重点关注的薄弱环节"]
}}

注意：
- 只输出JSON，不要有其他内容
- scenes 数组必须包含至少 {num_scenes} 个场景
- 每个场景的 description 要具体，像真实工作中会遇到的情况"""

    def generate_scene_chain(self, lecture_content: str, num_scenes: int = 4) -> Optional[SceneChain]:
        """
        根据讲义内容生成场景链

        Args:
            lecture_content: 讲义内容
            num_scenes: 场景数量，默认4个

        Returns:
            SceneChain 对象，或 None（生成失败时）
        """
        # 预处理讲义内容
        cleaned_content = self._clean_content(lecture_content)

        # 调用 LLM 生成场景
        try:
            from .course_gen import call_llm

            prompt = self.scene_prompt_template.format(
                content=cleaned_content[:4000],  # 限制内容长度
                num_scenes=num_scenes
            )

            response = call_llm(prompt, "")

            # 解析 JSON 响应
            scenes_data = self._parse_json_response(response)

            if not scenes_data or 'scenes' not in scenes_data:
                # 如果解析失败，生成默认场景
                return self._generate_default_chain(lecture_content, num_scenes)

            # 构建 Scene 对象列表
            scenes = []
            for i, scene_data in enumerate(scenes_data.get('scenes', [])):
                scene = Scene(
                    index=i + 1,
                    title=scene_data.get('title', f'场景{i+1}'),
                    description=scene_data.get('description', ''),
                    knowledge_points=scene_data.get('knowledge_points', []),
                    correct_answer=scene_data.get('correct_answer', ''),
                    explanation=scene_data.get('explanation', ''),
                    hint=scene_data.get('hint', '')
                )
                scenes.append(scene)

            # 构建 SceneChain
            weak_points = scenes_data.get('weak_points', [])

            return SceneChain(
                task_id="",  # 稍后设置
                scenes=scenes,
                weak_points=weak_points
            )

        except Exception as e:
            print(f"生成场景链失败: {e}")
            # 生成默认场景链
            return self._generate_default_chain(lecture_content, num_scenes)

    def _clean_content(self, content: str) -> str:
        """清理讲义内容"""
        if not content:
            return content

        # 移除 AI 思考过程标记
        content = re.sub(r'<think>[\s\S]*?</think>', '', content)

        # 移除 Markdown 表格的分隔行（保留表头和数据）
        lines = content.split('\n')
        cleaned_lines = []
        skip_next = False

        for i, line in enumerate(lines):
            # 跳过纯分隔行
            if re.match(r'^\|[\s\-:|]+\|$', line.strip()):
                continue
            # 跳过常见的引导性内容
            if any(kw in line for kw in ['通过本培训', '本章将介绍', '让我们从一个问题开始']):
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _parse_json_response(self, response: str) -> Optional[dict]:
        """解析 LLM 返回的 JSON 响应"""
        if not response:
            return None

        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 块
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _generate_default_chain(self, lecture_content: str, num_scenes: int) -> SceneChain:
        """
        生成默认场景链（当 LLM 生成失败时使用）

        从讲义内容中提取关键段落作为场景
        """
        # 提取讲义中的关键段落
        key_sections = self._extract_key_sections(lecture_content, num_scenes)

        scenes = []
        for i, section in enumerate(key_sections):
            scene = Scene(
                index=i + 1,
                title=f"场景{i+1}：{section.get('title', '学习内容')}",
                description=section.get('content', ''),
                knowledge_points=section.get('knowledge_points', []),
                correct_answer=section.get('correct_answer', '按照培训要求处理'),
                explanation=section.get('explanation', ''),
                hint="结合培训内容处理"
            )
            scenes.append(scene)

        return SceneChain(
            task_id="",
            scenes=scenes,
            weak_points=["培训相关内容"]
        )

    def _extract_key_sections(self, content: str, num_scenes: int) -> list[dict]:
        """从讲义内容中提取关键段落"""
        sections = []

        # 按 ## 标题分割内容
        parts = re.split(r'^##\s+', content, flags=re.MULTILINE)

        for i, part in enumerate(parts[1:num_scenes+1]):  # 跳过第一个空部分
            lines = part.strip().split('\n')
            title = lines[0] if lines else f"内容{i+1}"
            content_text = '\n'.join(lines[1:5])  # 取前几行作为内容

            sections.append({
                'title': title[:50],
                'content': content_text[:200],
                'knowledge_points': [title],
                'correct_answer': '按照培训要求处理',
                'explanation': content_text[:100]
            })

        # 如果提取的不够，补充
        while len(sections) < num_scenes:
            sections.append({
                'title': f'场景{len(sections)+1}',
                'content': '请根据培训内容完成相关任务',
                'knowledge_points': ['培训内容'],
                'correct_answer': '按照培训要求处理',
                'explanation': '请认真学习培训内容'
            })

        return sections[:num_scenes]


def generate_scene_chain(lecture_content: str, num_scenes: int = 4, task_id: str = None) -> Optional[SceneChain]:
    """
    便捷函数：根据讲义内容生成场景链

    Args:
        lecture_content: 讲义内容
        num_scenes: 场景数量，默认4个
        task_id: 任务ID（可选）

    Returns:
        SceneChain 对象，或 None
    """
    generator = SceneGenerator()
    chain = generator.generate_scene_chain(lecture_content, num_scenes)
    if chain and task_id:
        chain.task_id = task_id
    return chain
