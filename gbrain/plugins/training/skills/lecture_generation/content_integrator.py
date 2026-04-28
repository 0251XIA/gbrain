import re
import logging
from .models import ParsedPrompt, IntegratedContent, SYNONYM_MAP

logger = logging.getLogger(__name__)
DEBUG_FILE = '/tmp/debug_integrator.txt'


class ContentIntegrator:
    def integrate(self, parsed: ParsedPrompt, file_contents: list[str]) -> IntegratedContent:
        """按大纲结构分配内容，碎片化内容结构化整合"""
        with open(DEBUG_FILE, 'a') as f:
            f.write(f"[ContentIntegrator] START: {len(file_contents)} files, chars={sum(len(c) for c in file_contents)}\n")
            f.write(f"[ContentIntegrator] parsed.outline_structure={parsed.outline_structure}\n")
            if file_contents:
                f.write(f"[ContentIntegrator] file_contents[0][:300]={file_contents[0][:300]}\n")

        module_contents: dict[str, list[str]] = {}
        modules = self._get_modules_from_outline(parsed.outline_structure)
        with open(DEBUG_FILE, 'a') as f:
            f.write(f"[ContentIntegrator] modules={modules}\n")

        for module in modules:
            module_contents[module] = []

        fallback_pool: list[str] = []

        # 智能拆分并分配内容
        for file_content in file_contents:
            sections = self._split_content_by_sections(file_content)
            with open(DEBUG_FILE, 'a') as f:
                f.write(f"[ContentIntegrator] split into {len(sections)} sections\n")
                for i, sec in enumerate(sections[:5]):
                    f.write(f"[ContentIntegrator] section[{i}]={sec[:80]}...\n")

            for section in sections:
                distributed = self._distribute_content(section, module_contents, modules)
                if not distributed:
                    fallback_pool.append(section)

        with open(DEBUG_FILE, 'a') as f:
            f.write(f"[ContentIntegrator] after distribute: fallback_pool={len(fallback_pool)}, module_chars={dict((k, sum(len(c) for c in v)) for k,v in module_contents.items())}\n")

        if fallback_pool and parsed.objectives:
            self._process_fallback_pool(fallback_pool, module_contents, modules, parsed.objectives)
        elif fallback_pool and modules:
            empty_modules = [m for m in modules if not module_contents[m]]
            if empty_modules:
                for content in fallback_pool:
                    for mod in empty_modules:
                        module_contents[mod].append(content)
            else:
                for content in fallback_pool:
                    for mod in modules:
                        module_contents[mod].append(content)

        with open(DEBUG_FILE, 'a') as f:
            f.write(f"[ContentIntegrator] after fallback: module_chars={dict((k, sum(len(c) for c in v)) for k,v in module_contents.items())}\n")

        case_library = self._extract_cases(file_contents)
        supplementary = self._extract_supplementary(file_contents)

        all_module_chars = sum(len(c) for contents in module_contents.values() for c in contents)
        if file_contents and all_module_chars > 0:
            empty_modules = [m for m in modules if not module_contents[m]]
            if empty_modules:
                with open(DEBUG_FILE, 'a') as f:
                    f.write(f"[ContentIntegrator] supplementing empty modules: {empty_modules}\n")
                for empty_mod in empty_modules:
                    for src_mod in modules:
                        if module_contents[src_mod]:
                            module_contents[empty_mod].extend(module_contents[src_mod][:1])
                            break

        with open(DEBUG_FILE, 'a') as f:
            f.write(f"[ContentIntegrator] FINAL: module_chars={dict((k, sum(len(c) for c in v)) for k,v in module_contents.items())}\n")

        return IntegratedContent(
            module_contents=module_contents,
            case_library=case_library,
            supplementary_materials=supplementary,
            raw_file_contents=file_contents
        )

    def _split_content_by_sections(self, content: str) -> list[str]:
        """按章节拆分 KB 内容"""
        lines = content.split('\n')

        def is_likely_title(line: str) -> bool:
            stripped = line.strip()
            # 基本检查：长度 4-20
            if not (4 <= len(stripped) <= 20):
                return False
            # 不以列表符号开头
            if re.match(r'^[\-\*\d]', stripped):
                return False
            # 排除带冒号的描述性内容
            if '：' in stripped or ':' in stripped:
                return False
            # 排除以"的"结尾的描述性标题
            if stripped.endswith('的'):
                return False
            # 排除包含较多描述性文字的标题
            if '的' in stripped and len(stripped) > 6:
                return False
            # 以中文为主
            chinese = re.findall(r'[一-龥]', stripped)
            if len(chinese) < len(stripped) * 0.5:
                return False
            # 后面是空行
            try:
                idx = lines.index(line)
                if idx + 1 >= len(lines) or lines[idx + 1].strip() != '':
                    return False
            except ValueError:
                return False
            return True

        # 找出章节标题行
        section_starts = []
        for i, line in enumerate(lines):
            if is_likely_title(line):
                section_starts.append(i)

        # 按章节分割
        sections = []
        for i, start_idx in enumerate(section_starts):
            end_idx = section_starts[i + 1] if i + 1 < len(section_starts) else len(lines)
            chapter_lines = lines[start_idx:end_idx]
            while chapter_lines and not chapter_lines[-1].strip():
                chapter_lines.pop()
            if chapter_lines:
                sections.append('\n'.join(chapter_lines))

        if len(sections) < 2:
            return [content]

        return sections

    def _get_modules_from_outline(self, outline: dict) -> list[str]:
        modules = []
        for section_name, items in outline.items():
            if section_name == "模块拆解层":
                modules.extend(items)
        return modules

    def _extract_keywords(self, text: str) -> list[str]:
        keywords = []
        english_words = re.findall(r'[a-zA-Z0-9]+', text)
        keywords.extend([w for w in english_words if len(w) > 1])
        chinese_text = re.sub(r'[a-zA-Z0-9\s]', '', text)
        for i in range(len(chinese_text) - 1):
            kw = chinese_text[i:i+2]
            if kw not in keywords:
                keywords.append(kw)
        return [k for k in keywords if len(k) > 1]

    def _process_fallback_pool(self, fallback_pool: list[str], module_contents: dict[str, list[str]], modules: list[str], objectives: list[str]):
        objective_keywords: list[str] = []
        for obj in objectives:
            keywords = self._extract_keywords(obj)
            objective_keywords.extend(keywords)

        for content in fallback_pool:
            best_module = None
            best_score = 0
            for module in modules:
                score = sum(1 for kw in objective_keywords if kw in content)
                if score > best_score:
                    best_score = score
                    best_module = module
            if best_module and best_score > 0:
                module_contents[best_module].append(content)
            elif modules:
                module_contents[modules[0]].append(content)

    def _distribute_content(self, content: str, module_contents: dict[str, list[str]], modules: list[str]) -> bool:
        """分配内容到最佳匹配的模块"""
        digit_map = {'1': '一', '2': '二', '3': '三', '4': '四', '5': '五',
                     '6': '六', '7': '七', '8': '八', '9': '九', '0': '零'}

        # 改进：优先使用完整模块名匹配
        module_scores: dict[str, int] = {}
        for module in modules:
            score = 0
            # 1. 完整模块名匹配（高权重）
            if module in content:
                score += 10  # 完整匹配给高分
            # 2. 拆分关键词匹配（较低权重）
            keywords = re.findall(r'[\w]+', module)
            stopwords = {'模块', '章节', '第', '一', '二', '三', '四', '五', '的', '和'}
            keywords = [k for k in keywords if k not in stopwords and len(k) > 1]
            for kw in keywords:
                if kw in content:
                    score += 1
            module_scores[module] = score

        # 找最高分
        max_score = max(module_scores.values()) if module_scores else 0
        if max_score == 0:
            with open(DEBUG_FILE, 'a') as f:
                f.write(f"[ContentIntegrator] _distribute: no match for content (first 100): {content[:100]}\n")
            return False

        # 找最佳模块（优先选择得分最高的，如果有多于1个模块得分相同，选择最短的避免模糊匹配）
        best_module = None
        best_score = -1
        for module, score in module_scores.items():
            if score > best_score:
                best_score = score
                best_module = module
            elif score == best_score == best_score:
                # 得分相同时，选择最短的模块名（更精确）
                if len(module) < len(best_module):
                    best_module = module

        if best_module:
            module_contents[best_module].append(content)
            with open(DEBUG_FILE, 'a') as f:
                f.write(f"[ContentIntegrator] _distribute: assigned to '{best_module}' with score {max_score}\n")
            return True
        return False

    def _extract_cases(self, file_contents: list[str]) -> list[dict]:
        cases = []
        case_patterns = [
            re.compile(r'案例\s*[\d零一二三四五六七八九十百]+[：:]\s*(.{20,})?(?=\n\n|\n案例|\Z)', re.DOTALL),
            re.compile(r'案例\s*：[：:]\s*(.{20,})?(?=\n\n|\Z)', re.DOTALL),
            re.compile(r'^#{1,3}\s*案例[^\n]*\n+(.{20,})?(?=\n#{1,3}\s|\Z)', re.DOTALL | re.MULTILINE),
            re.compile(r'(?:^|\n)(CASE|case|Case)[^\n]*\n+(.{20,})?(?=\n(?:CASE|case|Case)|\Z)', re.DOTALL | re.MULTILINE),
        ]
        for content in file_contents:
            matched_cases: set[str] = set()
            for pattern in case_patterns:
                for match in pattern.finditer(content):
                    case_content = match.group(1).strip() if match.group(1) else ""
                    if case_content and case_content not in matched_cases:
                        matched_cases.add(case_content)
                        paragraphs = re.split(r'(?<=[。！？\n])', case_content)
                        case_text = ''.join(paragraphs[:3])
                        cases.append({"content": case_text, "type": "case"})
            if not matched_cases and ('案例' in content or re.search(r'\bcase\b', content, re.I)):
                sentences = re.split(r'[\n。]+', content)
                for sentence in sentences:
                    if '案例' in sentence or re.search(r'\bcase\b', sentence, re.I):
                        case_text = sentence.strip()
                        if case_text and len(case_text) > 10:
                            cases.append({"content": case_text, "type": "case"})
                        break
        return cases

    def _extract_supplementary(self, file_contents: list[str]) -> dict[str, list[str]]:
        resources: list[str] = []
        policies: list[str] = []
        resource_patterns = [
            re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+'),
            re.compile(r'《([^》]+)》'),
            re.compile(r'(?:资源|资料|附件|参考|手册|文档)\s*[:：]\s*([^\n]{5,100})'),
        ]
        policy_patterns = [
            re.compile(r'《([^》]+规定)》'),
            re.compile(r'《([^》]+规范)》'),
            re.compile(r'《([^》]+制度)》'),
            re.compile(r'《([^》]+流程)》'),
            re.compile(r'《([^》]+办法)》'),
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