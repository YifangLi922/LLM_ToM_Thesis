from __future__ import annotations

import json

import pytest

from candidates import build_candidate
from common import read_jsonl
from export_evaluation import (
    ANSWER_INSTRUCTION, LeakError, assert_no_leak, build_messages, export_gold, export_pretest,
    export_story_questions, write_exports,
)
from schemas import CONDITIONS


@pytest.fixture()
def record(k01, bundle, family_out):
    return build_candidate(family_id="F001", fact=k01, bundle=bundle, family_out=family_out,
                           generator_model="MOCK", prompt_version="x", created_at="2026-01-01T00:00:00+00:00")


# ----------------------------------------------------------------- Q0
def test_q0_exactly_one_per_fact_and_no_story(facts):
    rows = export_pretest(facts)
    assert len(rows) == 30 and len({r["fact_id"] for r in rows}) == 30
    assert all(set(r) == {"fact_id", "item_id", "question_type", "question"} for r in rows)
    assert all(r["question_type"] == "Q0" and "story" not in r for r in rows)
    by_id = {f.fact_id: f for f in facts}
    for r in rows:
        assert r["question"] == by_id[r["fact_id"]].pretest_question          # 直接取自事实库，未改写
        assert r["item_id"] == f"{r['fact_id']}_Q0"


def test_q0_prompt_contains_no_story_or_claims(facts):
    for r in export_pretest(facts):
        content = build_messages(r)[0]["content"]
        assert content == f"{r['question']}\n\n{ANSWER_INSTRUCTION}"
        f = next(x for x in facts if x.fact_id == r["fact_id"])
        assert f.conflicting_claim.lower() not in content.lower()
        assert f.aligned_claim.lower() not in content.lower()


def test_no_q0_question_contains_its_own_answer(facts):
    gold = export_gold(facts, [])
    assert_no_leak(export_pretest(facts), gold)       # 30 条真实事实全部通过


# ----------------------------------------------------------------- Q1-Q3
def test_story_rows_one_request_per_family_condition_question(record):
    rows = export_story_questions([record])
    assert len(rows) == 12
    assert {(r["condition"], r["question_type"]) for r in rows} == {(c, q) for c in CONDITIONS for q in ("Q1", "Q2", "Q3")}
    assert len({r["item_id"] for r in rows}) == 12
    # 同一问题措辞在四个条件下完全相同
    for q in ("Q1", "Q2", "Q3"):
        assert len({r["question"] for r in rows if r["question_type"] == q}) == 1


def test_each_request_is_single_turn_with_one_question(record):
    for row in export_story_questions([record]):
        msgs = build_messages(row)
        assert len(msgs) == 1 and msgs[0]["role"] == "user"
        content = msgs[0]["content"]
        assert content.startswith(row["story"]) and row["question"] in content
        assert content.endswith(ANSWER_INSTRUCTION)
        others = {"Q1": record.questions.q1, "Q2": record.questions.q2, "Q3": record.questions.q3}
        for qt, text in others.items():
            if qt != row["question_type"]:
                assert text not in content, "一个请求里不得出现另一个问题"


def test_rejected_candidates_not_exported_by_default(record):
    rejected = record.model_copy(update={"validation_status": "auto_rejected"})
    assert export_story_questions([rejected]) == []
    assert len(export_story_questions([rejected], include_rejected=True)) == 12


# ----------------------------------------------------------------- gold
def test_gold_content_and_q3_constant(facts, record):
    gold = {g["item_id"]: g for g in export_gold(facts, [record])}
    assert gold["K01_Q0"]["reference_answer"] == "8"
    assert gold["F001_implicit_aligned_Q1"]["reference_answer"] == "8"
    assert gold["F001_implicit_conflicting_Q1"]["reference_answer"] == "6"
    assert gold["F001_explicit_aligned_Q2"]["reference_answer"] == "32"
    assert gold["F001_explicit_conflicting_Q2"]["reference_answer"] == "24"
    assert {gold[f"F001_{c}_Q3"]["reference_answer"] for c in CONDITIONS} == {"8"}    # 现实答案不随条件变化
    assert gold["F001_implicit_conflicting_Q2"]["accepted_variants"] == ["twenty-four", "24 pipe cleaners"]
    assert gold["F001_implicit_conflicting_Q2"]["gold_status"] == "proposed"


# ----------------------------------------------------------------- 泄漏守门
def test_exported_rows_have_no_gold_fields(facts, record):
    for r in export_pretest(facts) + export_story_questions([record]):
        blob = json.dumps(r).lower()
        for needle in ("reference_answer", "accepted_variants", "gold_status", "conflicting_belief_gold", "world_gold"):
            assert needle not in blob


def test_full_export_roundtrip_and_ids_join(tmp_path, facts, record):
    counts = write_exports(tmp_path, facts, [record])
    assert counts == {"pretest_questions.jsonl": 30, "story_questions.jsonl": 12, "gold_answers.jsonl": 42}
    eval_ids = {r["item_id"] for r in read_jsonl(tmp_path / "pretest_questions.jsonl") + read_jsonl(tmp_path / "story_questions.jsonl")}
    gold_ids = {r["item_id"] for r in read_jsonl(tmp_path / "gold_answers.jsonl")}
    assert eval_ids == gold_ids


def test_leak_guard_rejects_gold_field_in_eval_row(facts, record):
    rows = export_story_questions([record])
    gold = export_gold(facts, [record])
    rows[0]["reference_answer"] = "8"
    with pytest.raises(LeakError):
        assert_no_leak(rows, gold)
    with pytest.raises(LeakError):
        build_messages(rows[0])


@pytest.mark.parametrize("bad_key", ["accepted_variants", "gold", "source_urls", "bundle", "notes", "validation_status"])
def test_leak_guard_rejects_any_metadata_key(record, bad_key):
    row = export_story_questions([record])[0] | {bad_key: "x"}
    with pytest.raises(LeakError):
        build_messages(row)


def test_leak_guard_rejects_answer_in_question(facts, record):
    rows = export_story_questions([record])
    gold = export_gold(facts, [record])
    q2 = next(r for r in rows if r["question_type"] == "Q2")
    q2["question"] = "Will Emma set aside 32 pipe cleaners?" if "aligned" in q2["condition"] and "conflicting" not in q2["condition"] else "Will Emma set aside 24 pipe cleaners?"
    ref = next(g for g in gold if g["item_id"] == q2["item_id"])["reference_answer"]
    assert ref in q2["question"]
    with pytest.raises(LeakError, match="参考答案"):
        assert_no_leak(rows, gold)


def test_leak_guard_rejects_missing_gold_and_duplicates(facts, record):
    rows = export_story_questions([record])
    gold = export_gold(facts, [record])
    with pytest.raises(LeakError, match="没有对应"):
        assert_no_leak(rows, [g for g in gold if g["item_id"] != rows[0]["item_id"]])
    with pytest.raises(LeakError, match="重复"):
        assert_no_leak(rows + [rows[0]], gold)


def test_q0_with_story_rejected():
    with pytest.raises(LeakError):
        build_messages({"fact_id": "K01", "item_id": "K01_Q0", "question_type": "Q0", "question": "q", "story": "leak"})
