"""Pydantic 数据模型。

分三类：
1. KnowledgeRecord           —— knowledge_pool.jsonl 的一行（锁定输入，不允许造题模型改动）。
2. ProposeBundlesOutput / GenerateFamilyOutput —— 造题 LLM 的两种输出，字段与 guideline §10 对齐。
   这两个模型会被转成 JSON Schema 交给 OpenAI Structured Outputs（strict 模式），因此刻意遵守：
   - 所有对象 extra="forbid"（=> additionalProperties:false），所有字段都是必填键（可空用 `X | None`）；
   - 不使用 default / minLength / minItems / const 等 strict 模式可能不支持的关键字；
   - 需要"非空""至少一个"等约束时，用 Python 校验器实现（校验器不会出现在 JSON Schema 里）。
3. CandidateRecord           —— 流水线自己的主记录（candidates.jsonl 的一行）。
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, model_validator

# --------------------------------------------------------------------------- 枚举（来自 guideline）
TemplateId = Literal["T1", "T2", "T3", "T4A", "T4C", "T5"]
ActionType = Literal["A1", "A2", "A3", "A4", "A5"]
ReasoningStructure = Literal[
    "direct_copy", "one_step_mapping", "simple_calculation",
    "procedure_selection", "prediction_application", "targeted_revision",
]
BeliefCue = Literal["B1", "B2", "B3", "B4", "B5", "B6"]
KnowledgeCategory = Literal[
    "basic_biology_category", "basic_physics_causal",
    "object_functions_properties", "social_institutional_conventions",
]
Condition = Literal["implicit_aligned", "implicit_conflicting", "explicit_aligned", "explicit_conflicting"]
QuestionType = Literal["Q0", "Q1", "Q2", "Q3"]

CONDITIONS: tuple[str, ...] = ("implicit_aligned", "implicit_conflicting", "explicit_aligned", "explicit_conflicting")
EXPECTED_CATEGORY_COUNTS = {  # 任务书：9 / 9 / 6 / 6
    "basic_biology_category": 9,
    "basic_physics_causal": 9,
    "object_functions_properties": 6,
    "social_institutional_conventions": 6,
}
# guideline §10：生成模型永远不得输出 validated / human_gold_confirmed
LLM_VALIDATION_STATUS = "needs_human_review"
FACT_STATUS_PENDING = "candidate_pending_researcher_signoff"


def _nonempty(v: str) -> str:
    if not v or not v.strip():
        raise ValueError("字符串不能为空")
    return v


NonEmptyStr = Annotated[str, AfterValidator(_nonempty)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Issue(StrictModel):
    """一条检查结果。error 会使候选被拒绝；warning 只提示人工审查。"""
    severity: Literal["error", "warning"]
    code: str
    message: str


def err(code: str, message: str) -> Issue:
    return Issue(severity="error", code=code, message=message)


def warn(code: str, message: str) -> Issue:
    return Issue(severity="warning", code=code, message=message)


# --------------------------------------------------------------------------- 1. 知识记录
class KnowledgeRecord(StrictModel):
    fact_id: str
    knowledge_category: KnowledgeCategory
    world_fact: NonEmptyStr
    aligned_claim: NonEmptyStr
    conflicting_claim: NonEmptyStr
    world_gold: NonEmptyStr
    conflicting_belief_gold: NonEmptyStr
    pretest_question: NonEmptyStr
    pretest_accepted_answers: list[NonEmptyStr]
    qualification_notes: NonEmptyStr
    source_urls: list[NonEmptyStr]
    review_flags: list[str]
    fact_status: NonEmptyStr

    @model_validator(mode="after")
    def _check(self) -> "KnowledgeRecord":
        import re

        if not re.fullmatch(r"K\d{2}", self.fact_id):
            raise ValueError(f"fact_id 格式应为 K 加两位数字，实际为 {self.fact_id!r}")
        if not self.pretest_accepted_answers:
            raise ValueError("pretest_accepted_answers 不能为空")
        if not self.source_urls:
            raise ValueError("source_urls 不能为空")
        for u in self.source_urls:
            if not u.startswith(("http://", "https://")):
                raise ValueError(f"source_urls 含非 http(s) 地址: {u!r}")
        if self.aligned_claim.strip() == self.conflicting_claim.strip():
            raise ValueError("aligned_claim 与 conflicting_claim 不能相同")
        if self.world_gold.strip().lower() == self.conflicting_belief_gold.strip().lower():
            raise ValueError("world_gold 与 conflicting_belief_gold 不能相同")
        return self


# --------------------------------------------------------------------------- 2a. propose_bundles 输出
class Bundle(StrictModel):
    bundle_id: NonEmptyStr
    suggested_template_ids: list[TemplateId]
    agent_goal: NonEmptyStr
    new_task: NonEmptyStr
    action_constraints: NonEmptyStr
    action_type: ActionType
    reasoning_structure: ReasoningStructure
    target_output: NonEmptyStr
    aligned_action_gold: NonEmptyStr
    conflicting_action_gold: NonEmptyStr
    belief_to_action_rule: NonEmptyStr
    potential_ambiguities: list[str]
    risk_flags: list[str]

    @model_validator(mode="after")
    def _check(self) -> "Bundle":
        if not self.suggested_template_ids:
            raise ValueError("suggested_template_ids 至少要有一个模板")
        return self


class ProposeBundlesOutput(StrictModel):
    task_mode: str
    fact_id: NonEmptyStr
    status: Literal["candidates_proposed", "no_valid_bundle"]
    bundles: list[Bundle]
    failure_reason: str | None

    @model_validator(mode="after")
    def _check(self) -> "ProposeBundlesOutput":
        if self.task_mode != "propose_bundles":
            raise ValueError("task_mode 必须是 'propose_bundles'")
        if self.status == "candidates_proposed":
            if not self.bundles:
                raise ValueError("status=candidates_proposed 时 bundles 不能为空")
        else:
            if self.bundles:
                raise ValueError("status=no_valid_bundle 时 bundles 必须为空")
            if not (self.failure_reason and self.failure_reason.strip()):
                raise ValueError("no_valid_bundle 必须给出实质性的 failure_reason")
        return self


# --------------------------------------------------------------------------- 2b. generate_family 输出
class GoldPair(StrictModel):
    q1: NonEmptyStr
    q2: NonEmptyStr


class ProposedGold(StrictModel):
    aligned: GoldPair
    conflicting: GoldPair
    q3: NonEmptyStr


class AnswerVariants(StrictModel):
    """guideline 示例里是一个 dict；strict 模式不支持任意键的 dict，所以展开成固定键。"""
    q1_aligned: list[str]
    q1_conflicting: list[str]
    q2_aligned: list[str]
    q2_conflicting: list[str]
    q3: list[str]


class GenerateFamilyOutput(StrictModel):
    """status=candidate_generated 时所有内容字段必填；status=needs_revision 时内容字段可为 null，
    但必须在 revision_reasons 里给出具体原因（revision_reasons 是相对 guideline 示例新增的唯一字段）。"""
    task_mode: str
    fact_id: NonEmptyStr
    bundle_id: NonEmptyStr
    status: Literal["candidate_generated", "needs_revision"]
    template_id: TemplateId | None
    agent: NonEmptyStr | None
    setting: NonEmptyStr | None
    source_type: NonEmptyStr | None
    belief_cue_ids: list[BeliefCue]
    action_type: ActionType | None
    reasoning_structure: ReasoningStructure | None
    story_backbone: NonEmptyStr | None
    claim_span_aligned: NonEmptyStr | None
    claim_span_conflicting: NonEmptyStr | None
    belief_sentence_aligned: NonEmptyStr | None
    belief_sentence_conflicting: NonEmptyStr | None
    belief_question: NonEmptyStr | None
    action_question: NonEmptyStr | None
    reality_question: NonEmptyStr | None
    proposed_gold: ProposedGold | None
    answer_variants: AnswerVariants | None
    action_constraints: NonEmptyStr | None
    belief_to_action_rule: NonEmptyStr | None
    risk_flags: list[str]
    potential_ambiguities: list[str]
    validation_status: str | None
    notes: str | None
    revision_reasons: list[str]

    @model_validator(mode="after")
    def _check(self) -> "GenerateFamilyOutput":
        if self.task_mode != "generate_family":
            raise ValueError("task_mode 必须是 'generate_family'")
        if self.status == "needs_revision":
            if not any(r.strip() for r in self.revision_reasons):
                raise ValueError("needs_revision 必须在 revision_reasons 里给出具体原因")
            return self
        required = [
            "template_id", "agent", "setting", "source_type", "action_type", "reasoning_structure",
            "story_backbone", "claim_span_aligned", "claim_span_conflicting",
            "belief_sentence_aligned", "belief_sentence_conflicting",
            "belief_question", "action_question", "reality_question",
            "proposed_gold", "answer_variants", "action_constraints", "belief_to_action_rule",
        ]
        missing = [f for f in required if getattr(self, f) is None]
        if missing:
            raise ValueError(f"status=candidate_generated 时这些字段不能为 null: {missing}")
        if len(self.belief_cue_ids) > 2:
            raise ValueError("belief_cue_ids 最多两个 (guideline §4)")
        if self.validation_status != LLM_VALIDATION_STATUS:
            raise ValueError(
                f"validation_status 必须是 {LLM_VALIDATION_STATUS!r}"
                "（生成模型不得自称 validated / human_gold_confirmed）"
            )
        return self


# --------------------------------------------------------------------------- 3. 流水线主记录
class Variants(StrictModel):
    implicit_aligned: str
    implicit_conflicting: str
    explicit_aligned: str
    explicit_conflicting: str

    def as_dict(self) -> dict[str, str]:
        return {c: getattr(self, c) for c in CONDITIONS}


class Questions(StrictModel):
    q1: str
    q2: str
    q3: str


class FactSnapshot(StrictModel):
    """记录生成当时引用的锁定事实，便于追溯（Q0 另在 pretest_questions 里按 fact 导出一次）。"""
    fact_id: str
    world_fact: str
    aligned_claim: str
    conflicting_claim: str
    world_gold: str
    conflicting_belief_gold: str
    pretest_question: str
    source_urls: list[str]
    fact_status: str


class Provenance(StrictModel):
    generator_model: str
    prompt_version: str          # guideline 文件 SHA-256
    schema_version: str
    created_at: str              # ISO 8601，由脚本写入
    task_mode: str
    notes: str | None


class CandidateRecord(StrictModel):
    family_id: str
    fact_id: str
    bundle: Bundle
    template_id: TemplateId
    agent: str
    setting: str
    source_type: str
    belief_cue_ids: list[BeliefCue]
    action_type: ActionType
    reasoning_structure: ReasoningStructure
    story_backbone: str
    claim_span_aligned: str
    claim_span_conflicting: str
    belief_sentence_aligned: str
    belief_sentence_conflicting: str
    questions: Questions
    proposed_gold: ProposedGold
    answer_variants: AnswerVariants
    risk_flags: list[str]
    potential_ambiguities: list[str]
    variants: Variants | None    # 渲染失败（占位符错误等）时为 None
    fact: FactSnapshot
    validation_status: Literal["needs_human_review", "auto_rejected"]
    # 自动检查永远不能把它设为 True；人工确认走后续里程碑里单独的、有记录的审查流程。
    human_validated: Literal[False]
    issues: list[Issue]
    provenance: Provenance
