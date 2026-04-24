from dataclasses import dataclass, field
from typing import Literal

TrainingType = Literal["product", "compliance", "sales_skill"]
StyleType = Literal["实操导向", "专业严谨", "口语化"]


@dataclass(frozen=True)
class ParsedPrompt:
    topic: str
    audience: str
    position: str
    industry: str
    duration: str
    style: StyleType
    objectives: list[str]
    special_requirements: list[str]
    forbidden_content: list[str]
    num_modules: int
    outline_structure: dict


@dataclass(frozen=True)
class KnowledgePoint:
    id: str
    name: str
    content: str
    difficulty: int  # 1-5
    prerequisites: list[str]
    assessment_weight: float
    business_scenario: str


@dataclass(frozen=True)
class IntegratedContent:
    module_contents: dict
    case_library: list[dict]
    supplementary_materials: dict


@dataclass(frozen=True)
class ValidationReport:
    prompt_match_score: int
    coverage_score: int
    compliance_score: int
    practical_score: int
    structure_score: int
    overall_score: int
    issues: list[str]
    suggestions: list[str]


@dataclass(frozen=True)
class LectureOutput:
    content: str
    user_prompt_params: dict
    outline: dict
    validation_report: ValidationReport
    knowledge_points: list[KnowledgePoint]
    metadata: dict
