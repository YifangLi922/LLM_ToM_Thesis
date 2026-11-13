from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas import CandidateRecord, GenerateFamilyOutput, ProposeBundlesOutput

# OpenAI Structured Outputs（strict）可能不支持的关键字——我们的输出 schema 里不应出现它们。
_RISKY_KEYS = {"default", "minLength", "maxLength", "minItems", "maxItems", "pattern", "format",
               "minimum", "maximum", "const", "uniqueItems", "patternProperties"}


def _walk(node, path, problems):
    if isinstance(node, dict):
        if node.get("type") == "object" or "properties" in node:
            if node.get("additionalProperties") is not False:
                problems.append(f"{path}: additionalProperties 必须为 false")
            if set(node.get("properties", {})) != set(node.get("required", [])):
                problems.append(f"{path}: 所有属性都必须出现在 required 里")
        for k in node:
            if k in _RISKY_KEYS and path.rsplit("/", 1)[-1] != "properties":
                problems.append(f"{path}: 含 strict 模式可能不支持的关键字 {k!r}")
        for k, v in node.items():
            _walk(v, f"{path}/{k}", problems)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, f"{path}[{i}]", problems)


@pytest.mark.parametrize("model", [ProposeBundlesOutput, GenerateFamilyOutput])
def test_output_schemas_are_strict_mode_compatible(model):
    problems: list[str] = []
    _walk(model.model_json_schema(), model.__name__, problems)
    assert not problems, "\n".join(problems)


def test_fixture_validates(propose_out, family_out):
    assert propose_out.status == "candidates_proposed"
    assert family_out.status == "candidate_generated"


# ------------------------------------------------------------------ propose_bundles 规则
def test_no_valid_bundle_requires_reason_and_empty_bundles(fixture_raw):
    ok = {**fixture_raw["propose_output"], "status": "no_valid_bundle", "bundles": [],
          "failure_reason": "Every candidate action is identical under both beliefs."}
    ProposeBundlesOutput.model_validate(ok)
    with pytest.raises(ValidationError):
        ProposeBundlesOutput.model_validate({**ok, "failure_reason": None})
    with pytest.raises(ValidationError):
        ProposeBundlesOutput.model_validate({**ok, "bundles": fixture_raw["propose_output"]["bundles"]})


def test_candidates_proposed_needs_bundles(fixture_raw):
    with pytest.raises(ValidationError):
        ProposeBundlesOutput.model_validate({**fixture_raw["propose_output"], "bundles": []})


def test_bad_enum_values_rejected(fixture_raw):
    p = fixture_raw["propose_output"]
    p["bundles"][0]["action_type"] = "A9"
    with pytest.raises(ValidationError):
        ProposeBundlesOutput.model_validate(p)


def test_extra_fields_rejected(fixture_raw):
    p = fixture_raw["propose_output"]
    p["surprise"] = 1
    with pytest.raises(ValidationError):
        ProposeBundlesOutput.model_validate(p)


# ------------------------------------------------------------------ generate_family 规则
@pytest.mark.parametrize("status", ["validated", "human_gold_confirmed"])
def test_generator_may_not_self_validate(family_dict, status):
    family_dict["validation_status"] = status
    with pytest.raises(ValidationError, match="needs_human_review"):
        GenerateFamilyOutput.model_validate(family_dict)


def test_candidate_requires_content_fields(family_dict):
    family_dict["story_backbone"] = None
    with pytest.raises(ValidationError, match="story_backbone"):
        GenerateFamilyOutput.model_validate(family_dict)


def test_needs_revision_requires_reasons_but_not_content(family_dict):
    nr = {k: (None if isinstance(v, (str, dict)) and k not in ("task_mode", "fact_id", "bundle_id") else v)
          for k, v in family_dict.items()}
    nr.update(status="needs_revision", belief_cue_ids=[], risk_flags=[], potential_ambiguities=[],
              revision_reasons=[])
    with pytest.raises(ValidationError, match="revision_reasons"):
        GenerateFamilyOutput.model_validate(nr)
    nr["revision_reasons"] = ["Both beliefs lead to the same craft quantity once the setting is fixed."]
    out = GenerateFamilyOutput.model_validate(nr)
    assert out.status == "needs_revision"


def test_max_two_belief_cues(family_dict):
    family_dict["belief_cue_ids"] = ["B1", "B2", "B3"]
    with pytest.raises(ValidationError, match="最多两个"):
        GenerateFamilyOutput.model_validate(family_dict)


def test_candidate_record_cannot_be_human_validated(k01, bundle, family_out):
    from candidates import build_candidate

    rec = build_candidate(family_id="F001", fact=k01, bundle=bundle, family_out=family_out,
                          generator_model="MOCK", prompt_version="x", created_at="2026-01-01T00:00:00+00:00")
    assert rec.human_validated is False
    with pytest.raises(ValidationError):
        CandidateRecord.model_validate({**rec.model_dump(), "human_validated": True})
    with pytest.raises(ValidationError):
        CandidateRecord.model_validate({**rec.model_dump(), "validation_status": "validated"})
