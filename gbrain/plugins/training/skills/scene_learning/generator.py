"""
场景生成器
"""

import re
import json
from typing import Optional

from .models import Scene, SceneChain
from .prompts import SCENE_GENERATION_PROMPT


class SceneGenerator:
    """场景生成器"""

    def __init__(self):
        pass

    def generate_scene_chain(
        self,
        lecture_content: str,
        num_scenes: int = 4,
        task_id: str = ""
    ) -> Optional[SceneChain]:
        """
        根据讲义内容生成场景链

        Args:
            lecture_content: 讲义内容
            num_scenes: 场景数量，默认4个
            task_id: 任务ID

        Returns:
            SceneChain 对象，或 None
        """
        # 清理讲义内容
        cleaned_content = self._clean_content(lecture_content)

        try:
            from gbrain.plugins.training.course_gen import call_llm

            prompt = SCENE_GENERATION_PROMPT.format(
                content=cleaned_content[:4000],
                num_scenes=num_scenes
            )

            response = call_llm(prompt, "")

            # 解析 JSON 响应
            scenes_data = self._parse_json_response(response)

            if not scenes_data or 'scenes' not in scenes_data:
                return self._generate_default_chain(lecture_content, num_scenes, task_id)

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
                task_id=task_id,
                scenes=scenes,
                weak_points=weak_points
            )

        except Exception as e:
            print(f"生成场景链失败: {e}")
            return self._generate_default_chain(lecture_content, num_scenes, task_id)

    def _clean_content(self, content: str) -> str:
        """清理讲义内容"""
        # 移除 markdown 图片
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        # 移除多余空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()

    def _parse_json_response(self, response: str) -> Optional[dict]:
        """解析 JSON 响应"""
        # 尝试直接解析
        try:
            return json.loads(response)
        except:
            pass

        # 尝试提取 ```json ... ``` 块
        match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except:
                pass

        # 尝试提取 ``` ... ``` 块
        match = re.search(r'```\s*([\s\S]*?)\s*```', response)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except:
                pass

        # 尝试找到 JSON 对象
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

    def _generate_default_chain(
        self,
        lecture_content: str,
        num_scenes: int,
        task_id: str
    ) -> Optional[SceneChain]:
        """生成默认场景链"""
        key_sections = self._extract_key_sections(lecture_content, num_scenes)

        scenes = []
        for i, section in enumerate(key_sections):
            scene = Scene(
                index=i + 1,
                title=section.get('title', f'场景{i+1}'),
                description=section.get('description', ''),
                knowledge_points=section.get('knowledge_points', []),
                correct_answer=section.get('correct_answer', '按照培训要求处理'),
                explanation=section.get('explanation', ''),
                hint='请结合培训内容回答'
            )
            scenes.append(scene)

        return SceneChain(
            task_id=task_id,
            scenes=scenes,
            weak_points=["培训相关内容"]
        )

    def _extract_key_sections(self, content: str, num_scenes: int) -> list[dict]:
        """从讲义内容中提取关键段落"""
        cleaned_content = self._clean_content(content)

        # Step 1: 提取知识点列表
        knowledge_points = self._extract_knowledge_points(cleaned_content)

        # Step 2: 计算场景数量（每个知识点 1-2 个场景）
        actual_num_scenes = self._calculate_scene_count(len(knowledge_points))

        # Step 3: 按优先级提取关键段落
        sections = self._extract_sections_by_priority(cleaned_content, knowledge_points, actual_num_scenes)

        return sections

    def _extract_knowledge_points(self, content: str) -> list[str]:
        """从讲义内容中提取知识点列表（按优先级）"""
        knowledge_points = []
        seen = set()  # 去重

        # P1: ### 三级标题
        h3_pattern = r'^###\s+(.+?)$'
        for match in re.finditer(h3_pattern, content, re.MULTILINE):
            title = match.group(1).strip()
            title = re.sub(r'^[\d\.、\s]+', '', title)
            if title and title not in seen:
                seen.add(title)
                knowledge_points.append(title)

        # P2: 有序号的重要行（1. xxx 2. xxx）
        for line in content.split('\n'):
            line = line.strip()
            # 匹配 "1. xxx 2. xxx 3. xxx" 格式
            if re.match(r'^\d+\.', line):
                # 拆分序号项
                items = re.split(r'(?=\d+\.)', line)
                for item in items:
                    item = item.strip()
                    if item and re.match(r'^\d+\.', item):
                        # 去掉序号
                        point = re.sub(r'^\d+\.\s*', '', item).strip()
                        # 取前20个字符作为知识点名
                        point = point[:30]
                        if point and point not in seen:
                            seen.add(point)
                            knowledge_points.append(point)

        # P3: 加粗/高亮关键词 **xxx**
        bold_pattern = r'\*\*(.+?)\*\*'
        for match in re.finditer(bold_pattern, content):
            point = match.group(1).strip()
            if len(point) >= 2 and point not in seen:
                seen.add(point)
                knowledge_points.append(point)

        # P4: 表格第一列（作为关键操作项）
        table_pattern = r'^\|.+\|\s*$'
        for line in content.split('\n'):
            line = line.strip()
            if re.match(r'^\|.+\|.*\|', line):
                # 提取第一列
                cols = line.split('|')
                if len(cols) >= 2:
                    first_col = cols[1].strip()
                    first_col = re.sub(r'^#+\s*', '', first_col)
                    if first_col and first_col not in seen and len(first_col) < 30:
                        seen.add(first_col)
                        knowledge_points.append(first_col)

        return knowledge_points

    def _calculate_scene_count(self, num_kp: int) -> int:
        """根据知识点数量计算场景数量（每个知识点 1-2 个场景）"""
        if num_kp <= 0:
            return 3
        min_scenes = num_kp                    # 每个知识点至少 1 个场景
        max_scenes = min(num_kp * 2, 8)       # 每个知识点最多 2 个场景，上限 8
        return max(3, min_scenes)            # 最少 3 个场景

    def _extract_sections_by_priority(
        self,
        content: str,
        knowledge_points: list[str],
        num_scenes: int
    ) -> list[dict]:
        """按优先级提取场景段落"""
        sections = []
        cleaned_content = self._clean_content(content)

        # 按 ## 分割成模块
        parts = re.split(r'^##\s+', cleaned_content, flags=re.MULTILINE)

        scene_index = 0
        for part_idx, part in enumerate(parts[1:], 1):
            sub_parts = re.split(r'^###\s+', part, flags=re.MULTILINE)

            for sub_idx, sub_part in enumerate(sub_parts[1:], 1):
                if scene_index >= num_scenes:
                    break

                sub_lines = [l for l in sub_part.strip().split('\n') if l.strip()]
                if not sub_lines:
                    continue

                title_line = sub_lines[0]
                title = re.sub(r'^[\d\.、\s]+', '', title_line)
                title = re.sub(r'^#+\s*', '', title)

                description_lines = sub_lines[1:6]
                description = '\n'.join(description_lines).strip()

                if len(description) < 20:
                    continue

                sections.append({
                    'title': f'场景{scene_index + 1}：{title[:20]}',
                    'description': description[:150],
                    'knowledge_points': [title] if title in knowledge_points else [title],
                    'correct_answer': f"按照培训中关于「{title}」的要求规范处理。",
                    'explanation': f"结合前面所有场景的内容来处理"
                })

                scene_index += 1

            if scene_index >= num_scenes:
                break

        # 如果提取不够，补充综合场景
        while len(sections) < num_scenes:
            sections.append({
                'title': f'场景{len(sections) + 1}：综合应用',
                'description': '结合前面学到的培训内容，综合处理这个工作场景',
                'knowledge_points': ['综合应用'],
                'correct_answer': '综合运用培训中学到的知识处理',
                'explanation': '结合前面所有场景的内容来处理'
            })

        return sections[:num_scenes]


def generate_scene_chain(
    lecture_content: str,
    num_scenes: int = 4,
    task_id: str = None
) -> Optional[SceneChain]:
    """便捷函数"""
    generator = SceneGenerator()
    chain = generator.generate_scene_chain(lecture_content, num_scenes, task_id or "")
    return chain
