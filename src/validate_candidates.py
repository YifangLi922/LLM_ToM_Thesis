"""Stage B / D 的确定性硬检查（guideline v1.1 B4 的 "Code checks"）。

返回 `list[Issue]`：severity="error" 的候选必须拒绝/重新生成（并保存原因）；
severity="warning" 只提示人工审查。这里**不**使用被测模型的任何回答来判断题目好坏，
也**永远不会**把任何东西标成 human_validated。语义层面的审查（agent 先验知识、Q2 是否真由信念决定……）
留给人工/后续里程碑：代码里的子串命中只是"需要复核"的触发条件，不是证明。
"""
from __future__ import annotations

import re
from collections import Counter

from common import answers_equivalent, contains_word, normalize_answer
from render_pairs import BELIEF_TOKEN, CLAIM_TOKEN, render_and_check
from schemas import (
    Bundle, GenerateFamilyOutput, Issue, KnowledgeRecord, LeakHit, ProposeBundlesOutput, Variants, err, warn,
)


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)


# --------------------------------------------------------------------------- Stage B：bundle
_NO_CHANGE = {"no change", "none", "nothing", "no edit", "leave unchanged", "keep unchanged"}


def is_binary_design(bundle: Bundle, fact: KnowledgeRecord | None = None) -> bool:
    """bundle 是否本质上是"在两个竞争答案里选一个"：其中一个答案是"不改"，
    或 Q2 的两个答案恰好就是事实本身的"对 / 错"两个选项（world_gold / conflicting_belief_gold）。"""
    if (normalize_answer(bundle.aligned_action_gold) in _NO_CHANGE
            or normalize_answer(bundle.conflicting_action_gold) in _NO_CHANGE):
        return True
    return fact is not None and _is_fact_pair(bundle.aligned_action_gold, bundle.conflicting_action_gold, fact)


def _is_fact_pair(aligned_q2: str, conflicting_q2: str, fact: KnowledgeRecord) -> bool:
    return (answers_equivalent(aligned_q2, fact.world_gold)
            and answers_equivalent(conflicting_q2, fact.conflicting_belief_gold))


def check_bundle(bundle: Bundle, fact: KnowledgeRecord | None = None) -> list[Issue]:
    """guideline A5 里能用代码判断的部分。语义部分（因果相关、是否有隐藏前提等）留给后续审查。"""
    issues: list[Issue] = []
    tag = f"bundle {bundle.bundle_id}"
    if answers_equivalent(bundle.aligned_action_gold, bundle.conflicting_action_gold):
        issues.append(err("action_gold_identical",
                          f"{tag}: aligned 与 conflicting 的行动答案相同 ({bundle.aligned_action_gold!r})，信念不改变行动"))
    if len(set(bundle.risk_flags)) != len(bundle.risk_flags):
        issues.append(warn("risk_flag_duplicate", f"{tag}: risk_flags 有重复值（应为互不相同的枚举）"))
    if bundle.risk_flags and not bundle.risk_notes.strip():
        issues.append(warn("risk_notes_missing", f"{tag}: 标了 risk_flags 但 risk_notes 为空"))
    if is_binary_design(bundle, fact):
        issues.append(warn("binary_choice_design", f"{tag}: 行动本质上是在两个竞争答案中二选一（只记录，不拒绝）"))
    if bundle.reasoning_structure == "direct_copy":
        issues.append(warn("direct_copy", f"{tag}: reasoning_structure=direct_copy，容易变成照抄而非应用 (guideline A4)"))
    if bundle.reasoning_structure == "simple_calculation" and "q2_non_tom_difficulty" not in bundle.risk_flags:
        issues.append(warn("arithmetic_flag_missing", f"{tag}: 需要计算，但 risk_flags 没有 q2_non_tom_difficulty"))
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
        issues += check_bundle(b, fact)
    return issues


# --------------------------------------------------------------------------- Stage D：family
_Q3_BAD = re.compile(r"according to|\bthink|\bbelieve|\bexpect|\bthe guide\b|\bthe manual\b", re.IGNORECASE)
_BELIEF_WORDS = re.compile(r"\bbelieve|\bthinks?\b|\bassum", re.IGNORECASE)

# 名字分组决定代词（见 guideline v1.1 B1 的 Implementation note）：故事里出现"相反组"的代词只给 warning，
# 因为也可能指故事里的其他角色，需要人工确认。
_OPPOSITE_PRONOUNS = {
    "feminine": re.compile(r"\b(he|him|his|himself)\b", re.IGNORECASE),
    "masculine": re.compile(r"\b(she|her|hers|herself)\b", re.IGNORECASE),
}
_EITHER_OR = re.compile(r"\beither\b[^.?!]*\bor\b", re.IGNORECASE)

