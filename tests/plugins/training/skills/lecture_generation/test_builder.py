import pytest
from gbrain.plugins.training.skills.lecture_generation.builder import LectureGenerationBuilder


def test_full_build():
    builder = LectureGenerationBuilder()

    user_prompt = """# 新人销售培训 - 产品知识

## 基本信息
- 培训主题：契约锁产品知识培训
- 培训受众：新入职销售
- 目标岗位：销售代表
- 所属行业：企业服务/SaaS
- 时长：90分钟
- 风格：专业严谨

## 学习目标
1. 掌握契约锁核心产品功能
"""

    file_contents = ["契约锁电子签章服务介绍"]

    result = builder.build(user_prompt, file_contents, "product")

    assert "content" in result
    assert "user_prompt_params" in result
    assert "validation_report" in result
    assert result["validation_report"]["overall_score"] >= 80
