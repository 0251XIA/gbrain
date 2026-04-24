import re
from dataclasses import dataclass
from typing import Literal
from .models import ParsedPrompt, StyleType


class PromptParser:
    def parse(self, markdown: str) -> ParsedPrompt:
        """解析 Markdown 格式的用户需求"""
        lines = markdown.strip().split('\n')

        # 提取基本信息
        info = self._extract_info(lines)

        # 提取需求描述
        description = self._extract_description(lines)

        # 提取学习目标
        objectives = self._extract_objectives(lines)

        # 提取特殊要求
        special_req = self._extract_special_requirements(lines)

        # 提取禁止内容
        forbidden = self._extract_forbidden_content(lines)

        # 提取大纲结构
        outline = self._extract_outline_structure(lines)

        # 计算模块数量
        num_modules = self._count_modules(lines)

        return ParsedPrompt(
            topic=info.get('topic', ''),
            audience=info.get('audience', ''),
            position=info.get('position', ''),
            industry=info.get('industry', ''),
            duration=info.get('duration', ''),
            style=self._parse_style(info.get('style', '专业严谨')),
            description=description,
            objectives=objectives,
            special_requirements=special_req,
            forbidden_content=forbidden,
            num_modules=num_modules,
            outline_structure=outline
        )

    def _extract_info(self, lines: list[str]) -> dict[str, str]:
        # 中文 key 到英文 key 的映射
        key_map = {
            '培训主题': 'topic',
            '培训受众': 'audience',
            '目标岗位': 'position',
            '所属行业': 'industry',
            '时长': 'duration',
            '风格': 'style',
            '需求描述': 'description'
        }
        in_basic_info = False
        info = {}
        for line in lines:
            if '## 基本信息' in line:
                in_basic_info = True
                continue
            if in_basic_info:
                if line.startswith('## '):
                    break
                match = re.match(r'- (.+?)：(.+)', line)
                if match:
                    raw_key, value = match.groups()
                    key = key_map.get(raw_key.strip(), raw_key.strip())
                    info[key] = value.strip()
        return info

    def _extract_objectives(self, lines: list[str]) -> list[str]:
        in_objectives = False
        objectives = []
        for line in lines:
            if '## 学习目标' in line:
                in_objectives = True
                continue
            if in_objectives:
                if line.startswith('## '):
                    break
                match = re.match(r'\d+\.\s*(.+)', line)
                if match:
                    objectives.append(match.group(1).strip())
        return objectives

    def _extract_description(self, lines: list[str]) -> str:
        """提取需求描述"""
        in_desc = False
        desc_lines = []
        for line in lines:
            if '## 需求描述' in line:
                in_desc = True
                continue
            if in_desc:
                if line.startswith('## '):
                    break
                desc_lines.append(line.strip())
        return '\n'.join(desc_lines).strip()

    def _extract_special_requirements(self, lines: list[str]) -> list[str]:
        in_req = False
        reqs = []
        for line in lines:
            if '## 特殊要求' in line:
                in_req = True
                continue
            if in_req:
                if line.startswith('## '):
                    break
                if line.startswith('- '):
                    reqs.append(line[2:].strip())
        return reqs

    def _extract_forbidden_content(self, lines: list[str]) -> list[str]:
        in_forbidden = False
        forbidden = []
        for line in lines:
            if '## 禁止内容' in line or '## 禁忌' in line:
                in_forbidden = True
                continue
            if in_forbidden:
                if line.startswith('## '):
                    break
                if line.startswith('- '):
                    forbidden.append(line[2:].strip())
        return forbidden

    def _extract_outline_structure(self, lines: list[str]) -> dict:
        in_outline = False
        outline = {}
        current_section = None
        for line in lines:
            if '## 大纲结构' in line:
                in_outline = True
                continue
            if in_outline:
                if line.startswith('## '):
                    break
                # 检查是否是一级标题（### 而非 ####）
                if line.startswith('### ') and not line.startswith('#### '):
                    current_section = line.replace('### ', '').strip()
                    outline[current_section] = []
                elif current_section and line.startswith('#### '):
                    outline[current_section].append(line.replace('#### ', '').strip())
        return outline

    def _count_modules(self, lines: list[str]) -> int:
        return sum(1 for line in lines if re.match(r'#### 模块', line))

    def _parse_style(self, style: str) -> StyleType:
        style_map = {
            '实操导向': '实操导向',
            '专业严谨': '专业严谨',
            '口语化': '口语化'
        }
        return style_map.get(style, '专业严谨')
