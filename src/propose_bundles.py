"""Stage B：对一条事实调用造题模型，得到 knowledge–action bundles，并做初步兼容性检查与挑选。

场景域（setting_domain）由代码分配：先用抽样器给的初始域去 propose_bundles；若模型返回 no_valid_bundle
（场景域与事实/行动不兼容），由代码按确定性的备选顺序改派下一个域并记录，而不是让模型偷偷换域（guideline v1.1 B1）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from generation_prompts import load_model_prompt, propose_payload
from llm_client import CallResult, call_structured
from sampling import Assignment, AssignmentSampler
from schemas import Bundle, Issue, KnowledgeRecord, ProposeBundlesOutput
from validate_candidates import check_bundle, check_propose_output, has_errors


@dataclass
class ProposeResult:
    call: CallResult
    issues: list[Issue]                      # 整体检查结果（含各 bundle 的 issue）
    per_bundle_issues: dict[str, list[Issue]]


@dataclass
class DomainAttempt:
    domain: str
    attempt: int
    result: ProposeResult


def run_propose(
    client, *, model: str, fact: KnowledgeRecord, max_bundles: int, max_output_tokens: int, max_retries: int,
    template_id: str | None = None, action_type: str | None = None, reasoning_structure: str | None = None,
    setting_domain: str | None = None, setting_label: str | None = None,
) -> ProposeResult:
    call = call_structured(
        client, model=model, instructions=load_model_prompt(),
        user_payload=propose_payload(fact, max_bundles=max_bundles, template_id=template_id,
                                     action_type=action_type, reasoning_structure=reasoning_structure,
                                     setting_domain=setting_domain, setting_label=setting_label),
        schema_model=ProposeBundlesOutput, schema_name="propose_bundles_output",
        max_output_tokens=max_output_tokens, max_retries=max_retries,
    )
    if not call.ok:
        return ProposeResult(call, [], {})
    out: ProposeBundlesOutput = call.parsed  # type: ignore[assignment]
    issues = check_propose_output(out, fact, max_bundles=max_bundles)
    per = {b.bundle_id: check_bundle(b, fact) for b in out.bundles}
    if template_id is not None:
        for b in out.bundles:
            if b.suggested_template_ids != [template_id]:
                per[b.bundle_id].append(Issue(severity="warning", code="template_assignment_ignored",
                                              message=f"bundle {b.bundle_id}: 请求指定 {template_id}，实际建议 {b.suggested_template_ids}"))
    return ProposeResult(call, issues, per)


def propose_with_domain_fallback(
    client, *, sampler: AssignmentSampler, assignment: Assignment, max_domain_reassignments: int,
    **propose_kwargs,
) -> tuple[Assignment, list[DomainAttempt]]:
    """按 domain_order 依次尝试场景域，直到得到 candidates_proposed（或 API 层失败 / 用完改派次数）。

    返回 (最终使用的分配, 每次尝试的记录)。只有"模型合规地返回 no_valid_bundle"才会改派；API 失败不改派。"""
    order = sampler.domain_order(assignment.index)
    attempts: list[DomainAttempt] = []
    current = assignment
    for k in range(0, max_domain_reassignments + 1):
        if k >= len(order):
            break
        current = assignment.with_domain(order[k], k)
        res = run_propose(client, setting_domain=current.setting_domain, **propose_kwargs)
        attempts.append(DomainAttempt(domain=current.setting_domain, attempt=k, result=res))
        if not res.call.ok:
            break
        if res.call.parsed.status == "candidates_proposed":  # type: ignore[union-attr]
            break
    return current, attempts


def select_bundle(out: ProposeBundlesOutput, per_bundle_issues: dict[str, list[Issue]]) -> tuple[Bundle | None, str]:
    """MVP 的挑选规则（确定性、可解释）：排除有 error 的 bundle，其余取 warning 最少者，并列取先提出的。
    二选一设计只记录为 warning，不再单独降权。返回 (bundle, 挑选理由)。这只是自动初筛，最终仍需研究者人工判断。"""
    viable = [(sum(i.severity == "warning" for i in per_bundle_issues[b.bundle_id]), idx, b)
              for idx, b in enumerate(out.bundles) if not has_errors(per_bundle_issues[b.bundle_id])]
    if not viable:
        return None, "所有 bundle 都未通过硬检查，没有可选项"
    n_warn, _, best = min(viable, key=lambda t: (t[0], t[1]))
    return best, (f"自动选择 {best.bundle_id}：在 {len(viable)}/{len(out.bundles)} 个通过硬检查的 bundle 中，"
                  f"取 warning 最少（{n_warn} 个），并列取先提出者。")
