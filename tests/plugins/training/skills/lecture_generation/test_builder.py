import pytest
from unittest.mock import patch, MagicMock
from gbrain.plugins.training.skills.lecture_generation.builder import LectureGenerationBuilder


def test_full_build():
    """测试完整构建流程（mock LLM）"""
    builder = LectureGenerationBuilder()

    user_prompt = """## 基本信息
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

## 大纲结构
### 模块拆解层
#### 模块1：产品功能（权重40%）
#### 模块2：客户价值（权重35%）
"""

    file_contents = [
        "契约锁产品功能：电子签章、时间戳、身份认证",
        "客户痛点：合同管理混乱、签署效率低",
        "成功案例：某科技公司使用契约锁后签署效率提升80%"
    ]

    # Mock LLM 返回模拟讲义内容
    mock_lecture = """# 契约锁产品知识培训

## 学习目标
1. 掌握契约锁核心产品功能
2. 理解客户痛点和解决方案
3. 能独立完成产品演示

### 开篇
**【场景引入】**
小李是一名新入职的销售，今天第一次拜访客户

**【问题抛出】**
客户问：契约锁和竞品有什么区别？

**【方法讲解】**
契约锁的核心优势：...

**【案例佐证】**
某科技公司使用后效率提升80%

**【避坑指南】**
- ✅ 正确：提前了解客户行业
- ❌ 错误：不了解客户需求直接推销

**【即时练习】**
请列出契约锁的三个核心功能

### 模块1：产品功能

**【场景引入】**
...

"""

    with patch('gbrain.plugins.training.skills.lecture_generation.lecture_generator.call_llm', return_value=mock_lecture):
        result = builder.build(user_prompt, file_contents, "product")

    # 验证输出结构
    assert "content" in result
    assert "user_prompt_params" in result
    assert "validation_report" in result
    assert "case_library" in result
    assert "supplementary_materials" in result

    # 验证内容
    assert "契约锁" in result["content"]

    # 验证用户参数
    params = result["user_prompt_params"]
    assert params["topic"] == "契约锁产品知识培训"
    assert params["training_type"] == "product"
    assert params["audience"] == "新入职销售"

    # 验证校验报告结构
    report = result["validation_report"]
    assert "overall_score" in report
    assert "prompt_match_score" in report


def test_builder_knowledge_context_passed():
    """验证知识库内容正确传递给生成器"""
    builder = LectureGenerationBuilder()

    user_prompt = """## 基本信息
- 培训主题：商务礼仪培训
- 培训受众：新员工
- 目标岗位：通用
- 所属行业：通用
- 时长：60分钟
- 风格：专业严谨

## 大纲结构
### 模块拆解层
#### 模块1：职业形象
"""

    file_contents = ["职业形象：着装规范、仪容整洁", "电话礼仪：接听流程"]

    mock_content = """# 商务礼仪培训

## 学习目标

### 模块1：职业形象

**【方法讲解】**
职业形象包括着装规范和仪容整洁
"""

    captured_prompt = None

    def capture_llm(prompt, system_prompt=""):
        nonlocal captured_prompt
        captured_prompt = prompt
        return mock_content

    with patch('gbrain.plugins.training.skills.lecture_generation.lecture_generator.call_llm', side_effect=capture_llm):
        result = builder.build(user_prompt, file_contents, "product")

    # 验证知识库内容被传递
    assert captured_prompt is not None
    assert "职业形象" in captured_prompt
    assert "电话礼仪" in captured_prompt
