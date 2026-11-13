"""Stage B / D 的确定性硬检查。

返回 `list[Issue]`：severity="error" 的候选必须拒绝/重新生成（并保存原因）；
severity="warning" 只提示人工审查。这里**不**使用被测模型的任何回答来判断题目好坏，
也**永远不会**把任何东西标成 human_validated。
"""
from __future__ import annotations

import re
from collections import Counter

from common import answers_equivalent, contains_word, normalize_answer
from render_pairs import BELIEF_TOKEN, CLAIM_TOKEN, render_and_check
from schemas import (
    Bundle, GenerateFamilyOutput, Issue, KnowledgeRecord, ProposeBundlesOutput, Variants, err, warn,
)


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)


# --------------------------------------------------------------------------- Stage B：bundle
def check_bundle(bundle: Bundle) -> list[Issue]:
    """guideline §6 里能用代码判断的部分。语义部分（因果相关、是否有隐藏前提等）留给后续审查。"""
    issues: list[Issue] = []
    tag = f"bundle {bundle.bundle_id}"
    if answers_equivalent(bundle.aligned_action_gold, bundle.conflicting_action_gold):
        issues.append(err("action_gold_identical",
                          f"{tag}: aligned 与 conflicting 的行动答案相同 ({bundle.aligned_action_gold!r})，信念不改变行动"))
    if bundle.reasoning_structure == "direct_copy":
        issues.append(warn("direct_copy", f"{tag}: reasoning_structure=direct_copy，容易变成照抄而非应用 (guideline §5)"))
    if bundle.reasoning_structure == "simple_calculation" and "arithmetic_control_recommended" not in bundle.risk_flags:
        issues.append(warn("arithmetic_flag_missing", f"{tag}: 需要计算，但 risk_flags 没有记录算术难度"))
    return issues


def check_propose_output(
    out: ProposeBundlesOutput, fact: KnowledgeRecord, max_bundles: int | None = None
) -> list[Issue]:
    issues: list[Issue] = []
    if out.fact_id != fact.fact_id:
        issues.append(err("fact_id_mismatch", f"输出的 fact_id={out.fact_id} 与请求的 {fact.fact_id} 不一致"))
    if max_bundles is not None and len(out.bundles) > max_bundles:
        issues.append(err("too_many_bundles", f"返回 {len(out.bundles)} 个 bundle，超过上限 {max_bundles}"))
    dup = [b for b, n in Counter(b.bundle_id for b in out.bundles).items() if n > 1]
    if dup:
        issues.append(err("bundle_id_duplicate", f"bundle_id 重复: {dup}"))
    for b in out.bundles:
        issues += check_bundle(b)
    return issues


# --------------------------------------------------------------------------- Stage D：family
_Q3_BAD = re.compile(r"according to|\bthink|\bbelieve|\bexpect|\bthe guide\b|\bthe manual\b", re.IGNORECASE)
_BELIEF_WORDS = re.compile(r"\bbelieve|\bthinks?\b|\bassum", re.IGNORECASE)