# guideline A8：故事里不得藏"选项菜单"、规则谜题或技术性免责声明。下面是简单的正则检查，命中只标记（warning），交人工判断。
STORY_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("pattern_exactly", re.compile(r"\bexactly\b", re.IGNORECASE),
     "含 'exactly'：常见于过度精确的技术性约束"),
    ("pattern_available_list", re.compile(
        r"\bavailable\s*:|\b(?:two|three|four|five|several|both)\b[^.?!]{0,40}\b(?:are|is)\s+available\b", re.IGNORECASE),
     "含 'available:' / 'two … are available'：可能把候选行动/数值列成了选项菜单"),
    ("either_or_in_story", _EITHER_OR, "含 'either … or …'：可能变相列出备选答案"),
    ("pattern_two_options", re.compile(
        r"\b(?:two|three|four|\d+)\s+(?:options|choices|alternatives)\b|\bchoose\s+(?:between|from)\b|"
        r"\b(?:options|choices)\s+(?:are|include)\b", re.IGNORECASE),
     "含 'two options' / 'choose between' 一类措辞：可能把选项写进了故事"),
    ("pattern_rule_puzzle", re.compile(r"\botherwise\b|\bpreserve\b[^.?!]*\bif\b", re.IGNORECASE),
     "含 'otherwise' / 'preserve … if'：可能是用来逼出答案的 if–then 规则（rule puzzle）"),
    ("pattern_technical_caveat", re.compile(
        r"\bno phase change\b|\bcompeting forces\b|\bwide enough\b|\bmodel(?:s|ing|led|ed)?\s+ordinary\b|\bwithout (?:any )?overhang\b",
        re.IGNORECASE),
     "含技术性免责声明（如 'no phase change'、'competing forces'、'wide enough'）：应放进 risk_notes，不要写进故事"),
]

_STOP = {
    "the", "and", "are", "for", "not", "that", "with", "from", "when", "than", "its", "has", "have", "can", "any",
    "all", "was", "were", "will", "into", "over", "also", "does", "only", "than", "their", "this", "these", "those",
    "rather", "instead", "normally", "generally", "usually", "typically", "ordinary",
}


def _gold_matches(answer: str, locked_gold: str) -> bool:
    """模型写的 gold 可以比知识库的 gold 更完整（"It expands in length." vs "expands"）：相等或作为独立词出现都算一致。"""
    return answers_equivalent(answer, locked_gold) or contains_word(answer, locked_gold)


def _shared_text(backbone: str) -> str:
    return backbone.replace(CLAIM_TOKEN, " ").replace(BELIEF_TOKEN, " ")


def _stems(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w[:5] for w in words if len(w) >= 3 and w not in _STOP}


def claim_fidelity(span: str, locked_claim: str) -> float:
    """锁定声明里的实词（取前 5 个字母的粗略词干）有多大比例出现在 claim span 里。仅作忠实度的粗筛。"""
    want = _stems(locked_claim)
    return 1.0 if not want else len(want & _stems(span)) / len(want)


def design_tag(out: GenerateFamilyOutput, fact: KnowledgeRecord | None = None, bundle: Bundle | None = None) -> str:
    """行动设计标签（只用于统计各类设计的占比，不据此拒绝）：
    forced_binary_options：故事里同时写出了 Q2 的两个竞争答案；
    inherently_binary：故事没列选项，但 Q2 本身就是"不改/改"或事实本身的 对/错 两个选项；
    open_numeric：Q2 是数值；open_other：其他开放式答案。"""
    g = out.proposed_gold
    shared = _shared_text(out.story_backbone)
    if contains_word(shared, g.aligned.q2) and contains_word(shared, g.conflicting.q2):
        return "forced_binary_options"
    if bundle is not None and is_binary_design(bundle, fact):
        return "inherently_binary"
    if fact is not None and _is_fact_pair(g.aligned.q2, g.conflicting.q2, fact):
        return "inherently_binary"
    if all(re.search(r"\d", normalize_answer(x)) for x in (g.aligned.q2, g.conflicting.q2)):
        return "open_numeric"
    return "open_other"


