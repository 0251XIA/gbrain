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
