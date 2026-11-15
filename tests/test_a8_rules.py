"""guideline A8 相关的新规则：110 词硬上限、正则标记（隐藏选项菜单 / 规则谜题 / 技术性免责声明）、
A8 文本已进入 prompt 与完整 guideline、gold 带句号的检测修复、Q1 gold 用包含判断。全部离线。"""
from __future__ import annotations

import json

import pytest

from common import GUIDELINE_PATH
from fakes import FakeClient, FakeResp
from generate_families import FEEDBACK_EN, generate_with_regeneration
from generation_prompts import ADDENDUM_GENERATE, ADDENDUM_PROPOSE, load_model_prompt
from render_pairs import MAX_STORY_WORDS, check_minimal_pairs, render_variants
from schemas import GenerateFamilyOutput
from validate_candidates import check_family_output, design_tag

CA, CC = "cats have four legs", "cats have six legs"
AG = "Ann"


def codes(issues, severity="error"):
    return {i.code for i in issues if i.severity == severity}


def _mut(family_dict, **over):
    return GenerateFamilyOutput.model_validate({**family_dict, **over})


def _padded_story(total_words: int) -> str:
    """implicit 故事恰好 total_words 个词（claim 为 'cats have six legs'）。"""
    head = "Ann reads the manual. It says that {{CLAIM_SPAN}}.{{BELIEF_INSERTION}} "
    base = len("Ann reads the manual. It says that cats have six legs.".split())
    return head + " ".join(["w"] * (total_words - base))


def _check(bb):
    v = render_variants(bb, CA, CC, CA, CC, AG)
    return v, check_minimal_pairs(v, CA, CC, CA, CC, AG)


# ----------------------------------------------------------------- 110 词硬上限
def test_limit_constant_is_110():
    assert MAX_STORY_WORDS == 110


def test_exactly_110_words_passes_111_is_an_error():
    v110, issues110 = _check(_padded_story(110))
    assert len(v110.implicit_conflicting.split()) == 110 and "story_too_long" not in codes(issues110)
    v111, issues111 = _check(_padded_story(111))
    assert len(v111.implicit_conflicting.split()) == 111 and "story_too_long" in codes(issues111)
    assert "story_length" not in codes(issues111, "warning")           # 超长是 error，不再是 warning


def test_under_70_words_only_warns():
    _, issues = _check(_padded_story(60))
    assert "story_length" in codes(issues, "warning") and "story_too_long" not in codes(issues)


def test_the_longer_implicit_variant_counts():
    ca, cc = "cats have four legs", "cats have six legs and a very long tail indeed"
    bb = "Ann reads the manual. It says that {{CLAIM_SPAN}}.{{BELIEF_INSERTION}} " + " ".join(["w"] * 97)
    v = render_variants(bb, ca, cc, ca, cc, AG)
    assert len(v.implicit_aligned.split()) <= 110 < len(v.implicit_conflicting.split())
    assert "story_too_long" in codes(check_minimal_pairs(v, ca, cc, ca, cc, AG))


def test_over_length_story_is_an_error_in_the_family_check(family_dict, k30, bundle):
    long_bb = family_dict["story_backbone"].replace(
        "before the school year starts.", "before the school year starts. " + " ".join(["She checks the list again."] * 10))
    _, issues = check_family_output(_mut(family_dict, story_backbone=long_bb), k30, bundle)
    assert "story_too_long" in codes(issues)


def test_over_length_story_triggers_regeneration_with_feedback(family_dict, k30, bundle, asg):
    long_bb = family_dict["story_backbone"].replace(
        "before the school year starts.", "before the school year starts. " + " ".join(["She checks the list again."] * 10))
    c = FakeClient(FakeResp(json.dumps({**family_dict, "story_backbone": long_bb})), FakeResp(json.dumps(family_dict)))
    attempts = generate_with_regeneration(
        c, model="m", fact=k30, bundle=bundle, assignment=asg, family_id="F001", max_output_tokens=100,
        max_retries=0, max_regenerations=2, notes="t")
    assert [a.record.validation_status for a in attempts] == ["auto_rejected", "needs_human_review"]
    assert "story_too_long" in [i.code for i in attempts[0].record.issues]
    assert attempts[1].feedback_given == [FEEDBACK_EN["story_too_long"]]
    assert "110 words" in FEEDBACK_EN["story_too_long"]


# ----------------------------------------------------------------- 正则标记（只标记，不拒绝）
def _story_with(family_dict, extra: str) -> str:
    return family_dict["story_backbone"].replace("before the school year starts.", f"before the school year starts. {extra}")


