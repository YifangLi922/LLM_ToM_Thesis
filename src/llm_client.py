"""造题模型（OpenAI）的结构化调用层。

设计要点：
- 用 Structured Outputs（strict JSON Schema），但**自己解析并校验**输出，这样即使输出不合格，
  原始响应也一定会被保存下来（不会因为 SDK 内部抛异常而丢失）。
- 只对瞬时错误（连接/超时/429 限流/5xx）做有限次退避重试；额度用尽、鉴权错误、参数错误不重试。
- 绝不把 API 错误当作"题目质量问题"，两者在返回值里分开记录。
- 不打印、不保存 API key。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Type, TypeVar

from openai import APIConnectionError, APIError, APITimeoutError, InternalServerError, OpenAI, RateLimitError
from openai.lib._pydantic import to_strict_json_schema  # SDK 内部工具：把 Pydantic 模型转成 strict schema
from pydantic import BaseModel, ValidationError

M = TypeVar("M", bound=BaseModel)

# 失败类别（写入日志，便于统计）
ERR_API = "api_error"
ERR_INCOMPLETE = "incomplete_response"
ERR_REFUSAL = "refusal_or_empty"
ERR_JSON = "json_invalid"
ERR_SCHEMA = "schema_invalid"


@dataclass
class CallResult:
    ok: bool
    parsed: BaseModel | None = None
    error_type: str | None = None
    error_detail: str | None = None
    output_text: str | None = None
    raw_response: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    attempts: int = 0
    elapsed_s: float = 0.0
    request_meta: dict[str, Any] = field(default_factory=dict)

    def log_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok, "error_type": self.error_type, "error_detail": self.error_detail,
            "attempts": self.attempts, "elapsed_s": round(self.elapsed_s, 2), "usage": self.usage,
            "request_meta": self.request_meta, "output_text": self.output_text, "raw_response": self.raw_response,
        }


def make_client() -> OpenAI:
    """从环境变量 / .env 读取 OPENAI_API_KEY。"""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    return OpenAI()


def _is_retryable(e: Exception) -> bool:
    if isinstance(e, (APIConnectionError, APITimeoutError, InternalServerError)):
        return True
    if isinstance(e, RateLimitError):
        return getattr(e, "code", None) != "insufficient_quota"     # 额度用尽重试没有意义
    return False


def call_structured(
    client: OpenAI,
    *,
    model: str,
    instructions: str,
    user_payload: dict[str, Any],
    schema_model: Type[M],
    schema_name: str,
    max_output_tokens: int,
    max_retries: int = 2,
    backoff_s: float = 4.0,
) -> CallResult:
    user_text = json.dumps(user_payload, ensure_ascii=False, indent=2)
    meta = {
        "model": model, "schema_name": schema_name, "max_output_tokens": max_output_tokens,
        "instructions_chars": len(instructions), "user_input": user_payload, "store": False,
    }
    text_cfg = {"format": {"type": "json_schema", "name": schema_name,
                           "schema": to_strict_json_schema(schema_model), "strict": True}}
    res = CallResult(ok=False, request_meta=meta)
    t0 = time.time()
    resp = None
    for attempt in range(1, max_retries + 2):
        res.attempts = attempt
        try:
            resp = client.responses.create(
                model=model, instructions=instructions, input=user_text, text=text_cfg,
                max_output_tokens=max_output_tokens, store=False,
            )
            break
        except APIError as e:
            res.error_type, res.error_detail = ERR_API, f"{type(e).__name__} (HTTP {getattr(e, 'status_code', None)}): {str(getattr(e, 'message', e))[:300]}"
            if attempt <= max_retries and _is_retryable(e):
                time.sleep(backoff_s * attempt)
                continue
            res.elapsed_s = time.time() - t0
            return res
    res.elapsed_s = time.time() - t0
    assert resp is not None
    res.error_type = res.error_detail = None

    res.raw_response = resp.model_dump(mode="json")
    res.usage = resp.usage.model_dump(mode="json") if resp.usage else None
    if resp.status == "incomplete":
        reason = getattr(getattr(resp, "incomplete_details", None), "reason", None)
        res.error_type, res.error_detail = ERR_INCOMPLETE, f"status=incomplete, reason={reason}（可能是 max_output_tokens 不够）"
        return res
    text = resp.output_text or ""
    res.output_text = text
    if not text.strip():
        res.error_type, res.error_detail = ERR_REFUSAL, "没有文本输出（可能是拒答，请查看 raw_response）"
        return res
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        res.error_type, res.error_detail = ERR_JSON, str(e)
        return res
    try:
        res.parsed = schema_model.model_validate(obj)
    except ValidationError as e:
        res.error_type = ERR_SCHEMA
        res.error_detail = "; ".join(f"{'.'.join(map(str, d['loc'])) or '(root)'}: {d['msg']}" for d in e.errors())[:1500]
        return res
    res.ok = True
    return res
