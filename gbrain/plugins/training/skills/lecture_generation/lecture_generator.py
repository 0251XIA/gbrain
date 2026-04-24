from .models import ParsedPrompt, IntegratedContent


class LectureGenerator:
    CONTENT_TEMPLATE = """# {topic}

## 培训信息
- **培训受众：** {audience}
- **目标岗位：** {position}
- **所属行业：** {industry}
- **预计时长：** {duration}
- **培训风格：** {style}

## 学习目标
{objectives}

## 内容单元结构

### 开篇锚定层
**【场景引入】**
（真实业务场景）

**【问题抛出】**
（1-2个思考问题）

**【方法讲解】**
（核心知识点）

**【案例佐证】**
（公司真实案例）

**【避坑指南】**
- ✅ 正确做法
- ❌ 错误做法
- ⚠️ 注意事项

**【即时练习】**
（配套练习题）

{module_contents}
"""

    def generate(self, parsed: ParsedPrompt, integrated: IntegratedContent) -> str:
        """生成完整讲义"""
        objectives_text = '\n'.join(f"{i+1}. {obj}" for i, obj in enumerate(parsed.objectives))

        module_text = self._generate_modules(parsed, integrated)

        content = self.CONTENT_TEMPLATE.format(
            topic=parsed.topic,
            audience=parsed.audience,
            position=parsed.position,
            industry=parsed.industry,
            duration=parsed.duration,
            style=parsed.style,
            objectives=objectives_text,
            module_contents=module_text
        )

        return content

    def _generate_modules(self, parsed: ParsedPrompt, integrated: IntegratedContent) -> str:
        modules = []
        for module_name, contents in integrated.module_contents.items():
            if contents:
                module_text = f"""
### {module_name}

**【场景引入】**
（基于培训受众的实际业务场景）

**【方法讲解】**
{''.join(contents)}

**【案例佐证】**
（公司真实案例）

**【避坑指南】**
- ✅ 正确做法
- ❌ 错误做法

**【即时练习】**
（配套练习题）
"""
                modules.append(module_text)
        return '\n'.join(modules)