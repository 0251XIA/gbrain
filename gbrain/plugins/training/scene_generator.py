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
        """从讲义内容中提取关键段落，生成具体场景"""
        sections = []

        # 预处理：清理内容
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            if any(kw in line for kw in ['通过本培训', '本章将介绍', '让我们从一个问题开始']):
                continue
            if re.match(r'^\|[\s\-:|]+\|$', line.strip()):
                continue
            cleaned_lines.append(line)

        cleaned_content = '\n'.join(cleaned_lines)

        # 按 ### 或 ## 标题分割内容
        parts = re.split(r'^#{2,3}\s+', cleaned_content, flags=re.MULTILINE)

        # 提取每个部分作为场景
        for i, part in enumerate(parts[1:num_scenes+1]):
            part_lines = [l for l in part.strip().split('\n') if l.strip()]
            if not part_lines:
                continue

            title = part_lines[0] if part_lines else f"内容{i+1}"
            body_lines = part_lines[1:7] if len(part_lines) > 1 else part_lines[:1]
            body_text = '\n'.join(body_lines)

            # 清理 markdown 格式
            body_text = re.sub(r'^[-*]\s+', '', body_text)
            body_text = re.sub(r'\*\*(.+?)\*\*', r'\1', body_text)
            body_text = re.sub(r'\*\s*', '', body_text)

            # 生成具体场景
            scene = self._build_scene_from_content(title, body_text, i + 1)
            sections.append(scene)

        # 如果提取的不够，尝试从内容中提取关键句子作为场景
        if len(sections) < num_scenes:
            key_lines = []
            for line in cleaned_lines:
                if any(kw in line for kw in ['服务', '处理', '响应', '操作', '流程', '规范', '要求', '礼仪', '着装', '拜访', '沟通']):
                    line_clean = re.sub(r'^[-*]\s+', '', line.strip())
                    if len(line_clean) > 10:
                        key_lines.append(line_clean)

            for kw_line in key_lines[:num_scenes - len(sections)]:
                sections.append({
                    'title': f'场景{len(sections)+1}',
                    'description': f"请根据以下内容回答：\n\n{kw_line}",
                    'knowledge_points': [kw_line[:20]],
                    'correct_answer': '结合培训内容给出完整回答',
                    'explanation': kw_line,
                    'hint': '请结合培训学到的知识来回答'
                })

        # 如果仍然不够，补充
        while len(sections) < num_scenes:
            sections.append({
                'title': f'场景{len(sections)+1}：综合应用',
                'description': '结合前面学到的培训内容，综合处理这个工作场景',
                'knowledge_points': ['综合应用'],
                'correct_answer': '综合运用培训所学知识',
                'explanation': '结合前面所有场景的内容来处理'
            })

        return sections[:num_scenes]

    def _build_scene_from_content(self, title: str, body: str, index: int) -> dict:
        """根据内容构建具体场景"""
        # 提取关键词
        keywords = []
        for kw in ['礼仪', '着装', '拜访', '沟通', '服务', '处理', '规范', '要求', '电话', '邮件', '介绍', '握手', '名片']:
            if kw in body or kw in title:
                keywords.append(kw)

        # 生成情境描述
        if not keywords:
            scenario_context = "在日常工作中"
            action = "处理以下工作场景"
        else:
            kw = keywords[0]
            contexts = {
                '礼仪': '在商务交往中',
                '着装': '在准备拜访客户时',
                '拜访': '在拜访重要客户时',
                '沟通': '在与同事协作时',
                '服务': '在客户服务过程中',
                '处理': '在处理工作时',
                '规范': '在按照公司要求执行时',
                '要求': '在完成工作任务时',
                '电话': '在接听商务电话时',
                '邮件': '在撰写商务邮件时',
                '介绍': '在介绍公司或产品时',
                '握手': '在与客户会面时',
                '名片': '在交换名片时'
            }
            scenario_context = contexts.get(kw, '在工作中')

        # 简化body，只保留核心内容
        body_short = body[:200].strip() if body else ""

        return {
            'title': f'{index}. {title[:40]}',
            'description': f"{scenario_context}，遇到以下情况：\n\n{body_short}\n\n请问你会如何处理？",
            'knowledge_points': keywords if keywords else [title[:20]],
            'correct_answer': self._generate_correct_answer(title, body),
            'explanation': body_short,
            'hint': f'请结合"{title}"的要点来回答'
        }

    def _generate_correct_answer(self, title: str, body: str) -> str:
        """生成参考答案"""
        # 根据标题生成参考答案
        if '着装' in title or '穿着' in title:
            return "应穿着深色西装搭配白色衬衫和深色领带，皮鞋保持光亮，体现专业形象。"
        elif '礼仪' in title:
            return "遵循商务礼仪规范，尊重对方，注意言行举止，给对方留下良好印象。"
        elif '拜访' in title:
            return "提前预约，准时到达，准备充分，注意着装和沟通礼仪。"
        elif '沟通' in title:
            return "使用礼貌用语，认真倾听，及时回应，保持专业态度。"
        elif '电话' in title:
            return "响铃三声内接听，先问候并自报家门，注意通话礼仪。"
        elif '邮件' in title:
            return "主题明确，内容简洁，使用礼貌用语，附件清晰标注。"
        else:
            return f"按照培训中关于「{title}」的要求规范处理。"


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
