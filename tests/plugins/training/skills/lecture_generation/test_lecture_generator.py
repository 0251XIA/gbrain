import pytest
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

    result = generator.generate(parsed, integrated)

    assert "# 契约锁产品知识培训" in result
    assert "新入职销售" in result