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
        "max_tokens": 8192,
        "temperature": 0.7
    }

    try:
        response = requests.post(
            f"{MINIMAX_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=180
        )
        if response.status_code != 200:
            raise Exception(f"API 错误: {response.status_code}")
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"LLM 调用失败: {str(e)}")


class LectureGenerator:
    """
    讲义生成器

    改进点：
    1. 不传占位符，直接给结构化指令
    2. 强调必须使用知识库内容，禁止编造
    3. 分步骤明确输出要求
    """

    def generate(self, parsed: ParsedPrompt, integrated: IntegratedContent, training_type: str, output_format: str = "lecture") -> str:
        """生成完整讲义"""
        # 构建知识库上下文
        knowledge_context = self._build_knowledge_context(integrated)

        # 根据格式选择生成策略
        if output_format == "digital_human_script":
            return self._generate_script(parsed, integrated, knowledge_context)
        else:
            return self._generate_lecture(parsed, integrated, knowledge_context, training_type)

    def _build_knowledge_context(self, integrated: IntegratedContent) -> str:
        """构建知识库上下文，用于 prompt"""
        parts = []

        # 模块内容
        for module_name, contents in integrated.module_contents.items():
            if contents:
                parts.append(f"## {module_name}\n" + "\n".join(contents))

        # 案例库
        if integrated.case_library:
            parts.append("\n## 案例库\n" + "\n".join(f"- {c['content']}" for c in integrated.case_library[:5]))

        # 配套材料
        if integrated.supplementary_materials:
            res = integrated.supplementary_materials.get("resources", [])
            if res:
                parts.append("\n## 配套资源\n" + "\n".join(f"- {r}" for r in res[:5]))

        # 如果模块内容太少（总字数 < 500），使用原始文件内容补充
        total_module_chars = sum(len(c) for contents in integrated.module_contents.values() for c in contents)
        if total_module_chars < 500 and integrated.raw_file_contents:
            raw_content = "\n\n".join(integrated.raw_file_contents)
            if raw_content not in "\n\n".join(parts):
                parts.insert(0, f"## 知识库原始内容（用于补充讲义）\n{raw_content}")

        return "\n\n".join(parts) if parts else "（暂无知识库内容）"

    def _generate_lecture(self, parsed: ParsedPrompt, integrated: IntegratedContent, knowledge_context: str, training_type: str) -> str:
        """生成培训讲义"""
        # 构建需求描述文本
        description_text = parsed.description if parsed.description else "\n".join(f"{i+1}. {obj}" for i, obj in enumerate(parsed.objectives))

        # 构建明确的任务指令（不是占位符模板）
        task_instructions = self._build_lecture_instructions(parsed, integrated, training_type)

        prompt = f"""# 任务：生成培训讲义

## 基本信息
- 主题：{parsed.topic}
- 受众：{parsed.audience}
- 岗位：{parsed.position}
- 行业：{parsed.industry}
- 时长：{parsed.duration}
- 风格：{parsed.style}

## 需求描述（必须严格按照以下要求生成）
{description_text}

## 知识库内容（用于补充和验证，禁止编造，可参考使用）
{knowledge_context}

{task_instructions}

## 输出要求
1. 严格遵循"需求描述"中的所有要求，不得遗漏
2. 每个章节必须有实质性内容，不能只写标题
3. 案例、练习题要具体可执行
4. 语言专业简洁，符合成人学习特点

直接输出 Markdown 格式讲义内容："""

        system_prompt = """你是一个企业培训课件生成专家。你的职责是：
1. 严格按照用户提供的需求描述生成讲义，禁止编造
2. 生成的讲义要专业、简洁、实操性强
3. 每个章节必须有实质性内容，不能只有标题框架
4. 案例要具体，练习题要可执行
5. 如果知识库内容不足以支撑某个章节，使用通用商务礼仪知识补充"""

        try:
            result = call_llm(prompt, system_prompt)
            if result and result.strip():
                return result.strip()
            raise Exception("LLM 返回空内容")
        except Exception as e:
            raise Exception(f"AI 生成讲义失败: {str(e)}") from e

    def _build_lecture_instructions(self, parsed: ParsedPrompt, integrated: IntegratedContent, training_type: str) -> str:
        """构建讲义生成指令"""
        type_specific = self._get_type_specific_instructions(training_type)

        module_list = list(integrated.module_contents.keys())
        modules_instruction = ""
        if module_list:
            modules_instruction = f"""
### 模块章节
必须包含以下 {len(module_list)} 个模块：
"""
            for i, module in enumerate(module_list, 1):
                modules_instruction += f"{i}. {module}\n"

        return f"""## 内容结构要求

### 开篇
- 场景引入：基于受众的实际业务场景，描述一个具体情境
- 学习目标：明确本讲义的预期学习成果

{type_specific}

{modules_instruction}

### 收尾
- 总结回顾：梳理核心要点
- 行动计划：提供可操作的实践建议
"""

    def _get_type_specific_instructions(self, training_type: str) -> str:
        """根据培训类型返回特定的内容要求"""
        templates = {
            "compliance": """### 合规要点（必须包含）
- 法规背景：相关法律法规概述
- 规则讲解：核心合规知识点
- 案例分析：合规/违规真实案例对比
- 避坑指南：✅ 合规做法 / ❌ 违规做法
- 即时练习：场景判断题""",
            "sales_skill": """### 销售技能要点（必须包含）
- 场景引入：真实销售场景
- 技能方法：核心销售技能点
- 话术示范：可落地的话术模板
- 案例分析：成功/失败案例对比
- 避坑指南：✅ 正确做法 / ❌ 错误做法
- 即时练习：场景模拟演练""",
            "product": """### 产品知识要点（必须包含）
- 产品功能：核心功能介绍
- 客户价值：解决什么问题
- 使用场景：实际应用场景
- 案例佐证：公司真实案例
- 避坑指南：✅ 正确做法 / ❌ 错误做法
- 即时练习：产品演示模拟""",
            "business_etiquette": """### 商务礼仪要点（必须包含）
- 基本原则：礼仪的核心价值和作用
- 行为规范：具体的行为标准和要求
- 案例分析：正面/反面案例对比
- 避坑指南：✅ 正确做法 / ❌ 错误做法
- 即时练习：场景模拟演练"""
        }
        return templates.get(training_type, templates.get("product", templates["product"]))

    def _generate_script(self, parsed: ParsedPrompt, integrated: IntegratedContent, knowledge_context: str) -> str:
        """生成数字人口播脚本"""
        objectives_text = "\n".join(f"{i+1}. {obj}" for i, obj in enumerate(parsed.objectives))

        prompt = f"""# 任务：生成数字人口播培训脚本

## 角色
你是专业的**新人培训数字人口播内容扩写专家**。

## 基本信息
- 主题：{parsed.topic}
- 受众：{parsed.audience}
- 岗位：{parsed.position}
- 时长：{parsed.duration}

## 学习目标
{objectives_text}

## 知识库内容（必须基于这些内容生成，禁止编造）
{knowledge_context}

## 输出格式

### 0. 课程定位
- 适用对象
- 培训目标
- 课程时长建议

### 1. 课程开场白
数字人口播稿（打招呼、课程介绍、学习目标预告）

### 2. 知识点梳理
表格：原始章节 | 核心知识点 | 新人必须掌握的行为

### 3. 分章节口播正文
每个章节包含：
- 原始资料对应内容
- 数字人口播稿（口语化扩写）
- 新人易错点
- 正确示范
- 错误示范

### 4. 场景化演练（至少4个）
每个场景：背景 / 正确做法 / 数字人示范话术 / 观察要点

### 5. 课后小测（10题：单选+判断+场景题）
题目、选项、答案、解析

### 6. 新人自查清单
表格：检查项 | 是否做到 | 备注

## 严格规则
1. 保守扩写：仅基于原始资料扩展，绝不编造
2. 不确定内容标注：【需人工确认】
3. 禁止编造：公司制度、考核标准、处罚规则

直接输出 Markdown 格式口播稿内容："""

        system_prompt = """你是一个专业的新人培训数字人口播内容扩写专家。
- 风格：自然口语化、像资深培训师面对面授课
- 原则：保守扩写，仅基于原始资料扩展，绝不编造未提及的内容
- 禁止编造公司制度、考核标准、处罚规则
- 不确定内容标注【需人工确认】"""

        try:
            result = call_llm(prompt, system_prompt)
            if result and result.strip():
                return result.strip()
            raise Exception("LLM 返回空内容")
        except Exception as e:
            raise Exception(f"AI 生成脚本失败: {str(e)}") from e