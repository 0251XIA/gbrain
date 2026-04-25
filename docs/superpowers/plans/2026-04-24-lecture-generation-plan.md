# training:lecture-generation 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 实现 `training:lecture-generation` Skill，将用户 Markdown 格式需求转换为完整培训讲义

**架构：** 单一职责模块设计：PromptParser（解析）、ContentIntegrator（融合）、LectureGenerator（生成）、Validator（校验）、Builder（构建）

**技术栈：** Python + FastAPI + Redis + PostgreSQL

---

## 文件结构

```
gbrain/plugins/training/
├── skills/
│   └── lecture_generation/
│       ├── __init__.py
│       ├── skill.yaml           # Skill 定义
│       ├── prompt_parser.py     # 解析 user_prompt
│       ├── content_integrator.py # 内容融合
│       ├── lecture_generator.py  # AI 生成讲义
│       ├── validator.py         # 校验
│       └── builder.py           # 整合构建
│
├── chat_engine.py               # 现有
├── learning_agent.py            # 现有
└── service.py                  # 现有
```

---

## Task 1: 创建 Skill 目录结构和 models.py

**Files:**
- Create: `gbrain/plugins/training/skills/lecture_generation/__init__.py`
- Create: `gbrain/plugins/training/skills/lecture_generation/models.py`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p gbrain/plugins/training/skills/lecture_generation
```

- [ ] **Step 2: 创建 __init__.py**

```python
"""training:lecture-generation Skill"""

__version__ = "1.0.0"
```

- [ ] **Step 3: 创建 models.py**

```python
from dataclasses import dataclass, field
from typing import Literal

TrainingType = Literal["product", "compliance", "sales_skill"]
StyleType = Literal["实操导向", "专业严谨", "口语化"]

@dataclass(frozen=True)
class ParsedPrompt:
    topic: str
    audience: str
    position: str
    industry: str
    duration: str
    style: StyleType
    objectives: list[str]
    special_requirements: list[str]
    forbidden_content: list[str]
    num_modules: int
    outline_structure: dict

@dataclass(frozen=True)
class KnowledgePoint:
    id: str
    name: str
    content: str
    difficulty: int  # 1-5
    prerequisites: list[str]
    assessment_weight: float
    business_scenario: str

@dataclass(frozen=True)
class IntegratedContent:
    module_contents: dict
    case_library: list[dict]
    supplementary_materials: dict

@dataclass(frozen=True)
class ValidationReport:
    prompt_match_score: int
    coverage_score: int
    compliance_score: int
    practical_score: int
    structure_score: int
    overall_score: int
    issues: list[str]
    suggestions: list[str]

@dataclass(frozen=True)
class LectureOutput:
    content: str
    user_prompt_params: dict
    outline: dict
    validation_report: ValidationReport
    knowledge_points: list[KnowledgePoint]
    metadata: dict
```

- [ ] **Step 4: 验证 models.py**

Run: `python -c "from gbrain.plugins.training.skills.lecture_generation.models import ParsedPrompt, KnowledgePoint, ValidationReport; print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add gbrain/plugins/training/skills/lecture_generation/__init__.py gbrain/plugins/training/skills/lecture_generation/models.py
git commit -m "feat: add lecture-generation skill models"
```

---

## Task 2: PromptParser 实现

**Files:**
- Create: `gbrain/plugins/training/skills/lecture_generation/prompt_parser.py`
- Test: `tests/plugins/training/skills/lecture_generation/test_prompt_parser.py`

- [ ] **Step 1: 创建测试文件**

```python
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/plugins/training/skills/lecture_generation/test_prompt_parser.py -v`

Expected: FAIL - module not found

- [ ] **Step 3: 实现 PromptParser**

```python
import re
from dataclasses import dataclass
from typing import Literal
from .models import ParsedPrompt, StyleType

