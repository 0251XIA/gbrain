import pytest
from gbrain.plugins.training.skills.lecture_generation.validator import Validator
from gbrain.plugins.training.skills.lecture_generation.models import ParsedPrompt, ValidationReport


def test_validate_lecture():
    validator = Validator()

    parsed = ParsedPrompt(
        topic="契约锁产品知识培训",
        audience="新入职销售",
        position="销售代表",
        industry="企业服务/SaaS",
        duration="90分钟",
        style="专业严谨",
        description="",
        objectives=["掌握核心功能", "理解客户痛点"],
        special_requirements=["每章需要包含真实案例"],
        forbidden_content=["竞品负面评价"],
        num_modules=1,
        outline_structure={}
    )

    lecture_content = """# 契约锁产品知识培训

## 目标受众：新入职销售

## 学习目标
1. 掌握核心功能
2. 理解客户痛点

## 场景引入
...

## 方法讲解
...

## 案例佐证
...

## 避坑指南
...

## 即时练习
..."""

    report = validator.validate(lecture_content, parsed)

    assert isinstance(report, ValidationReport)
    assert report.prompt_match_score >= 90
    assert report.overall_score >= 80
