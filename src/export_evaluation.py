"""导出三份实验文件，并保证 gold 不会泄漏进发给被测模型的请求。

    pretest_questions.jsonl  —— Q0：每条事实恰好一行，无故事            （发给被测模型）
    story_questions.jsonl    —— Q1/Q2/Q3：每 (family, condition, 问题类型) 一行 （发给被测模型）
    gold_answers.jsonl       —— 参考答案，按 item_id 关联                  （绝不发给被测模型）

发给被测模型的 prompt 只由 `story` 和 `question` 两个字段 + 统一指令拼成（见 build_messages）。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from common import contains_word, write_jsonl
from schemas import CONDITIONS, CandidateRecord, KnowledgeRecord

ANSWER_INSTRUCTION = "Answer with a number, one word, or a short phrase. Do not explain your answer."

PRETEST_KEYS = {"fact_id", "item_id", "question_type", "question"}
STORY_KEYS = {"family_id", "fact_id", "item_id", "condition", "question_type", "story", "question"}
_FORBIDDEN_KEY = re.compile(
    r"gold|reference|accepted|variant|answer|source|status|issue|provenance|bundle|rule|flag|ambigu|note|backbone",
    re.IGNORECASE,
)
_QTYPE_BY_NAME = {"Q1": "q1", "Q2": "q2", "Q3": "q3"}


class LeakError(ValueError):
    """评测请求里出现了不该出现的内容。"""


# --------------------------------------------------------------------------- 构建行
def story_item_id(family_id: str, condition: str, qtype: str) -> str:
    return f"{family_id}_{condition}_{qtype}"


def export_pretest(facts: Iterable[KnowledgeRecord]) -> list[dict]:
    """Q0：每条事实一行，问题直接取自事实库，**没有故事、没有 claim**。"""
    return [
        {"fact_id": f.fact_id, "item_id": f"{f.fact_id}_Q0", "question_type": "Q0", "question": f.pretest_question}
        for f in facts
    ]


def _usable(records: Iterable[CandidateRecord], include_rejected: bool) -> list[CandidateRecord]:
    return [
        r for r in records
        if r.variants is not None and (include_rejected or r.validation_status == "needs_human_review")
    ]


def export_story_questions(records: Iterable[CandidateRecord], *, include_rejected: bool = False) -> list[dict]:
    """每个 usable family 产生 4 条件 × 3 问题 = 12 行；每行是独立请求，同一故事在 Q1/Q2/Q3 里各出现一次。"""
    rows: list[dict] = []
    for r in _usable(records, include_rejected):
        qs = {"Q1": r.questions.q1, "Q2": r.questions.q2, "Q3": r.questions.q3}
        for cond in CONDITIONS:
            story = getattr(r.variants, cond)
            for qtype, question in qs.items():
                rows.append({
                    "family_id": r.family_id, "fact_id": r.fact_id,
                    "item_id": story_item_id(r.family_id, cond, qtype),
                    "condition": cond, "question_type": qtype, "story": story, "question": question,
                })
    return rows


def export_gold(
    facts: Iterable[KnowledgeRecord], records: Iterable[CandidateRecord], *, include_rejected: bool = False
) -> list[dict]:
    rows: list[dict] = []
    for f in facts:
        rows.append({
            "item_id": f"{f.fact_id}_Q0", "fact_id": f.fact_id, "question_type": "Q0",
            "reference_answer": f.world_gold, "accepted_variants": list(f.pretest_accepted_answers),
            "gold_status": "pre_specified", "fact_status": f.fact_status,
        })
    for r in _usable(records, include_rejected):
        g, av = r.proposed_gold, r.answer_variants
        for cond in CONDITIONS:
            side = "aligned" if cond.endswith("_aligned") else "conflicting"
            gold = {
                "Q1": (getattr(g, side).q1, getattr(av, f"q1_{side}")),
                "Q2": (getattr(g, side).q2, getattr(av, f"q2_{side}")),
                "Q3": (g.q3, av.q3),                    # 现实答案：四个条件完全相同
            }
            for qtype, (ref, variants) in gold.items():
                rows.append({
                    "item_id": story_item_id(r.family_id, cond, qtype), "family_id": r.family_id,
                    "fact_id": r.fact_id, "condition": cond, "question_type": qtype,
                    "reference_answer": ref, "accepted_variants": list(variants), "gold_status": "proposed",
                })
    return rows


# --------------------------------------------------------------------------- 请求与泄漏检查
def build_messages(row: dict, instruction: str = ANSWER_INSTRUCTION) -> list[dict]:
    """把一行评测题变成发给被测模型的消息：单条 user 消息，无历史，无 system 里的研究信息。"""
    _check_row_keys(row)
    if row["question_type"] == "Q0":
        content = f"{row['question']}\n\n{instruction}"
    else:
        content = f"{row['story']}\n\n{row['question']}\n\n{instruction}"
    return [{"role": "user", "content": content}]


def _check_row_keys(row: dict) -> None:
    allowed = PRETEST_KEYS if row.get("question_type") == "Q0" else STORY_KEYS
    extra = set(row) - allowed
    if extra:
        raise LeakError(f"{row.get('item_id')}: 评测行含不允许的字段 {sorted(extra)}")
    bad = [k for k in row if _FORBIDDEN_KEY.search(k)]
    if bad:
        raise LeakError(f"{row.get('item_id')}: 评测行含疑似 gold/元数据字段 {bad}")


def assert_no_leak(eval_rows: Iterable[dict], gold_rows: Iterable[dict]) -> None:
    """导出后的最终守门检查，任何一项不满足就抛 LeakError。"""
    gold = {g["item_id"]: g for g in gold_rows}
    seen: set[str] = set()
    for row in eval_rows:
        _check_row_keys(row)
        iid = row["item_id"]
        if iid in seen:
            raise LeakError(f"item_id 重复: {iid}")
        seen.add(iid)
        if iid not in gold:
            raise LeakError(f"{iid}: gold_answers 中没有对应的 item_id")
        if row["question_type"] == "Q0" and "story" in row:
            raise LeakError(f"{iid}: Q0 不得带故事")
        ref = gold[iid]["reference_answer"]
        if contains_word(row["question"], ref):
            raise LeakError(f"{iid}: 问题文字中包含了它自己的参考答案 {ref!r}")
        # 序列化后的整个请求里不得出现 gold 文件特有的措辞
        payload = "\n".join(m["content"] for m in build_messages(row))
        for marker in ("reference_answer", "accepted_variants", "gold_status"):
            if marker in payload:
                raise LeakError(f"{iid}: 请求文本里出现 {marker}")


def write_exports(
    out_dir: Path, facts: list[KnowledgeRecord], records: list[CandidateRecord], *, include_rejected: bool = False
) -> dict[str, int]:
    """生成并写出三份文件（先做泄漏检查，再落盘）。返回各文件行数。"""
    pretest = export_pretest(facts)
    story = export_story_questions(records, include_rejected=include_rejected)
    gold = export_gold(facts, records, include_rejected=include_rejected)
    assert_no_leak(pretest + story, gold)
    out_dir = Path(out_dir)
    return {
        "pretest_questions.jsonl": write_jsonl(out_dir / "pretest_questions.jsonl", pretest),
        "story_questions.jsonl": write_jsonl(out_dir / "story_questions.jsonl", story),
        "gold_answers.jsonl": write_jsonl(out_dir / "gold_answers.jsonl", gold),
    }