class PromptParser:
    def parse(self, markdown: str) -> ParsedPrompt:
        """解析 Markdown 格式的用户需求"""
        lines = markdown.strip().split('\n')
        
        # 提取基本信息
        info = self._extract_info(lines)
        
        # 提取学习目标
        objectives = self._extract_objectives(lines)
        
        # 提取特殊要求
        special_req = self._extract_special_requirements(lines)
        
        # 提取禁止内容
        forbidden = self._extract_forbidden_content(lines)
        
        # 提取大纲结构
        outline = self._extract_outline_structure(lines)
        
        # 计算模块数量
        num_modules = self._count_modules(lines)
        
        return ParsedPrompt(
            topic=info.get('topic', ''),
            audience=info.get('audience', ''),
            position=info.get('position', ''),
            industry=info.get('industry', ''),
            duration=info.get('duration', ''),
            style=self._parse_style(info.get('style', '专业严谨')),
            objectives=objectives,
            special_requirements=special_req,
            forbidden_content=forbidden,
            num_modules=num_modules,
            outline_structure=outline
        )
    
    def _extract_info(self, lines: list[str]) -> dict[str, str]:
        in_basic_info = False
        info = {}
        for line in lines:
            if '## 基本信息' in line:
                in_basic_info = True
                continue
            if in_basic_info:
                if line.startswith('## '):
                    break
                match = re.match(r'- (.+?)：(.+)', line)
                if match:
                    key, value = match.groups()
                    info[key.strip()] = value.strip()
        return info
    
    def _extract_objectives(self, lines: list[str]) -> list[str]:
        in_objectives = False
        objectives = []
        for line in lines:
            if '## 学习目标' in line:
                in_objectives = True
                continue
            if in_objectives:
                if line.startswith('## '):
                    break
                match = re.match(r'\d+\.\s*(.+)', line)
                if match:
                    objectives.append(match.group(1).strip())
        return objectives
    
    def _extract_special_requirements(self, lines: list[str]) -> list[str]:
        in_req = False
        reqs = []
        for line in lines:
            if '## 特殊要求' in line:
                in_req = True
                continue
            if in_req:
                if line.startswith('## '):
                    break
                if line.startswith('- '):
                    reqs.append(line[2:].strip())
        return reqs
    
    def _extract_forbidden_content(self, lines: list[str]) -> list[str]:
        in_forbidden = False
        forbidden = []
        for line in lines:
            if '## 禁止内容' in line or '## 禁忌' in line:
                in_forbidden = True
                continue
            if in_forbidden:
                if line.startswith('## '):
                    break
                if line.startswith('- '):
                    forbidden.append(line[2:].strip())
        return forbidden
    
    def _extract_outline_structure(self, lines: list[str]) -> dict:
        in_outline = False
        outline = {}
        current_section = None
        for line in lines:
            if '## 大纲结构' in line:
                in_outline = True
                continue
            if in_outline:
                if line.startswith('## '):
                    break
                if '### ' in line:
                    current_section = line.replace('### ', '').strip()
                    outline[current_section] = []
                elif current_section and line.startswith('#### '):
                    outline[current_section].append(line.replace('#### ', '').strip())
        return outline
    
    def _count_modules(self, lines: list[str]) -> int:
        return sum(1 for line in lines if re.match(r'#### \u6a21\u5757\d+', line))
    
    def _parse_style(self, style: str) -> StyleType:
        style_map = {
            '\u5b9e\u64cd\u5bfc\u5411': '实操导向',
            '\u4e13\u4e1a\u4e25\u8c28': '专业严谨',
            '\u53e3\u8bed\u5316': '口语化'
        }
        return style_map.get(style, '专业严谨')
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/plugins/training/skills/lecture_generation/test_prompt_parser.py -v`

- [ ] **Step 5: Commit**

```bash
git add gbrain/plugins/training/skills/lecture_generation/prompt_parser.py tests/plugins/training/skills/lecture_generation/test_prompt_parser.py
git commit -m "feat: implement PromptParser for lecture generation"
```

---

## Task 3: ContentIntegrator 实现

**Files:**
- Create: `gbrain/plugins/training/skills/lecture_generation/content_integrator.py`
- Test: `tests/plugins/training/skills/lecture_generation/test_content_integrator.py`

- [ ] **Step 1: 创建测试文件**

```python
import pytest
from gbrain.plugins.training.skills.lecture_generation.content_integrator import ContentIntegrator
from gbrain.plugins.training.skills.lecture_generation.models import ParsedPrompt, IntegratedContent

def test_integrate_content():
    parser = PromptParser()
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
        outline_structure={"开篇锚定层": [], "模块拆解层": ["模块1"]}
    )
    
    file_contents = ["契约锁产品功能介绍：电子签章、时间戳服务"]
    
    result = integrator.integrate(parsed, file_contents)
    
    assert isinstance(result, IntegratedContent)
    assert "模块1" in result.module_contents
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/plugins/training/skills/lecture_generation/test_content_integrator.py -v`

- [ ] **Step 3: 实现 ContentIntegrator**

```python
from dataclasses import dataclass
from .models import ParsedPrompt, IntegratedContent

