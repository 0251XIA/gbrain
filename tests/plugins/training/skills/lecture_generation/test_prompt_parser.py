import pytest
from gbrain.plugins.training.skills.lecture_generation.prompt_parser import PromptParser

def test_parse_basic_prompt():
    parser = PromptParser()
    markdown = """# 新人销售培训 - 产品知识

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

## 特殊要求
- 每章需要包含真实案例

## 大纲结构

### 开篇锚定层
学习目标、适用场景

### 模块拆解层
#### 模块1：产品功能（权重40%）
"""
    result = parser.parse(markdown)
    assert result.topic == "契约锁产品知识培训"
    assert result.audience == "新入职销售"
    assert result.num_modules == 1