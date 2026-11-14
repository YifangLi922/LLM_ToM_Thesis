"""四条件 minimal-pair 渲染器（guideline v1.1 B2）与差异检查。

规则（全部由代码保证，而不是让 LLM 再写一遍）：
    implicit_aligned     = backbone 中 {{CLAIM_SPAN}} -> claim_span_aligned，{{BELIEF_INSERTION}} -> 空
    implicit_conflicting = 同上，换成 claim_span_conflicting
    explicit_aligned     = implicit_aligned 的 {{BELIEF_INSERTION}} 位置插入
                           ' ' + agent_name + ' believes that ' + belief_proposition_aligned + '.'
    explicit_conflicting = 同上，冲突版本
两次替换都作用在**未改动的原始 backbone** 上；只规范化插入点周围无害的空格。
解释句由代码按固定句式拼出（模型只提供不带 "that"、人名和句号的从句 belief_proposition_*）。
"""
from __future__ import annotations

import re

from schemas import CONDITIONS, Issue, Variants, err, warn
from common import normalize_answer

CLAIM_TOKEN = "{{CLAIM_SPAN}}"
BELIEF_TOKEN = "{{BELIEF_INSERTION}}"
BELIEF_TEMPLATE = "{name} believes that {proposition}."     # guideline v1.1 A2：固定的统一句式
MAX_STORY_WORDS = 110     # guideline v1.1 A8：含 claim span 的硬上限
MIN_STORY_WORDS = 70      # 建议下限（只提示）


class RenderError(ValueError):
    """backbone 或替换内容不满足渲染前提。"""


def belief_sentence(agent_name: str, proposition: str) -> str:
    """explicit 条件里插入的那一句话（不含前导空格）。"""
    return BELIEF_TEMPLATE.format(name=agent_name, proposition=proposition)


_END = r"[.!?][\"')\]”’]*"


# --------------------------------------------------------------------------- proposition 检查
def check_propositions(agent_name: str, pa: str, pc: str) -> list[Issue]:
    """belief_proposition 必须是不带 initial "that"、不以人名开头、不带句末标点的肯定从句（guideline v1.1 A2）。"""
    issues: list[Issue] = []
    for label, p in (("aligned", pa), ("conflicting", pc)):
        t = p.strip()
        name = f"belief_proposition_{label}"
        if "{{" in t or "}}" in t:
            issues.append(err("placeholder_in_content", f"{name} 不能包含 {{{{ }}}} 标记"))
        if re.match(r"that\b", t, flags=re.IGNORECASE):
            issues.append(err("proposition_leading_that", f"{name} 不应以 'that' 开头（代码会补上 'believes that'）"))
        if re.match(re.escape(agent_name) + r"\b", t, flags=re.IGNORECASE):
            issues.append(err("proposition_leading_agent", f"{name} 不应以人物名字 {agent_name!r} 开头（代码会补上）"))
        if re.search(_END + r"\s*$", t):
            issues.append(err("proposition_terminal_punct", f"{name} 不应带句末标点（代码会补上句号）"))
        elif re.search(r"[.!?]\s+\S", t):
            issues.append(err("proposition_multi_sentence", f"{name} 必须是单个从句，不能包含多句话"))
        if p != t:
            issues.append(err("proposition_whitespace", f"{name} 首尾不应有空白"))
    if normalize_answer(pa) == normalize_answer(pc):
        issues.append(err("belief_propositions_identical", "aligned 与 conflicting 的 belief proposition 相同"))
    return issues


# --------------------------------------------------------------------------- backbone 检查
def check_backbone(backbone: str) -> list[Issue]:
    issues: list[Issue] = []
    n_claim, n_belief = backbone.count(CLAIM_TOKEN), backbone.count(BELIEF_TOKEN)
    if n_claim != 1:
        issues.append(err("placeholder_claim_count", f"{CLAIM_TOKEN} 必须恰好出现 1 次，实际 {n_claim} 次"))
    if n_belief != 1:
        issues.append(err("placeholder_belief_count", f"{BELIEF_TOKEN} 必须恰好出现 1 次，实际 {n_belief} 次"))
    leftover = backbone.replace(CLAIM_TOKEN, "").replace(BELIEF_TOKEN, "")
    if "{{" in leftover or "}}" in leftover:
        issues.append(err("placeholder_unknown", "backbone 中出现了约定之外的 {{ }} 标记"))
    if n_claim == 1 and n_belief == 1:
        ic, ib = backbone.index(CLAIM_TOKEN), backbone.index(BELIEF_TOKEN)
        if ib < ic:
            issues.append(err("placeholder_order", f"{BELIEF_TOKEN} 必须出现在 {CLAIM_TOKEN} 之后"))
    return issues


