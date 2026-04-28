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
        training_type: str,
        output_format: str = "lecture"
    ) -> dict:
        """完整构建流程"""
        # Step 1: 解析 user_prompt
        parsed = self.parser.parse(user_prompt)

        # Step 2: 内容融合
        integrated = self.integrator.integrate(parsed, file_contents)

        # Step 3: AI 生成讲义（传入 training_type 用于选择内容模板）
        content = self.generator.generate(parsed, integrated, training_type, output_format)

        # Step 4: 校验
        validation_report = self.validator.validate(content, parsed, training_type)

        # 构建输出
        return {
            "content": content,
            "user_prompt_params": {
                "topic": parsed.topic,
                "training_type": training_type,
                "audience": parsed.audience,
                "position": parsed.position,
                "industry": parsed.industry,
                "description": parsed.description,
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
            # 知识点提取需要 AI 深度分析，当前版本暂未实现
            # TODO: 实现知识点头部生成器，从 content 中提取知识点
            "knowledge_points": [],
            "case_library": integrated.case_library,
            "supplementary_materials": integrated.supplementary_materials,
            "metadata": {"version": "1.0.0"}
        }