@pytest.mark.parametrize("extra, code", [
    ("The fitting takes exactly one hour.", "pattern_exactly"),
    ("Two slots are available: March and August.", "pattern_available_list"),
    ("Slots available: March, August.", "pattern_available_list"),
    ("She may book either March or August.", "either_or_in_story"),
    ("She has two options for the fitting.", "pattern_two_options"),
    ("She must choose between the slots.", "pattern_two_options"),
    ("Book the fitting early if possible; otherwise wait.", "pattern_rule_puzzle"),
    ("The rod has no phase change or competing forces.", "pattern_technical_caveat"),
    ("Both trays are wide enough.", "pattern_technical_caveat"),
    ("The tile is linked to an ordinary single-function hygrometer.", "pattern_technical_caveat"),
    ("The tile is linked to a single function sensor.", "pattern_technical_caveat"),
    ("The tile is linked to a multi-function device.", "pattern_technical_caveat"),
])
def test_story_patterns_are_flagged_as_warnings_only(family_dict, k30, bundle, extra, code):
    _, issues = check_family_output(_mut(family_dict, story_backbone=_story_with(family_dict, extra)), k30, bundle)
    assert code in codes(issues, "warning")
    assert code not in codes(issues)


def test_clean_story_has_no_pattern_flags(family_out, k30, bundle):
    _, issues = check_family_output(family_out, k30, bundle)
    assert not {c for c in codes(issues, "warning") if c.startswith("pattern_") or c == "either_or_in_story"}


@pytest.mark.parametrize("extra", [
    "Two controls are available: admit air into the gap, or activate the transmitter.",
    "The available trays have usable lengths of exactly 20 cm and 21 cm; both are wide enough.",
])
def test_the_two_typical_v1_run_patterns_would_be_flagged(family_dict, k30, bundle, extra):
    """gpt-6.1-sol 第一轮的两个典型写法：把候选行动/数值列进故事。"""
    _, issues = check_family_output(_mut(family_dict, story_backbone=_story_with(family_dict, extra)), k30, bundle)
    assert codes(issues, "warning") & {"pattern_available_list", "either_or_in_story", "pattern_exactly"}


# ----------------------------------------------------------------- gold 带句号 / Q1 gold 包含判断
def test_gold_with_terminal_period_is_still_found_in_the_story(family_dict, k30):
    g = {**family_dict["proposed_gold"], "aligned": {"q1": "April", "q2": "Book the fitting early."},
         "conflicting": {"q1": "September", "q2": "Skip the fitting."}}
    bb = _story_with(family_dict, "She can book the fitting early or skip the fitting.")
    assert design_tag(_mut(family_dict, proposed_gold=g, story_backbone=bb), k30) == "forced_binary_options"


def test_fuller_q1_gold_is_not_flagged_when_it_contains_the_locked_gold(family_dict, k30, bundle):
    g = {**family_dict["proposed_gold"], "aligned": {"q1": "It begins in April.", "q2": "March"},
         "conflicting": {"q1": "In September.", "q2": "August"}}
    _, issues = check_family_output(_mut(family_dict, proposed_gold=g), k30, bundle)
    assert not {"q1_aligned_vs_world_gold", "q1_conflicting_vs_belief_gold"} & codes(issues, "warning")
    g2 = {**g, "aligned": {"q1": "May", "q2": "March"}}
    _, issues2 = check_family_output(_mut(family_dict, proposed_gold=g2), k30, bundle)
    assert "q1_aligned_vs_world_gold" in codes(issues2, "warning")


# ----------------------------------------------------------------- A8 文本在 prompt 与完整 guideline 里
@pytest.mark.parametrize("text", [load_model_prompt(), GUIDELINE_PATH.read_text(encoding="utf-8")],
                         ids=["model_prompt", "full_guideline"])
def test_a8_text_is_present(text):
    assert "## A8. Naturalness and open-response actions" in text
    assert "Open response, not a hidden menu." in text and "Two controls are available" in text
    assert "No rule puzzles." in text and "Qualifications constrain you, not the story." in text
    assert "Put residual caution in metadata." in text and "Hard limit: 110 words" in text
    assert "110 is a hard upper limit" in text                     # A6 与 A8 保持一致


def test_a8_follows_a7_in_part_a_and_is_not_in_part_b():
    g = GUIDELINE_PATH.read_text(encoding="utf-8")
    assert g.index("## A7.") < g.index("## A8.") < g.index("# Part B")
    assert "## A8." in load_model_prompt() and "Part B" not in load_model_prompt()


