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
        import sys

        # 计算每个模块的字符数
        module_chars = {k: sum(len(c) for c in v) for k, v in integrated.module_contents.items()}
        module_info = {k: f"{len(v)}items/{module_chars[k]}chars" for k, v in integrated.module_contents.items()}
        min_module_chars = min(module_chars.values()) if module_chars else 0

        sys.stderr.write(f"[LectureGenerator] START _build_knowledge_context\n")
        sys.stderr.write(f"[LectureGenerator] module_contents={module_info}\n")
        sys.stderr.write(f"[LectureGenerator] min_module_chars={min_module_chars}, threshold=1500\n")
        sys.stderr.write(f"[LectureGenerator] raw_file_contents={len(integrated.raw_file_contents)} items\n")
        sys.stderr.flush()

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

        # 补充策略：如果任何模块内容 < 1500 chars，使用原始文件内容补充
        if min_module_chars < 1500 and integrated.raw_file_contents:
            sys.stderr.write(f"[LectureGenerator] SUPPLEMENT triggered: min_module_chars={min_module_chars} < 1500\n")
            raw_content = "\n\n".join(integrated.raw_file_contents)
            if raw_content not in seen_contents:
                parts.insert(0, f"## 知识库原始内容\n{raw_content}")
                sys.stderr.write(f"[LectureGenerator] Added raw content, len={len(raw_content)}\n")
                sys.stderr.flush()
        else:
            sys.stderr.write(f"[LectureGenerator] SUPPLEMENT NOT triggered: min_module_chars={min_module_chars}, raw_file_contents={len(integrated.raw_file_contents)}\n")
            sys.stderr.flush()

        result = "\n\n".join(parts) if parts else "（暂无知识库内容）"
        sys.stderr.write(f"[LectureGenerator] FINAL knowledge_context length={len(result)}\n")
        sys.stderr.flush()
        return result

    def _generate_lecture(self, parsed: ParsedPrompt, integrated: IntegratedContent, knowledge_context: str, training_type: str) -> str:
        """生成培训讲义"""
        task_instructions = self._build_lecture_instructions(parsed, integrated, training_type)

        prompt = f"""生成一份关于「{parsed.topic}」的培训讲义。

受众：{parsed.audience}
时长：{parsed.duration}

知识库内容：
{knowledge_context}

结构：{task_instructions}

【重要-输出格式要求】
1. 直接以「## 开篇」作为开头
2. 不要输出任何「主题：」「受众：」「需求：」「描述：」「根据XXX」等字样
3. 只输出纯讲义Markdown内容
4. 禁止在讲义内容前输出任何思考过程、推理说明或中间分析"""

        system_prompt = """你是企业培训专家。
【强制要求】
- 输出必须直接以「## 开篇」开头，不要有任何前缀说明
- 禁止输出「主题：」「受众：」「需求：」「描述：」「根据XXX」「以下为XXX」等字样
- 禁止复制输入的原文
- 只输出纯讲义内容，每个章节必须有实质性内容
- 禁止输出思考过程、推理说明、中间分析
- 直接输出讲义内容，不要有任何前置说明"""

        try:
            result = call_llm(prompt, system_prompt)
            if result and result.strip():
                # 清理思考过程标记
                return self._clean_thinking_markers(result.strip())
            raise Exception("LLM 返回空内容")
        except Exception as e:
            raise Exception(f"AI 生成讲义失败: {str(e)}") from e

    def _clean_thinking_markers(self, text: str) -> str:
        """清理文本中的思考过程标记"""
        import re
        think_start = '<think>'
        think_end = '</think>'
        text = re.sub(think_start + r'[\s\S]*?' + think_end, '', text)
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()

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
你是资深的企业培训讲义生成大师。你的核心任务是基于企业提供的知识文件，生成一本结构严谨、内容落地、语言鲜活的新人培训"活讲义"。你既要保证知识的准确性，也要让内容具备"数字人口播"般的自然与生动，让新人看得懂、学得会、做得对。

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

### 0. 课程定位与导航
-适用对象画像：用一两句话勾勒出新人的岗位痛点与期待。
-核心培训目标：提炼本次培训要解决的具体问题。
-时长分配建议：给出开场、讲授、演练、测评各环节的分钟数。


### 1. 课程开场白
以亲切的问候和共情切入，点出新人的常见困惑。
清晰预告本次课程的学习路径与收获，激发期待。
语言要求：像资深导师在迎新会上聊天，自然、有感染力。

### 2. 知识点梳理
表格：原始章节 | 核心知识点 | 新人必须掌握的行为

### 3. 分章节讲义内容（正文）
每章包含5个模块，形成"学、讲、练、示"闭环：
📚 原始知识锚点：摘录对应的知识库原文，确保师出有名。
🎙️ 数字人讲师口播稿：
   -对原文进行口语化、场景化扩写。
   -多用类比、举例、设问等手法，把枯燥的条文转化为生动的讲解。
   -严守边界：只对原文进行解释和举例，不新增规则。
⚠️ 新人避坑指南：列出该知识点下新人最容易犯的1-2个具体错误。
✅ 正确示范：用一段话或一个动作描述，展示规范做法。
❌ 错误还原：用一段话或一个动作描述，展示典型错误（需有明显错误标签）。


### 4. 场景化演练（至少4个）
设置贴近真实工作的情境，让新人"做中学"：
工作场景：描述一个具体、真实的任务背景。
演练要求：给出需要新人完成的具体动作或决策。
观察要点：列出讲师观察新人表现的核查点。
✅ 示范话术/行为：提供一个标准答案式的正确应对范本。

### 5. 课后小测（10题：单选+判断+场景题）
检验核心知识掌握情况，形式多样化：
 题型构成：单选题、判断题、基于场景的最佳实践题。
 每题提供：题目、选项（如有）、正确答案、详细解析。
 解析原则：不仅解惑，更要回归到知识库原文或演练要点。

### 6. 新人自查清单
表格：检查项 | 是否做到 | 备注

## 严格规则
1. 保守扩写：仅基于原始资料扩展，绝不编造
2. 不确定内容标注：【需人工确认】
3. 禁止编造：公司制度、考核标准、处罚规则

直接输出 Markdown 格式口播稿内容："""

        system_prompt = """你是资深的企业培训讲义生成大师。你的核心任务是基于企业提供的知识文件，生成一本结构严谨、内容落地、语言鲜活的新人培训"活讲义"。你既要保证知识的准确性，也要让内容具备"数字人口播"般的自然与生动，让新人看得懂、学得会、做得对。
- 风格：自然口语化、像资深培训师面对面授课
- 原则：保守扩写，仅基于原始资料扩展，绝不编造未提及的内容
- 禁止编造公司制度、考核标准、处罚规则
- 不确定内容标注【需人工确认】
- 禁止输出思考过程、推理说明、中间分析
- 直接输出讲义内容，不要有任何前置说明"""

        try:
            result = call_llm(prompt, system_prompt)
            if result and result.strip():
                # 清理思考过程标记
                return self._clean_thinking_markers(result.strip())
            raise Exception("LLM 返回空内容")
        except Exception as e:
            raise Exception(f"AI 生成脚本失败: {str(e)}") from e