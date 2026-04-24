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
