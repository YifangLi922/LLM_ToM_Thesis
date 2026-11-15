"""人工修改后的 REVIEW 文件导回流水线 / 导出评测文件：离线测试。"""
from __future__ import annotations

import json

import pytest

from build_review_report import render_card
from candidates import build_candidate
from import_reviewed import (
    ReviewParseError, derive_proposition, export_all, parse_review, parse_story, rebuild,
)

INSTR = "Answer with a number, one word, or a short phrase. Do not explain your answer."


@pytest.fixture()
def rec(k30, bundle, family_out, asg):
    return build_candidate(family_id="F001", fact=k30, bundle=bundle, family_out=family_out, generator_model="MOCK",
                           prompt_version="x", created_at="2026-01-01T00:00:00+00:00", assignment=asg)


@pytest.fixture()
def orig(rec):
    return json.loads(rec.model_dump_json())


def _card_text(rec, story=None):
    text = render_card(rec)
    if story is not None:
        old = next(line for line in text.splitlines() if line.startswith("> ") and "**[" in line)
        text = text.replace(old, "> " + story)
    return text


def _rebuild(orig, k30, text, set_q=None):
    card = parse_review(text)["F001"]
    return rebuild(orig, card, k30, set_q or {})


# ----------------------------------------------------------------- 往返：生成的卡片 -> 解析 -> 重建，四个条件不变
def test_roundtrip_reproduces_the_four_variants_exactly(rec, orig, k30):
    new, notes = _rebuild(orig, k30, _card_text(rec))
    assert new.variants == rec.variants and notes == []
    assert new.story_backbone == rec.story_backbone
    assert new.questions == rec.questions and new.proposed_gold == rec.proposed_gold


def test_story_edits_are_reflected_in_all_four_conditions(rec, orig, k30):
    story = merged = None
    from build_review_report import merged_story
    story = merged_story(rec).replace("Later, Grace starts a checklist", "Next, Grace begins a checklist")
    new, _ = _rebuild(orig, k30, _card_text(rec, story))
    for cond in ("implicit_aligned", "implicit_conflicting", "explicit_aligned", "explicit_conflicting"):
        assert "Next, Grace begins a checklist" in getattr(new.variants, cond)
        assert "Later, Grace starts" not in getattr(new.variants, cond)


def test_edited_claim_spans_are_used_verbatim(rec, orig, k30):
    from build_review_report import merged_story
    s = merged_story(rec).replace("generally begins in September]", "begins in September]")
    s = s.replace("generally begins in September].⟩", "begins in September].⟩")
    new, _ = _rebuild(orig, k30, _card_text(rec, s))
    assert new.claim_span_conflicting.endswith("begins in September") and "generally begins in September" not in new.claim_span_conflicting
    assert new.variants.explicit_conflicting.count("begins in September") == 2


# ----------------------------------------------------------------- 研究者手改时常见的小问题
def test_missing_explicit_insertion_is_restored_in_the_right_place(rec, orig, k30):
    from build_review_report import merged_story
    import re
    s = re.sub(r"\s*⟨.*?⟩", "", merged_story(rec))
    new, notes = _rebuild(orig, k30, _card_text(rec, s))
    assert new.variants == rec.variants                       # 与原来完全一致：解释句被补回到来源句之后
    assert any("没有 ⟨ ⟩" in n for n in notes)


def test_ascii_bar_and_double_spaces_are_accepted(rec, orig, k30):
    from build_review_report import merged_story
    s = merged_story(rec).replace("｜", " | ").replace("Grace starts", "Grace  starts")
    new, _ = _rebuild(orig, k30, _card_text(rec, s))
    assert new.variants == rec.variants                       # 双空格被整理，不改任何词


