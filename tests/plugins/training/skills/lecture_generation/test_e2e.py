import pytest
from gbrain.plugins.training.skills.lecture_generation.builder import LectureGenerationBuilder


@pytest.mark.e2e
def test_lecture_generation_e2e():
    """端到端测试：user_prompt → 完整讲义"""
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
2. 理解客户痛点和解决方案
3. 能独立完成产品演示

## 特殊要求
- 每章需要包含真实案例
- 话术部分需要可落地执行

## 大纲结构

### 开篇锚定层
学习目标、适用场景

### 模块拆解层
#### 模块1：产品功能（权重40%）
#### 模块2：客户价值（权重35%）
"""

    file_contents = [
        "契约锁产品功能：电子签章、时间戳、身份认证",
        "客户痛点：合同管理混乱、签署效率低",
        "成功案例：某科技公司使用契约锁后签署效率提升80%"
    ]

    result = builder.build(user_prompt, file_contents, "product")

    # 验证输出结构
    assert "content" in result
    assert "user_prompt_params" in result
    assert "validation_report" in result

    # 验证内容质量
    content = result["content"]
    assert "契约锁产品知识培训" in content
    assert "新入职销售" in content

    # 验证校验报告
    report = result["validation_report"]
    assert report["overall_score"] >= 80
    assert report["prompt_match_score"] >= 90

    # 验证用户参数
    params = result["user_prompt_params"]
    assert params["topic"] == "契约锁产品知识培训"
    assert params["training_type"] == "product"
