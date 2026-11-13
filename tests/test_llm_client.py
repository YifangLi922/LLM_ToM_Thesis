"""用假客户端测试调用层：不联网、不需要 key。"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

try:  # 新版 openai SDK 使用 httpx2，旧版使用 httpx
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx
from openai import APIConnectionError, AuthenticationError, RateLimitError

from generation_prompts import ADDENDUM_GENERATE, fact_payload, generate_payload, propose_payload, prompt_version
from llm_client import ERR_API, ERR_INCOMPLETE, ERR_JSON, ERR_REFUSAL, ERR_SCHEMA, call_structured
from propose_bundles import select_bundle
from schemas import GenerateFamilyOutput, Issue, ProposeBundlesOutput

_REQ = httpx.Request("POST", "https://api.openai.com/v1/responses")


class FakeResp:
    def __init__(self, text, status="completed", reason=None):
        self.status, self.output_text = status, text
        self.incomplete_details = SimpleNamespace(reason=reason) if reason else None
        self.usage = SimpleNamespace(model_dump=lambda mode=None: {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})

    def model_dump(self, mode=None):
        return {"status": self.status, "output_text": self.output_text}


class FakeClient:
    """按顺序依次返回/抛出预设的结果。"""
    def __init__(self, *script):
        self.script, self.calls = list(script), []
        self.responses = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls.append(kw)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _call(client, **kw):
    return call_structured(client, model="m", instructions="guideline", user_payload={"x": 1},
                           schema_model=ProposeBundlesOutput, schema_name="s", max_output_tokens=100,
                           backoff_s=0, **kw)


def test_success_saves_raw_and_parses(fixture_raw):
    c = FakeClient(FakeResp(json.dumps(fixture_raw["propose_output"])))
    r = _call(c)
    assert r.ok and r.parsed.fact_id == "K01" and r.raw_response and r.usage["total_tokens"] == 15
    sent = c.calls[0]
    assert sent["store"] is False and sent["text"]["format"]["strict"] is True
    assert sent["text"]["format"]["type"] == "json_schema" and "temperature" not in sent


@pytest.mark.parametrize("resp, etype", [
    (FakeResp("", status="completed"), ERR_REFUSAL),
    (FakeResp("{not json"), ERR_JSON),
    (FakeResp('{"task_mode": "propose_bundles"}'), ERR_SCHEMA),
    (FakeResp("", status="incomplete", reason="max_output_tokens"), ERR_INCOMPLETE),
])
def test_bad_outputs_are_classified_and_raw_is_kept(resp, etype):
    r = _call(FakeClient(resp))
    assert not r.ok and r.error_type == etype and r.raw_response is not None


def test_transient_errors_are_retried_then_succeed(fixture_raw):
    good = FakeResp(json.dumps(fixture_raw["propose_output"]))
    c = FakeClient(APIConnectionError(request=_REQ), RateLimitError("slow down", response=httpx.Response(429, request=_REQ), body=None), good)
    r = _call(c, max_retries=2)
    assert r.ok and r.attempts == 3 and len(c.calls) == 3


def test_retries_are_bounded():
    c = FakeClient(*[APIConnectionError(request=_REQ) for _ in range(5)])
    r = _call(c, max_retries=2)
    assert not r.ok and r.error_type == ERR_API and len(c.calls) == 3


def test_non_retryable_errors_are_not_retried():
    err = AuthenticationError("bad key", response=httpx.Response(401, request=_REQ), body=None)
    c = FakeClient(err, FakeResp("{}"))
    r = _call(c, max_retries=2)
    assert not r.ok and r.error_type == ERR_API and len(c.calls) == 1 and "401" in r.error_detail


def test_quota_exhaustion_is_not_retried():
    err = RateLimitError("quota", response=httpx.Response(429, request=_REQ), body={"code": "insufficient_quota", "message": "quota"})
    assert getattr(err, "code", None) == "insufficient_quota"
    c = FakeClient(err, FakeResp("{}"))
    r = _call(c, max_retries=2)
    assert not r.ok and len(c.calls) == 1


def test_log_dict_contains_no_secrets_fields(fixture_raw):
    r = _call(FakeClient(FakeResp(json.dumps(fixture_raw["propose_output"]))))
    blob = json.dumps(r.log_dict()).lower()
    assert "api_key" not in blob and "authorization" not in blob and "sk-" not in blob


# ------------------------------------------------------------------ 请求构造
def test_payloads_do_not_leak_pipeline_metadata(k01, bundle):
    assert "fact_status" not in fact_payload(k01)
    p = propose_payload(k01, max_bundles=3, template_id="T1")
    assert p["task_mode"] == "propose_bundles" and p["assignments"]["template_id"] == "T1"
    assert p["fact_record"]["world_gold"] == "8" and p["fact_record"]["pretest_question"].startswith("How many legs")
    g = generate_payload(k01, bundle, template_id="T4A")
    assert g["selected_bundle"]["bundle_id"] == "B01" and g["assignments"]["action_type"] == "A2"
    assert "{{CLAIM_SPAN}}" in ADDENDUM_GENERATE and "{{BELIEF_INSERTION}}" in ADDENDUM_GENERATE


def test_prompt_version_is_stable():
    assert prompt_version() == prompt_version() and len(prompt_version()) == 64


def test_both_output_models_convert_to_strict_schema():
    from openai.lib._pydantic import to_strict_json_schema

    for m in (ProposeBundlesOutput, GenerateFamilyOutput):
        s = to_strict_json_schema(m)
        assert s["additionalProperties"] is False and set(s["required"]) == set(s["properties"])


# ------------------------------------------------------------------ bundle 挑选
def test_select_bundle_prefers_fewest_warnings_and_skips_errors(propose_out, bundle):
    b2, b3 = bundle.model_copy(update={"bundle_id": "B02"}), bundle.model_copy(update={"bundle_id": "B03"})
    out = propose_out.model_copy(update={"bundles": [bundle, b2, b3]})
    w = Issue(severity="warning", code="w", message="w")
    e = Issue(severity="error", code="e", message="e")
    chosen, reason = select_bundle(out, {"B01": [w, w], "B02": [w], "B03": [e]})
    assert chosen.bundle_id == "B02" and "B02" in reason
    none, _ = select_bundle(out, {"B01": [e], "B02": [e], "B03": [e]})
    assert none is None
    tie, _ = select_bundle(out, {"B01": [w], "B02": [w], "B03": []})
    assert tie.bundle_id == "B03"
    first, _ = select_bundle(out, {"B01": [], "B02": [], "B03": []})
    assert first.bundle_id == "B01"
