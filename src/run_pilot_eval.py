"""Pilot 评测：把 eval_requests.jsonl 里的每条请求发给 OpenRouter 上的被测模型配置，**完整保存原始响应**。

- 每条请求都是单条 user 消息、没有历史（Q0 独立；Q1/Q2/Q3 各自 fresh context）；请求里不含任何 gold / 元数据。
- 配置来自 config/pilot.yaml 的 evaluated_models（模型 ID、thinking 开关、固定的后端服务商）。
- 可断点续跑：已成功的 (配置, item) 会跳过；加 --retry-failed 只重试失败的。
- 不打印、不保存 API key。

用法：
    python src/run_pilot_eval.py --limit 2                       # 每个配置只发 2 条，试跑
    python src/run_pilot_eval.py                                  # 全量（会花钱）
    python src/run_pilot_eval.py --retry-failed
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

from common import REPO_ROOT, read_jsonl
from config import EvalModelConfig, load_config

DEFAULT_REQUESTS = REPO_ROOT / "datasets" / "generation" / "pilot_12" / "eval_input" / "eval_requests.jsonl"
DEFAULT_OUT = REPO_ROOT / "results" / "pilot_eval" / "raw_responses.jsonl"
RETRYABLE = {0, 408, 429, 500, 502, 503, 504}


def build_body(m: EvalModelConfig, messages: list[dict], max_tokens: int) -> dict:
    body: dict = {"model": m.model_id, "messages": messages, "max_tokens": max_tokens}
    if m.thinking is not None:
        body["reasoning"] = {"enabled": bool(m.thinking)}
    if m.pinned_provider:
        body["provider"] = {"order": [m.pinned_provider], "allow_fallbacks": False}
    if m.temperature is not None:
        body["temperature"] = m.temperature
    if m.seed is not None:
        body["seed"] = m.seed
    return body


def post(url: str, key: str, body: dict, timeout: int = 300) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            payload = {"error": "unparseable error body"}
        return e.code, payload
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, {"error": f"{type(e).__name__}: {e}"}
    except json.JSONDecodeError:
        return 0, {"error": "invalid json in response"}


def one_request(cfg_base: str, key: str, m: EvalModelConfig, row: dict, max_tokens: int, max_retries: int) -> dict:
    body = build_body(m, row["messages"], max_tokens)
    t0 = time.time()
    status, resp, attempts = 0, {}, 0
    for attempts in range(1, max_retries + 2):
        status, resp = post(cfg_base.rstrip("/") + "/chat/completions", key, body)
        has_choice = status == 200 and isinstance(resp, dict) and resp.get("choices")
        if has_choice:
            break
        if status not in RETRYABLE and not (status == 200 and not has_choice):
            break
        time.sleep(3 * attempts)
    ch = (resp.get("choices") or [{}])[0] if isinstance(resp, dict) else {}
    msg = ch.get("message") or {}
    usage = resp.get("usage") or {} if isinstance(resp, dict) else {}
    content = msg.get("content")
    reasoning = msg.get("reasoning") or msg.get("reasoning_content")
    ok = status == 200 and content is not None and str(content).strip() != "" and ch.get("finish_reason") != "length"
    err = None
    if not ok:
        if status != 200 or not ch:
            err = json.dumps(resp.get("error", resp) if isinstance(resp, dict) else resp, ensure_ascii=False)[:500]
        elif ch.get("finish_reason") == "length":
            err = "truncated: finish_reason=length（max_tokens 不够）"
        else:
            err = "empty content"
    return {
        "request_id": f"{m.condition_id}|{row['item_id']}", "condition_id": m.condition_id, "item_id": row["item_id"],
        "ok": ok, "http_status": status, "attempts": attempts, "elapsed_s": round(time.time() - t0, 2), "error": err,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "request": {"model": m.model_id, "pinned_provider": m.pinned_provider, "reasoning": body.get("reasoning"),
                    "max_tokens": max_tokens, "temperature": body.get("temperature"), "messages": row["messages"]},
        "content": content, "reasoning_text": reasoning, "provider": resp.get("provider") if isinstance(resp, dict) else None,
        "model_returned": resp.get("model") if isinstance(resp, dict) else None,
        "finish_reason": ch.get("finish_reason"), "native_finish_reason": ch.get("native_finish_reason"),
        "usage": usage, "response": resp,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--requests", type=Path, default=DEFAULT_REQUESTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=None, help="每个配置只发前 N 条（试跑）")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-tokens-nonthinking", type=int, default=400)
    ap.add_argument("--max-tokens-thinking", type=int, default=16000)
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument("--retry-failed", action="store_true", help="重新发送此前失败（含被截断）的请求")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    cfg = load_config()
    rows = read_jsonl(args.requests)
    if args.limit:
        rows = rows[: args.limit]
    keys = {m.api_key_env: os.getenv(m.api_key_env, "").strip() for m in cfg.evaluated_models}
    if not all(keys.values()):
        print("缺少 API key 环境变量：", [k for k, v in keys.items() if not v])
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done_ok: set[str] = set()
    if args.out.exists():
        for r in read_jsonl(args.out):
            if r["ok"]:
                done_ok.add(r["request_id"])
    jobs = [(m, row) for row in rows for m in cfg.evaluated_models if f"{m.condition_id}|{row['item_id']}" not in done_ok]
    print(f"待发送 {len(jobs)} 条请求（已成功 {len(done_ok)} 条）；配置：{[m.condition_id for m in cfg.evaluated_models]}")
    if not jobs:
        return 0

    lock = threading.Lock()
    counters = {"ok": 0, "fail": 0}
    abort = threading.Event()
    t_start = time.time()
    with open(args.out, "a", encoding="utf-8", newline="\n") as f, ThreadPoolExecutor(max_workers=args.workers) as ex:
        def work(job):
            m, row = job
            if abort.is_set():
                return None
            mt = args.max_tokens_thinking if m.thinking else args.max_tokens_nonthinking
            return one_request(cfg.eval_base_url, keys[m.api_key_env], m, row, mt, args.max_retries)

        futs = [ex.submit(work, j) for j in jobs]
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            if r is None:
                continue
            with lock:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                f.flush()
                counters["ok" if r["ok"] else "fail"] += 1
                if not r["ok"] and r["http_status"] in (401, 402, 403):
                    abort.set()
                    print(f"遇到 HTTP {r['http_status']}（鉴权/额度问题），中止：{r['error']}")
                if i % 25 == 0 or i == len(futs):
                    print(f"  进度 {i}/{len(futs)} | 成功 {counters['ok']} 失败 {counters['fail']} | {time.time() - t_start:.0f}s")
    print(f"完成：成功 {counters['ok']}，失败 {counters['fail']}；原始响应追加写入 {args.out}")
    return 0 if counters["fail"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