class ContentIntegrator:
    def integrate(self, parsed: ParsedPrompt, file_contents: list[str]) -> IntegratedContent:
        """按大纲结构分配内容，碎片化内容结构化整合"""
        module_contents = {}
        
        # 获取模块列表
        modules = self._get_modules_from_outline(parsed.outline_structure)
        
        # 初始化模块内容
        for module in modules:
            module_contents[module] = []
        
        # 分配文件内容到模块
        for content in file_contents:
            self._distribute_content(content, module_contents, modules)
        
        # 提取案例库
        case_library = self._extract_cases(file_contents)
        
        # 提取配套材料
        supplementary = self._extract_supplementary(file_contents)
        
        return IntegratedContent(
            module_contents=module_contents,
            case_library=case_library,
            supplementary_materials=supplementary
        )
    
    def _get_modules_from_outline(self, outline: dict) -> list[str]:
        modules = []
        for section_name, items in outline.items():
            if section_name == "模块拆解层":
                modules.extend(items)
        return modules
    
    def _distribute_content(self, content: str, module_contents: dict, modules: list[str]):
        """将内容分配到对应模块"""
        for module in modules:
            if module in content:
                module_contents[module].append(content)
    
    def _extract_cases(self, file_contents: list[str]) -> list[dict]:
        cases = []
        for content in file_contents:
            if '案例' in content or 'case' in content.lower():
                cases.append({"content": content, "type": "case"})
        return cases
    
    def _extract_supplementary(self, file_contents: list[str]) -> dict:
        return {"resources": [], "policies": []}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/plugins/training/skills/lecture_generation/test_content_integrator.py -v`

- [ ] **Step 5: Commit**

```bash
git add gbrain/plugins/training/skills/lecture_generation/content_integrator.py tests/plugins/training/skills/lecture_generation/test_content_integrator.py
git commit -m "feat: implement ContentIntegrator for content fusion"
```

---

## Task 4: LectureGenerator 实现

**Files:**
- Create: `gbrain/plugins/training/skills/lecture_generation/lecture_generator.py`
- Test: `tests/plugins/training/skills/lecture_generation/test_lecture_generator.py`

- [ ] **Step 1: 创建测试文件**

```python
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/plugins/training/skills/lecture_generation/test_lecture_generator.py -v`

- [ ] **Step 3: 实现 LectureGenerator**

```python
from .models import ParsedPrompt, IntegratedContent

class LectureGenerator:
    CONTENT_TEMPLATE = """# {topic}

## 培训信息
- **培训受众：** {audience}
- **目标岗位：** {position}
- **所属行业：** {industry}
- **预计时长：** {duration}
- **培训风格：** {style}

## 学习目标
{objectives}

## 内容单元结构

### 开篇锚定层
**【场景引入】**
（真实业务场景）

**【问题抛出】**
（1-2个思考问题）

**【方法讲解】**
（核心知识点）

**【案例佐证】**
（公司真实案例）

**【避坑指南】**
- ✅ 正确做法
- ❌ 错误做法
- ⚠️ 注意事项

**【即时练习】**
（配套练习题）

{module_contents}
"""

    def generate(self, parsed: ParsedPrompt, integrated: IntegratedContent) -> str:
        """生成完整讲义"""
        objectives_text = '\n'.join(f"{i+1}. {obj}" for i, obj in enumerate(parsed.objectives))
        
        module_text = self._generate_modules(parsed, integrated)
        
        content = self.CONTENT_TEMPLATE.format(
            topic=parsed.topic,
            audience=parsed.audience,
            position=parsed.position,
            industry=parsed.industry,
            duration=parsed.duration,
            style=parsed.style,
            objectives=objectives_text,
            module_contents=module_text
        )
        
        return content
    
    def _generate_modules(self, parsed: ParsedPrompt, integrated: IntegratedContent) -> str:
        modules = []
        for module_name, contents in integrated.module_contents.items():
            if contents:
                module_text = f"""
### {module_name}

**【场景引入】**
（基于培训受众的实际业务场景）

**【方法讲解】**
{''.join(contents)}

**【案例佐证】**
（公司真实案例）

**【避坑指南】**
- ✅ 正确做法
- ❌ 错误做法

**【即时练习】**
（配套练习题）
"""
                modules.append(module_text)
        return '\n'.join(modules)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/plugins/training/skills/lecture_generation/test_lecture_generator.py -v`

- [ ] **Step 5: Commit**

```bash
git add gbrain/plugins/training/skills/lecture_generation/lecture_generator.py tests/plugins/training/skills/lecture_generation/test_lecture_generator.py
git commit -m "feat: implement LectureGenerator for AI lecture generation"
```

---

## Task 5: Validator 实现

**Files:**
- Create: `gbrain/plugins/training/skills/lecture_generation/validator.py`
- Test: `tests/plugins/training/skills/lecture_generation/test_validator.py`

- [ ] **Step 1: 创建测试文件**

```python
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
        objectives=["掌握核心功能", "理解客户痛点"],
        special_requirements=["每章需要包含真实案例"],
        forbidden_content=["竞品负面评价"],
        num_modules=1,
        outline_structure={}
    )
    
    lecture_content = "# 契约锁产品知识培训\n\n## 学习目标\n1. 掌握核心功能\n2. 理解客户痛点"
    
    report = validator.validate(lecture_content, parsed)
    
    assert isinstance(report, ValidationReport)
    assert report.prompt_match_score >= 90
    assert report.overall_score >= 80
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/plugins/training/skills/lecture_generation/test_validator.py -v`

- [ ] **Step 3: 实现 Validator**

```python
from .models import ParsedPrompt, ValidationReport

