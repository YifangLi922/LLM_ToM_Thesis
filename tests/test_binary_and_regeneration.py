"""二选一限制、人物名字/模板分配检查、自动重新生成机制。全部离线。"""
from __future__ import annotations

import json

import pytest
from openai import AuthenticationError

from candidates import build_candidate
from fakes import REQ, FakeClient, FakeResp, httpx
from generate_families import FEEDBACK_EN, generate_with_regeneration
from generation_prompts import ADDENDUM_GENERATE, ADDENDUM_PROPOSE, generate_payload
from propose_bundles import select_bundle
from sampling import Assignment
from schemas import GenerateFamilyOutput, Issue
from validate_candidates import check_bundle, check_family_output, design_tag, is_binary_design

ASG = Assignment(index=0, template_id="T4A", agent_name="Emma", agent_gender="female")   # 与模拟样例一致


def codes(issues, severity="error"):
    return {i.code for i in issues if i.severity == severity}


def _fam(family_dict, **over):
    return GenerateFamilyOutput.model_validate({**family_dict, **over})


def _with_options(family_dict):
    """把两个竞争的 Q2 答案（32 与 24）写进故事公共文字，制造"二选一"。"""
    bb = family_dict["story_backbone"].replace(
        "holds plenty of pipe cleaners.", "holds plenty of pipe cleaners, so she may need either 32 or 24 of them.")
    return _fam(family_dict, story_backbone=bb)


# ------------------------------------------------------------------ 设计标签与二选一检查
def test_numeric_design_is_open_and_clean(family_out, k01, bundle):
    assert design_tag(family_out) == "open_numeric"
    _, issues = check_family_output(family_out, k01, bundle, expected_template="T4A", expected_agent="Emma",
                                    expected_gender="female")
    assert not codes(issues) and not codes(issues, "warning")


def test_binary_by_nature_is_tagged_even_when_options_are_not_listed(family_out, bundle):
    """K18 新题的情形：故事没有列出选项，但行动本身是 左/右 二选一（模型自己标了 forced_binary_choice）。"""
    binary_bundle = bundle.model_copy(update={"risk_flags": ["forced_binary_choice"]})
    assert design_tag(family_out) == "open_numeric"                       # 不看 bundle 时按答案形式判断
    assert design_tag(family_out, binary_bundle) == "inherently_binary"   # 看 bundle 后如实标成"本质二选一"


def test_both_competing_answers_in_story_is_forced_binary(family_dict, k01, bundle):
    out = _with_options(family_dict)
    assert design_tag(out) == "forced_binary_options"
    _, issues = check_family_output(out, k01, bundle, binary_policy="reject")
    assert "forced_binary_options_in_story" in codes(issues)


def test_warn_policy_only_warns(family_dict, k01, bundle):
    _, issues = check_family_output(_with_options(family_dict), k01, bundle, binary_policy="warn")
    assert "forced_binary_options_in_story" in codes(issues, "warning")
    assert "forced_binary_options_in_story" not in codes(issues)


def test_only_one_answer_visible_is_not_forced_binary(family_dict, k01, bundle):
    bb = family_dict["story_backbone"].replace("holds plenty of pipe cleaners.", "holds plenty of pipe cleaners; 32 are blue.")
    out = _fam(family_dict, story_backbone=bb)
    assert design_tag(out) != "forced_binary_options"
    _, issues = check_family_output(out, k01, bundle)
    assert "forced_binary_options_in_story" not in codes(issues)


def test_either_or_in_story_warns(family_dict, k01, bundle):
    bb = family_dict["story_backbone"].replace("plenty of pipe cleaners.", "plenty of pipe cleaners, either red or green.")
    _, issues = check_family_output(_fam(family_dict, story_backbone=bb), k01, bundle)
    assert "either_or_in_story" in codes(issues, "warning")