def test_addenda_mention_a8_and_the_word_limit():
    assert "A8" in ADDENDUM_PROPOSE and "OPEN answer space" in ADDENDUM_PROPOSE
    assert "110 words" in ADDENDUM_GENERATE and "A8" in ADDENDUM_GENERATE


# ----------------------------------------------------------------- claim span 必须复述锁定的事实（所有模板，含 T4C）
def test_indirect_routine_paraphrase_instead_of_the_locked_claim_is_rejected_and_regenerated(facts, bundle, asg):
    """复现上一轮 K18 的问题：claim span 写成"标记的位置在室温端点之外"，而不是锁定的 claim。"""
    from conftest import FIXTURE_PATH

    k18 = next(f for f in facts if f.fact_id == "K18")
    fx = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["family_output"]
    bad = {**fx, "fact_id": "K18",
           "story_backbone": ("Grace is new to metalwork at a club. Across several demonstrations, her instructor marks each "
                              "rod's expected tip position after warming {{CLAIM_SPAN}}.{{BELIEF_INSERTION}} Later, Grace sketches "
                              "a storage recess for a different iron rod and wants it to match the warm rod's length."),
           "claim_span_aligned": "beyond its room-temperature tip", "claim_span_conflicting": "short of its room-temperature tip",
           "belief_proposition_aligned": "an iron rod generally expands in length when heated moderately",
           "belief_proposition_conflicting": "an iron rod generally contracts in length when heated moderately",
           "proposed_gold": {"aligned": {"q1": "expands", "q2": "longer"}, "conflicting": {"q1": "contracts", "q2": "shorter"},
                             "q3": "expands"}}
    out = GenerateFamilyOutput.model_validate(bad)
    _, issues = check_family_output(out, k18)
    assert "claim_span_not_locked_claim" in codes(issues)
    good = {**bad, "claim_span_aligned": "an unconstrained iron rod generally expands in length when heated moderately",
            "claim_span_conflicting": "an unconstrained iron rod generally contracts in length when heated moderately"}
    _, issues2 = check_family_output(GenerateFamilyOutput.model_validate(good), k18)
    assert "claim_span_not_locked_claim" not in codes(issues2)


def test_claim_span_error_triggers_regeneration_with_feedback(family_dict, k30, bundle, asg):
    c = FakeClient(FakeResp(json.dumps({**family_dict, "claim_span_conflicting": "school starts in the fall"})),
                   FakeResp(json.dumps(family_dict)))
    attempts = generate_with_regeneration(
        c, model="m", fact=k30, bundle=bundle, assignment=asg, family_id="F001", max_output_tokens=100,
        max_retries=0, max_regenerations=2, notes="t")
    assert attempts[0].record.validation_status == "auto_rejected" and attempts[1].record.validation_status == "needs_human_review"
    assert attempts[1].feedback_given == [FEEDBACK_EN["claim_span_not_locked_claim"]]
    assert "indirect or behavioural paraphrase" in FEEDBACK_EN["claim_span_not_locked_claim"]


@pytest.mark.parametrize("text", [load_model_prompt(), GUIDELINE_PATH.read_text(encoding="utf-8")],
                         ids=["model_prompt", "full_guideline"])
def test_claim_span_rule_is_in_prompt_and_guideline(text):
    assert "restate the locked claim itself" in text
    t4c_row = next(line for line in text.splitlines() if line.startswith("| **T4C**"))
    assert "claim span must still restate the locked claim itself" in t4c_row


def test_addendum_requires_restating_the_locked_claim():
    assert "restate the locked aligned_claim / conflicting_claim itself" in ADDENDUM_GENERATE.replace("\n", " ")


# ----------------------------------------------------------------- A6：Q3 Leakage Prevention
@pytest.mark.parametrize("text", [load_model_prompt(), GUIDELINE_PATH.read_text(encoding="utf-8")],
                         ids=["model_prompt", "full_guideline"])
def test_q3_leakage_prevention_block_is_in_a6(text):
    assert "**Q3 Leakage Prevention**" in text
    for bullet in ("Prefer false claims stated positively, without mentioning the true answer as a rejected alternative.",
                   'Avoid phrases such as "instead of X" or "rather than X" when X is the real answer.',
                   "If a locked claim contains the real answer, flag it for researcher review. Do not rewrite it.",
                   "Unavoidable exposure in comparative claims should be flagged, not silently removed."):
        assert bullet in text
    assert text.index("**Q3 answer-leakage rule:**") < text.index("**Q3 Leakage Prevention**") < text.index("## A7.")
