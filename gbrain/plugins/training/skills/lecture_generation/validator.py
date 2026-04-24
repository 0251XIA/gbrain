from .models import ParsedPrompt, ValidationReport


class Validator:
    def validate(self, lecture_content: str, parsed: ParsedPrompt) -> ValidationReport:
        """校验讲义内容与用户需求的匹配度"""
        issues: list[str] = []
        suggestions: list[str] = []

        # Prompt Match Score
        prompt_match = self._check_prompt_match(lecture_content, parsed, issues, suggestions)

        # Coverage Score
        coverage = self._check_coverage(lecture_content, parsed, issues, suggestions)

        # Compliance Score
        compliance = self._check_compliance(lecture_content, parsed, issues, suggestions)

        # Practical Score
        practical = self._check_practical(lecture_content, parsed, issues, suggestions)

        # Structure Score
        structure = self._check_structure(lecture_content, parsed, issues, suggestions)

        # Calculate overall
        overall = int((prompt_match + coverage + compliance + practical + structure) / 5)

        return ValidationReport(
            prompt_match_score=prompt_match,
            coverage_score=coverage,
            compliance_score=compliance,
            practical_score=practical,
            structure_score=structure,
            overall_score=overall,
            issues=issues,
            suggestions=suggestions,
        )

    def _check_prompt_match(self, content: str, parsed: ParsedPrompt, issues: list[str], suggestions: list[str]) -> int:
        score = 100
        if parsed.topic and parsed.topic not in content:
            issues.append(f"讲义内容未包含指定主题：{parsed.topic}")
            suggestions.append("在讲义开头明确阐述主题内容")
            score -= 20
        if parsed.audience and parsed.audience not in content:
            issues.append(f"讲义内容未明确针对受众：{parsed.audience}")
            suggestions.append("在讲义中明确说明目标受众群体")
            score -= 20
        return max(score, 0)

    def _check_coverage(self, content: str, parsed: ParsedPrompt, issues: list[str], suggestions: list[str]) -> int:
        score = 100
        covered_objectives = [obj for obj in parsed.objectives if obj in content]
        missing_objectives = [obj for obj in parsed.objectives if obj not in content]
        if parsed.objectives:
            coverage_ratio = len(covered_objectives) / len(parsed.objectives)
            score = int(coverage_ratio * 100)
        if missing_objectives:
            issues.append(f"学习目标未完全覆盖，缺失：{'、'.join(missing_objectives)}")
            suggestions.append("在讲义中添加对应章节以覆盖所有学习目标")
        return score

    def _check_compliance(self, content: str, parsed: ParsedPrompt, issues: list[str], suggestions: list[str]) -> int:
        score = 100
        for forbidden in parsed.forbidden_content:
            if forbidden in content:
                issues.append(f"内容包含禁止内容：{forbidden}")
                suggestions.append(f"移除或改写包含「{forbidden}」的内容")
                score -= 30
        return max(score, 0)

    def _check_practical(self, content: str, parsed: ParsedPrompt, issues: list[str], suggestions: list[str]) -> int:
        score = 70
        has_cases = "案例" in content or "case" in content.lower()
        has_exercises = "练习" in content or "练习题" in content
        if has_cases:
            score += 10
        if has_exercises:
            score += 10
        if not has_cases:
            issues.append("讲义缺少案例内容")
            suggestions.append("添加真实或模拟案例以帮助学员理解")
        if not has_exercises:
            issues.append("讲义缺少练习内容")
            suggestions.append("添加即时练习题以巩固学习效果")
        return min(score, 100)

    def _check_structure(self, content: str, parsed: ParsedPrompt, issues: list[str], suggestions: list[str]) -> int:
        score = 80
        required_sections = ["场景引入", "方法讲解", "案例佐证", "避坑指南", "即时练习"]
        for section in required_sections:
            if section not in content:
                issues.append(f"讲义缺少必要章节：{section}")
                suggestions.append(f"添加「{section}」章节以完善讲义结构")
                score -= 10
        return max(score, 0)
