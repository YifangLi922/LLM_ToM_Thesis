from __future__ import annotations

import pytest

from candidates import build_candidate
from common import answers_equivalent, normalize_answer
from schemas import GenerateFamilyOutput
from validate_candidates import (
    check_bundle, check_family_output, check_propose_output, claim_fidelity, has_errors, scan_q3_leakage,
)


def codes(issues, severity="error"):
    return {i.code for i in issues if i.severity == severity}


# ----------------------------------------------------------------- 答案标准化
@pytest.mark.parametrize("a, b, same", [
    ("8", "eight", True), ("32", "thirty-two", True), ("24 pipe cleaners", "twenty-four pipe cleaners", True),
    ("Eight.", "8", True), ("24", "32", False), ("3 October", "3 November", False),
    ("tip", "no tip", False), ("six", "8", False),
])
def test_answers_equivalent(a, b, same):
    assert answers_equivalent(a, b) is same


def test_normalize_answer_number_words():
    assert normalize_answer("Twenty-Four") == "24" and normalize_answer(" nineteen ") == "19"


# ----------------------------------------------------------------- Stage B
def test_valid_bundle_and_output_pass(propose_out, k30):
    assert not codes(check_propose_output(propose_out, k30, max_bundles=3))


@pytest.mark.parametrize("a, b", [("March", "March"), ("8", "eight"), ("Twenty-four", "24.")])
def test_identical_action_gold_rejected(bundle, k30, a, b):
    bad = bundle.model_copy(update={"aligned_action_gold": a, "conflicting_action_gold": b})
    assert "action_gold_identical" in codes(check_bundle(bad, k30))


def test_too_many_bundles_and_wrong_fact_rejected(propose_out, k30, bundle):
    big = propose_out.model_copy(update={"bundles": [bundle, bundle.model_copy(update={"bundle_id": "B02"})]})
    assert "too_many_bundles" in codes(check_propose_output(big, k30, max_bundles=1))
    assert "fact_id_mismatch" in codes(check_propose_output(propose_out.model_copy(update={"fact_id": "K02"}), k30))


def test_duplicate_bundle_ids_rejected(propose_out, k30, bundle):
    dup = propose_out.model_copy(update={"bundles": [bundle, bundle]})
    assert "bundle_id_duplicate" in codes(check_propose_output(dup, k30))


def test_bundle_risk_and_difficulty_warnings(bundle, k30):
    calc = bundle.model_copy(update={"reasoning_structure": "simple_calculation", "risk_flags": []})
    assert "arithmetic_flag_missing" in codes(check_bundle(calc, k30), "warning")
    ok = calc.model_copy(update={"risk_flags": ["q2_non_tom_difficulty"], "risk_notes": "needs one multiplication"})
    assert "arithmetic_flag_missing" not in codes(check_bundle(ok, k30), "warning")
    nonotes = bundle.model_copy(update={"risk_notes": " "})
    assert "risk_notes_missing" in codes(check_bundle(nonotes, k30), "warning")
    copy_ = bundle.model_copy(update={"reasoning_structure": "direct_copy"})
    assert "direct_copy" in codes(check_bundle(copy_, k30), "warning")


# ----------------------------------------------------------------- Stage D
def test_fixture_family_passes_without_errors(family_out, k30, bundle, asg):
    variants, issues = check_family_output(
        family_out, k30, bundle, expected_template=asg.template_id, expected_agent=asg.agent_name,
        expected_group=asg.name_pool_group, expected_domain=asg.setting_domain)
    assert variants is not None and not codes(issues), issues
    assert not codes(issues, "warning"), "模拟样例本身不应带 warning"


def _mut(family_dict, **over):
    return GenerateFamilyOutput.model_validate({**family_dict, **over})


def test_identical_q2_gold_rejected(family_dict, k30, bundle):
    g = {**family_dict["proposed_gold"], "conflicting": {"q1": "September", "q2": "March"}}
    _, issues = check_family_output(_mut(family_dict, proposed_gold=g), k30, bundle)
    assert "q2_gold_identical" in codes(issues)


def test_identical_q1_gold_rejected(family_dict, k30, bundle):
    g = {**family_dict["proposed_gold"], "conflicting": {"q1": "april", "q2": "August"}}
    _, issues = check_family_output(_mut(family_dict, proposed_gold=g), k30, bundle)
    assert "q1_gold_identical" in codes(issues)


def test_missing_placeholder_rejected_and_not_rendered(family_dict, k30, bundle):
    bad = _mut(family_dict, story_backbone=family_dict["story_backbone"].replace("{{BELIEF_INSERTION}}", ""))
    variants, issues = check_family_output(bad, k30, bundle)
    assert variants is None and "render_failed" in codes(issues)


