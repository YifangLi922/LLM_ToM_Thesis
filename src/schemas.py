"""Pydantic 数据模型（对应 generator guideline v1.1）。

分三类：
1. KnowledgeRecord           —— 知识库的一行（锁定输入，不允许造题模型改动）。
2. ProposeBundlesOutput / GenerateFamilyOutput —— 造题 LLM 的两种输出，字段与 guideline v1.1 的 A7 / B5 对齐。
   这两个模型会被转成 JSON Schema 交给 OpenAI Structured Outputs（strict 模式），因此刻意遵守：
   - 所有对象 extra="forbid"（=> additionalProperties:false），所有字段都是必填键（可空用 `X | None`）；
   - 不使用 default / minLength / minItems / const 等 strict 模式可能不支持的关键字；
   - 需要"非空""至少一个"等约束时，用 Python 校验器实现（校验器不会出现在 JSON Schema 里）；
   - 每个字段的 `description` 会进入 schema：v1.1 的 Part A 没有逐字段说明 propose_bundles 的输出，字段含义靠这里。
3. CandidateRecord           —— 流水线自己的主记录（candidates.jsonl 的一行）。

v1.1 相对 v1.0 的字段变化：agent -> agent_name；新增 setting_domain；belief_sentence_* -> belief_proposition_*
（代码负责拼出固定的解释句）；risk_flags 改为 13 个值的受控词表 + 单个 risk_notes；删除 potential_ambiguities / notes；
revision_reasons -> failure_reason。旧版 (v1.0) 的原始输出保留在 datasets/generation_v1.0/，不迁移、不覆盖。
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

# --------------------------------------------------------------------------- 枚举（来自 guideline v1.1）
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
# guideline B1：受控的场景域；只能通过带版本的代码改动来扩充。
SettingDomain = Literal[
    "education_training", "museum_exhibition", "community_volunteering", "workplace_operations",
    "arts_media", "hobbies_games", "environment_weather", "travel_cultural_orientation",
    "events_planning", "technical_workshop",
]
# guideline A7：受控的 risk_flags 词表（13 个）。
RiskFlag = Literal[
    "agent_prior_knowledge_risk", "source_acceptance_ambiguity", "source_vs_belief_ambiguity",
    "action_ambiguity", "q2_copy_shortcut", "q2_non_tom_difficulty", "overconstrained_story",
    "unnatural_redundancy", "q3_answer_leakage", "world_fact_scope_risk", "template_task_mismatch",
    "near_duplicate_structure", "implicit_belief_leakage",
]
# 名字分组（仅为抽样与让故事代词自然一致的技术性分组；见 guideline B1 的 Implementation note）。
NamePoolGroup = Literal["masculine", "feminine"]
Condition = Literal["implicit_aligned", "implicit_conflicting", "explicit_aligned", "explicit_conflicting"]
QuestionType = Literal["Q0", "Q1", "Q2", "Q3"]

CONDITIONS: tuple[str, ...] = ("implicit_aligned", "implicit_conflicting", "explicit_aligned", "explicit_conflicting")
SETTING_DOMAINS: tuple[str, ...] = SettingDomain.__args__  # type: ignore[attr-defined]
RISK_FLAGS: tuple[str, ...] = RiskFlag.__args__  # type: ignore[attr-defined]
# pilot 12 条知识库的类别分布（knowledge_pool_pilot_12_v1.jsonl）
EXPECTED_CATEGORY_COUNTS = {
    "basic_biology_category": 3,
    "basic_physics_causal": 3,
    "object_functions_properties": 2,
    "social_institutional_conventions": 4,
}
# guideline A7：生成模型永远不得输出 validated / approved / human_gold_confirmed
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
    """一个 knowledge–action bundle（guideline A5 的兼容性闸门：写故事之前先把行动设计清楚）。"""
    bundle_id: NonEmptyStr = Field(description="Short id such as B01.")
    suggested_template_ids: list[TemplateId] = Field(
        description="Compatible framework ids. If a template is assigned by the caller, exactly that one id.")
    agent_goal: NonEmptyStr = Field(description="The agent's practical goal.")
    new_task: NonEmptyStr = Field(
        description="A NEW task, distinct from the information encounter (not a copy of the source).")
    action_constraints: NonEmptyStr = Field(
        description="Constraints/resources from which the gold follows; no hidden rule or extra event. "
                    "Never a list of candidate actions or values, and no if-then decision rules (A8).")
    action_type: ActionType
    reasoning_structure: ReasoningStructure
    target_output: NonEmptyStr = Field(description="The single specific action/output/parameter Q2 will ask for.")
    aligned_action_gold: NonEmptyStr = Field(description="Intended Q2 answer if the agent holds the aligned (true) belief.")
    conflicting_action_gold: NonEmptyStr = Field(
        description="Intended Q2 answer if the agent holds the conflicting (false) belief; must differ from the aligned gold.")
    belief_to_action_rule: NonEmptyStr = Field(
        description="Brief metadata rule showing how each belief plus the constraints yields its gold (not shown in the story).")
    risk_flags: list[RiskFlag] = Field(
        description="Zero or more distinct values from the controlled vocabulary; only for concrete risks.")
    risk_notes: str = Field(
        description="One free-text string explaining each flagged risk specifically; empty string if no flags.")

    @model_validator(mode="after")
    def _check(self) -> "Bundle":
        if not self.suggested_template_ids:
            raise ValueError("suggested_template_ids 至少要有一个模板")
        return self


class ProposeBundlesOutput(StrictModel):
    task_mode: str = Field(description="Must be 'propose_bundles'.")
    fact_id: NonEmptyStr
    status: Literal["candidates_proposed", "no_valid_bundle"]
    bundles: list[Bundle]
    failure_reason: str | None = Field(
        description="null when candidates_proposed; a substantive reason when no_valid_bundle.")

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
    """status=candidate_generated 时所有内容字段必填、failure_reason 为 null；
    status=needs_revision 时内容字段可为 null，但必须给出具体的 failure_reason。"""
    task_mode: str = Field(description="Must be 'generate_family'.")
    fact_id: NonEmptyStr
    bundle_id: NonEmptyStr
    status: Literal["candidate_generated", "needs_revision"]
    template_id: TemplateId | None
    agent_name: NonEmptyStr | None = Field(description="Exactly the assigned agent_name.")
    setting_domain: SettingDomain | None = Field(description="Exactly the assigned setting_domain.")
    setting: NonEmptyStr | None = Field(
        description="The assigned setting_label if given, else one specific natural setting within the assigned domain.")
    source_type: NonEmptyStr | None
    belief_cue_ids: list[BeliefCue] = Field(description="Zero, one or two cue ids; [] when needs_revision.")
    action_type: ActionType | None
    reasoning_structure: ReasoningStructure | None
    story_backbone: NonEmptyStr | None = Field(
        description="Shared story with exactly one {{CLAIM_SPAN}} and one {{BELIEF_INSERTION}} "
                    "(directly after the sentence containing the claim).")
    claim_span_aligned: NonEmptyStr | None
    claim_span_conflicting: NonEmptyStr | None
    belief_proposition_aligned: NonEmptyStr | None = Field(
        description="Affirmative finite-clause complement: no initial 'that', no agent name, no final punctuation.")
    belief_proposition_conflicting: NonEmptyStr | None = Field(
        description="Affirmative finite-clause complement: no initial 'that', no agent name, no final punctuation.")
    belief_question: NonEmptyStr | None
    action_question: NonEmptyStr | None
    reality_question: NonEmptyStr | None
    proposed_gold: ProposedGold | None
    answer_variants: AnswerVariants | None
    action_constraints: NonEmptyStr | None
    belief_to_action_rule: NonEmptyStr | None
    risk_flags: list[RiskFlag] = Field(
        description="Zero or more distinct values from the controlled vocabulary; only for concrete risks.")
    risk_notes: str = Field(
        description="One free-text string explaining each flagged risk specifically; empty string if no flags.")
    validation_status: str | None = Field(description="Exactly 'needs_human_review' when candidate_generated, else null.")
    failure_reason: str | None = Field(
        description="null when candidate_generated; the concrete reason when needs_revision.")

    @model_validator(mode="after")
    def _check(self) -> "GenerateFamilyOutput":
        if self.task_mode != "generate_family":
            raise ValueError("task_mode 必须是 'generate_family'")
        if self.status == "needs_revision":
            if not (self.failure_reason and self.failure_reason.strip()):
                raise ValueError("needs_revision 必须在 failure_reason 里给出具体原因")
            return self
        required = [
            "template_id", "agent_name", "setting_domain", "setting", "source_type", "action_type",
            "reasoning_structure", "story_backbone", "claim_span_aligned", "claim_span_conflicting",
            "belief_proposition_aligned", "belief_proposition_conflicting",
            "belief_question", "action_question", "reality_question",
            "proposed_gold", "answer_variants", "action_constraints", "belief_to_action_rule",
        ]
        missing = [f for f in required if getattr(self, f) is None]
        if missing:
            raise ValueError(f"status=candidate_generated 时这些字段不能为 null: {missing}")
        if self.failure_reason is not None and self.failure_reason.strip():
            raise ValueError("status=candidate_generated 时 failure_reason 必须为 null")
        if len(self.belief_cue_ids) > 2:
            raise ValueError("belief_cue_ids 最多两个 (guideline A4)")
        if self.validation_status != LLM_VALIDATION_STATUS:
            raise ValueError(
                f"validation_status 必须是 {LLM_VALIDATION_STATUS!r}"
                "（生成模型不得自称 validated / approved / human_gold_confirmed）"
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
    qualification_notes: str
    source_urls: list[str]
    fact_status: str


class Provenance(StrictModel):
    generator_model: str
    prompt_version: str          # 发给造题模型的 prompt（generator_model_prompt_v1_1.md + 补充说明）的 SHA-256
    guideline_version: str       # 如 "1.1"
    schema_version: str
    created_at: str              # ISO 8601，由脚本写入
    task_mode: str
    notes: str | None
    # 抽样器分配（模板 / 名字 / 名字分组 / 场景域 / 种子 …），便于复现与审计
    assignments: dict[str, str | int | None] | None = None


class LeakHit(StrictModel):
    """Q3 答案泄漏扫描的一条命中（guideline B4）。子串命中只是"需要复核"的触发条件，不是泄漏的证明。
    category：
      aligned_source_claim     —— 出现在 aligned 的来源声明里：设计上必然，仅记录；
      conflicting_source_claim —— 出现在锁定的 conflicting 声明里：需要标记风险，但不改知识库；
      elsewhere                —— 出现在声明以外的公共文字里：可能是意外泄漏，需人工复核。"""
    term: str
    category: Literal["aligned_source_claim", "conflicting_source_claim", "elsewhere"]
    where: str      # claim_span_aligned / claim_span_conflicting / story_shared_text / belief_question / action_question


DesignTag = Literal["open_numeric", "open_other", "inherently_binary", "forced_binary_options"]


class CandidateRecord(StrictModel):
    family_id: str
    fact_id: str
    bundle: Bundle
    template_id: TemplateId
    agent_name: str
    name_pool_group: NamePoolGroup | None
    setting_domain: SettingDomain
    setting: str
    source_type: str
    belief_cue_ids: list[BeliefCue]
    action_type: ActionType
    reasoning_structure: ReasoningStructure
    story_backbone: str
    claim_span_aligned: str
    claim_span_conflicting: str
    belief_proposition_aligned: str
    belief_proposition_conflicting: str
    questions: Questions
    proposed_gold: ProposedGold
    answer_variants: AnswerVariants
    risk_flags: list[RiskFlag]
    risk_notes: str
    variants: Variants | None    # 渲染失败（占位符错误等）时为 None
    # 行动设计标签（只做统计，不据此拒绝）：forced_binary_options = 故事里同时出现了 Q2 的两个竞争答案；
    # inherently_binary = Q2 答案就是事实本身的"对/错"两个选项；open_numeric = 数值；open_other = 其他开放式。
    design_tag: DesignTag
    q3_leakage_scan: list[LeakHit] = Field(default_factory=list)
    fact: FactSnapshot
    validation_status: Literal["needs_human_review", "auto_rejected"]
    # 自动检查永远不能把它设为 True；人工确认走后续里程碑里单独的、有记录的审查流程。
    human_validated: Literal[False]
    issues: list[Issue]
    provenance: Provenance