def insertion_point_problem(span: str, tail: str) -> str | None:
    """belief 句必须紧跟在"含 claim span 的那句话"之后。

    span：填入的 claim；tail：claim 之后到插入点之间的文字（可为空，也可能只是句号）。
    claim span 可以自带句末标点（整句），也可以由骨架补句号，两种写法都合法；
    但句子必须在插入点之前结束，且不能出现 ".." 这样的重复标点。返回问题描述，或 None。
    """
    seg = (span + tail).rstrip()
    if not re.search(_END + "$", seg):
        return "来源信息那句话在插入 belief 句之前没有以句末标点结束"
    if not re.fullmatch(r"[^.!?]*(" + _END + ")?", tail):
        return f"claim 与插入点之间还有其他句子或多余标点: {tail!r}"
    if tail and re.search(_END + "$", span.rstrip()) and re.search(_END, tail):
        return "claim span 已带句末标点，骨架里又补了一个，会出现重复标点"
    return None


def _has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)


# --------------------------------------------------------------------------- 渲染
def _render_one(backbone: str, claim: str, belief: str | None) -> str:
    pre, post = backbone.split(BELIEF_TOKEN)           # 已确认恰好一个
    pre = pre.replace(CLAIM_TOKEN, claim).rstrip(" \t")
    post = post.lstrip(" \t")
    out = pre
    if belief is not None:
        out += " " + belief
    if post:
        out += post if post.startswith("\n") else " " + post
    return out


def render_variants(
    backbone: str,
    claim_span_aligned: str,
    claim_span_conflicting: str,
    belief_proposition_aligned: str,
    belief_proposition_conflicting: str,
    agent_name: str,
) -> Variants:
    """确定性渲染四个版本；前提不满足时抛 RenderError（不会"尽力而为"地乱拼）。"""
    problems = check_backbone(backbone)
    for name, text in [("claim_span_aligned", claim_span_aligned), ("claim_span_conflicting", claim_span_conflicting)]:
        if "{{" in text or "}}" in text:
            problems.append(err("placeholder_in_content", f"{name} 不能包含 {{{{ }}}} 标记"))
    problems += check_propositions(agent_name, belief_proposition_aligned, belief_proposition_conflicting)
    if not _has_errors(problems):
        tail = backbone[backbone.index(CLAIM_TOKEN) + len(CLAIM_TOKEN): backbone.index(BELIEF_TOKEN)].rstrip(" \t")
        for name, span in [("claim_span_aligned", claim_span_aligned), ("claim_span_conflicting", claim_span_conflicting)]:
            msg = insertion_point_problem(span, tail)
            if msg:
                problems.append(err("belief_not_after_sentence", f"{name}: {msg}"))
    if _has_errors(problems):
        raise RenderError("; ".join(f"[{p.code}] {p.message}" for p in problems if p.severity == "error"))
    ba = belief_sentence(agent_name, belief_proposition_aligned)
    bc = belief_sentence(agent_name, belief_proposition_conflicting)
    return Variants(
        implicit_aligned=_render_one(backbone, claim_span_aligned, None),
        implicit_conflicting=_render_one(backbone, claim_span_conflicting, None),
        explicit_aligned=_render_one(backbone, claim_span_aligned, ba),
        explicit_conflicting=_render_one(backbone, claim_span_conflicting, bc),
    )


# --------------------------------------------------------------------------- 差异检查
_MARK = "\u0000"


