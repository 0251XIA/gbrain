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
        description="",
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


def test_distribute_content_fallback_pool():
    """未匹配内容应进入 fallback 池重新分配"""
    integrator = ContentIntegrator()

    parsed = ParsedPrompt(
        topic="产品培训",
        audience="全员",
        position="员工",
        industry="通用",
        duration="60分钟",
        style="专业严谨",
        description="",
        objectives=["了解企业文化", "掌握产品知识"],
        special_requirements=[],
        forbidden_content=[],
        num_modules=2,
        outline_structure={"模块拆解层": ["模块1-企业文化", "模块2-产品知识"]}
    )

    # 内容与模块无关键词匹配
    file_contents = ["这是一段通用的公司介绍内容，与具体模块无直接关联"]

    result = integrator.integrate(parsed, file_contents)

    # 内容应至少分配到一个模块（fallback 到第一个）
    total = sum(len(v) for v in result.module_contents.values())
    assert total >= 1


def test_extract_cases_no_truncation():
    """案例提取不应有500字符限制"""
    integrator = ContentIntegrator()

    # 创建一个超过500字符的案例内容，每个段落包含多个分句
    # 用逗号连接使整个段落成为一个自然段落
    long_paragraph1 = "案例一：这是一个非常长的客户成功案例，" + "涉及多个方面的详细描述和深入分析，" * 50
    long_paragraph2 = "第二段内容，包含丰富的实践案例和经验总结，" * 50
    long_paragraph3 = "第三段内容，进一步补充说明和延伸讨论，" * 50
    long_case = long_paragraph1 + "。" + long_paragraph2 + "。" + long_paragraph3 + "。"

    file_contents = [f"销售培训内容包括：\n\n{long_case}"]

    result = integrator.integrate(
        ParsedPrompt(
            topic="销售培训",
            audience="销售",
            position="销售",
            industry="通用",
            duration="60分钟",
            style="专业严谨",
            description="",
            objectives=["掌握销售技巧"],
            special_requirements=[],
            forbidden_content=[],
            num_modules=1,
            outline_structure={"模块拆解层": ["模块1"]}
        ),
        file_contents
    )

    if result.case_library:
        # 案例内容应接近原始长度（允许句号分割差异）
        assert len(result.case_library[0]["content"]) > 500


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
        description="",
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
