"""四条件 minimal-pair 渲染器（guideline §8）与差异检查。

规则（全部由代码保证，而不是让 LLM 再写一遍）：
    implicit_aligned     = backbone 中 {{CLAIM_SPAN}} -> claim_span_aligned，{{BELIEF_INSERTION}} -> 空
    implicit_conflicting = 同上，换成 claim_span_conflicting
    explicit_aligned     = implicit_aligned 的 {{BELIEF_INSERTION}} 位置插入 ' ' + belief_sentence_aligned
    explicit_conflicting = 同上，冲突版本
两次替换都作用在**未改动的原始 backbone** 上；只规范化插入点周围无害的空格。
"""
from __future__ import annotations

import re

from schemas import CONDITIONS, Issue, Variants, err, warn
from common import normalize_answer

CLAIM_TOKEN = "{{CLAIM_SPAN}}"
BELIEF_TOKEN = "{{BELIEF_INSERTION}}"
_SENTENCE_END = (".", "!", "?")


class RenderError(ValueError):
    """backbone 或替换内容不满足渲染前提。"""


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
        else:
            before = backbone[:ib].rstrip(" \t")
            if not re.search(r"[.!?][\"')\]”’]*$", before):
                issues.append(err(
                    "belief_not_after_sentence",
                    f"{BELIEF_TOKEN} 必须紧跟在来源信息那句话（含句末标点）之后",
                ))
    return issues


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
    belief_sentence_aligned: str,
    belief_sentence_conflicting: str,
) -> Variants:
    """确定性渲染四个版本；前提不满足时抛 RenderError（不会"尽力而为"地乱拼）。"""
    problems = check_backbone(backbone)
    for name, text in [
        ("claim_span_aligned", claim_span_aligned), ("claim_span_conflicting", claim_span_conflicting),
        ("belief_sentence_aligned", belief_sentence_aligned),
        ("belief_sentence_conflicting", belief_sentence_conflicting),
    ]:
        if "{{" in text or "}}" in text:
            problems.append(err("placeholder_in_content", f"{name} 不能包含 {{{{ }}}} 标记"))
    if _has_errors(problems):
        raise RenderError("; ".join(f"[{p.code}] {p.message}" for p in problems if p.severity == "error"))
    return Variants(
        implicit_aligned=_render_one(backbone, claim_span_aligned, None),
        implicit_conflicting=_render_one(backbone, claim_span_conflicting, None),
        explicit_aligned=_render_one(backbone, claim_span_aligned, belief_sentence_aligned),
        explicit_conflicting=_render_one(backbone, claim_span_conflicting, belief_sentence_conflicting),
    )


# --------------------------------------------------------------------------- 差异检查
_MARK = "\u0000"


def check_minimal_pairs(
    variants: Variants,
    claim_span_aligned: str,
    claim_span_conflicting: str,
    belief_sentence_aligned: str,
    belief_sentence_conflicting: str,
) -> list[Issue]:
    """只看四个最终字符串，检验差异是否严格限于允许范围。

    这样即使有人（或 LLM）绕过渲染器、手工改写了某个版本，也能被发现。
    """
    issues: list[Issue] = []
    ca, cc, ba, bc = claim_span_aligned, claim_span_conflicting, belief_sentence_aligned, belief_sentence_conflicting

    if normalize_answer(ca) == normalize_answer(cc):
        issues.append(err("claim_spans_identical", "aligned 与 conflicting 的 claim span 相同"))
    if normalize_answer(ba) == normalize_answer(bc):
        issues.append(err("belief_sentences_identical", "aligned 与 conflicting 的 belief sentence 相同"))
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

    # 5) 位置：belief 句必须紧跟在包含 claim span 的那句话之后（guideline §8）。
    #    只看去掉 belief 句后的"claim 之后到插入点"这一小段：它只能是该句话剩下的部分 + 句末标点（可带右引号/括号）。
    for cond, sent, span in [("explicit_aligned", ba, ca), ("explicit_conflicting", bc, cc)]:
        text = getattr(v, cond)
        prefix = text[: text.index(" " + sent)]
        tail = prefix[prefix.rfind(span) + len(span):]
        if not re.fullmatch(r"[^.!?]*[.!?][\"')\]”’]*", tail):
            issues.append(err("belief_not_after_source_sentence",
                              f"{cond}: belief sentence 没有紧跟在来源信息那句话之后（claim 与插入点之间是 {tail!r}）"))

    # 6) 软提示
    for name, sent in [("aligned", ba), ("conflicting", bc)]:
        s = sent.strip()
        if not s.endswith(_SENTENCE_END):
            issues.append(warn("belief_sentence_punct", f"belief_sentence_{name} 未以句号/问号/感叹号结尾"))
        if re.search(r"[.!?]\s+[A-Z]", s):
            issues.append(warn("belief_sentence_multi", f"belief_sentence_{name} 可能包含多于一句话"))
    n_words = len(v.implicit_aligned.split())
    if not 70 <= n_words <= 130:
        issues.append(warn("story_length", f"implicit 故事共 {n_words} 词，超出 guideline 建议的约 70–130 词"))
    return issues


def render_and_check(
    backbone: str, ca: str, cc: str, ba: str, bc: str
) -> tuple[Variants | None, list[Issue]]:
    """渲染 + 检查，一步完成；渲染不了就返回 (None, issues)。"""
    try:
        variants = render_variants(backbone, ca, cc, ba, bc)
    except RenderError as e:
        return None, [err("render_failed", str(e))]
    return variants, check_minimal_pairs(variants, ca, cc, ba, bc)


__all__ = [
    "CLAIM_TOKEN", "BELIEF_TOKEN", "CONDITIONS", "RenderError",
    "check_backbone", "render_variants", "check_minimal_pairs", "render_and_check",
]
