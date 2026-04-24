from .prompt_parser import PromptParser
from .content_integrator import ContentIntegrator
from .lecture_generator import LectureGenerator
from .validator import Validator
from .models import LectureOutput


class LectureGenerationBuilder:
    def __init__(self) -> None:
        self.parser = PromptParser()
        self.integrator = ContentIntegrator()
        self.generator = LectureGenerator()
        self.validator = Validator()

    def build(
        self,
        user_prompt: str,
        file_contents: list[str],
        training_type: str
    ) -> dict:
        """完整构建流程"""
        # Step 1: 解析 user_prompt
        parsed = self.parser.parse(user_prompt)

        # Step 2: 内容融合
        integrated = self.integrator.integrate(parsed, file_contents)

        # Step 3: AI 生成讲义
        content = self.generator.generate(parsed, integrated)

        # Step 4: 校验
        validation_report = self.validator.validate(content, parsed)

        # 构建输出
        return {
            "content": content,
            "user_prompt_params": {
                "topic": parsed.topic,
                "training_type": training_type,
                "audience": parsed.audience,
                "position": parsed.position,
                "industry": parsed.industry,
                "objectives": parsed.objectives,
                "special_requirements": parsed.special_requirements,
                "forbidden_content": parsed.forbidden_content,
                "num_modules": parsed.num_modules,
                "estimated_duration": parsed.duration,
                "style": parsed.style
            },
            "outline": parsed.outline_structure,
            "validation_report": {
                "prompt_match_score": validation_report.prompt_match_score,
                "coverage_score": validation_report.coverage_score,
                "compliance_score": validation_report.compliance_score,
                "practical_score": validation_report.practical_score,
                "structure_score": validation_report.structure_score,
                "overall_score": validation_report.overall_score,
                "issues": validation_report.issues,
                "suggestions": validation_report.suggestions
            },
            "knowledge_points": [],
            "metadata": {"version": "1.0.0"}
        }
