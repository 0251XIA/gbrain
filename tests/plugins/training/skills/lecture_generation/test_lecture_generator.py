import pytest
from unittest.mock import patch, MagicMock
from gbrain.plugins.training.skills.lecture_generation.lecture_generator import LectureGenerator
from gbrain.plugins.training.skills.lecture_generation.models import ParsedPrompt, IntegratedContent


@patch("gbrain.plugins.training.skills.lecture_generation.lecture_generator.call_llm")
def test_generate_lecture(mock_call_llm):
    """测试生成培训讲义（mock LLM）"""
    mock_call_llm.return_value = """# 契约锁产品知识培训

## 培训信息
- **培训受众：** 新入职销售
- **目标岗位：** 销售代表

## 学习目标
1. 掌握核心功能

### 开篇

**【场景引入】**
...

**【方法讲解】**
契约锁核心功能包括...

### 模块1

**【方法讲解】**
电子签章服务

**【案例佐证】**
某科技公司案例

**【避坑指南】**
- ✅ 正确做法

**【即时练习】**
...
"""

    generator = LectureGenerator()

    parsed = ParsedPrompt(
        topic="契约锁产品知识培训",
        audience="新入职销售",
        position="销售代表",
        industry="企业服务/SaaS",
        duration="90分钟",
        style="专业严谨",
        description="",
        objectives=["掌握核心功能"],
        special_requirements=[],
        forbidden_content=[],
        num_modules=1,
        outline_structure={"模块拆解层": ["模块1"]}
    )

    integrated = IntegratedContent(
        module_contents={"模块1": ["电子签章服务"]},
        case_library=[],
        supplementary_materials={}
    )

    result = generator.generate(parsed, integrated, "product")

    assert "# 契约锁产品知识培训" in result
    assert "新入职销售" in result


@patch("gbrain.plugins.training.skills.lecture_generation.lecture_generator.call_llm")
def test_generate_digital_human_script(mock_call_llm):
    """测试 output_format=digital_human_script 输出口播稿格式"""
    mock_call_llm.return_value = """# 课程定位

## 适用对象
新入职销售团队

## 培训目标
1. 掌握核心功能
2. 了解使用场景

## 课程时长建议
90分钟

---

# 课程开场白

各位新入职的销售伙伴，大家好！欢迎来到契约锁产品知识培训...

---

# 口播正文

## 模块1：电子签章服务

### 数字人口播稿
今天我们来学习契约锁的核心功能——电子签章服务...
"""

    generator = LectureGenerator()

    parsed = ParsedPrompt(
        topic="契约锁产品知识培训",
        audience="新入职销售",
        position="销售代表",
        industry="企业服务/SaaS",
        duration="90分钟",
        style="口语化",
        description="",
        objectives=["掌握核心功能", "了解使用场景"],
        special_requirements=[],
        forbidden_content=[],
        num_modules=1,
        outline_structure={"模块拆解层": ["模块1"]}
    )

    integrated = IntegratedContent(
        module_contents={"模块1": ["电子签章服务：帮助企业实现合同电子签署"]},
        case_library=[{"content": "某公司使用电子签章提升效率案例", "type": "case"}],
        supplementary_materials={}
    )

    result = generator.generate(parsed, integrated, "product", output_format="digital_human_script")

    # 口播稿应包含特定章节标记
    assert "课程定位" in result or "课程开场白" in result or "口播" in result


@patch("gbrain.plugins.training.skills.lecture_generation.lecture_generator.call_llm")
def test_generate_with_knowledge_context(mock_call_llm):
    """测试知识库内容被正确传递"""
    captured_prompt = None

    def capture_call(prompt, system_prompt=""):
        nonlocal captured_prompt
        captured_prompt = prompt
        return "# 商务礼仪培训\n\n## 学习目标\n1. 掌握职业形象"

    mock_call_llm.side_effect = capture_call

    generator = LectureGenerator()

    parsed = ParsedPrompt(
        topic="商务礼仪培训",
        audience="新员工",
        position="通用",
        industry="通用",
        duration="60分钟",
        style="专业严谨",
        description="",
        objectives=["掌握职业形象"],
        special_requirements=[],
        forbidden_content=[],
        num_modules=1,
        outline_structure={"模块拆解层": ["职业形象"]}
    )

    integrated = IntegratedContent(
        module_contents={"职业形象": ["着装规范：商务正装，色彩搭配"]},
        case_library=[{"content": "某公司员工着装得体获客户好评案例", "type": "case"}],
        supplementary_materials={"resources": ["培训手册V2.0"]}
    )

    result = generator.generate(parsed, integrated, "product")

    # 验证知识库内容被传递
    assert captured_prompt is not None
    assert "着装规范" in captured_prompt
    assert "商务正装" in captured_prompt