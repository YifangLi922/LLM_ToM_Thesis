from __future__ import annotations

import pytest

from candidates import build_candidate
from common import answers_equivalent, normalize_answer
from schemas import GenerateFamilyOutput
from validate_candidates import check_bundle, check_family_output, check_propose_output, has_errors


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
def test_valid_bundle_and_output_pass(propose_out, k01):
    assert not codes(check_propose_output(propose_out, k01, max_bundles=3))


@pytest.mark.parametrize("a, b", [("24", "24"), ("8", "eight"), ("Twenty-four", "24.")])
def test_identical_action_gold_rejected(propose_out, bundle, a, b):
    bad = bundle.model_copy(update={"aligned_action_gold": a, "conflicting_action_gold": b})
    assert "action_gold_identical" in codes(check_bundle(bad))


def test_too_many_bundles_and_wrong_fact_rejected(propose_out, k01, bundle):
    big = propose_out.model_copy(update={"bundles": [bundle, bundle.model_copy(update={"bundle_id": "B02"})]})
    assert "too_many_bundles" in codes(check_propose_output(big, k01, max_bundles=1))
    assert "fact_id_mismatch" in codes(check_propose_output(propose_out.model_copy(update={"fact_id": "K02"}), k01))


def test_duplicate_bundle_ids_rejected(propose_out, k01, bundle):
    dup = propose_out.model_copy(update={"bundles": [bundle, bundle]})
    assert "bundle_id_duplicate" in codes(check_propose_output(dup, k01))


# ----------------------------------------------------------------- Stage D
def test_fixture_family_passes_without_errors(family_out, k01, bundle):
    variants, issues = check_family_output(family_out, k01, bundle)
    assert variants is not None and not codes(issues), issues
    assert not codes(issues, "warning"), "模拟样例本身不应带 warning"


def _mut(family_dict, **over):
    return GenerateFamilyOutput.model_validate({**family_dict, **over})


def test_identical_q2_gold_rejected(family_dict, k01, bundle):
    g = {**family_dict["proposed_gold"], "conflicting": {"q1": "6", "q2": "32"}}
    _, issues = check_family_output(_mut(family_dict, proposed_gold=g), k01, bundle)
    assert "q2_gold_identical" in codes(issues)


def test_identical_q1_gold_rejected(family_dict, k01, bundle):
    g = {**family_dict["proposed_gold"], "conflicting": {"q1": "eight", "q2": "24"}}
    _, issues = check_family_output(_mut(family_dict, proposed_gold=g), k01, bundle)
    assert "q1_gold_identical" in codes(issues)


def test_missing_placeholder_rejected_and_not_rendered(family_dict, k01, bundle):
    bad = _mut(family_dict, story_backbone=family_dict["story_backbone"].replace("{{BELIEF_INSERTION}}", ""))
    variants, issues = check_family_output(bad, k01, bundle)
    assert variants is None and "render_failed" in codes(issues)


def test_identical_claim_spans_rejected(family_dict, k01, bundle):
    bad = _mut(family_dict, claim_span_conflicting=family_dict["claim_span_aligned"])
    _, issues = check_family_output(bad, k01, bundle)
    assert "claim_spans_identical" in codes(issues)


def test_bundle_linkage_mismatches_rejected(family_dict, k01, bundle):
    _, issues = check_family_output(_mut(family_dict, bundle_id="B99", action_type="A3"), k01, bundle)
    assert {"bundle_id_mismatch", "action_type_mismatch"} <= codes(issues)


def test_wrong_fact_rejected(family_dict, facts, bundle):
    k02 = next(f for f in facts if f.fact_id == "K02")
    _, issues = check_family_output(_mut(family_dict), k02, bundle)
    assert "fact_id_mismatch" in codes(issues)


def test_needs_revision_is_reported_as_error(family_dict, k01):
    nr = {**family_dict, "status": "needs_revision", "revision_reasons": ["No distinct action possible."],
          "story_backbone": None, "validation_status": None}
    variants, issues = check_family_output(GenerateFamilyOutput.model_validate(nr), k01)
    assert variants is None and "needs_revision" in codes(issues)


def test_gold_leak_in_backbone_is_warning(family_dict, k01, bundle):
    bb = family_dict["story_backbone"].replace("plenty of pipe cleaners", "plenty of pipe cleaners (24 are blue)")
    _, issues = check_family_output(_mut(family_dict, story_backbone=bb), k01, bundle)
    assert "gold_in_backbone" in codes(issues, "warning")


@pytest.mark.parametrize("field, value, warning", [
    ("reality_question", "According to the manual, how many legs does a spider have?", "q3_not_reality_directed"),
    ("reality_question", "How many legs does Emma think a spider has?", "q3_not_reality_directed"),
    ("action_question", "Does Emma believe she needs 24 or 32 pipe cleaners?", "q2_cues_belief"),
    ("action_question", "Will Emma set aside 24 or 32 pipe cleaners?", "question_has_alternatives"),
    ("belief_question", "How many legs does Emma expect", "question_format"),
])
def test_question_heuristics_warn(family_dict, k01, bundle, field, value, warning):
    _, issues = check_family_output(_mut(family_dict, **{field: value}), k01, bundle)
    assert warning in codes(issues, "warning")


def test_q3_mismatch_with_locked_fact_warns(family_dict, k01, bundle):
    g = {**family_dict["proposed_gold"], "q3": "6"}
    _, issues = check_family_output(_mut(family_dict, proposed_gold=g), k01, bundle)
    assert "q3_vs_world_gold" in codes(issues, "warning")


# ----------------------------------------------------------------- 主记录
def test_rejected_candidate_is_kept_with_reasons(family_dict, k01, bundle):
    bad = _mut(family_dict, story_backbone="No placeholders at all.")
    rec = build_candidate(family_id="F002", fact=k01, bundle=bundle, family_out=bad, generator_model="MOCK",
                          prompt_version="x", created_at="2026-01-01T00:00:00+00:00")
    assert rec.validation_status == "auto_rejected" and rec.variants is None and has_errors(rec.issues)
    assert rec.human_validated is False


def test_good_candidate_awaits_human_review(family_out, k01, bundle):
    rec = build_candidate(family_id="F001", fact=k01, bundle=bundle, family_out=family_out, generator_model="MOCK",
                          prompt_version="abc", created_at="2026-01-01T00:00:00+00:00")
    assert rec.validation_status == "needs_human_review" and rec.human_validated is False
    assert rec.provenance.prompt_version == "abc" and rec.provenance.generator_model == "MOCK"
    assert rec.fact.world_gold == "8"


def test_needs_revision_cannot_become_record(family_dict, k01, bundle):
    nr = GenerateFamilyOutput.model_validate({**family_dict, "status": "needs_revision",
                                              "revision_reasons": ["x"], "validation_status": None})
    with pytest.raises(ValueError):
        build_candidate(family_id="F003", fact=k01, bundle=bundle, family_out=nr, generator_model="MOCK",
                        prompt_version="x")