def test_classic_k05_k18_shape_is_caught(k01):
    """复现上一轮 K05 / K18 的结构：故事里写了 'either A or B'，且 A、B 就是 Q2 的两个答案。"""
    from schemas import AnswerVariants, GoldPair, ProposedGold

    g = ProposedGold(aligned=GoldPair(q1="floats", q2="water surface"), conflicting=GoldPair(q1="sinks", q2="tank bottom"), q3="floats")
    av = AnswerVariants(q1_aligned=["float"], q1_conflicting=["sink"], q2_aligned=["the water surface"],
                        q2_conflicting=["the tank bottom"], q3=["float"])
    out = GenerateFamilyOutput(
        task_mode="generate_family", fact_id="K01", bundle_id="B01", status="candidate_generated", template_id="T1",
        agent="Maya", setting="s", source_type="handbook", belief_cue_ids=["B4"], action_type="A4",
        reasoning_structure="prediction_application",
        story_backbone="Maya reads: {{CLAIM_SPAN}}.{{BELIEF_INSERTION}} Her narrow view can cover either the water surface or the tank bottom.",
        claim_span_aligned="an ice cube floats", claim_span_conflicting="an ice cube sinks",
        belief_sentence_aligned="Maya believes an ice cube floats.", belief_sentence_conflicting="Maya believes an ice cube sinks.",
        belief_question="What does Maya believe?", action_question="Where will Maya aim the camera?",
        reality_question="What actually happens?", proposed_gold=g, answer_variants=av, action_constraints="c",
        belief_to_action_rule="r", risk_flags=[], potential_ambiguities=[], validation_status="needs_human_review",
        notes=None, revision_reasons=[])
    assert design_tag(out) == "forced_binary_options"


# ------------------------------------------------------------------ 抽样器分配的检查
def test_template_mismatch_is_error(family_out, k01, bundle):
    _, issues = check_family_output(family_out, k01, bundle, expected_template="T2")
    assert "template_mismatch" in codes(issues)


def test_agent_name_must_match_and_appear(family_dict, k01, bundle):
    out = _fam(family_dict)
    _, issues = check_family_output(out, k01, bundle, expected_agent="Sophie", expected_gender="female")
    assert {"agent_mismatch", "agent_not_in_story"} <= codes(issues)


def test_pronoun_mismatch_warns_only(family_dict, k01, bundle):
    bb = family_dict["story_backbone"].replace("her supervisor", "his supervisor")
    _, issues = check_family_output(_fam(family_dict, story_backbone=bb), k01, bundle,
                                    expected_agent="Emma", expected_gender="female")
    assert "pronoun_mismatch" in codes(issues, "warning") and "pronoun_mismatch" not in codes(issues)


# ------------------------------------------------------------------ bundle 级：识别并降权二选一
@pytest.mark.parametrize("flags, a, c, expected", [
    (["binary_location_shortcut"], "water surface", "tank bottom", True),
    (["forced_binary_choice"], "x", "y", True),
    ([], "move to bird column", "no change", True),
    ([], "No change", "move", True),
    (["arithmetic_control_recommended"], "32", "24", False),
])
def test_is_binary_design(bundle, flags, a, c, expected):
    b = bundle.model_copy(update={"risk_flags": flags, "aligned_action_gold": a, "conflicting_action_gold": c})
    assert is_binary_design(b) is expected
    assert ("binary_choice_design" in codes(check_bundle(b), "warning")) is expected


def test_select_bundle_prefers_non_binary_even_with_more_warnings(propose_out, bundle):
    binary = bundle.model_copy(update={"bundle_id": "B01", "risk_flags": ["binary_direction_shortcut"]})
    open_ = bundle.model_copy(update={"bundle_id": "B02"})
    out = propose_out.model_copy(update={"bundles": [binary, open_]})
    w = Issue(severity="warning", code="w", message="w")
    chosen, reason = select_bundle(out, {"B01": [], "B02": [w, w]})     # 二选一那个 warning 更少，但仍应选 B02
    assert chosen.bundle_id == "B02" and "非二选一" in reason
    only_binary, reason2 = select_bundle(out.model_copy(update={"bundles": [binary]}), {"B01": []})
    assert only_binary.bundle_id == "B01" and "只能从中选择" in reason2


# ------------------------------------------------------------------ prompt 与 payload
def test_prompt_rules_and_payload_carry_assignments(k01, bundle):
    assert "forced_binary_choice" in ADDENDUM_PROPOSE and "open-ended" in ADDENDUM_PROPOSE
    assert "must not list, name or enumerate the competing answers" in ADDENDUM_GENERATE
    assert "assignments.agent_name" in ADDENDUM_GENERATE and "revision_feedback" in ADDENDUM_GENERATE
    p = generate_payload(k01, bundle, template_id="T3", agent_name="Hannah", agent_gender="female",
                         revision_feedback=["fix it"])
    assert p["assignments"]["agent_name"] == "Hannah" and p["assignments"]["agent_gender"] == "female"
    assert p["assignments"]["template_id"] == "T3" and p["revision_feedback"] == ["fix it"]
    assert generate_payload(k01, bundle, template_id="T3")["revision_feedback"] == []