class Validator:
    def validate(self, lecture_content: str, parsed: ParsedPrompt) -> ValidationReport:
        """校验讲义内容与用户需求的匹配度"""
        issues = []
        suggestions = []
        
        # Prompt Match Score
        prompt_match = self._check_prompt_match(lecture_content, parsed)
        
        # Coverage Score
        coverage = self._check_coverage(lecture_content, parsed)
        
        # Compliance Score
        compliance = self._check_compliance(lecture_content, parsed)
        
        # Practical Score
        practical = self._check_practical(lecture_content, parsed)
        
        # Structure Score
        structure = self._check_structure(lecture_content, parsed)
        
        # Calculate overall
        overall = int((prompt_match + coverage + compliance + practical + structure) / 5)
        
        return ValidationReport(
            prompt_match_score=prompt_match,
            coverage_score=coverage,
            compliance_score=compliance,
            practical_score=practical,
            structure_score=structure,
            overall_score=overall,
            issues=issues,
            suggestions=suggestions
        )
    
    def _check_prompt_match(self, content: str, parsed: ParsedPrompt) -> int:
        score = 100
        if parsed.topic and parsed.topic not in content:
            score -= 20
        if parsed.audience and parsed.audience not in content:
            score -= 20
        return max(score, 0)
    
    def _check_coverage(self, content: str, parsed: ParsedPrompt) -> int:
        score = 100
        covered_objectives = sum(1 for obj in parsed.objectives if obj in content)
        if parsed.objectives:
            coverage_ratio = covered_objectives / len(parsed.objectives)
            score = int(coverage_ratio * 100)
        return score
    
    def _check_compliance(self, content: str, parsed: ParsedPrompt) -> int:
        score = 100
        for forbidden in parsed.forbidden_content:
            if forbidden in content:
                score -= 30
        return max(score, 0)
    
    def _check_practical(self, content: str, parsed: ParsedPrompt) -> int:
        score = 70
        has_cases = '案例' in content or 'case' in content.lower()
        has_exercises = '练习' in content or '练习题' in content
        if has_cases:
            score += 10
        if has_exercises:
            score += 10
        return min(score, 100)
    
    def _check_structure(self, content: str, parsed: ParsedPrompt) -> int:
        score = 80
        required_sections = ['场景引入', '方法讲解', '案例佐证', '避坑指南', '即时练习']
        for section in required_sections:
            if section not in content:
                score -= 10
        return max(score, 0)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/plugins/training/skills/lecture_generation/test_validator.py -v`

- [ ] **Step 5: Commit**

```bash
git add gbrain/plugins/training/skills/lecture_generation/validator.py tests/plugins/training/skills/lecture_generation/test_validator.py
git commit -m "feat: implement Validator for lecture quality check"
```

---

## Task 6: Builder 和 skill.yaml

**Files:**
- Create: `gbrain/plugins/training/skills/lecture_generation/builder.py`
- Create: `gbrain/plugins/training/skills/lecture_generation/skill.yaml`
- Test: `tests/plugins/training/skills/lecture_generation/test_builder.py`

- [ ] **Step 1: 创建测试文件**

```python
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/plugins/training/skills/lecture_generation/test_builder.py -v`

- [ ] **Step 3: 实现 Builder**

```python
from .prompt_parser import PromptParser
from .content_integrator import ContentIntegrator
from .lecture_generator import LectureGenerator
from .validator import Validator
from .models import LectureOutput