def scan_q3_leakage(out: GenerateFamilyOutput, fact: KnowledgeRecord) -> list[LeakHit]:
    """把 world_gold 与 pretest_accepted_answers 拿去扫描故事（含 claim span）和 Q1/Q2 问题，并分类（guideline B4）：
    (a) aligned_source_claim：出现在 aligned 来源声明里（设计上必然）；
    (b) conflicting_source_claim：出现在锁定的 conflicting 声明里（需标记风险，但不改知识库）；
    (c) elsewhere：出现在声明以外的公共文字/问题里（可能是意外泄漏）。
    子串命中不等于泄漏，需要人工复核否定、单位、同义改写等。"""
    terms = list(dict.fromkeys([fact.world_gold, *fact.pretest_accepted_answers]))
    shared = _shared_text(out.story_backbone or "")
    where = [
        ("claim_span_aligned", out.claim_span_aligned or "", "aligned_source_claim"),
        ("claim_span_conflicting", out.claim_span_conflicting or "", "conflicting_source_claim"),
        ("story_shared_text", shared, "elsewhere"),
        ("belief_question", out.belief_question or "", "elsewhere"),
        ("action_question", out.action_question or "", "elsewhere"),
    ]
    hits: list[LeakHit] = []
    for place, text, category in where:
        for t in terms:
            if contains_word(text, t):
                hits.append(LeakHit(term=t, category=category, where=place))   # type: ignore[arg-type]
    return hits


