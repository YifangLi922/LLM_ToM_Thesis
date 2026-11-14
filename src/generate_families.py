"""Stage C：对选中的 bundle 调用造题模型生成一个 story backbone 及 Q1–Q3，然后交给确定性代码渲染与检查。

若候选被自动检查拒绝（error），最多重新生成 `max_regenerations` 次，并把具体问题作为 revision_feedback 反馈给模型。
每一次尝试的原始响应都会保留；最终只有最后一次尝试会成为该 family 的主记录。
"""
from __future__ import annotations

from dataclasses import dataclass

from candidates import build_candidate
from generation_prompts import generate_payload, load_model_prompt, prompt_version
from llm_client import ERR_API, CallResult, call_structured
from sampling import Assignment
from schemas import Bundle, CandidateRecord, GenerateFamilyOutput, Issue, KnowledgeRecord

# 给模型看的英文修改意见（按检查代码）；没有登记的代码给通用提示。
FEEDBACK_EN = {
    "agent_mismatch": "Set `agent_name` to exactly the name in assignments.agent_name.",
    "agent_not_in_story": "The protagonist named in assignments.agent_name must appear in the story.",
    "setting_domain_mismatch": "Set `setting_domain` to exactly assignments.setting_domain and keep the story in that domain.",
    "template_mismatch": "template_id must equal assignments.template_id, and the story must follow that framework.",
    "belief_not_after_sentence": ("{{BELIEF_INSERTION}} must come directly after the complete sentence containing "
                                  "{{CLAIM_SPAN}} (including its final punctuation, without doubling it)."),
    "story_too_long": ("The story backbone (including the claim span) exceeds the hard limit of 110 words. Cut constraints "
                       "and background first; keep it a natural few-sentence anecdote."),
    "claim_span_not_locked_claim": (
        "Each claim span must restate the locked aligned_claim / conflicting_claim itself (same content and qualifiers, "
        "same wording as far as the grammar allows). Do not replace it with an indirect or behavioural paraphrase, such "
        "as a routine or marking that merely implies the fact; a T4C routine may be described around the claim, but the "
        "claim span itself must carry the locked claim."),
    "q2_gold_identical": "The two Q2 golds must differ.",
    "q1_gold_identical": "The two Q1 golds must differ.",
}
# render_failed 的原因是一串带代码的消息（占位符 / belief proposition 格式 / 插入点位置），把它原样给模型。
_RENDER_HINT = ("The backbone must contain {{CLAIM_SPAN}} and {{BELIEF_INSERTION}} exactly once each, with "
                "{{BELIEF_INSERTION}} directly after the sentence that contains {{CLAIM_SPAN}}; each belief proposition "
                "must be an affirmative clause without an initial 'that', without the agent's name at the start and "
                "without final punctuation. Details: ")


def feedback_for(issue: Issue) -> str:
    if issue.code == "render_failed":
        return _RENDER_HINT + issue.message
    return FEEDBACK_EN.get(issue.code, f"Automatic check failed: {issue.code}.")


@dataclass
class Attempt:
    number: int
    call: CallResult
    record: CandidateRecord | None
    feedback_given: list[str]


def run_generate(
    client, *, model: str, fact: KnowledgeRecord, bundle: Bundle, assignment: Assignment,
    max_output_tokens: int, max_retries: int, setting_label: str | None = None,
    revision_feedback: list[str] | None = None,
) -> CallResult:
    return call_structured(
        client, model=model, instructions=load_model_prompt(),
        user_payload=generate_payload(
            fact, bundle, template_id=assignment.template_id, agent_name=assignment.agent_name,
            agent_pronouns=assignment.pronouns, setting_domain=assignment.setting_domain,
            setting_label=setting_label, revision_feedback=revision_feedback),
        schema_model=GenerateFamilyOutput, schema_name="generate_family_output",
        max_output_tokens=max_output_tokens, max_retries=max_retries,
    )


def generate_with_regeneration(
    client, *, model: str, fact: KnowledgeRecord, bundle: Bundle, assignment: Assignment, family_id: str,
    max_output_tokens: int, max_retries: int, max_regenerations: int, notes: str | None,
    setting_label: str | None = None,
) -> list[Attempt]:
    """返回按顺序排列的所有尝试。最后一次尝试的 record 就是该 family 的结果（可能仍是 auto_rejected）。

    只有"模型产出了不合格的内容"才会触发重新生成；API 层错误（已在 call_structured 内重试过）、
    以及模型合规地返回 needs_revision，都不会重新生成。"""
    attempts: list[Attempt] = []
    feedback: list[str] = []
    for n in range(1, max_regenerations + 2):
        call = run_generate(client, model=model, fact=fact, bundle=bundle, assignment=assignment,
                            max_output_tokens=max_output_tokens, max_retries=max_retries,
                            setting_label=setting_label, revision_feedback=feedback)
        record = None
        if call.ok and call.parsed.status == "candidate_generated":  # type: ignore[union-attr]
            record = build_candidate(
                family_id=family_id, fact=fact, bundle=bundle, family_out=call.parsed,  # type: ignore[arg-type]
                generator_model=model, prompt_version=prompt_version(), assignment=assignment,
                notes=f"{notes or ''} | attempt {n}/{max_regenerations + 1}".strip(" |"),
            )
        attempts.append(Attempt(n, call, record, list(feedback)))

        if call.error_type == ERR_API:
            break                                                  # API 问题不是"重写"能解决的
        if call.ok and call.parsed.status == "needs_revision":     # type: ignore[union-attr]
            break                                                  # 合规的拒绝，不强迫模型硬写
        if record is not None and record.validation_status == "needs_human_review":
            break
        if record is not None:
            errors = [i for i in record.issues if i.severity == "error"]
            feedback = list(dict.fromkeys(feedback_for(i) for i in errors))
        else:
            feedback = [f"Your previous output was unusable ({call.error_type}). Return a complete, valid JSON object."]
    return attempts
