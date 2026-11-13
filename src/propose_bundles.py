"""Stage B：对一条事实调用造题模型，得到 knowledge–action bundles，并做初步兼容性检查与挑选。"""
from __future__ import annotations

from dataclasses import dataclass

from generation_prompts import load_guideline, propose_payload
from llm_client import CallResult, call_structured
from schemas import Bundle, Issue, KnowledgeRecord, ProposeBundlesOutput
from validate_candidates import check_bundle, check_propose_output, has_errors


@dataclass
class ProposeResult:
    call: CallResult
    issues: list[Issue]                      # 整体检查结果（含各 bundle 的 issue）
    per_bundle_issues: dict[str, list[Issue]]


def run_propose(
    client, *, model: str, fact: KnowledgeRecord, max_bundles: int, max_output_tokens: int, max_retries: int,
    template_id: str | None = None, action_type: str | None = None, reasoning_structure: str | None = None,
) -> ProposeResult:
    call = call_structured(
        client, model=model, instructions=load_guideline(),
        user_payload=propose_payload(fact, max_bundles=max_bundles, template_id=template_id,
                                     action_type=action_type, reasoning_structure=reasoning_structure),
        schema_model=ProposeBundlesOutput, schema_name="propose_bundles_output",
        max_output_tokens=max_output_tokens, max_retries=max_retries,
    )
    if not call.ok:
        return ProposeResult(call, [], {})
    out: ProposeBundlesOutput = call.parsed  # type: ignore[assignment]
    issues = check_propose_output(out, fact, max_bundles=max_bundles)
    per = {b.bundle_id: check_bundle(b) for b in out.bundles}
    if template_id is not None:
        for b in out.bundles:
            if b.suggested_template_ids != [template_id]:
                per[b.bundle_id].append(Issue(severity="warning", code="template_assignment_ignored",
                                              message=f"bundle {b.bundle_id}: 请求指定 {template_id}，实际建议 {b.suggested_template_ids}"))
    return ProposeResult(call, issues, per)


def select_bundle(out: ProposeBundlesOutput, per_bundle_issues: dict[str, list[Issue]]) -> tuple[Bundle | None, str]:
    """MVP 的挑选规则（确定性、可解释）：排除有 error 的 bundle，其余取 warning 最少者，并列取先提出的。
    返回 (bundle, 挑选理由)。这只是自动初筛，最终仍需研究者人工判断。"""
    viable = [(sum(i.severity == "warning" for i in per_bundle_issues[b.bundle_id]), idx, b)
              for idx, b in enumerate(out.bundles) if not has_errors(per_bundle_issues[b.bundle_id])]
    if not viable:
        return None, "所有 bundle 都未通过硬检查，没有可选项"
    n_warn, _, best = min(viable, key=lambda t: (t[0], t[1]))
    return best, (f"自动选择 {best.bundle_id}：在 {len(viable)}/{len(out.bundles)} 个通过硬检查的 bundle 中 "
                  f"warning 最少（{n_warn} 个），并列时取先提出者。")
