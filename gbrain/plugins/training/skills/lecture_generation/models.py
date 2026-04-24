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


# 领域同义词映射表
SYNONYM_MAP: dict[str, list[str]] = {
    "电话": ["话术", "沟通技巧", "通话", "语音"],
    "销售": ["营销", "推销", "商务", "售卖"],
    "客户": ["顾客", "用户", "采购方", "买家"],
    "合同": ["合约", "协议", "契约"],
    "签署": ["签名", "签字", "签订", "签章"],
    "产品": ["商品", "服务", "解决方案"],
    "培训": ["训练", "学习", "教学"],
    "系统": ["平台", "软件", "工具"],
    "流程": ["步骤", "过程", "工序"],
    "规范": ["标准", "准则", "规程"],
}
