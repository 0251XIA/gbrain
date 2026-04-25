# 讲义生成 Skill 设计规格

**日期：** 2026-04-24
**Skill 名称：** `training:lecture-generation`
**状态：** 已确认

---

## 1. 概述

### 1.1 定位

通用讲义生成 Skill，将用户提供的 Markdown 格式需求（包含大纲结构）转换为完整的培训讲义。

### 1.2 输入输出

**输入：**
```yaml
user_prompt: string          # Markdown 格式（客户需求描述 + 大纲结构）
file_contents: list[string] # 文件内容列表（知识库/上传文档）
training_type: string        # product | compliance | sales_skill
```

**输出：**
```json
{
  "content": "# 完整讲义（Markdown格式全文）",
  "user_prompt_params": {
    "topic": "培训主题",
    "training_type": "product/compliance/sales_skill",
    "audience": "培训受众",
    "position": "目标岗位",
    "industry": "所属行业",
    "objectives": ["学习目标1", "学习目标2"],
    "special_requirements": ["特殊要求1", "特殊要求2"],
    "forbidden_content": ["禁止内容1", "禁止内容2"],
    "num_modules": 3,
    "estimated_duration": "90分钟",
    "style": "实操导向/专业严谨/口语化"
  },
  "outline": {
    "opening_layer": {...},
    "modules": [...],
    "closing_layer": {...}
  },
  "validation_report": {
    "prompt_match_score": 95,
    "coverage_score": 90,
    "compliance_score": 100,
    "practical_score": 85,
    "structure_score": 90,
    "overall_score": 90,
    "issues": [],
    "suggestions": []
  },
  "knowledge_points": [...],
  "metadata": {...}
}
```

---

## 2. 工作流程

```
user_prompt (Markdown)
    │
    ▼
┌─────────────────────────────┐
│  Step 1: 解析 user_prompt   │
│  - 提取用户要求参数          │
│  - 提取大纲结构              │
│  - 识别内容优先级            │
└─────────────────────────────┘
    │
    ▼
file_contents (文件列表)
    │
    ▼
┌─────────────────────────────┐
│  Step 2: 内容融合            │
│  - 按大纲结构分配内容        │
│  - 碎片化内容结构化整合      │
│  - 缺失信息智能补全          │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  Step 3: AI 生成讲义        │
│  - 严格遵循大纲结构          │
│  - 内容填充（案例/话术/练习） │
│  - 符合培训类型风格          │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  Step 4: 校验与输出          │
│  - prompt_match 校验         │
│  - 自动修复（可选）          │
│  - 输出完整 JSON             │
└─────────────────────────────┘
```

---

## 3. 核心模块设计

### 3.1 PromptParser - 解析 user_prompt

**职责：**
1. 解析 Markdown 中的用户要求参数
2. 提取期望的大纲结构
3. 识别内容优先级和特殊要求

**输入格式示例（user_prompt）：**

```markdown
# 新人销售培训 - 产品知识

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
- 禁止出现竞品负面评价

## 大纲结构

### 开篇锚定层
学习目标、适用场景、前置知识要求、考核标准

### 模块拆解层
#### 模块1：产品功能（权重40%）
#### 模块2：客户价值（权重35%）
#### 模块3：异议处理（权重25%）

### 收尾闭环层
核心复盘、进阶路径、配套资源
```

**输出：**
```python
@dataclass
class ParsedPrompt:
    topic: str
    audience: str
    position: str
    industry: str
    duration: str
    style: str  # 实操导向/专业严谨/口语化
    objectives: list[str]
    special_requirements: list[str]
    forbidden_content: list[str]
    num_modules: int
    outline_structure: dict  # 大纲结构
```

### 3.2 ContentIntegrator - 内容融合

**职责：**
1. 按大纲结构分配文件内容
2. 碎片化内容结构化整合
3. 缺失信息智能补全

**输入：**
- `ParsedPrompt` - 解析后的参数和大纲
- `file_contents` - 文件内容列表

**输出：**
```python
@dataclass
class IntegratedContent:
    module_contents: dict  # {module_id: content}
    case_library: list[dict]  # 案例库
    supplementary_materials: dict  # 配套材料
```

### 3.3 LectureGenerator - 讲义生成

**职责：**
1. 严格遵循大纲结构
2. AI 填充详细内容
3. 符合培训类型风格

**培训类型风格：**
| 类型 | 内容风格 | 案例要求 | 练习题类型 |
|------|---------|---------|-----------|
| product | 技术参数→客户价值 | 客户痛点→产品解决 | 产品演示模拟 |
| compliance | 规则→行为准则 | 违规场景→正确操作 | 场景判断题 |
| sales_skill | 步骤→话术→演练 | 成功话术→失败话术 | 场景模拟演练 |

**内容单元结构：**
```
### [单元名称]

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
```

### 3.4 Validator - 校验

**职责：**
1. prompt_match_score（用户提示匹配度）校验
2. coverage_score（覆盖率）校验
3. 自动修复低分项

**校验维度：**
```python
{
    "prompt_match_score": 95,   # 用户提示匹配度（最高权重）
    "coverage_score": 90,        # 内容覆盖率
    "compliance_score": 100,     # 合规性
    "practical_score": 85,       # 实用性（案例/练习题）
    "structure_score": 90        # 结构规范性
}
```

---

## 4. 文件结构

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

## 5. Skill 接口

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
  content: string           # Markdown 格式完整讲义
  user_prompt_params: object # 解析后的用户参数
  outline: object          # 大纲结构
  validation_report: object # 校验报告
  knowledge_points: array   # 知识点列表
  metadata: object         # 元数据
```

---

## 6. 实现计划

### Phase 1: 核心模块
1. [ ] `prompt_parser.py` - 解析 user_prompt
2. [ ] `content_integrator.py` - 内容融合
3. [ ] `lecture_generator.py` - AI 生成讲义

### Phase 2: 校验与整合
4. [ ] `validator.py` - 校验逻辑
5. [ ] `builder.py` - 整合构建
6. [ ] `skill.yaml` - Skill 定义

### Phase 3: 测试
7. [ ] 端到端测试
8. [ ] 不同培训类型测试

---

## 7. 成功标准

| 指标 | 目标 |
|------|------|
| prompt_match_score | ≥ 90% |
| coverage_score | ≥ 90% |
| 生成时间 | ≤ 60s |