def test_identical_claim_spans_rejected(family_dict, k30, bundle):
    bad = _mut(family_dict, claim_span_conflicting=family_dict["claim_span_aligned"])
    _, issues = check_family_output(bad, k30, bundle)
    assert "claim_spans_identical" in codes(issues)


@pytest.mark.parametrize("prop, code", [
    ("that the public elementary-school year in Japan generally begins in April", "proposition_leading_that"),
    ("the public elementary-school year in Japan generally begins in April.", "proposition_terminal_punct"),
    ("Grace has learned the school year begins in April", "proposition_leading_agent"),
])
def test_bad_belief_proposition_makes_render_fail(family_dict, k30, bundle, prop, code):
    _, issues = check_family_output(_mut(family_dict, belief_proposition_aligned=prop), k30, bundle)
    assert "render_failed" in codes(issues)
    assert code in next(i.message for i in issues if i.code == "render_failed")


def test_bundle_linkage_mismatches_rejected(family_dict, k30, bundle):
    _, issues = check_family_output(_mut(family_dict, bundle_id="B99", action_type="A3"), k30, bundle)
    assert {"bundle_id_mismatch", "action_type_mismatch"} <= codes(issues)


def test_wrong_fact_rejected(family_dict, facts, bundle):
    k13 = next(f for f in facts if f.fact_id == "K13")
    _, issues = check_family_output(_mut(family_dict), k13, bundle)
    assert "fact_id_mismatch" in codes(issues)


def test_needs_revision_is_reported_as_error(family_dict, k30):
    nr = {**family_dict, "status": "needs_revision", "failure_reason": "No distinct action possible.",
          "story_backbone": None, "validation_status": None}
    variants, issues = check_family_output(GenerateFamilyOutput.model_validate(nr), k30)
    assert variants is None and "needs_revision" in codes(issues)


def test_gold_leak_in_backbone_is_warning(family_dict, k30, bundle):
    bb = family_dict["story_backbone"].replace("uniform fitting, which", "uniform fitting in August, which")
    _, issues = check_family_output(_mut(family_dict, story_backbone=bb), k30, bundle)
    assert "gold_in_backbone" in codes(issues, "warning")


@pytest.mark.parametrize("field, value, warning", [
    ("reality_question", "According to the manual, in which month does the school year begin?", "q3_not_reality_directed"),
    ("reality_question", "In which month does Grace think the school year begins?", "q3_not_reality_directed"),
    ("action_question", "Does Grace believe she should pick March or August?", "q2_cues_belief"),
    ("action_question", "Will Grace schedule the fitting in March or August?", "question_has_alternatives"),
    ("belief_question", "In which month does Grace expect", "question_format"),
])
def test_question_heuristics_warn(family_dict, k30, bundle, field, value, warning):
    _, issues = check_family_output(_mut(family_dict, **{field: value}), k30, bundle)
    assert warning in codes(issues, "warning")


def test_q3_mismatch_with_locked_fact_warns(family_dict, k30, bundle):
    g = {**family_dict["proposed_gold"], "q3": "September"}
    _, issues = check_family_output(_mut(family_dict, proposed_gold=g), k30, bundle)
    assert "q3_vs_world_gold" in codes(issues, "warning")


# ----------------------------------------------------------------- v1.1：Q3 答案泄漏扫描（B4）
def test_aligned_claim_containing_the_answer_is_recorded_not_flagged(family_out, k30):
    hits = scan_q3_leakage(family_out, k30)
    assert [(h.term, h.category, h.where) for h in hits] == [("April", "aligned_source_claim", "claim_span_aligned")]


def test_answer_in_shared_story_text_is_flagged_for_review(family_dict, k30, bundle):
    bb = family_dict["story_backbone"].replace("Japan. One line", "Japan, where classes once began in April. One line")
    out = _mut(family_dict, story_backbone=bb)
    assert any(h.category == "elsewhere" and h.where == "story_shared_text" for h in scan_q3_leakage(out, k30))
    _, issues = check_family_output(out, k30, bundle)
    assert "q3_answer_leakage_review" in codes(issues, "warning")


def test_answer_in_action_question_is_flagged(family_dict, k30):
    out = _mut(family_dict, action_question="Will Grace schedule the fitting before April?")
    assert any(h.where == "action_question" for h in scan_q3_leakage(out, k30))


