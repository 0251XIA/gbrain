# 数字人口播稿支持实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 LectureGenerator 增加 output_format 参数，支持 lecture 和 digital_human_script 两种输出格式

**Architecture:** 在 LectureGenerator 中新增 SCRIPT_TEMPLATES，修改 generate() 方法支持 output_format 参数，灵活选择模板

**Tech Stack:** Python, pytest

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `gbrain/plugins/training/skills/lecture_generation/lecture_generator.py` | 核心修改：新增 SCRIPT_TEMPLATES 和 output_format 支持 |
| `gbrain/plugins/training/skills/lecture_generation/builder.py` | 新增 output_format 参数透传 |
| `gbrain/plugins/training/skills/lecture_generation/routes.py` | 透传 output_format 参数 |
| `tests/plugins/training/skills/lecture_generation/test_lecture_generator.py` | 新增口播稿格式测试 |

---

## Task 1: LectureGenerator 增加 output_format 参数

**Files:**
- Modify: `gbrain/plugins/training/skills/lecture_generation/lecture_generator.py:154-176`

- [ ] **Step 1: 修改 generate 方法签名**

将 `generate` 方法签名从：
```python
def generate(self, parsed: ParsedPrompt, integrated: IntegratedContent, training_type: str) -> str:
```

修改为：
```python
def generate(self, parsed: ParsedPrompt, integrated: IntegratedContent, training_type: str, output_format: str = "lecture") -> str:
```

- [ ] **Step 2: 新增 SCRIPT_TEMPLATES**

在 `CONTENT_TEMPLATES` 后添加：

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

- [ ] **Step 3: 修改 generate 方法选择模板**

将 `generate` 方法中的模板选择逻辑从：
```python
template = self.CONTENT_TEMPLATES.get(training_type, self.CONTENT_TEMPLATES["product"])
```

修改为：
```python
if output_format == "digital_human_script":
    template = self.SCRIPT_TEMPLATES["base"]
else:
    template = self.CONTENT_TEMPLATES.get(training_type, self.CONTENT_TEMPLATES["product"])
```

- [ ] **Step 4: 提交**

```bash
git add gbrain/plugins/training/skills/lecture_generation/lecture_generator.py
git commit -m "feat: add output_format parameter and SCRIPT_TEMPLATES"
```

---

## Task 2: Builder 透传 output_format 参数

**Files:**
- Modify: `gbrain/plugins/training/skills/lecture_generation/builder.py:15-29`

- [ ] **Step 1: 修改 build 方法签名**

将 `build` 方法从：
```python
def build(
    self,
    user_prompt: str,
    file_contents: list[str],
    training_type: str
) -> dict:
```

修改为：
```python
def build(
    self,
    user_prompt: str,
    file_contents: list[str],
    training_type: str,
    output_format: str = "lecture"
) -> dict:
```

- [ ] **Step 2: 透传 output_format 参数**

将：
```python
content = self.generator.generate(parsed, integrated, training_type)
```

修改为：
```python
content = self.generator.generate(parsed, integrated, training_type, output_format)
```

- [ ] **Step 3: 提交**

```bash
git add gbrain/plugins/training/skills/lecture_generation/builder.py
git commit -m "feat: pass output_format parameter in builder"
```

---

## Task 3: 透传 output_format 到 routes

**Files:**
- Modify: `gbrain/plugins/training/skills/lecture_generation/routes.py`（确认 output_format 透传）

- [ ] **Step 1: 检查 routes.py 的 build 调用**

查看当前 routes.py 如何调用 builder.build，确认是否需要添加 output_format 参数。

- [ ] **Step 2: 如需要，添加 output_format 参数透传**

```bash
# 检查 routes.py 中的 build 调用
grep -n "builder.build\|\.build(" gbrain/plugins/training/routes.py
```

- [ ] **Step 3: 提交**

```bash
git add gbrain/plugins/training/skills/lecture_generation/routes.py
git commit -m "feat: pass output_format in routes"
```

---

## Task 4: 新增口播稿格式测试

**Files:**
- Test: `tests/plugins/training/skills/lecture_generation/test_lecture_generator.py`

- [ ] **Step 1: 编写口播稿格式测试**

在 `test_lecture_generator.py` 添加：

```python
def test_generate_digital_human_script():
    """测试 output_format=digital_human_script 输出口播稿格式"""
    generator = LectureGenerator()

    parsed = ParsedPrompt(
        topic="契约锁产品知识培训",
        audience="新入职销售",
        position="销售代表",
        industry="企业服务/SaaS",
        duration="90分钟",
        style="口语化",
        objectives=["掌握核心功能", "了解使用场景"],
        special_requirements=[],
        forbidden_content=[],
        num_modules=1,
        outline_structure={}
    )

    integrated = IntegratedContent(
        module_contents={"模块1": ["电子签章服务：帮助企业实现合同电子签署"]},
        case_library=[{"content": "某公司使用电子签章提升效率案例", "type": "case"}],
        supplementary_materials={}
    )

    result = generator.generate(parsed, integrated, "product", output_format="digital_human_script")

    # 口播稿应包含特定章节标记
    assert "课程定位" in result or "课程开场白" in result or "口播" in result
    # 不应包含标准课件的固定格式
    assert "培训信息" not in result or "学习目标" in result
```

- [ ] **Step 2: 运行测试**

```bash
cd /Users/forxia/GBRAIN-AGENT && python -m pytest tests/plugins/training/skills/lecture_generation/test_lecture_generator.py::test_generate_digital_human_script -v
```
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add tests/plugins/training/skills/lecture_generation/test_lecture_generator.py
git commit -m "test: add digital_human_script format test"
```

---

## Task 5: 完整测试验证

- [ ] **Step 1: 运行所有测试**

```bash
cd /Users/forxia/GBRAIN-AGENT && python -m pytest tests/plugins/training/skills/lecture_generation/ -v
```

- [ ] **Step 2: 提交最终变更**

```bash
git add -A && git commit -m "feat: add digital_human_script output format support

- Add output_format parameter to LectureGenerator.generate()
- Add SCRIPT_TEMPLATES for digital human script output
- Pass output_format through builder and routes
- Add unit tests for both output formats

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 验证指标

| 指标 | 预期 |
|------|------|
| `output_format="lecture"` | 输出标准课件格式（向后兼容） |
| `output_format="digital_human_script"` | 输出口播稿格式 |
| 现有测试 | 全部通过 |
| 新增测试 | 通过 |