def test_stale_proposition_is_rederived_from_an_edited_claim(rec, orig, k30):
    """研究者只改了来源声明，没改 ⟨ ⟩ 里的 proposition：proposition 应跟着新声明走。"""
    from build_review_report import merged_story
    s = merged_story(rec).replace(
        "**[the public elementary-school year in Japan generally begins in April ｜ "
        "the public elementary-school year in Japan generally begins in September]**",
        "**[the public elementary-school year in Japan generally begins in April ｜ "
        "the public elementary-school year in Japan begins in autumn]**")
    new, notes = _rebuild(orig, k30, _card_text(rec, s))
    assert new.claim_span_conflicting.endswith("begins in autumn")
    assert new.belief_proposition_conflicting == "the public elementary-school year in Japan begins in autumn"
    assert new.belief_proposition_aligned == rec.belief_proposition_aligned          # 没改的一侧保持不变
    assert any("还是旧的" in n for n in notes)


def test_user_edited_proposition_is_kept_when_it_was_edited_too(rec, orig, k30):
    from build_review_report import merged_story
    s = merged_story(rec).replace("[the public elementary-school year in Japan generally begins in April ｜",
                                  "[Japan's public elementary-school year generally begins in April ｜", 1)
    s = s.replace("⟨Grace believes that [the public elementary-school year in Japan generally begins in April ｜",
                  "⟨Grace believes that [Japan's public elementary-school year generally begins in April ｜")
    new, notes = _rebuild(orig, k30, _card_text(rec, s))
    assert new.belief_proposition_aligned == "Japan's public elementary-school year generally begins in April"
    assert not any("还是旧的" in n for n in notes)


def test_gibberish_story_gives_a_clear_error(rec):
    with pytest.raises(ReviewParseError, match="找不到"):
        parse_story("No markers at all.")
    with pytest.raises(ReviewParseError, match="两段"):
        parse_story("It says **[only one claim]**. Next.")


def test_derive_proposition():
    assert derive_proposition("A hygrometer measures air temperature.") == "a hygrometer measures air temperature"
    assert derive_proposition("Mushrooms belong to the plant kingdom.") == "mushrooms belong to the plant kingdom"


# ----------------------------------------------------------------- 问题 / gold 的修改与显式覆盖
def test_changed_question_and_gold_are_picked_up_and_variants_reset(rec, orig, k30):
    text = _card_text(rec)
    text = text.replace("| March | August |", "| Yes | No |").replace(rec.questions.q2, "Will Grace book a fitting?")
    new, notes = _rebuild(orig, k30, text)
    assert new.questions.q2 == "Will Grace book a fitting?"
    assert (new.proposed_gold.aligned.q2, new.proposed_gold.conflicting.q2) == ("Yes", "No")
    assert new.answer_variants.q2_aligned == ["Yes"] and new.answer_variants.q2_conflicting == ["No"]
    assert any("Q2 的 gold 已按你的修改" in n for n in notes)


def test_set_question_override_is_recorded(rec, orig, k30):
    new, notes = _rebuild(orig, k30, _card_text(rec), {("F001", "q1"): "What month does Grace think it is?"})
    assert new.questions.q1 == "What month does Grace think it is?" and any("--set-question" in n for n in notes)


# ----------------------------------------------------------------- 导出：泄漏守门仍然有效
def test_export_blocks_a_question_that_contains_its_own_answer(rec, orig, facts):
    bad = rec.model_copy(update={"questions": rec.questions.model_copy(update={"q1": "Is it April or September?"})})
    *_, failures = export_all([bad], facts, INSTR)
    assert failures and any("参考答案" in f for f in failures)


def test_export_shapes_and_no_answer_keys_in_eval_files(rec, facts):
    pretest, story, gold, requests, failures = export_all([rec], facts, INSTR)
    assert not failures and len(pretest) == 12 and len(story) == 12 and len(requests) == 24
    assert all(len(r["messages"]) == 1 and r["messages"][0]["role"] == "user" for r in requests)
    assert all(r["messages"][0]["content"].endswith(INSTR) for r in requests)
    blob = json.dumps(pretest + story + requests)
    assert not any(k in blob for k in ("reference_answer", "accepted_variants", "gold_status", "world_gold"))
    assert {g["item_id"] for g in gold} == {r["item_id"] for r in pretest + story}
