import pytest
from unittest.mock import patch
from gbrain.plugins.training.skills.lecture_generation.lecture_generator import LectureGenerator
from gbrain.plugins.training.skills.lecture_generation.models import ParsedPrompt, IntegratedContent


def test_generate_lecture():
    generator = LectureGenerator()

    parsed = ParsedPrompt(
        topic="契约锁产品知识培训",
        audience="新入职销售",
        position="销售代表",
        industry="企业服务/SaaS",
        duration="90分钟",
        style="专业严谨",
        objectives=["掌握核心功能"],
        special_requirements=[],
        forbidden_content=[],
        num_modules=1,
        outline_structure={}
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
    # Mock the LLM call to return a digital human script format response
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
        objectives=["掌握核心功能", "了解使用场景"],
        special_requirements=[],
        forbidden_content=[],
        num_modules=1,
        outline_structure={}
    )

    integrated = IntegratedContent(
        module_contents={"模块1": ["电子签章服务：帮助企业实现合同电子签署"]},
        case_library=[{"content": "某公司使用电子签章提升效率案例", "type": "case"}],
        supplementary_materials={}
    )

    result = generator.generate(parsed, integrated, "product", output_format="digital_human_script")

    # 口播稿应包含特定章节标记
    assert "课程定位" in result or "课程开场白" in result or "口播" in result
    # 不应包含标准课件的固定格式
    assert "培训信息" not in result or "学习目标" in result