def check_family_output(
    out: GenerateFamilyOutput, fact: KnowledgeRecord, bundle: Bundle | None = None
) -> tuple[Variants | None, list[Issue]]:
    """检查一个 generate_family 输出，并（若可能）渲染四版本。返回 (variants, issues)。"""
    issues: list[Issue] = []
    if out.status != "candidate_generated":
        return None, [err("needs_revision", "生成模型返回 needs_revision: " + "; ".join(out.revision_reasons))]

    # ---- ID 关联与事实锁定
    if out.fact_id != fact.fact_id:
        issues.append(err("fact_id_mismatch", f"输出的 fact_id={out.fact_id} 与请求的 {fact.fact_id} 不一致"))
    if bundle is not None:
        if out.bundle_id != bundle.bundle_id:
            issues.append(err("bundle_id_mismatch", f"输出 bundle_id={out.bundle_id} 与所选 {bundle.bundle_id} 不一致"))
        if out.action_type != bundle.action_type:
            issues.append(err("action_type_mismatch", f"action_type {out.action_type} 与 bundle 的 {bundle.action_type} 不一致"))
        if out.reasoning_structure != bundle.reasoning_structure:
            issues.append(err("reasoning_structure_mismatch",
                              f"reasoning_structure {out.reasoning_structure} 与 bundle 的 {bundle.reasoning_structure} 不一致"))
        if out.template_id not in bundle.suggested_template_ids:
            issues.append(warn("template_not_suggested", f"template_id={out.template_id} 不在 bundle 建议的 {bundle.suggested_template_ids} 中"))
        for label, got in [("aligned", out.proposed_gold.aligned.q2), ("conflicting", out.proposed_gold.conflicting.q2)]:
            want = bundle.aligned_action_gold if label == "aligned" else bundle.conflicting_action_gold
            if not answers_equivalent(got, want):
                issues.append(warn("q2_gold_differs_from_bundle", f"{label} 的 Q2 gold {got!r} 与 bundle 的 {want!r} 不同"))

    # ---- belief cues
    if len(set(out.belief_cue_ids)) != len(out.belief_cue_ids):
        issues.append(err("belief_cue_duplicate", f"belief_cue_ids 有重复: {out.belief_cue_ids}"))
    if not out.belief_cue_ids:
        issues.append(warn("no_belief_cue", "未选择任何 belief cue；guideline 要求给出具体理由"))

    # ---- gold
    g = out.proposed_gold
    if answers_equivalent(g.aligned.q1, g.conflicting.q1):
        issues.append(err("q1_gold_identical", f"aligned/conflicting 的 Q1 答案相同: {g.aligned.q1!r}"))
    if answers_equivalent(g.aligned.q2, g.conflicting.q2):
        issues.append(err("q2_gold_identical", f"aligned/conflicting 的 Q2 答案相同: {g.aligned.q2!r}"))
    # 与锁定事实的一致性：措辞可能合理不同，所以只给 warning
    if not answers_equivalent(g.q3, fact.world_gold):
        issues.append(warn("q3_vs_world_gold", f"Q3 gold {g.q3!r} 与事实库 world_gold {fact.world_gold!r} 不同，请人工确认"))
    if not answers_equivalent(g.aligned.q1, fact.world_gold):
        issues.append(warn("q1_aligned_vs_world_gold", f"aligned Q1 {g.aligned.q1!r} 与 world_gold {fact.world_gold!r} 不同"))
    if not answers_equivalent(g.conflicting.q1, fact.conflicting_belief_gold):
        issues.append(warn("q1_conflicting_vs_belief_gold",
                           f"conflicting Q1 {g.conflicting.q1!r} 与 conflicting_belief_gold {fact.conflicting_belief_gold!r} 不同"))
    av = out.answer_variants
    for name, lst in [("q1_aligned", av.q1_aligned), ("q1_conflicting", av.q1_conflicting),
                      ("q2_aligned", av.q2_aligned), ("q2_conflicting", av.q2_conflicting), ("q3", av.q3)]:
        if not lst:
            issues.append(warn("answer_variants_empty", f"answer_variants.{name} 为空，评分时没有同义写法可用"))

    # ---- 问题措辞（启发式，均为 warning）
    for name, q in [("belief_question", out.belief_question), ("action_question", out.action_question),
                    ("reality_question", out.reality_question)]:
        if not q.strip().endswith("?"):
            issues.append(warn("question_format", f"{name} 没有以问号结尾"))
        if re.search(r"\bor\b", q):
            issues.append(warn("question_has_alternatives", f"{name} 含 'or'，可能在提供备选项（应为开放式简答）"))
    if _Q3_BAD.search(out.reality_question) or (out.agent and contains_word(out.reality_question, out.agent)):
        issues.append(warn("q3_not_reality_directed", "reality_question 看起来在问来源/角色想法，应是纯现实问题"))
    if _BELIEF_WORDS.search(out.action_question):
        issues.append(warn("q2_cues_belief", "action_question 含 believe/think 等词，可能提示了目标信念"))
    if normalize_answer(out.claim_span_conflicting) in normalize_answer(out.belief_question):
        issues.append(warn("q1_direct_copy_risk", "belief_question 逐字包含了 conflicting claim，Q1 可能退化为照抄"))

    # ---- 答案泄漏到公共 backbone
    shared = out.story_backbone.replace(CLAIM_TOKEN, " ").replace(BELIEF_TOKEN, " ")
    for name, ans in [("Q2 aligned", g.aligned.q2), ("Q2 conflicting", g.conflicting.q2),
                      ("Q1 aligned", g.aligned.q1), ("Q1 conflicting", g.conflicting.q1)]:
        if contains_word(shared, ans):
            issues.append(warn("gold_in_backbone", f"{name} 的答案 {ans!r} 出现在 claim/belief 以外的公共文字里，可能泄漏答案"))

    # ---- 渲染与 minimal-pair 检查
    variants, pair_issues = render_and_check(
        out.story_backbone, out.claim_span_aligned, out.claim_span_conflicting,
        out.belief_sentence_aligned, out.belief_sentence_conflicting,
    )
    issues += pair_issues
    return variants, issues