def check_family_output(
    out: GenerateFamilyOutput, fact: KnowledgeRecord, bundle: Bundle | None = None, *,
    expected_template: str | None = None, expected_agent: str | None = None,
    expected_group: str | None = None, expected_domain: str | None = None,
) -> tuple[Variants | None, list[Issue]]:
    """检查一个 generate_family 输出，并（若可能）渲染四版本。返回 (variants, issues)。

    expected_*：抽样器分配的模板 / 人物名字 / 名字分组 / 场景域。"""
    issues: list[Issue] = []
    if out.status != "candidate_generated":
        return None, [err("needs_revision", "生成模型返回 needs_revision: " + (out.failure_reason or ""))]

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

    # ---- 抽样器分配（名字、场景域、模板都是输入，不是模型的创作选择）
    if expected_template and out.template_id != expected_template:
        issues.append(err("template_mismatch", f"template_id={out.template_id}，但抽样器分配的是 {expected_template}"))
    if expected_domain and out.setting_domain != expected_domain:
        issues.append(err("setting_domain_mismatch",
                          f"setting_domain={out.setting_domain}，但抽样器分配的是 {expected_domain}"))
    if expected_agent:
        if (out.agent_name or "").strip().lower() != expected_agent.strip().lower():
            issues.append(err("agent_mismatch", f"agent_name={out.agent_name!r}，但抽样器分配的是 {expected_agent!r}"))
        if not contains_word(out.story_backbone, expected_agent):
            issues.append(err("agent_not_in_story", f"故事里没有出现被分配的人物名字 {expected_agent!r}"))
        pron = _OPPOSITE_PRONOUNS.get(expected_group or "")
        if pron and pron.search(_shared_text(out.story_backbone)):
            issues.append(warn("pronoun_mismatch",
                               f"{expected_agent} 的代词应为 {'he/him' if expected_group == 'masculine' else 'she/her'}，"
                               "但故事里出现了相反的代词（也可能指其他角色，请人工确认）"))

    # ---- belief cues（0–2 个都允许）
    if len(set(out.belief_cue_ids)) != len(out.belief_cue_ids):
        issues.append(err("belief_cue_duplicate", f"belief_cue_ids 有重复: {out.belief_cue_ids}"))

    # ---- 受控 risk_flags + risk_notes
    if len(set(out.risk_flags)) != len(out.risk_flags):
        issues.append(warn("risk_flag_duplicate", "risk_flags 有重复值（应为互不相同的枚举）"))
    if out.risk_flags and not out.risk_notes.strip():
        issues.append(warn("risk_notes_missing", "标了 risk_flags 但 risk_notes 为空"))

    # ---- gold
    g = out.proposed_gold
    if answers_equivalent(g.aligned.q1, g.conflicting.q1):
        issues.append(err("q1_gold_identical", f"aligned/conflicting 的 Q1 答案相同: {g.aligned.q1!r}"))
    if answers_equivalent(g.aligned.q2, g.conflicting.q2):
        issues.append(err("q2_gold_identical", f"aligned/conflicting 的 Q2 答案相同: {g.aligned.q2!r}"))
    # 与锁定事实的一致性：措辞可能合理不同，所以只给 warning
    if not answers_equivalent(g.q3, fact.world_gold):
        issues.append(warn("q3_vs_world_gold", f"Q3 gold {g.q3!r} 与事实库 world_gold {fact.world_gold!r} 不同，请人工确认"))
    if not _gold_matches(g.aligned.q1, fact.world_gold):
        issues.append(warn("q1_aligned_vs_world_gold", f"aligned Q1 {g.aligned.q1!r} 与 world_gold {fact.world_gold!r} 不同"))
    if not _gold_matches(g.conflicting.q1, fact.conflicting_belief_gold):
        issues.append(warn("q1_conflicting_vs_belief_gold",
                           f"conflicting Q1 {g.conflicting.q1!r} 与 conflicting_belief_gold {fact.conflicting_belief_gold!r} 不同"))
    av = out.answer_variants
    for name, lst in [("q1_aligned", av.q1_aligned), ("q1_conflicting", av.q1_conflicting),
                      ("q2_aligned", av.q2_aligned), ("q2_conflicting", av.q2_conflicting), ("q3", av.q3)]:
        if not lst:
            issues.append(warn("answer_variants_empty", f"answer_variants.{name} 为空，评分时没有同义写法可用"))

    # ---- 锁定声明的忠实度（粗筛，仅 warning）
    for label, span, locked in [("aligned", out.claim_span_aligned, fact.aligned_claim),
                                ("conflicting", out.claim_span_conflicting, fact.conflicting_claim)]:
        ratio = claim_fidelity(span, locked)
        if ratio < 0.6:
            issues.append(warn("claim_span_fidelity",
                               f"claim_span_{label} 只覆盖了锁定 {label}_claim 实词的 {ratio:.0%}，请确认没有改写事实或丢掉限定词"))

    # ---- 问题措辞（启发式，均为 warning）
    for name, q in [("belief_question", out.belief_question), ("action_question", out.action_question),
                    ("reality_question", out.reality_question)]:
        if not q.strip().endswith("?"):
            issues.append(warn("question_format", f"{name} 没有以问号结尾"))
        if re.search(r"\bor\b", q):
            issues.append(warn("question_has_alternatives", f"{name} 含 'or'，可能在提供备选项（应为开放式简答）"))
    if _Q3_BAD.search(out.reality_question) or (out.agent_name and contains_word(out.reality_question, out.agent_name)):
        issues.append(warn("q3_not_reality_directed", "reality_question 看起来在问来源/角色想法，应是纯现实问题"))
    if _BELIEF_WORDS.search(out.action_question):
        issues.append(warn("q2_cues_belief", "action_question 含 believe/think 等词，可能提示了目标信念"))
    if normalize_answer(out.claim_span_conflicting) in normalize_answer(out.belief_question):
        issues.append(warn("q1_direct_copy_risk", "belief_question 逐字包含了 conflicting claim，Q1 可能退化为照抄"))

    # ---- 答案泄漏到公共 backbone（Q1/Q2 的答案）
    shared = _shared_text(out.story_backbone)
    for name, ans in [("Q2 aligned", g.aligned.q2), ("Q2 conflicting", g.conflicting.q2),
                      ("Q1 aligned", g.aligned.q1), ("Q1 conflicting", g.conflicting.q1)]:
        if contains_word(shared, ans):
            issues.append(warn("gold_in_backbone", f"{name} 的答案 {ans!r} 出现在 claim/belief 以外的公共文字里，可能泄漏答案"))

    # ---- Q3 答案泄漏扫描（world_gold / pretest_accepted_answers）
    for hit in scan_q3_leakage(out, fact):
        if hit.category == "conflicting_source_claim":
            issues.append(warn("q3_answer_in_conflicting_claim",
                               f"真实答案 {hit.term!r} 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，"
                               "需标记风险（不改知识库）；请人工确认语义（否定/同义）"))
        elif hit.category == "elsewhere":
            issues.append(warn("q3_answer_leakage_review",
                               f"真实答案 {hit.term!r} 出现在 {hit.where}（claim 以外），可能是意外泄漏，需人工复核（子串命中不等于泄漏）"))
        # aligned_source_claim：设计上必然，仅记录在候选的 q3_leakage_scan 里，不报 issue

    # ---- 二选一：只记录，不拒绝
    if design_tag(out, fact, bundle) == "forced_binary_options":
        issues.append(warn("forced_binary_options_in_story",
                           f"Q2 的两个竞争答案 {g.aligned.q2!r} 与 {g.conflicting.q2!r} 都出现在故事的公共文字里"
                           "（只记录，不拒绝；设计标签 forced_binary_options）"))

    # ---- 正则标记：隐藏的选项菜单 / 规则谜题 / 技术性免责声明（guideline A8；只标记，不拒绝）
    for code, rx, msg in STORY_PATTERNS:
        m = rx.search(shared)
        if m:
            issues.append(warn(code, f"故事公共文字里命中 {m.group(0)!r}：{msg}"))

    # ---- 渲染与 minimal-pair 检查
    variants, pair_issues = render_and_check(
        out.story_backbone, out.claim_span_aligned, out.claim_span_conflicting,
        out.belief_proposition_aligned, out.belief_proposition_conflicting, expected_agent or out.agent_name,
    )
    issues += pair_issues
    return variants, issues
