"""被测模型的 capability check（OpenRouter）。

对 config/pilot.yaml 里的每个评测条件各发 2 个极小请求（一个 Q0 风格的短问题，一个带故事的问题），
再对每个模型做 1 次"固定后端服务商"的请求，确认：
  1. 能调通；2. thinking 开/关开关是否真的生效（看推理 token / reasoning 字段 / <think> 标签）；
  3. 实际由哪个后端服务商处理；4. 回答是否被截断、token 用量如何；5. 固定服务商的参数是否可用。

原始响应会保存到 results/capability_check/（不含 key）。费用极低。
用法：python src/check_eval_models.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from common import REPO_ROOT
from config import EvalModelConfig, load_config
from export_evaluation import ANSWER_INSTRUCTION
from render_pairs import render_variants

CHAT_URL_SUFFIX = "/chat/completions"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "mock_k01_family.json"
Q0_PROMPT = f"Which biological class do penguins belong to?\n\n{ANSWER_INSTRUCTION}"


def story_prompt() -> str:
    f = json.loads(FIXTURE.read_text(encoding="utf-8"))["family_output"]
    v = render_variants(f["story_backbone"], f["claim_span_aligned"], f["claim_span_conflicting"],
                        f["belief_sentence_aligned"], f["belief_sentence_conflicting"])
    return f"{v.implicit_conflicting}\n\n{f['action_question']}\n\n{ANSWER_INSTRUCTION}"


def post(base_url: str, key: str, body: dict, timeout: int = 240) -> tuple[int, dict]:
    req = urllib.request.Request(
        base_url.rstrip("/") + CHAT_URL_SUFFIX, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            payload = {"error": "unparseable body"}
        return e.code, payload
    except urllib.error.URLError as e:
        return 0, {"error": str(e.reason)}


def summarize(status: int, resp: dict) -> dict:
    """从原始响应里抽出我们关心的信息。"""
    if status != 200 or "choices" not in resp:
        return {"ok": False, "http": status, "error": json.dumps(resp.get("error", resp), ensure_ascii=False)[:400]}
    ch = resp["choices"][0]
    msg = ch.get("message", {}) or {}
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
    usage = resp.get("usage", {}) or {}
    details = usage.get("completion_tokens_details") or {}
    return {
        "ok": True, "http": status, "provider": resp.get("provider"), "model_returned": resp.get("model"),
        "finish_reason": ch.get("finish_reason"), "native_finish_reason": ch.get("native_finish_reason"),
        "content": content, "has_reasoning_field": bool(reasoning), "reasoning_chars": len(reasoning),
        "think_tag_in_content": "<think>" in content or "</think>" in content,
        "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens"), "cost": usage.get("cost"),
    }


def request_body(m: EvalModelConfig, prompt: str, max_tokens: int, pin: str | None = None) -> dict:
    body: dict = {"model": m.model_id, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
    if m.thinking is not None:
        body["reasoning"] = {"enabled": bool(m.thinking)}
    if pin:
        body["provider"] = {"order": [pin], "allow_fallbacks": False}
    return body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thinking-max-tokens", type=int, default=4000)
    ap.add_argument("--plain-max-tokens", type=int, default=64)
    ap.add_argument("--pin", action="append", default=[], metavar="MODEL_ID=PROVIDER",
                    help="对该模型再做一次固定服务商的测试，如 qwen/qwen3-32b=DeepInfra（可重复）")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    cfg = load_config()
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("未找到 OPENROUTER_API_KEY（请检查 .env）")
        return 1
    prompts = {"q0_short": Q0_PROMPT, "story_q2": story_prompt()}
    pins = dict(p.split("=", 1) for p in args.pin)
    results: list[dict] = []

    def run(label: str, m: EvalModelConfig, prompt_name: str, pin: str | None = None) -> None:
        mt = args.thinking_max_tokens if m.thinking else args.plain_max_tokens
        if prompt_name == "story_q2" and not m.thinking:
            mt = max(mt, 128)
        body = request_body(m, prompts[prompt_name], mt, pin)
        t0 = time.time()
        status, resp = post(cfg.eval_base_url, key, body)
        s = summarize(status, resp)
        s.update(condition=m.condition_id, prompt=prompt_name, pinned=pin, max_tokens=mt,
                 elapsed_s=round(time.time() - t0, 1), request_reasoning_param=body.get("reasoning"))
        results.append({"summary": s, "raw_response": resp})
        flag = "OK " if s["ok"] else "ERR"
        tail = (f"provider={s.get('provider')} finish={s.get('finish_reason')} out_tok={s.get('completion_tokens')} "
                f"reasoning_tok={s.get('reasoning_tokens')} reasoning_field={s.get('has_reasoning_field')} "
                f"think_tag={s.get('think_tag_in_content')} {s['elapsed_s']}s") if s["ok"] else s["error"]
        print(f"[{flag}] {m.condition_id:28s} {prompt_name:9s}{' pin=' + pin if pin else ''}  {tail}")
        if s["ok"]:
            print(f"        answer: {s['content'].strip()[:150]!r}")

    for m in cfg.evaluated_models:
        for pname in prompts:
            run("base", m, pname)
    for model_id, provider in pins.items():
        m = next((x for x in cfg.evaluated_models if x.model_id == model_id and x.thinking is False), None) \
            or next((x for x in cfg.evaluated_models if x.model_id == model_id), None)
        if m:
            run("pin", m, "q0_short", pin=provider)

    out_dir = REPO_ROOT / "results" / "capability_check"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_openrouter.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    total_cost = sum((r["summary"].get("cost") or 0) for r in results)
    print(f"\n已保存：{path}\n本次已返回的 cost 合计（美元，若平台返回该字段）：{total_cost}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