class LectureGenerationBuilder:
    def __init__(self):
        self.parser = PromptParser()
        self.integrator = ContentIntegrator()
        self.generator = LectureGenerator()
        self.validator = Validator()
    
    def build(self, user_prompt: str, file_contents: list[str], training_type: str) -> dict:
        """完整构建流程"""
        # Step 1: 解析 user_prompt
        parsed = self.parser.parse(user_prompt)
        
        # Step 2: 内容融合
        integrated = self.integrator.integrate(parsed, file_contents)
        
        # Step 3: AI 生成讲义
        content = self.generator.generate(parsed, integrated)
        
        # Step 4: 校验
        validation_report = self.validator.validate(content, parsed)
        
        # 构建输出
        return {
            "content": content,
            "user_prompt_params": {
                "topic": parsed.topic,
                "training_type": training_type,
                "audience": parsed.audience,
                "position": parsed.position,
                "industry": parsed.industry,
                "objectives": parsed.objectives,
                "special_requirements": parsed.special_requirements,
                "forbidden_content": parsed.forbidden_content,
                "num_modules": parsed.num_modules,
                "estimated_duration": parsed.duration,
                "style": parsed.style
            },
            "outline": parsed.outline_structure,
            "validation_report": {
                "prompt_match_score": validation_report.prompt_match_score,
                "coverage_score": validation_report.coverage_score,
                "compliance_score": validation_report.compliance_score,
                "practical_score": validation_report.practical_score,
                "structure_score": validation_report.structure_score,
                "overall_score": validation_report.overall_score,
                "issues": validation_report.issues,
                "suggestions": validation_report.suggestions
            },
            "knowledge_points": [],
            "metadata": {"version": "1.0.0"}
        }
```

- [ ] **Step 4: 创建 skill.yaml**

```yaml
name: training:lecture-generation
description: 将用户 Markdown 格式需求转换为完整培训讲义

inputs:
  user_prompt:
    type: string
    required: true
    description: Markdown 格式，包含需求描述和期望的大纲结构
  file_contents:
    type: array
    items: string
    required: false
    description: 文件内容列表（知识库/上传文档）
  training_type:
    type: string
    enum: [product, compliance, sales_skill]
    required: true

outputs:
  content:
    type: string
    description: Markdown 格式完整讲义
  user_prompt_params:
    type: object
    description: 解析后的用户参数
  outline:
    type: object
    description: 大纲结构
  validation_report:
    type: object
    description: 校验报告
  knowledge_points:
    type: array
    description: 知识点列表
  metadata:
    type: object
    description: 元数据
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/plugins/training/skills/lecture_generation/test_builder.py -v`

- [ ] **Step 6: Commit**

```bash
git add gbrain/plugins/training/skills/lecture_generation/builder.py gbrain/plugins/training/skills/lecture_generation/skill.yaml tests/plugins/training/skills/lecture_generation/test_builder.py
git commit -m "feat: add Builder and skill.yaml for lecture generation"
```

---

## Task 7: 端到端测试

**Files:**
- Create: `tests/plugins/training/skills/lecture_generation/test_e2e.py`

- [ ] **Step 1: 创建端到端测试**

```python
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
```

- [ ] **Step 2: 运行端到端测试**

Run: `pytest tests/plugins/training/skills/lecture_generation/test_e2e.py -v`

- [ ] **Step 3: Commit**

```bash
git add tests/plugins/training/skills/lecture_generation/test_e2e.py
git commit -m "test: add e2e tests for lecture generation"
```

---

## 成功标准

| 指标 | 目标 |
|------|------|
| prompt_match_score | ≥ 90% |
| coverage_score | ≥ 90% |
| 生成时间 | ≤ 60s |
| 测试覆盖率 | ≥ 80% |
