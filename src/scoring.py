"""短答案的规则评分（不依赖任何模型）：规范化、日期/单位处理、否定检查、与 gold / 另一条件的 gold 比较。

只做"能确定"的判断，其余一律交给上层处理（LLM 裁判或人工复核）：
    correct      —— 匹配本题 gold，且不匹配另一个条件的 gold
    wrong_alt    —— 只匹配另一个条件的 gold（例如 conflicting 题答成了 aligned 的答案）
    undecided    —— 同时匹配两者、两者都不匹配、答案过长，或匹配处被否定词修饰
不会因为"答案里包含某个关键词"就判对：被否定的匹配不算匹配（"fungi, not plants" 只匹配 fungi）。
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from common import normalize_answer

MONTHS = {
    "january": "january", "jan": "january", "february": "february", "feb": "february", "march": "march", "mar": "march",
    "april": "april", "apr": "april", "may": "may", "june": "june", "jun": "june", "july": "july", "jul": "july",
    "august": "august", "aug": "august", "september": "september", "sep": "september", "sept": "september",
    "october": "october", "oct": "october", "november": "november", "nov": "november", "december": "december",
    "dec": "december",
}
_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
_DAY_MONTH = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_RE})\b")
_MONTH_DAY = re.compile(rf"\b({_MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b")
NEG = {"not", "no", "never", "cannot", "without", "neither", "nor", "can't", "isn't", "doesn't", "don't", "won't",
       "wouldn't", "didn't", "aren't", "shouldn't", "couldn't", "nt"}
MAX_TOKENS_FOR_RULES = 30


def _canon_months(text: str) -> str:
    text = _DAY_MONTH.sub(lambda m: f"{int(m.group(1))} {MONTHS[m.group(2)]}", text)
    text = _MONTH_DAY.sub(lambda m: f"{int(m.group(2))} {MONTHS[m.group(1)]}", text)
    return re.sub(rf"\b({_MONTH_RE})\b", lambda m: MONTHS[m.group(1)], text)


def tokens(text: str) -> list[str]:
    """小写、统一单位/日期/数字写法后切词，并做轻量词干化（去复数 s）。"""
    s = unicodedata.normalize("NFKC", str(text)).lower().replace("’", "'")
    s = re.sub(r"degrees?\s+celsius|celsius|℃|°\s*c\b|deg(?:rees?)?\s*c\b", " °c ", s)
    s = re.sub(r"\bper\s*cent\b|\bpercent(?:age)?\b", " % ", s)
    s = normalize_answer(s) if len(s) < 400 else s            # 英文数字词 -> 阿拉伯数字（只改词，不删内容）
    s = _canon_months(s)
    out = []
    for t in re.findall(r"[a-z0-9]+(?:'[a-z]+)?|%|°c", s):
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss") and t not in NEG:
            t = t[:-1]
        out.append(t)
    return out


def _segments(gold: str) -> list[list[str]]:
    """gold 本身，以及按 ';' 或 '.' 切开的、至少 2 个词的片段（如 "No change; retain the effect." -> "no change"）。"""
    full = tokens(gold)
    segs = [full] if full else []
    for part in re.split(r"[;.]", gold):
        t = tokens(part)
        if len(t) >= 2 and t != full:
            segs.append(t)
    return segs


def _find(ans: list[str], gold: list[str]) -> list[int]:
    n = len(gold)
    return [i for i in range(len(ans) - n + 1) if ans[i:i + n] == gold] if n else []


HEDGE = {"or", "either", "depending", "depends", "maybe", "possibly", "perhaps", "might", "unclear", "unknown"}


def _match_remainder(answer: str, golds: list[str]) -> list[str] | None:
    """若答案（未被否定地）包含 golds 中任一 gold 或其片段，返回"去掉匹配部分后剩下的词"；否则返回 None。"""
    ans = tokens(answer)
    for g in golds:
        for seg in _segments(g):
            gold_has_neg = any(t in NEG for t in seg)
            for i in _find(ans, seg):
                window = ans[max(0, i - 3):i]
                if gold_has_neg or not any(t in NEG for t in window):
                    return ans[:i] + ans[i + len(seg):]
    return None


def matches(answer: str, golds: list[str]) -> bool:
    """答案是否（未被否定地）包含 golds 中任意一个 gold 或其片段。"""
    return _match_remainder(answer, golds) is not None


def _hedged(answer: str, golds: list[str]) -> bool:
    """匹配之外的部分里还有 "or / either / depending / maybe …"：说明答案在两可或附带条件，不能自动判对/判错。"""
    rest = _match_remainder(answer, golds)
    return rest is not None and any(t in HEDGE for t in rest)


@dataclass
class RuleResult:
    verdict: str          # correct / wrong_alt / undecided
    matched_own: bool
    matched_alt: bool
    reason: str


def rule_score(answer: str | None, own: list[str], alt: list[str]) -> RuleResult:
    if answer is None or not answer.strip():
        return RuleResult("undecided", False, False, "empty answer")
    own_hit, alt_hit = matches(answer, own), matches(answer, alt)
    if len(tokens(answer)) > MAX_TOKENS_FOR_RULES:
        return RuleResult("undecided", own_hit, alt_hit, f"answer longer than {MAX_TOKENS_FOR_RULES} tokens")
    if (own_hit and _hedged(answer, own)) or (alt_hit and _hedged(answer, alt)):
        return RuleResult("undecided", own_hit, alt_hit, "hedged answer (or / either / depending …)")
    if own_hit and not alt_hit:
        return RuleResult("correct", True, False, "matches own gold only")
    if alt_hit and not own_hit:
        return RuleResult("wrong_alt", False, True, "matches the other condition's gold only")
    if own_hit and alt_hit:
        return RuleResult("undecided", True, True, "matches both golds")
    return RuleResult("undecided", False, False, "matches neither gold")


def answer_kind(answer: str | None) -> str:
    """粗分答案类型：numeric / date_or_month / coordinate / other（只用于错误归因的启发式）。"""
    a = (answer or "").lower()
    if re.search(rf"\b({_MONTH_RE})\b", a):
        return "date_or_month"
    if re.search(r"\b[a-h][1-8]\b", a):
        return "coordinate"
    if re.search(r"\d", a):
        return "numeric"
    return "other"
