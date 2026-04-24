from .models import ParsedPrompt, IntegratedContent
import re


def call_llm(prompt: str, system_prompt: str = "") -> str:
    """调用 MiniMax API 生成内容"""
    import requests
    from gbrain.config import MINIMAX_API_KEY, MINIMAX_BASE_URL, MODEL_NAME

    api_key = MINIMAX_API_KEY

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.7
    }

    try:
        response = requests.post(
            f"{MINIMAX_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=120
        )
        if response.status_code != 200:
            raise Exception(f"API 错误: {response.status_code}")
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"LLM 调用失败: {str(e)}")


class LectureGenerator:
    CONTENT_TEMPLATES = {
        "product": """# {topic}

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
""",
        "compliance": """# {topic}

## 合规培训信息
- **培训受众：** {audience}
- **目标岗位：** {position}
- **所属行业：** {industry}
- **预计时长：** {duration}
- **培训风格：** {style}

## 学习目标
{objectives}

## 合规要点结构

### 开篇锚定层
**【法规背景】**
（相关法律法规概述）

**【问题抛出】**
（1-2个合规思考问题）

**【合规要点讲解】**
（核心合规知识点）

**【案例佐证】**
（合规/违规真实案例）

**【避坑指南】**
- ✅ 合规做法
- ❌ 违规做法
- ⚠️ 注意事项

**【即时练习】**
（配套练习题）

{module_contents}
""",
        "sales_skill": """# {topic}

## 销售技能培训信息
- **培训受众：** {audience}
- **目标岗位：** {position}
- **所属行业：** {industry}
- **预计时长：** {duration}
- **培训风格：** {style}

## 学习目标
{objectives}

## 销售技能结构

### 开篇锚定层
**【销售场景引入】**
（真实销售场景）

**【问题抛出】**
（1-2个销售问题）

**【技能方法讲解】**
（核心销售技能点）

**【案例佐证】**
（成功/失败销售案例）

**【避坑指南】**
- ✅ 正确做法
- ❌ 错误做法
- ⚠️ 注意事项

**【即时练习】**
（配套练习题）

{module_contents}
""",
    }

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

    def generate(self, parsed: ParsedPrompt, integrated: IntegratedContent, training_type: str, output_format: str = "lecture") -> str:
        """生成完整讲义"""
        objectives_text = '\n'.join(f"{i+1}. {obj}" for i, obj in enumerate(parsed.objectives))

        module_text = self._generate_modules(parsed, integrated)

        # 根据 output_format 和 training_type 选择模板
        if output_format == "digital_human_script":
            template = self.SCRIPT_TEMPLATES["base"]
        else:
            template = self.CONTENT_TEMPLATES.get(training_type, self.CONTENT_TEMPLATES["product"])

        # 构建基础结构（用于 AI 生成）
        base_content = template.format(
            topic=parsed.topic,
            audience=parsed.audience,
            position=parsed.position,
            industry=parsed.industry,
            duration=parsed.duration,
            style=parsed.style,
            objectives=objectives_text,
            module_contents=module_text
        )

        # 使用 AI 生成实际内容
        return self._generate_with_ai(parsed, integrated, base_content, objectives_text)

    def _generate_with_ai(self, parsed: ParsedPrompt, integrated: IntegratedContent, base_content: str, objectives_text: str) -> str:
        """使用 AI 根据知识库内容生成实际讲义"""
        # 收集所有知识库内容
        knowledge_context = ""
        for module_name, contents in integrated.module_contents.items():
            if contents:
                knowledge_context += f"\n\n### {module_name}\n" + "\n".join(contents)

        prompt = f"""请根据以下信息，生成完整的培训讲义。

【培训主题】{parsed.topic}
【培训受众】{parsed.audience}
【目标岗位】{parsed.position}
【行业】{parsed.industry}
【时长】{parsed.duration}
【风格】{parsed.style}

【学习目标】
{objectives_text}

【知识库内容】
{knowledge_context if knowledge_context.strip() else '（暂无知识库内容，请根据培训主题、受众和学习目标自行生成专业、实用的培训内容）'}

请直接生成完整的 Markdown 格式培训讲义，内容要：
1. 紧密围绕知识库内容，不要凭空编造
2. 语言专业、简洁、易懂，符合成人学习规律
3. 结构完整：包含场景引入、问题抛出、方法讲解、案例、避坑指南、即时练习
4. 充分利用知识库中的真实案例和数据

直接输出 Markdown 内容，不需要解释："""

        system_prompt = """你是一个专业的企业培训课件生成专家。生成专业、简洁、实操性强的培训讲义。"""

        try:
            result = call_llm(prompt, system_prompt)
            if result and result.strip():
                return result.strip()
            raise Exception("LLM 返回空内容")
        except Exception as e:
            raise Exception(f"AI 生成讲义失败: {str(e)}") from e

    def _generate_modules(self, parsed: ParsedPrompt, integrated: IntegratedContent) -> str:
        modules = []
        for module_name, contents in integrated.module_contents.items():
            if contents:
                module_text = f"""
### {module_name}

**【场景引入】**
（基于培训受众的实际业务场景）

**【问题抛出】**
（1-2个思考问题）

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
