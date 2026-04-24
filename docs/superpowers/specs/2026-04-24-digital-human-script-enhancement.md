# 课件生成能力增强：数字人口播稿支持

**日期：** 2026-04-24
**状态：** 已批准

---

## 1. 背景与目标

现有 `lecture_generation` Skill 生成标准 Markdown 课件，用户需要口播稿格式（数字人直接朗读）。本次优化在不改变定位和架构的前提下，重写 AI prompt 模板，增加 `output_format` 参数支持。

**目标：**
- 支持 `output_format: lecture`（标准课件）和 `output_format: digital_human_script`（口播稿）两种输出
- 口播稿风格：自然口语化、像资深培训师面对面授课
- 输出灵活适配：有内容输出，无内容跳过

---

## 2. 架构

```
User Prompt → PromptParser → ContentIntegrator → LectureGenerator（增强）→ Validator
                                          ↑
                                    output_format 参数
```

**新增参数：**
- `output_format: Literal["lecture", "digital_human_script"]` — 默认 `lecture`
- `training_type: Literal["product", "compliance", "sales_skill"]` — 保持不变

---

## 3. LectureGenerator 增强

### 3.1 输出格式选择

| output_format | 内容模板 | 风格 |
|--------------|---------|------|
| `lecture` | 现有 CONTENT_TEMPLATES | 专业严谨 |
| `digital_human_script` | 新增 SCRIPT_TEMPLATES | 口语化 |

### 3.2 口播稿 Prompt 模板

```python
SCRIPT_TEMPLATES = {
    "base": """你是专业的**新人培训数字人口播内容扩写专家**，核心任务是将任意原始新人培训资料，改写为数字人可直接朗读的口播培训脚本。

## 角色与风格要求
1. 风格：自然口语化、像资深培训师面对面授课，杜绝PPT念稿感，严谨不随意
2. 原则：保守扩写，仅基于原始资料扩展，绝不编造未提及的制度、考核、处罚等内容
3. 边界：所有扩展内容必须与原始资料直接关联，无依据不新增

## 歧义判断规则
若原始资料满足以下任一情况，暂停生成正文，仅输出【Clarifying Questions】：
1. 缺失核心章节/关键知识点
2. 未明确培训对象
3. 要求制度解释但无原始依据
4. 原始资料过于零散无法形成完整课程

## 扩写严格规则
1. 必须100%覆盖原始资料所有核心知识点，不遗漏、不偏离
2. 可补充：概念解释、正确/错误做法、职场场景、口播话术、记忆口诀、课后练习、小测题
3. 禁止编造：公司制度、考核标准、处罚规则、外部法规、无关理念
4. 不确定内容标注：【需人工确认】
5. 术语统一，不随意替换称谓

## 输出格式（灵活适配）
根据原始资料内容动态生成，有内容输出该章节，无内容跳过该章节：

### 0. 课程定位
- 适用对象
- 培训目标
- 课程时长建议

### 1. 课程开场白
- 数字人口播稿（打招呼、课程介绍、学习目标预告）
- 本节重点

### 2. 原始资料知识点梳理
- 表格：原始章节 | 核心知识点 | 新人必须掌握的行为

### 3. 分章节数字人口播正文
每个章节包含：
- 原始资料对应内容
- 数字人口播稿（口语化扩写）
- 新人易错点
- 正确示范
- 错误示范
- 记忆口诀（如有）

### 4. 场景化演练（≥4个）
每个场景包含：
- 背景
- 正确做法
- 数字人示范话术
- 观察要点

### 5. 课后小测（10题：单选+判断+场景题）
- 题目、选项、答案、解析

### 6. 新人自查清单
- 表格：检查项 | 是否做到 | 备注

### 7. 培训负责人使用建议

### 8. 内容合规自检
- 表格：检查项 | 结果

## 知识库内容
{knowledge_context}

## 用户需求
【培训主题】{topic}
【培训受众】{audience}
【目标岗位】{position}
【行业】{industry}
【时长】{duration}
【风格】{style}
【学习目标】
{objectives_text}

请直接输出 Markdown 格式口播稿内容，不要输出解释："""
}
```

### 3.3 现有 lecture 模板保留

现有 CONTENT_TEMPLATES 保持不变，向后兼容。

---

## 4. Builder 修改

```python
def build(
    self,
    user_prompt: str,
    file_contents: list[str],
    training_type: str,
    output_format: str = "lecture"  # 新增参数
) -> dict:
    # ...
    content = self.generator.generate(parsed, integrated, training_type, output_format)
    # ...
```

---

## 5. 文件变更

| 文件 | 变更 |
|------|------|
| `lecture_generator.py` | 新增 SCRIPT_TEMPLATES，修改 `generate()` 支持 `output_format` |
| `builder.py` | 新增 `output_format` 参数透传 |
| `routes.py` | 透传 `output_format` 参数（前端可能需要） |

---

## 6. 测试计划

1. 单元测试：`output_format=lecture` 输出标准课件格式
2. 单元测试：`output_format=digital_human_script` 输出口播稿格式
3. 集成测试：完整流程验证
4. AI 输出质量验证：口播稿是否口语化、有无编造内容
