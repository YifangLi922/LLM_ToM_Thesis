"""把"锁定事实 + 选中的 bundle + 生成模型的 generate_family 输出"组装成流水线主记录（CandidateRecord）。

family_id / 时间戳 / prompt 版本 / 生成模型名都由脚本写入，而不是由 LLM 生成（guideline §10）。
被自动检查拒绝的候选同样会被保留（validation_status="auto_rejected"，并带完整 issues）。
"""
from __future__ import annotations

from datetime import datetime, timezone

from schemas import (
    Bundle, CandidateRecord, FactSnapshot, GenerateFamilyOutput, KnowledgeRecord, Provenance, Questions,
)
from sampling import Assignment
from validate_candidates import check_family_output, design_tag, has_errors

SCHEMA_VERSION = "m1-0.1"


def make_family_id(n: int) -> str:
    return f"F{n:03d}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def snapshot_fact(fact: KnowledgeRecord) -> FactSnapshot:
    return FactSnapshot(
        fact_id=fact.fact_id, world_fact=fact.world_fact, aligned_claim=fact.aligned_claim,
        conflicting_claim=fact.conflicting_claim, world_gold=fact.world_gold,
        conflicting_belief_gold=fact.conflicting_belief_gold, pretest_question=fact.pretest_question,
        source_urls=list(fact.source_urls), fact_status=fact.fact_status,
    )


def build_candidate(
    *,
    family_id: str,
    fact: KnowledgeRecord,
    bundle: Bundle,
    family_out: GenerateFamilyOutput,
    generator_model: str,
    prompt_version: str,
    created_at: str | None = None,
    notes: str | None = None,
    assignment: Assignment | None = None,
    binary_policy: str = "reject",
) -> CandidateRecord:
    """family_out.status 必须是 candidate_generated；needs_revision 没有可存的故事内容，
    应由调用方记入"尝试日志"（后续里程碑），而不是生成 CandidateRecord。"""
    if family_out.status != "candidate_generated":
        raise ValueError("needs_revision 的输出不能构建 CandidateRecord，请记录失败原因后重试/跳过")
    variants, issues = check_family_output(
        family_out, fact, bundle,
        expected_template=assignment.template_id if assignment else None,
        expected_agent=assignment.agent_name if assignment else None,
        expected_gender=assignment.agent_gender if assignment else None,
        binary_policy=binary_policy,
    )
    return CandidateRecord(
        family_id=family_id,
        fact_id=fact.fact_id,
        bundle=bundle,
        template_id=family_out.template_id,
        agent=family_out.agent,
        setting=family_out.setting,
        source_type=family_out.source_type,
        belief_cue_ids=family_out.belief_cue_ids,
        action_type=family_out.action_type,
        reasoning_structure=family_out.reasoning_structure,
        story_backbone=family_out.story_backbone,
        claim_span_aligned=family_out.claim_span_aligned,
        claim_span_conflicting=family_out.claim_span_conflicting,
        belief_sentence_aligned=family_out.belief_sentence_aligned,
        belief_sentence_conflicting=family_out.belief_sentence_conflicting,
        questions=Questions(
            q1=family_out.belief_question, q2=family_out.action_question, q3=family_out.reality_question,
        ),
        proposed_gold=family_out.proposed_gold,
        answer_variants=family_out.answer_variants,
        risk_flags=list(family_out.risk_flags),
        potential_ambiguities=list(family_out.potential_ambiguities),
        variants=variants,
        design_tag=design_tag(family_out, bundle),
        fact=snapshot_fact(fact),
        validation_status="auto_rejected" if has_errors(issues) or variants is None else "needs_human_review",
        human_validated=False,
        issues=issues,
        provenance=Provenance(
            generator_model=generator_model,
            prompt_version=prompt_version,
            schema_version=SCHEMA_VERSION,
            created_at=created_at or now_iso(),
            task_mode="generate_family",
            notes=notes,
            assignments=assignment.as_dict() if assignment else None,
        ),
    )
