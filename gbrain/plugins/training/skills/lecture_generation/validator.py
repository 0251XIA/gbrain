from .models import ParsedPrompt, ValidationReport


class Validator:
    def validate(self, lecture_content: str, parsed: ParsedPrompt) -> ValidationReport:
        """校验讲义内容与用户需求的匹配度"""
        issues: list[str] = []
        suggestions: list[str] = []

        # Prompt Match Score
        prompt_match = self._check_prompt_match(lecture_content, parsed)

        # Coverage Score
        coverage = self._check_coverage(lecture_content, parsed)

        # Compliance Score
        compliance = self._check_compliance(lecture_content, parsed)

        # Practical Score
        practical = self._check_practical(lecture_content, parsed)

        # Structure Score
        structure = self._check_structure(lecture_content, parsed)

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

    def _check_prompt_match(self, content: str, parsed: ParsedPrompt) -> int:
        score = 100
        if parsed.topic and parsed.topic not in content:
            score -= 20
        if parsed.audience and parsed.audience not in content:
            score -= 20
        return max(score, 0)

    def _check_coverage(self, content: str, parsed: ParsedPrompt) -> int:
        score = 100
        covered_objectives = sum(1 for obj in parsed.objectives if obj in content)
        if parsed.objectives:
            coverage_ratio = covered_objectives / len(parsed.objectives)
            score = int(coverage_ratio * 100)
        return score

    def _check_compliance(self, content: str, parsed: ParsedPrompt) -> int:
        score = 100
        for forbidden in parsed.forbidden_content:
            if forbidden in content:
                score -= 30
        return max(score, 0)

    def _check_practical(self, content: str, parsed: ParsedPrompt) -> int:
        score = 70
        has_cases = "案例" in content or "case" in content.lower()
        has_exercises = "练习" in content or "练习题" in content
        if has_cases:
            score += 10
        if has_exercises:
            score += 10
        return min(score, 100)

    def _check_structure(self, content: str, parsed: ParsedPrompt) -> int:
        score = 80
        required_sections = ["场景引入", "方法讲解", "案例佐证", "避坑指南", "即时练习"]
        for section in required_sections:
            if section not in content:
                score -= 10
        return max(score, 0)
