"""Stage C：对选中的 bundle 调用造题模型生成一个 story backbone 及 Q1–Q3，然后交给确定性代码渲染与检查。"""
from __future__ import annotations

from candidates import build_candidate
from generation_prompts import generate_payload, load_guideline, prompt_version
from llm_client import CallResult, call_structured
from schemas import Bundle, CandidateRecord, GenerateFamilyOutput, KnowledgeRecord


def run_generate(
    client, *, model: str, fact: KnowledgeRecord, bundle: Bundle, template_id: str,
    max_output_tokens: int, max_retries: int,
) -> CallResult:
    return call_structured(
        client, model=model, instructions=load_guideline(),
        user_payload=generate_payload(fact, bundle, template_id=template_id),
        schema_model=GenerateFamilyOutput, schema_name="generate_family_output",
        max_output_tokens=max_output_tokens, max_retries=max_retries,
    )


def to_candidate(
    call: CallResult, *, family_id: str, fact: KnowledgeRecord, bundle: Bundle, generator_model: str, notes: str | None,
) -> CandidateRecord | None:
    """call 成功且 status=candidate_generated 时组装主记录；否则返回 None（失败原因在 call / 输出里）。"""
    if not call.ok or call.parsed is None:
        return None
    out: GenerateFamilyOutput = call.parsed  # type: ignore[assignment]
    if out.status != "candidate_generated":
        return None
    return build_candidate(family_id=family_id, fact=fact, bundle=bundle, family_out=out,
                           generator_model=generator_model, prompt_version=prompt_version(), notes=notes)
