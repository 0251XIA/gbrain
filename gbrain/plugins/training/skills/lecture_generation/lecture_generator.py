from .models import ParsedPrompt, IntegratedContent
import re


def call_llm(prompt: str, system_prompt: str = "", max_retries: int = 3) -> str:
    """调用 MiniMax API 生成内容（带重试机制）"""
    import requests
    import time
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

    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{MINIMAX_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=300
            )
            if response.status_code == 429:
                # Rate limit - wait and retry
                wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                time.sleep(wait_time)
                continue
            if response.status_code != 200:
                raise Exception(f"API 错误: {response.status_code}")
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3  # 3, 6, 9 seconds
                time.sleep(wait_time)
                continue

    raise Exception(f"LLM 调用失败（已重试{max_retries}次）: {str(last_error)}")


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
        seen_contents = set()  # 用于去重

        # 模块内容（去重）
        for module_name, contents in integrated.module_contents.items():
            if contents:
                # 去重：避免同一个内容在多个模块中重复出现
                for content in contents:
                    if content not in seen_contents:
                        seen_contents.add(content)
                        parts.append(f"## {module_name}\n{content}")

        # 案例库
        if integrated.case_library:
            case_text = "\n".join(f"- {c['content']}" for c in integrated.case_library[:5])
            if case_text not in seen_contents:
                seen_contents.add(case_text)
                parts.append(f"\n## 案例库\n{case_text}")

        # 配套材料
        if integrated.supplementary_materials:
            res = integrated.supplementary_materials.get("resources", [])
            if res:
                res_text = "\n".join(f"- {r}" for r in res[:5])
                if res_text not in seen_contents:
                    seen_contents.add(res_text)
                    parts.append(f"\n## 配套资源\n{res_text}")

        # 如果模块内容太少（总字数 < 1500），使用原始文件内容补充
        total_module_chars = sum(len(c) for contents in integrated.module_contents.values() for c in contents)
        if total_module_chars < 1500 and integrated.raw_file_contents:
            raw_content = "\n\n".join(integrated.raw_file_contents)
            if raw_content not in seen_contents:
                parts.insert(0, f"## 知识库原始内容\n{raw_content}")

        return "\n\n".join(parts) if parts else "（暂无知识库内容）"

    def _generate_lecture(self, parsed: ParsedPrompt, integrated: IntegratedContent, knowledge_context: str, training_type: str) -> str:
        """生成培训讲义"""
        task_instructions = self._build_lecture_instructions(parsed, integrated, training_type)

        prompt = f"""生成一份关于「{parsed.topic}」的培训讲义。

受众：{parsed.audience}
时长：{parsed.duration}

知识库内容：
{knowledge_context}

结构：{task_instructions}

【重要】输出格式必须遵循：
1. 直接以「## 开篇」作为开头
2. 不要输出任何「主题：」「受众：」「需求：」「描述：」「根据XXX」等字样
3. 只输出纯讲义Markdown内容"""

        system_prompt = """你是企业培训专家。
【强制要求】
- 输出必须直接以「## 开篇」开头，不要有任何前缀说明
- 禁止输出「主题：」「受众：」「需求：」「描述：」「根据XXX」「以下为XXX」等字样
- 禁止复制输入的原文
- 只输出纯讲义内容，每个章节必须有实质性内容"""

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
            modules_instruction = "模块：" + "、".join(module_list)

        return f"""结构：开篇（场景+目标）| {type_specific} | {modules_instruction} | 总结"""

    def _get_type_specific_instructions(self, training_type: str) -> str:
        """根据培训类型返回特定的内容要求"""
        templates = {
            "compliance": "合规要点：法规背景、规则讲解、案例分析、避坑指南",
            "sales_skill": "销售要点：技能方法、话术示范、案例对比、场景演练",
            "product": "产品要点：功能介绍、客户价值、使用场景、案例佐证",
            "business_etiquette": "礼仪要点：基本原则、行为规范、案例分析、场景演练"
        }
        return templates.get(training_type, templates["product"])

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