def test_candidate_records_assignment_and_design_tag(family_out, k01, bundle):
    rec = build_candidate(family_id="F001", fact=k01, bundle=bundle, family_out=family_out, generator_model="MOCK",
                          prompt_version="x", created_at="2026-01-01T00:00:00+00:00", assignment=ASG)
    assert rec.provenance.assignments == {"index": 0, "template_id": "T4A", "agent_name": "Emma", "agent_gender": "female"}
    assert rec.design_tag == "open_numeric" and rec.validation_status == "needs_human_review"


# ------------------------------------------------------------------ 自动重新生成
def _regen(client, k01, bundle, max_regen=2, policy="reject"):
    return generate_with_regeneration(
        client, model="m", fact=k01, bundle=bundle, assignment=ASG, family_id="F001", max_output_tokens=100,
        max_retries=0, max_regenerations=max_regen, binary_policy=policy, notes="t")


def _resp(family_dict, **over):
    return FakeResp(json.dumps({**family_dict, **over}))


def test_regenerates_after_forced_binary_and_passes_feedback(family_dict, k01, bundle):
    bad = _resp(family_dict, story_backbone=_with_options(family_dict).story_backbone)
    c = FakeClient(bad, _resp(family_dict))
    attempts = _regen(c, k01, bundle)
    assert [a.number for a in attempts] == [1, 2]
    assert attempts[0].record.validation_status == "auto_rejected"
    assert attempts[1].record.validation_status == "needs_human_review"
    assert attempts[1].feedback_given == [FEEDBACK_EN["forced_binary_options_in_story"]]
    sent = json.loads(c.calls[1]["input"])
    assert sent["revision_feedback"] and sent["assignments"]["agent_name"] == "Emma"
    assert json.loads(c.calls[0]["input"])["revision_feedback"] == []


def test_regeneration_is_bounded_and_keeps_the_rejected_record(family_dict, k01, bundle):
    bad = _with_options(family_dict).story_backbone
    c = FakeClient(*[_resp(family_dict, story_backbone=bad) for _ in range(5)])
    attempts = _regen(c, k01, bundle, max_regen=2)
    assert len(attempts) == 3 and len(c.calls) == 3
    assert attempts[-1].record.validation_status == "auto_rejected"


def test_no_regeneration_when_first_attempt_is_fine(family_dict, k01, bundle):
    c = FakeClient(_resp(family_dict))
    assert len(_regen(c, k01, bundle)) == 1 and len(c.calls) == 1


def test_needs_revision_is_not_regenerated(family_dict, k01, bundle):
    nr = {**family_dict, "status": "needs_revision", "revision_reasons": ["no distinct action possible"],
          "validation_status": None}
    c = FakeClient(FakeResp(json.dumps(nr)), _resp(family_dict))
    attempts = _regen(c, k01, bundle)
    assert len(attempts) == 1 and attempts[0].record is None and len(c.calls) == 1


def test_api_errors_are_not_regenerated(k01, bundle, family_dict):
    err = AuthenticationError("bad key", response=httpx.Response(401, request=REQ), body=None)
    c = FakeClient(err, _resp(family_dict))
    attempts = _regen(c, k01, bundle)
    assert len(attempts) == 1 and attempts[0].call.error_type == "api_error" and len(c.calls) == 1


def test_invalid_json_triggers_a_regeneration(family_dict, k01, bundle):
    c = FakeClient(FakeResp("{not json"), _resp(family_dict))
    attempts = _regen(c, k01, bundle)
    assert len(attempts) == 2 and attempts[1].record.validation_status == "needs_human_review"
    assert "unusable" in attempts[1].feedback_given[0]


def test_wrong_agent_name_triggers_regeneration(family_dict, k01, bundle):
    wrong = _resp(family_dict, agent="Zoe")
    c = FakeClient(wrong, _resp(family_dict))
    attempts = _regen(c, k01, bundle)
    assert len(attempts) == 2 and "agent_mismatch" in [i.code for i in attempts[0].record.issues]