def check_minimal_pairs(
    variants: Variants,
    claim_span_aligned: str,
    claim_span_conflicting: str,
    belief_proposition_aligned: str,
    belief_proposition_conflicting: str,
    agent_name: str,
) -> list[Issue]:
    """只看四个最终字符串，检验差异是否严格限于允许范围。

    这样即使有人（或 LLM）绕过渲染器、手工改写了某个版本，也能被发现。
    解释句按固定句式由 agent_name + proposition 重建；explicit 条件必须恰好多出这一句。
    """
    issues: list[Issue] = []
    ca, cc = claim_span_aligned, claim_span_conflicting
    ba = belief_sentence(agent_name, belief_proposition_aligned)
    bc = belief_sentence(agent_name, belief_proposition_conflicting)

    if normalize_answer(ca) == normalize_answer(cc):
        issues.append(err("claim_spans_identical", "aligned 与 conflicting 的 claim span 相同"))
    issues += check_propositions(agent_name, belief_proposition_aligned, belief_proposition_conflicting)
    if _has_errors(issues):
        return issues

    v = variants
    # 1) belief sentence（渲染时前面带一个空格）只能出现在 explicit，且恰好一次。
    #    先把它从 explicit 里去掉：belief 句常常会复述 claim，不能让它干扰后面对 claim span 的计数。
    stripped: dict[str, str] = {}
    for cond, sent in [("explicit_aligned", ba), ("explicit_conflicting", bc)]:
        text = getattr(v, cond)
        n = text.count(" " + sent)
        if n != 1:
            issues.append(err("belief_sentence_count", f"{cond} 中 belief sentence 应恰好出现 1 次，实际 {n} 次"))
        else:
            stripped[cond] = text.replace(" " + sent, "", 1)
    for cond in ("implicit_aligned", "implicit_conflicting"):
        for sent in (ba, bc):
            if sent in getattr(v, cond):
                issues.append(err("belief_in_implicit", f"{cond} 不应包含 belief sentence"))
    if _has_errors(issues):
        return issues

    # 2) 去掉 belief 句之后，每个版本里 claim span 必须恰好出现一次
    bases = {
        "implicit_aligned": (v.implicit_aligned, ca), "implicit_conflicting": (v.implicit_conflicting, cc),
        "explicit_aligned": (stripped["explicit_aligned"], ca), "explicit_conflicting": (stripped["explicit_conflicting"], cc),
    }
    for cond, (text, span) in bases.items():
        n = text.count(span)
        if n != 1:
            issues.append(err("claim_span_count", f"{cond} 中 claim span 应恰好出现 1 次，实际 {n} 次"))
    if _has_errors(issues):
        return issues

    # 3) aligned / conflicting：把 claim span 换成同一记号后必须逐字节相同（implicit 与 explicit 各自比较）
    if bases["implicit_aligned"][0].replace(ca, _MARK) != bases["implicit_conflicting"][0].replace(cc, _MARK):
        issues.append(err("implicit_pair_differs", "implicit aligned/conflicting 在 claim span 以外存在差异"))
    if bases["explicit_aligned"][0].replace(ca, _MARK) != bases["explicit_conflicting"][0].replace(cc, _MARK):
        issues.append(err("explicit_pair_differs", "explicit aligned/conflicting 在 claim/belief 句以外存在差异"))
    # 4) implicit / explicit：去掉 ' ' + belief sentence 后必须与 implicit 完全一致
    if stripped["explicit_aligned"] != v.implicit_aligned:
        issues.append(err("explicit_vs_implicit_aligned", "explicit_aligned 与 implicit_aligned 的差异超出一句 belief sentence"))
    if stripped["explicit_conflicting"] != v.implicit_conflicting:
        issues.append(err("explicit_vs_implicit_conflicting", "explicit_conflicting 与 implicit_conflicting 的差异超出一句 belief sentence"))

    # 5) 位置：belief 句必须紧跟在包含 claim span 的那句话之后（guideline v1.1 A7）。
    #    只看去掉 belief 句后的"claim 之后到插入点"这一小段：它只能是该句话剩下的部分 + 句末标点（可带右引号/括号）。
    for cond, sent, span in [("explicit_aligned", ba, ca), ("explicit_conflicting", bc, cc)]:
        text = getattr(v, cond)
        prefix = text[: text.index(" " + sent)]
        tail = prefix[prefix.rfind(span) + len(span):]
        msg = insertion_point_problem(span, tail)
        if msg:
            issues.append(err("belief_not_after_source_sentence",
                              f"{cond}: belief sentence 没有紧跟在来源信息那句话之后（{msg}）"))

    # 6) 篇幅（guideline v1.1 A6/A8）：110 词是硬上限（含 claim span），超过则拒绝并重新生成；少于 70 词只是提示
    n_words = max(len(v.implicit_aligned.split()), len(v.implicit_conflicting.split()))
    if n_words > MAX_STORY_WORDS:
        issues.append(err("story_too_long", f"implicit 故事共 {n_words} 词，超过硬上限 {MAX_STORY_WORDS} 词（guideline A8）"))
    elif n_words < MIN_STORY_WORDS:
        issues.append(warn("story_length", f"implicit 故事共 {n_words} 词，少于建议的 {MIN_STORY_WORDS} 词"))
    return issues


def render_and_check(
    backbone: str, ca: str, cc: str, pa: str, pc: str, agent_name: str
) -> tuple[Variants | None, list[Issue]]:
    """渲染 + 检查，一步完成；渲染不了就返回 (None, issues)。"""
    try:
        variants = render_variants(backbone, ca, cc, pa, pc, agent_name)
    except RenderError as e:
        return None, [err("render_failed", str(e))]
    return variants, check_minimal_pairs(variants, ca, cc, pa, pc, agent_name)


__all__ = [
    "CLAIM_TOKEN", "BELIEF_TOKEN", "BELIEF_TEMPLATE", "MAX_STORY_WORDS", "MIN_STORY_WORDS", "CONDITIONS", "RenderError", "belief_sentence",
    "check_propositions", "check_backbone", "render_variants", "check_minimal_pairs", "render_and_check",
]
