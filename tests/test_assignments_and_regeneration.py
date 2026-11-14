"""设计标签（二选一只记录）、人物名字/代词/场景域分配检查、场景域改派、自动重新生成机制。全部离线。"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest
from openai import AuthenticationError

from candidates import build_candidate
from config import load_config
from fakes import REQ, FakeClient, FakeResp, httpx
from generate_families import FEEDBACK_EN, generate_with_regeneration
from generation_prompts import (
    ADDENDUM_COMMON, ADDENDUM_GENERATE, ADDENDUM_PROPOSE, generate_payload, propose_payload,
)
from propose_bundles import propose_with_domain_fallback, select_bundle
from sampling import AssignmentSampler
from schemas import GenerateFamilyOutput, Issue
from validate_candidates import check_bundle, check_family_output, design_tag, is_binary_design


def codes(issues, severity="error"):
    return {i.code for i in issues if i.severity == severity}


def _fam(family_dict, **over):
    return GenerateFamilyOutput.model_validate({**family_dict, **over})


def _check(out, k30, bundle, asg):
    return check_family_output(out, k30, bundle, expected_template=asg.template_id, expected_agent=asg.agent_name,
                               expected_group=asg.name_pool_group, expected_domain=asg.setting_domain)


def _with_options(family_dict):
    """把两个竞争的 Q2 答案（March 与 August）写进故事公共文字，制造"二选一"。"""
    bb = family_dict["story_backbone"].replace(
        "before the school year starts.", "before the school year starts, so it will be either March or August.")
    return _fam(family_dict, story_backbone=bb)


# ------------------------------------------------------------------ 二选一：只记录，不拒绝（用户决定，2026-11-14）
def test_open_design_is_clean(family_out, k30, bundle, asg):
    assert design_tag(family_out, k30, bundle) == "open_other"
    _, issues = _check(family_out, k30, bundle, asg)
    assert not codes(issues) and not codes(issues, "warning")


def test_both_competing_answers_in_story_is_tagged_and_only_warns(family_dict, k30, bundle, asg):
    out = _with_options(family_dict)
    assert design_tag(out, k30, bundle) == "forced_binary_options"
    _, issues = _check(out, k30, bundle, asg)
    assert "forced_binary_options_in_story" in codes(issues, "warning")
    assert "forced_binary_options_in_story" not in codes(issues)        # 不再是 error：不会自动拒绝
    rec = build_candidate(family_id="F001", fact=k30, bundle=bundle, family_out=out, generator_model="MOCK",
                          prompt_version="x", assignment=asg)
    assert rec.design_tag == "forced_binary_options" and rec.validation_status == "needs_human_review"


def test_fact_pair_answers_are_tagged_inherently_binary(family_dict, k30):
    """Q2 的两个答案恰好就是事实本身的 对/错 两个选项（如 April / September），即使故事没有列出选项。"""
    g = {**family_dict["proposed_gold"], "aligned": {"q1": "April", "q2": "April"},
         "conflicting": {"q1": "September", "q2": "September"}}
    assert design_tag(_fam(family_dict, proposed_gold=g), k30) == "inherently_binary"


def test_only_one_answer_visible_is_not_forced_binary(family_dict, k30, bundle):
    bb = family_dict["story_backbone"].replace("before the school year starts.", "before the school year starts, in March.")
    assert design_tag(_fam(family_dict, story_backbone=bb), k30, bundle) != "forced_binary_options"


def test_either_or_in_story_warns(family_dict, k30, bundle):
    bb = family_dict["story_backbone"].replace("uniform fitting", "uniform fitting, either blue or green,")
    _, issues = check_family_output(_fam(family_dict, story_backbone=bb), k30, bundle)
    assert "either_or_in_story" in codes(issues, "warning")


@pytest.mark.parametrize("a, c, expected", [
    ("April", "September", True),            # 恰为 K30 的 world_gold / conflicting_belief_gold
    ("move to bird column", "no change", True),
    ("No change", "move", True),
    ("March", "August", False),
])
def test_is_binary_design(bundle, k30, a, c, expected):
    b = bundle.model_copy(update={"aligned_action_gold": a, "conflicting_action_gold": c})
    assert is_binary_design(b, k30) is expected
    assert ("binary_choice_design" in codes(check_bundle(b, k30), "warning")) is expected
    assert "binary_choice_design" not in codes(check_bundle(b, k30))     # 只是 warning


def test_select_bundle_no_longer_deprioritises_binary_designs(propose_out, bundle):
    """二选一只记录：选 bundle 时只看 error / warning 数量，并列取先提出者。"""
    binary = bundle.model_copy(update={"bundle_id": "B01", "aligned_action_gold": "April", "conflicting_action_gold": "September"})
    open_ = bundle.model_copy(update={"bundle_id": "B02"})
    out = propose_out.model_copy(update={"bundles": [binary, open_]})
    w = Issue(severity="warning", code="w", message="w")
    chosen, _ = select_bundle(out, {"B01": [], "B02": [w, w]})
    assert chosen.bundle_id == "B01"
    chosen2, _ = select_bundle(out, {"B01": [w], "B02": [w]})
    assert chosen2.bundle_id == "B01"


# ------------------------------------------------------------------ 抽样器分配的检查
def test_template_mismatch_is_error(family_out, k30, bundle):
    _, issues = check_family_output(family_out, k30, bundle, expected_template="T2")
    assert "template_mismatch" in codes(issues)


def test_setting_domain_must_match_assignment(family_dict, k30, bundle):
    _, issues = check_family_output(_fam(family_dict, setting_domain="arts_media"), k30, bundle,
                                    expected_domain="travel_cultural_orientation")
    assert "setting_domain_mismatch" in codes(issues)


def test_agent_name_must_match_and_appear(family_dict, k30, bundle):
    _, issues = check_family_output(_fam(family_dict), k30, bundle, expected_agent="Sophia", expected_group="feminine")
    assert {"agent_mismatch", "agent_not_in_story"} <= codes(issues)


def test_pronoun_mismatch_warns_only_feminine_group(family_dict, k30, bundle):
    bb = family_dict["story_backbone"].replace("tells her", "tells him")
    _, issues = check_family_output(_fam(family_dict, story_backbone=bb), k30, bundle,
                                    expected_agent="Grace", expected_group="feminine")
    assert "pronoun_mismatch" in codes(issues, "warning") and "pronoun_mismatch" not in codes(issues)


def test_pronoun_mismatch_warns_only_masculine_group(family_dict, k30, bundle):
    """故事里用 her 指 Grace，但如果被分配的名字属于 masculine 组（he/him），应提醒。"""
    bb = family_dict["story_backbone"].replace("Grace", "Jack")
    out = _fam(family_dict, agent_name="Jack", story_backbone=bb)
    _, issues = check_family_output(out, k30, bundle, expected_agent="Jack", expected_group="masculine")
    assert "pronoun_mismatch" in codes(issues, "warning")


def test_matching_pronouns_do_not_warn(family_out, k30, bundle):
    _, issues = check_family_output(family_out, k30, bundle, expected_agent="Grace", expected_group="feminine")
    assert "pronoun_mismatch" not in codes(issues, "warning")


# ------------------------------------------------------------------ prompt 与 payload
def test_prompt_rules_and_payload_carry_assignments(k30, bundle):
    # v1.0 时代的规则不再出现：不再要求避开二选一、不再使用自由文本的 forced_binary_choice 标签
    assert "forced_binary_choice" not in ADDENDUM_PROPOSE and "enumerate the competing answers" not in ADDENDUM_GENERATE
    assert "guideline section" not in (ADDENDUM_COMMON + ADDENDUM_PROPOSE + ADDENDUM_GENERATE)
    assert "revision_reasons" not in ADDENDUM_GENERATE and "failure_reason" in ADDENDUM_GENERATE
    assert "controlled vocabulary" in ADDENDUM_COMMON and "approved" in ADDENDUM_COMMON
    assert "assignments.agent_name" in ADDENDUM_GENERATE and "assignments.setting_domain" in ADDENDUM_GENERATE
    assert "assignments.agent_pronouns" in ADDENDUM_GENERATE and "revision_feedback" in ADDENDUM_GENERATE
    assert "believes that" in ADDENDUM_GENERATE and "gender" not in ADDENDUM_GENERATE.lower()
    p = generate_payload(k30, bundle, template_id="T3", agent_name="Hannah", agent_pronouns="she/her",
                         setting_domain="museum_exhibition", setting_label="natural history museum",
                         revision_feedback=["fix it"])
    a = p["assignments"]
    assert a["agent_name"] == "Hannah" and a["agent_pronouns"] == "she/her" and "agent_gender" not in a
    assert a["setting_domain"] == "museum_exhibition" and a["setting_label"] == "natural history museum"
    assert a["template_id"] == "T3" and p["revision_feedback"] == ["fix it"]
    assert generate_payload(k30, bundle, template_id="T3")["revision_feedback"] == []
    pp = propose_payload(k30, max_bundles=2, setting_domain="arts_media")
    assert pp["assignments"]["setting_domain"] == "arts_media" and pp["assignments"]["setting_label"] is None


def test_candidate_records_assignment_and_design_tag(family_out, k30, bundle, asg):
    rec = build_candidate(family_id="F001", fact=k30, bundle=bundle, family_out=family_out, generator_model="MOCK",
                          prompt_version="x", created_at="2026-01-01T00:00:00+00:00", assignment=asg)
    assert rec.provenance.assignments == {
        "index": 0, "template_id": "T5", "agent_name": "Grace", "name_pool_group": "feminine",
        "setting_domain": "travel_cultural_orientation", "name_sampling_seed": 1, "domain_attempt": 0}
    assert rec.design_tag == "open_other" and rec.validation_status == "needs_human_review"


# ------------------------------------------------------------------ 场景域改派（propose 阶段）
def _sampler():
    return AssignmentSampler.from_config(load_config().sampling)


def _no_valid(fact_id="K30"):
    return FakeResp(json.dumps({"task_mode": "propose_bundles", "fact_id": fact_id, "status": "no_valid_bundle",
                                "bundles": [], "failure_reason": "No natural action in this setting domain."}))


def _kw(k30):
    return dict(model="m", fact=k30, max_bundles=3, max_output_tokens=100, max_retries=0, template_id="T5")


def test_domain_is_reassigned_after_no_valid_bundle(fixture_raw, k30):
    s = _sampler()
    asg = s.assignment_for(4)
    order = s.domain_order(4)
    good = FakeResp(json.dumps(fixture_raw["propose_output"]))
    c = FakeClient(_no_valid(), good)
    final, attempts = propose_with_domain_fallback(c, sampler=s, assignment=asg, max_domain_reassignments=2, **_kw(k30))
    assert [a.domain for a in attempts] == order[:2] and [a.attempt for a in attempts] == [0, 1]
    assert final.setting_domain == order[1] and final.domain_attempt == 1
    assert (final.agent_name, final.template_id) == (asg.agent_name, asg.template_id)       # 只换域，不换人
    sent = [json.loads(call["input"])["assignments"]["setting_domain"] for call in c.calls]
    assert sent == order[:2]


def test_domain_reassignment_is_bounded(k30):
    s = _sampler()
    c = FakeClient(*[_no_valid() for _ in range(6)])
    final, attempts = propose_with_domain_fallback(c, sampler=s, assignment=s.assignment_for(0),
                                                   max_domain_reassignments=2, **_kw(k30))
    assert len(attempts) == 3 and len(c.calls) == 3 and final.domain_attempt == 2


def test_no_reassignment_when_first_domain_works(fixture_raw, k30):
    s = _sampler()
    c = FakeClient(FakeResp(json.dumps(fixture_raw["propose_output"])))
    final, attempts = propose_with_domain_fallback(c, sampler=s, assignment=s.assignment_for(0),
                                                   max_domain_reassignments=2, **_kw(k30))
    assert len(attempts) == 1 and final.domain_attempt == 0


def test_api_error_does_not_reassign_domain(k30):
    s = _sampler()
    err = AuthenticationError("bad key", response=httpx.Response(401, request=REQ), body=None)
    c = FakeClient(err, _no_valid())
    _, attempts = propose_with_domain_fallback(c, sampler=s, assignment=s.assignment_for(0),
                                               max_domain_reassignments=2, **_kw(k30))
    assert len(attempts) == 1 and not attempts[0].result.call.ok


# ------------------------------------------------------------------ 自动重新生成
def _regen(client, k30, bundle, asg, max_regen=2):
    return generate_with_regeneration(
        client, model="m", fact=k30, bundle=bundle, assignment=asg, family_id="F001", max_output_tokens=100,
        max_retries=0, max_regenerations=max_regen, notes="t")


def _resp(family_dict, **over):
    return FakeResp(json.dumps({**family_dict, **over}))


def test_regenerates_after_error_and_passes_feedback(family_dict, k30, bundle, asg):
    bad = _resp(family_dict, setting_domain="arts_media")
    c = FakeClient(bad, _resp(family_dict))
    attempts = _regen(c, k30, bundle, asg)
    assert [a.number for a in attempts] == [1, 2]
    assert attempts[0].record.validation_status == "auto_rejected"
    assert attempts[1].record.validation_status == "needs_human_review"
    assert attempts[1].feedback_given == [FEEDBACK_EN["setting_domain_mismatch"]]
    sent = json.loads(c.calls[1]["input"])
    a = sent["assignments"]
    assert sent["revision_feedback"] and a["agent_name"] == "Grace" and a["agent_pronouns"] == "she/her"
    assert a["setting_domain"] == "travel_cultural_orientation"
    assert json.loads(c.calls[0]["input"])["revision_feedback"] == []


def test_bad_proposition_feedback_explains_the_format(family_dict, k30, bundle, asg):
    bad = _resp(family_dict, belief_proposition_aligned="that the public elementary-school year in Japan generally begins in April")
    c = FakeClient(bad, _resp(family_dict))
    attempts = _regen(c, k30, bundle, asg)
    fb = attempts[1].feedback_given[0]
    assert "without an initial 'that'" in fb and "proposition_leading_that" in fb


def test_forced_binary_story_is_not_regenerated(family_dict, k30, bundle, asg):
    """二选一只记录：不会触发自动拒绝，也就不会重新生成。"""
    c = FakeClient(_resp(family_dict, story_backbone=_with_options(family_dict).story_backbone), _resp(family_dict))
    attempts = _regen(c, k30, bundle, asg)
    assert len(attempts) == 1 and attempts[0].record.validation_status == "needs_human_review"
    assert attempts[0].record.design_tag == "forced_binary_options"


def test_regeneration_is_bounded_and_keeps_the_rejected_record(family_dict, k30, bundle, asg):
    c = FakeClient(*[_resp(family_dict, setting_domain="arts_media") for _ in range(5)])
    attempts = _regen(c, k30, bundle, asg, max_regen=2)
    assert len(attempts) == 3 and len(c.calls) == 3
    assert attempts[-1].record.validation_status == "auto_rejected"


def test_no_regeneration_when_first_attempt_is_fine(family_dict, k30, bundle, asg):
    c = FakeClient(_resp(family_dict))
    assert len(_regen(c, k30, bundle, asg)) == 1 and len(c.calls) == 1


def test_needs_revision_is_not_regenerated(family_dict, k30, bundle, asg):
    nr = {**family_dict, "status": "needs_revision", "failure_reason": "no distinct action possible",
          "validation_status": None}
    c = FakeClient(FakeResp(json.dumps(nr)), _resp(family_dict))
    attempts = _regen(c, k30, bundle, asg)
    assert len(attempts) == 1 and attempts[0].record is None and len(c.calls) == 1


def test_api_errors_are_not_regenerated(k30, bundle, asg, family_dict):
    err = AuthenticationError("bad key", response=httpx.Response(401, request=REQ), body=None)
    c = FakeClient(err, _resp(family_dict))
    attempts = _regen(c, k30, bundle, asg)
    assert len(attempts) == 1 and attempts[0].call.error_type == "api_error" and len(c.calls) == 1


def test_invalid_json_triggers_a_regeneration(family_dict, k30, bundle, asg):
    c = FakeClient(FakeResp("{not json"), _resp(family_dict))
    attempts = _regen(c, k30, bundle, asg)
    assert len(attempts) == 2 and attempts[1].record.validation_status == "needs_human_review"
    assert "unusable" in attempts[1].feedback_given[0]


def test_wrong_agent_name_triggers_regeneration(family_dict, k30, bundle, asg):
    c = FakeClient(_resp(family_dict, agent_name="Zoe"), _resp(family_dict))
    attempts = _regen(c, k30, bundle, asg)
    assert len(attempts) == 2 and "agent_mismatch" in [i.code for i in attempts[0].record.issues]


def test_regeneration_uses_the_model_prompt_as_instructions(family_dict, k30, bundle, asg):
    c = FakeClient(_resp(family_dict))
    _regen(c, k30, bundle, asg)
    assert c.calls[0]["instructions"].startswith("# Generator Model Prompt") and "Part B" not in c.calls[0]["instructions"]