def test_answer_inside_locked_conflicting_claim_is_flagged(facts, bundle):
    """K27：锁定的 conflicting_claim 本身含真实答案（"rather than diagonally"）。应标记风险，而不是改写知识库。"""
    k27 = next(f for f in facts if f.fact_id == "K27")
    assert "diagonally" in k27.conflicting_claim and k27.world_gold == "diagonally"
    out = GenerateFamilyOutput.model_validate({
        "task_mode": "generate_family", "fact_id": "K27", "bundle_id": "B01", "status": "candidate_generated",
        "template_id": "T1", "agent_name": "Grace", "setting_domain": "hobbies_games", "setting": "chess club",
        "source_type": "guide", "belief_cue_ids": [], "action_type": "A4", "reasoning_structure": "one_step_mapping",
        "story_backbone": "Grace reads that {{CLAIM_SPAN}}.{{BELIEF_INSERTION}} Later she sets up a practice board.",
        "claim_span_aligned": "under standard chess rules, a bishop moves diagonally",
        "claim_span_conflicting": "under standard chess rules, a bishop moves horizontally or vertically rather than diagonally",
        "belief_proposition_aligned": "x", "belief_proposition_conflicting": "y",
        "belief_question": "q?", "action_question": "q?", "reality_question": "q?",
        "proposed_gold": {"aligned": {"q1": "diagonally", "q2": "a"},
                          "conflicting": {"q1": "horizontally or vertically", "q2": "b"}, "q3": "diagonally"},
        "answer_variants": {"q1_aligned": [], "q1_conflicting": [], "q2_aligned": [], "q2_conflicting": [], "q3": []},
        "action_constraints": "c", "belief_to_action_rule": "r", "risk_flags": [], "risk_notes": "",
        "validation_status": "needs_human_review", "failure_reason": None})
    cats = {(h.term, h.category) for h in scan_q3_leakage(out, k27)}
    assert ("diagonally", "aligned_source_claim") in cats and ("diagonally", "conflicting_source_claim") in cats
    _, issues = check_family_output(out, k27)
    assert "q3_answer_in_conflicting_claim" in codes(issues, "warning")


# ----------------------------------------------------------------- v1.1：锁定声明忠实度（粗筛）
def test_claim_fidelity_ratio(k30):
    assert claim_fidelity("the public elementary-school year in Japan generally begins in April", k30.aligned_claim) == 1.0
    assert claim_fidelity("school starts sometime", k30.aligned_claim) < 0.6


def test_claim_span_that_does_not_restate_the_locked_claim_is_an_error(family_dict, k30, bundle):
    bad = _mut(family_dict, claim_span_conflicting="school starts in the fall")
    _, issues = check_family_output(bad, k30, bundle)
    assert "claim_span_not_locked_claim" in codes(issues)


def test_partial_restatement_only_warns(family_dict, k30, bundle):
    bad = _mut(family_dict, claim_span_conflicting="the school year begins in September")
    _, issues = check_family_output(bad, k30, bundle)
    assert "claim_span_fidelity" in codes(issues, "warning") and "claim_span_not_locked_claim" not in codes(issues)


# ----------------------------------------------------------------- 主记录
def test_rejected_candidate_is_kept_with_reasons(family_dict, k30, bundle):
    bad = _mut(family_dict, story_backbone="No placeholders at all.")
    rec = build_candidate(family_id="F002", fact=k30, bundle=bundle, family_out=bad, generator_model="MOCK",
                          prompt_version="x", created_at="2026-01-01T00:00:00+00:00")
    assert rec.validation_status == "auto_rejected" and rec.variants is None and has_errors(rec.issues)
    assert rec.human_validated is False


def test_good_candidate_awaits_human_review(family_out, k30, bundle, asg):
    rec = build_candidate(family_id="F001", fact=k30, bundle=bundle, family_out=family_out, generator_model="MOCK",
                          prompt_version="abc", created_at="2026-01-01T00:00:00+00:00", assignment=asg)
    assert rec.validation_status == "needs_human_review" and rec.human_validated is False
    assert rec.provenance.prompt_version == "abc" and rec.provenance.generator_model == "MOCK"
    assert rec.provenance.guideline_version == "1.1" and rec.provenance.assignments["name_sampling_seed"] == 1
    assert rec.fact.world_gold == "April" and rec.fact.qualification_notes
    assert rec.agent_name == "Grace" and rec.setting_domain == "travel_cultural_orientation"
    assert rec.name_pool_group == "feminine" and rec.risk_notes
    assert rec.variants.explicit_conflicting.count("Grace believes that the public elementary-school year in Japan "
                                                    "generally begins in September.") == 1


def test_needs_revision_cannot_become_record(family_dict, k30, bundle):
    nr = GenerateFamilyOutput.model_validate({**family_dict, "status": "needs_revision",
                                              "failure_reason": "x", "validation_status": None})
    with pytest.raises(ValueError):
        build_candidate(family_id="F003", fact=k30, bundle=bundle, family_out=nr, generator_model="MOCK",
                        prompt_version="x")
