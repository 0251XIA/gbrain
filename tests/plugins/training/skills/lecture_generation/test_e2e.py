import pytest
from unittest.mock import patch
from gbrain.plugins.training.skills.lecture_generation.builder import LectureGenerationBuilder


@pytest.mark.e2e
def test_lecture_generation_e2e():
    """端到端测试：user_prompt → 完整讲义（mock LLM）"""
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

    mock_content = """# 契约锁产品知识培训

## 培训信息
- **培训受众：** 新入职销售
- **目标岗位：** 销售代表
- **所属行业：** 企业服务/SaaS
- **预计时长：** 90分钟
- **培训风格：** 专业严谨

## 学习目标
1. 掌握契约锁核心产品功能
2. 理解客户痛点和解决方案
3. 能独立完成产品演示

### 开篇锚定层

**【场景引入】**
小李是一名新入职的销售，今天第一次向客户介绍契约锁产品

**【问题抛出】**
客户问：你们产品和其他家有什么区别？

**【方法讲解】**
契约锁的三大核心优势：...

**【案例佐证】**
某科技公司使用契约锁后，合同签署效率提升了80%

**【避坑指南】**
- ✅ 正确做法：提前了解客户的行业特点
- ❌ 错误做法：直接对比价格而不讲价值

**【即时练习】**
请列出契约锁的三个核心功能

### 模块1：产品功能

**【场景引入】**
...

**【问题抛出】**
...

**【方法讲解】**
契约锁产品功能包括：电子签章、时间戳、身份认证

**【案例佐证】**
某科技公司的成功案例

**【避坑指南】**
- ✅ 正确做法
- ❌ 错误做法

**【即时练习】**
...
"""

    with patch('gbrain.plugins.training.skills.lecture_generation.lecture_generator.call_llm', return_value=mock_content):
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