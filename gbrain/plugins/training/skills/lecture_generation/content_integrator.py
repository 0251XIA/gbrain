import re
from .models import ParsedPrompt, IntegratedContent, SYNONYM_MAP


class ContentIntegrator:
    def integrate(self, parsed: ParsedPrompt, file_contents: list[str]) -> IntegratedContent:
        """按大纲结构分配内容，碎片化内容结构化整合"""
        module_contents: dict[str, list[str]] = {}

        # 获取模块列表
        modules = self._get_modules_from_outline(parsed.outline_structure)

        # 初始化模块内容
        for module in modules:
            module_contents[module] = []

        # 收集未分配的内容
        fallback_pool: list[str] = []

        # 分配文件内容到模块
        for content in file_contents:
            distributed = self._distribute_content(content, module_contents, modules)
            if not distributed:
                fallback_pool.append(content)

        # Fallback 池处理：按学习目标关键词重新匹配
        if fallback_pool and parsed.objectives:
            self._process_fallback_pool(fallback_pool, module_contents, modules, parsed.objectives)

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

    def _process_fallback_pool(self, fallback_pool: list[str], module_contents: dict[str, list[str]], modules: list[str], objectives: list[str]):
        """将未分配内容按学习目标关键词重新分配"""
        # 提取学习目标关键词
        objective_keywords: list[str] = []
        for obj in objectives:
            keywords = re.findall(r'[\w]+', obj)
            objective_keywords.extend([k for k in keywords if len(k) > 1])

        # 尝试用学习目标关键词匹配
        for content in fallback_pool:
            best_module = None
            best_score = 0
            for module in modules:
                score = sum(1 for kw in objective_keywords if re.search(rf'\b{re.escape(kw)}\b', content))
                if score > best_score:
                    best_score = score
                    best_module = module

            if best_module and best_score > 0:
                module_contents[best_module].append(content)
            elif modules:
                # 仍有剩余则分配给第一个模块
                module_contents[modules[0]].append(content)

    def _distribute_content(self, content: str, module_contents: dict[str, list[str]], modules: list[str]) -> bool:
        """将内容分配到对应模块，返回是否分配成功"""
        # 构建每个模块的关键词集合（含同义词扩展）
        module_keywords: dict[str, list[str]] = {}
        for module in modules:
            keywords = re.findall(r'[\w]+', module)
            stopwords = {'模块', '章节', '第', '一', '二', '三', '四', '五', '的', '和'}
            keywords = [k for k in keywords if k not in stopwords and len(k) > 1]
            # 同义词扩展
            expanded = set(keywords)
            for kw in keywords:
                if kw in SYNONYM_MAP:
                    expanded.update(SYNONYM_MAP[kw])
            module_keywords[module] = list(expanded)

        def _keyword_matches(keyword: str, text: str) -> bool:
            """检查关键词是否在文本中（支持中文）"""
            # 直接包含
            if keyword in text:
                return True
            # 中文关键词4+字时，检查2-char子串匹配
            if len(keyword) >= 4 and all('\u4e00' <= c <= '\u9fff' for c in keyword):
                # 使用滑动窗口检查是否有2-char子串在text中
                for i in range(len(keyword) - 1):
                    sub = keyword[i:i+2]
                    if sub in text:
                        return True
            return False

        # 计算每个模块的匹配分数
        module_scores: dict[str, int] = {}
        for module in modules:
            score = 0
            for keyword in module_keywords[module]:
                if _keyword_matches(keyword, content):
                    score += 1
            module_scores[module] = score

        # 多模块分配：分配给所有分数超过阈值(0.3*最高分)的模块
        max_score = max(module_scores.values()) if module_scores else 0
        threshold = max_score * 0.3

        distributed = False
        for module, score in module_scores.items():
            if score >= threshold and score > 0:
                module_contents[module].append(content)
                distributed = True

        return distributed

    def _extract_cases(self, file_contents: list[str]) -> list[dict]:
        """从文件内容中提取案例，使用多种模式匹配"""
        cases = []
        # 案例模式：匹配"案例"或"case"开头的独立段落或章节
        case_patterns = [
            # 模式1: "案例N：" 或 "案例N：" 后面跟内容
            re.compile(r'案例\s*[\d零一二三四五六七八九十百]+[：:]\s*(.{20,500}?)(?=\n\n|\n案例|\Z)', re.DOTALL),
            # 模式2: "案例：" 后面跟内容
            re.compile(r'案例\s*：[：:]\s*(.{20,500}?)(?=\n\n|\Z)', re.DOTALL),
            # 模式3: 独立的案例标题行后面跟内容段落
            re.compile(r'^#{1,3}\s*案例[^\n]*\n+(.{20,500}?)(?=\n#{1,3}\s|\Z)', re.DOTALL | re.MULTILINE),
            # 模式4: "CASE" 或 "Case" 开头的内容块
            re.compile(r'(?:^|\n)(CASE|case|Case)[^\n]*\n+(.{20,500}?)(?=\n(?:CASE|case|Case)|\Z)', re.DOTALL | re.MULTILINE),
        ]

        for content in file_contents:
            matched_cases: set[str] = set()
            for pattern in case_patterns:
                for match in pattern.finditer(content):
                    case_content = match.group(1).strip()
                    if case_content and case_content not in matched_cases:
                        matched_cases.add(case_content)
                        cases.append({
                            "content": case_content,
                            "type": "case"
                        })

            # 如果没有通过模式匹配到，但文件包含"案例"关键词，
            # 则尝试提取包含关键词的整个段落
            if not matched_cases and ('案例' in content or re.search(r'\bcase\b', content, re.I)):
                # 提取包含"案例"关键词的完整句子/段落
                sentences = re.split(r'[\n。]+', content)
                for sentence in sentences:
                    if '案例' in sentence or re.search(r'\bcase\b', sentence, re.I):
                        case_text = sentence.strip()
                        if case_text and len(case_text) > 10:
                            cases.append({
                                "content": case_text,
                                "type": "case"
                            })
                        break

        return cases

    def _extract_supplementary(self, file_contents: list[str]) -> dict[str, list[str]]:
        """从文件内容中提取配套材料，包括资源和政策文件"""
        resources: list[str] = []
        policies: list[str] = []

        # 资源模式：匹配文档链接、附件、参考资料等
        resource_patterns = [
            # URL链接
            re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+'),
            # 文档引用，如"见附件《xxx》"、"参见《xxx》"
            re.compile(r'《([^》]+)》'),
            # 资源标记：资源、资料、附件、参考
            re.compile(r'(?:资源|资料|附件|参考|手册|文档)\s*[:：]\s*([^\n]{5,100})'),
        ]

        # 政策模式：匹配规范、制度、流程等政策文件
        policy_patterns = [
            # 政策文件引用，如"依据《xxx规定》"
            re.compile(r'《([^》]+规定)》'),
            re.compile(r'《([^》]+规范)》'),
            re.compile(r'《([^》]+制度)》'),
            re.compile(r'《([^》]+流程)》'),
            re.compile(r'《([^》]+办法)》'),
            # 政策标题标记
            re.compile(r'(?:政策|规范|制度|流程|规定)\s*[:：]\s*([^\n]{5,100})'),
        ]

        for content in file_contents:
            for pattern in resource_patterns:
                for match in pattern.finditer(content):
                    extracted = match.group(1) if match.lastindex else match.group(0)
                    extracted = extracted.strip()
                    if extracted and extracted not in resources:
                        resources.append(extracted)

            for pattern in policy_patterns:
                for match in pattern.finditer(content):
                    extracted = match.group(1) if match.lastindex else match.group(0)
                    extracted = extracted.strip()
                    if extracted and extracted not in policies:
                        policies.append(extracted)

        return {"resources": resources, "policies": policies}
