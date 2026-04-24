import pytest
from gbrain.plugins.training.skills.lecture_generation.content_integrator import ContentIntegrator
from gbrain.plugins.training.skills.lecture_generation.models import ParsedPrompt, IntegratedContent


def test_integrate_content():
    integrator = ContentIntegrator()

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
        outline_structure={"模块拆解层": ["模块1"]}
    )

    file_contents = ["契约锁产品功能介绍：电子签章、时间戳服务"]

    result = integrator.integrate(parsed, file_contents)

    assert isinstance(result, IntegratedContent)
    assert "模块1" in result.module_contents


def test_distribute_content_multi_module():
    """同一条内容应分配给多个相关模块"""
    integrator = ContentIntegrator()

    parsed = ParsedPrompt(
        topic="销售培训",
        audience="销售团队",
        position="销售代表",
        industry="企业服务",
        duration="60分钟",
        style="实操导向",
        objectives=["掌握话术", "了解产品"],
        special_requirements=[],
        forbidden_content=[],
        num_modules=2,
        outline_structure={"模块拆解层": ["模块1-电话话术", "模块2-产品知识"]}
    )

    file_contents = ["销售电话沟通技巧，包含与客户的话术对话，产品知识和销售技能"]

    result = integrator.integrate(parsed, file_contents)

    # 内容应同时分配给两个模块
    assert len(result.module_contents["模块1-电话话术"]) >= 1
    assert len(result.module_contents["模块2-产品知识"]) >= 1
