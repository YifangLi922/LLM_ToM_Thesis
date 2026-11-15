"""Pilot 评测的评分与汇总：读取 run_pilot_eval.py 保存的原始响应，输出 CSV 汇总与 Markdown 错误分析。

评分流程（不会把 gold 发给被测模型；gold 只在这里用于评分）：
  1) 规则评分（scoring.py）：规范化 + 日期/单位 + 否定检查，只在"能确定"时判定；
  2) 规则无法确定的（同时匹配两个 gold / 两个都不匹配 / 答案过长）交给 LLM 裁判（默认 gpt-6.1-sol），
     裁判只比较"模型答案 ≈ 参考答案 / ≈ 另一条件的答案 / 两者都像 / 都不像 / 无法判断"，不判断事实真假；
  3) 裁判说"两者都像"或"无法判断"的记为 pending（待人工复核），不计为正确。
所有裁判的输入输出都保存在 judge_raw.jsonl（同时作为缓存）。

用法：
    python src/score_pilot_eval.py                    # 评分 + 汇总 + 错误分析
    python src/score_pilot_eval.py --no-judge         # 不调用裁判（规则无法确定的全部记为 pending）
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from common import REPO_ROOT, read_jsonl
from config import load_config
from scoring import answer_kind, rule_score
from validate_knowledge import load_knowledge

PILOT = REPO_ROOT / "datasets" / "generation" / "pilot_12"
RES = REPO_ROOT / "results" / "pilot_eval"
STORY_RE = re.compile(r"^(F\d+)_(implicit|explicit)_(aligned|conflicting)_(Q[123])$")
CONDS = [("aligned", "implicit"), ("aligned", "explicit"), ("conflicting", "implicit"), ("conflicting", "explicit")]

# 错误类别（英文代码；"candidate" 表示只是启发式归因，需要人工确认）
REALITY = "reality_intrusion_candidate"
BELIEF = "belief_attribution_error_candidate"
NONTOM = "non_tom_reasoning_error_candidate"
AMBIG = "scoring_ambiguity"
MANUAL = "needs_manual_review"
Q3FALSE = "q3_false_claim_adopted"
Q0ERR = "q0_knowledge_error"
FAILED = "request_failed"


# --------------------------------------------------------------------------- LLM 裁判
class JudgeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: Literal["matches_reference", "matches_alternative", "matches_both", "neither", "unclear"]
    reason: str


JUDGE_INSTRUCTIONS = (
    "You are a strict but fair grader of short answers. You are given a question, a REFERENCE answer (with accepted "
    "variants), an ALTERNATIVE answer (with variants), and a MODEL answer. Decide what the model answer says: "
    "'matches_reference' if its final answer has the same meaning as the reference; 'matches_alternative' if it has "
    "the same meaning as the alternative; 'matches_both' if it hedges or lists both; 'neither' if it clearly says "
    "something else; 'unclear' if you cannot decide (partially correct, ambiguous, off-topic, or a refusal). "
    "Rules: judge the final answer, not the explanation; negation matters ('not X' is not X); a more verbose or more "
    "specific answer still matches if it is semantically equal; do NOT use outside knowledge to decide whether an "
    "answer is true — only compare its meaning with the reference and the alternative. Give a reason of at most 25 words."
)


def judge_key(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:24]


def run_judge(payloads: dict[str, dict], model: str, cache_path: Path, workers: int = 5,
              seed_paths: list[Path] | None = None) -> dict[str, dict]:
    from llm_client import call_structured, make_client

    cache: dict[str, dict] = {}
    for sp in [*(seed_paths or []), cache_path]:                 # 先读只读的种子缓存，再读本次输出目录里的缓存
        if sp.exists():
            for r in read_jsonl(sp):
                cache[r["key"]] = r
    todo = {k: p for k, p in payloads.items() if k not in cache}
    if not todo:
        return cache
    client = make_client()
    print(f"  调用裁判 {model}：{len(todo)} 条（缓存命中 {len(payloads) - len(todo)} 条）")

    def one(item):
        k, p = item
        res = call_structured(client, model=model, instructions=JUDGE_INSTRUCTIONS, user_payload=p, schema_model=JudgeOut,
                              schema_name="judge_out", max_output_tokens=3000, max_retries=2)
        out = {"key": k, "payload": p, "model": model, "ok": res.ok, "usage": res.usage, "error": res.error_detail}
        if res.ok:
            out.update(verdict=res.parsed.verdict, reason=res.parsed.reason)    # type: ignore[union-attr]
        else:
            out.update(verdict="unclear", reason=f"judge failed: {res.error_type}")
        return out

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "a", encoding="utf-8", newline="\n") as f, ThreadPoolExecutor(max_workers=workers) as ex:
        for out in ex.map(one, todo.items()):
            cache[out["key"]] = out
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
            f.flush()
    return cache


# --------------------------------------------------------------------------- 载入数据
def _best_by_request(paths: list[Path]) -> dict[str, dict]:
    raw: dict[str, dict] = {}
    for path in paths:
        for r in read_jsonl(path):                       # 同一请求多次记录：成功的优先，其次取最后一条
            old = raw.get(r["request_id"])
            if old is None or r["ok"] or not old["ok"]:
                raw[r["request_id"]] = r
    return raw


def load_inputs(raw_paths: list[Path], pilot_dir: Path = PILOT, override_paths: list[Path] | None = None):
    """override_paths：其中出现的 request_id 会**整体替换**主原始响应里的同名请求（用于替换某个 family 的新版本）。"""
    cfg = load_config()
    facts = {f.fact_id: f for f in load_knowledge()}
    gold = {g["item_id"]: g for g in read_jsonl(pilot_dir / "answer_keys" / "gold_answers.jsonl")}
    questions = {r["item_id"]: r["question"] for r in read_jsonl(pilot_dir / "eval_input" / "pretest_questions.jsonl")}
    questions |= {r["item_id"]: r["question"] for r in read_jsonl(pilot_dir / "eval_input" / "story_questions.jsonl")}
    fam_fact = {r["family_id"]: r["fact_id"] for r in read_jsonl(pilot_dir / "items_final.jsonl")}
    raw = _best_by_request(raw_paths)
    if override_paths:
        raw |= _best_by_request(override_paths)
    return cfg, facts, gold, questions, fam_fact, raw


def parse_item(item_id: str, fam_fact: dict[str, str]) -> dict[str, Any]:
    m = STORY_RE.match(item_id)
    if m:
        fam, expl, rel, q = m.groups()
        return {"family_id": fam, "fact_id": fam_fact[fam], "explicitness": expl, "relation": rel, "qtype": q}
    fid, q = item_id.split("_")
    return {"family_id": "", "fact_id": fid, "explicitness": "", "relation": "", "qtype": q}


def golds_for(item_id: str, info: dict, gold: dict, facts) -> tuple[list[str], list[str], str, str]:
    """返回 (本题可接受答案, 另一答案集合, 本题参考答案, 另一答案代表)。"""
    g = gold[item_id]
    own = [g["reference_answer"], *g["accepted_variants"]]
    q, f = info["qtype"], facts[info["fact_id"]]
    if q in ("Q0", "Q3"):                                  # 另一答案 = 故事/知识库里的"错误主张"对应的答案
        alt = [f.conflicting_belief_gold]
        return own, alt, g["reference_answer"], f.conflicting_belief_gold
    other_rel = "conflicting" if info["relation"] == "aligned" else "aligned"
    og = gold[f"{info['family_id']}_{info['explicitness']}_{other_rel}_{q}"]
    return own, [og["reference_answer"], *og["accepted_variants"]], g["reference_answer"], og["reference_answer"]


# --------------------------------------------------------------------------- 评分
def score_all(args) -> tuple[list[dict], list[str]]:
    cfg, facts, gold, questions, fam_fact, raw = load_inputs(args.raw, args.pilot_dir, args.raw_override)
    item_ids = list(questions)                            # Q0 在前，之后是故事题
    rows: list[dict] = []
    for m in cfg.evaluated_models:
        for item_id in item_ids:
            info = parse_item(item_id, fam_fact)
            own, alt, ref, alt_ref = golds_for(item_id, info, gold, facts)
            rec = raw.get(f"{m.condition_id}|{item_id}")
            u = (rec or {}).get("usage") or {}
            rows.append({
                "config_id": m.condition_id, "model_family": m.condition_id.split("__")[0],
                "thinking": "thinking" if m.thinking else "non_thinking", "item_id": item_id, **info,
                "question": questions[item_id], "model_answer": (rec or {}).get("content"), "reference": ref,
                "alternative": alt_ref, "_own": own, "_alt": alt, "request_ok": bool(rec and rec["ok"]),
                "error": (rec or {}).get("error") if rec else "no response recorded",
                "provider": (rec or {}).get("provider"), "finish_reason": (rec or {}).get("finish_reason"),
                "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                "cost_usd": u.get("cost"), "elapsed_s": (rec or {}).get("elapsed_s"), "attempts": (rec or {}).get("attempts"),
                "score": None, "method": "", "judge_verdict": "", "judge_reason": "", "matched_alt": False,
                "error_category": "", "note": "",
            })
    # --- 1) 规则
    need_judge: dict[str, dict] = {}
    for r in rows:
        if not r["request_ok"]:
            r["score"], r["method"] = "request_failed", "none"
            continue
        rs = rule_score(r["model_answer"], r["_own"], r["_alt"])
        r["rule_reason"] = rs.reason
        if rs.verdict == "correct":
            r["score"], r["method"] = "correct", "rule"
        elif rs.verdict == "wrong_alt":
            r["score"], r["method"], r["matched_alt"] = "incorrect", "rule", True
        else:
            payload = {"question": r["question"], "reference_answer": r["reference"], "reference_variants": r["_own"][1:],
                       "alternative_answer": r["alternative"], "alternative_variants": r["_alt"][1:],
                       "model_answer": r["model_answer"]}
            r["_jkey"] = judge_key(payload)
            need_judge[r["_jkey"]] = payload
    n_rule = sum(1 for r in rows if r["method"] == "rule")
    print(f"规则评分 {n_rule} 条；需要裁判/人工 {sum(1 for r in rows if r['score'] is None)} 条"
          f"（去重后 {len(need_judge)} 个不同的裁判输入）")
    # --- 2) 裁判
    cache: dict[str, dict] = {}
    if need_judge and not args.no_judge:
        cache = run_judge(need_judge, args.judge_model, args.out_dir / "judge_raw.jsonl", seed_paths=args.judge_seed)
    for r in rows:
        if r["score"] is not None:
            continue
        j = cache.get(r["_jkey"])
        if j is None:
            r["score"], r["method"], r["judge_reason"] = "pending", "rule_undecided", r.get("rule_reason", "")
            continue
        r["method"], r["judge_verdict"], r["judge_reason"] = "llm_judge", j["verdict"], j["reason"]
        r["score"] = {"matches_reference": "correct", "matches_alternative": "incorrect", "neither": "incorrect"}.get(j["verdict"], "pending")
        r["matched_alt"] = j["verdict"] == "matches_alternative"
    return rows, [m.condition_id for m in cfg.evaluated_models]


# --------------------------------------------------------------------------- 错误归因（启发式；无法确定 -> 待人工复核）
def classify_errors(rows: list[dict]) -> None:
    by = {(r["config_id"], r["item_id"]): r for r in rows}
    q0_ok = {(r["config_id"], r["fact_id"]): r["score"] == "correct" for r in rows if r["qtype"] == "Q0"}
    for r in rows:                                       # 先处理 Q0/Q1/Q3，再处理依赖 Q1 的 Q2
        r["q0_correct"] = q0_ok.get((r["config_id"], r["fact_id"]))
    order = {"Q0": 0, "Q1": 1, "Q3": 2, "Q2": 3}
    for r in sorted(rows, key=lambda x: order[x["qtype"]]):
        if r["score"] == "correct":
            continue
        q, rel = r["qtype"], r["relation"]
        if r["score"] == "request_failed":
            r["error_category"] = FAILED
        elif r["score"] == "pending":
            r["error_category"] = AMBIG if r["judge_verdict"] in ("matches_both", "unclear") else MANUAL
            r["note"] = "裁判认为两者都像/无法判断，或无裁判结果；待人工复核"
        elif q == "Q0":
            r["error_category"] = Q0ERR
            r["note"] = "答成了知识库里的错误主张" if r["matched_alt"] else "答案不匹配任何 gold（可能是知识缺口或评分歧义）"
        elif q == "Q3":
            if r["matched_alt"]:
                r["error_category"] = Q3FALSE
                r["note"] = "把故事里的错误主张当成了现实" + ("（该模型 Q0 答对，说明是故事干扰）" if r["q0_correct"] else "")
            else:
                r["error_category"], r["note"] = MANUAL, "Q3 答案不匹配任何 gold"
        elif q == "Q1":
            if rel == "conflicting" and r["matched_alt"]:
                r["error_category"] = REALITY
                r["note"] = "conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念"
            elif rel == "aligned" and r["matched_alt"]:
                r["error_category"], r["note"] = BELIEF, "aligned 题的 Q1 答成了 conflicting 的信念"
            else:
                r["error_category"], r["note"] = MANUAL, "Q1 答案不匹配任何 gold，可能是信念归因错误或措辞差异"
        else:                                            # Q2
            q1 = by.get((r["config_id"], r["item_id"].rsplit("_", 1)[0] + "_Q1"))
            q1_ok = q1 is not None and q1["score"] == "correct"
            if rel == "conflicting" and r["matched_alt"]:
                if q1_ok:
                    r["error_category"], r["note"] = REALITY, "Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动"
                elif q1 is not None and q1["error_category"] == REALITY:
                    r["error_category"], r["note"] = REALITY, "Q1 已是现实干扰，Q2 延续"
                else:
                    r["error_category"], r["note"] = BELIEF, "Q1 也错（非现实干扰类），Q2 的错误可能由信念归因错误传递"
            elif rel == "aligned" and r["matched_alt"]:
                r["error_category"], r["note"] = MANUAL, "aligned 题的 Q2 做了 conflicting 的行动，原因不明"
            elif q1_ok and answer_kind(r["model_answer"]) in ("numeric", "date_or_month", "coordinate"):
                r["error_category"] = NONTOM
                r["note"] = "Q1 答对，Q2 给出了一个不属于任何 gold 的具体数值/日期/坐标：可能是计算/映射错误"
            else:
                r["error_category"], r["note"] = MANUAL, "Q2 答案不匹配任何 gold"


# --------------------------------------------------------------------------- 汇总
def tally(rows: list[dict]) -> tuple[int, int, int, int]:
    """(正确数, 总数, 待复核数, 请求失败数)。待复核与失败都不计为正确。"""
    return (sum(r["score"] == "correct" for r in rows), len(rows), sum(r["score"] == "pending" for r in rows),
            sum(r["score"] == "request_failed" for r in rows))


def pct(n: int, d: int) -> float | None:
    return None if d == 0 else round(100 * n / d, 1)


def fmt(n: int, d: int) -> str:
    return f"{n}/{d}, {pct(n, d):.0f}%" if d else "n/a"


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:            # utf-8-sig：Excel 直接打开不乱码
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def sel(rows, config=None, q=None, rel=None, expl=None, family=None, mode=None):
    return [r for r in rows if (config is None or r["config_id"] == config) and (q is None or r["qtype"] == q)
            and (rel is None or r["relation"] == rel) and (expl is None or r["explicitness"] == expl)
            and (family is None or r["model_family"] == family) and (mode is None or r["thinking"] == mode)]


def accuracy_csv(rows, configs):
    out = []
    for c in configs:
        r0 = sel(rows, c)[0]
        base = [c, r0["model_family"], r0["thinking"]]
        n, d, p, f = tally(sel(rows, c, "Q0"))
        out.append([*base, "Q0", "", "", "Q0 (no story)", n, d, pct(n, d), p, f])
        for q in ("Q1", "Q2", "Q3"):
            for rel, expl in CONDS:
                n, d, p, f = tally(sel(rows, c, q, rel, expl))
                out.append([*base, q, rel, expl, f"{rel}/{expl}", n, d, pct(n, d), p, f])
            for label, kw in (("all four conditions", {}), ("aligned (implicit+explicit)", {"rel": "aligned"}),
                              ("conflicting (implicit+explicit)", {"rel": "conflicting"}),
                              ("implicit (aligned+conflicting)", {"expl": "implicit"}),
                              ("explicit (aligned+conflicting)", {"expl": "explicit"})):
                n, d, p, f = tally(sel(rows, c, q, **kw))
                out.append([*base, q, kw.get("rel", "pooled"), kw.get("expl", "pooled"), label, n, d, pct(n, d), p, f])
    return out


def key_metrics(rows, configs):
    M: list[list] = []

    def add(metric, scope, spec, la, a, lb, b, note=""):
        (na, da), (nb, db) = a[:2], b[:2]
        pa, pb = pct(na, da), pct(nb, db)
        diff = None if pa is None or pb is None else round(pa - pb, 1)
        M.append([metric, scope, spec, la, na, da, pa, lb, nb, db, pb, diff, note])

    fams = sorted({r["model_family"] for r in rows})
    for c in configs:
        # Application Gap = Q1 - Q2（同一条件、同一配置；分母=该条件下 12 个家族）
        for rel, expl in CONDS:
            add("Application Gap (Q1-Q2)", c, f"{rel}/{expl}", "Q1", tally(sel(rows, c, "Q1", rel, expl)),
                "Q2", tally(sel(rows, c, "Q2", rel, expl)), "分母 12 vs 12（12 个家族）")
        add("Application Gap (Q1-Q2)", c, "four conditions pooled", "Q1", tally(sel(rows, c, "Q1")), "Q2",
            tally(sel(rows, c, "Q2")), "分母 48 vs 48")
        # Conflict Gap = Aligned - Conflicting
        for q in ("Q1", "Q2", "Q3"):
            for expl in ("implicit", "explicit"):
                add("Conflict Gap (Aligned-Conflicting)", c, f"{q}, {expl}", "aligned", tally(sel(rows, c, q, "aligned", expl)),
                    "conflicting", tally(sel(rows, c, q, "conflicting", expl)), "分母 12 vs 12")
            add("Conflict Gap (Aligned-Conflicting)", c, f"{q}, implicit+explicit pooled", "aligned",
                tally(sel(rows, c, q, "aligned")), "conflicting", tally(sel(rows, c, q, "conflicting")), "分母 24 vs 24")
        # Explicitness Benefit = Explicit - Implicit
        for q in ("Q1", "Q2", "Q3"):
            for rel in ("aligned", "conflicting"):
                add("Explicitness Benefit (Explicit-Implicit)", c, f"{q}, {rel}", "explicit", tally(sel(rows, c, q, rel, "explicit")),
                    "implicit", tally(sel(rows, c, q, rel, "implicit")), "分母 12 vs 12")
            add("Explicitness Benefit (Explicit-Implicit)", c, f"{q}, aligned+conflicting pooled", "explicit",
                tally(sel(rows, c, q, expl="explicit")), "implicit", tally(sel(rows, c, q, expl="implicit")), "分母 24 vs 24")
        # Q0-conditioned Conflicting Q2：只看"该模型 Q0 答对的事实"上的 conflicting Q2
        conf_q2 = sel(rows, c, "Q2", "conflicting")
        for scope, subset in (("implicit+explicit pooled", conf_q2),
                              ("implicit", [r for r in conf_q2 if r["explicitness"] == "implicit"]),
                              ("explicit", [r for r in conf_q2 if r["explicitness"] == "explicit"])):
            a = tally([r for r in subset if r["q0_correct"]])
            b = tally([r for r in subset if not r["q0_correct"]])
            add("Q0-conditioned Conflicting Q2 accuracy", c, scope, "Q2 conflicting | Q0 correct", a,
                "Q2 conflicting | Q0 incorrect", b, "分母=该模型 Q0 答对/答错的事实所对应的 conflicting Q2 题数；Q0 答错组分母可能很小")
        # Paired Q2 Consistency：同一家族、同一 explicitness 下，aligned 与 conflicting 的 Q2 都答对
        for expl in ("implicit", "explicit", None):
            fams_ids = sorted({r["family_id"] for r in sel(rows, c, "Q2")})
            cells = Counter()
            both = tot = 0
            for fam in fams_ids:
                for e in ([expl] if expl else ["implicit", "explicit"]):
                    a = next(r for r in rows if r["config_id"] == c and r["family_id"] == fam and r["qtype"] == "Q2"
                             and r["relation"] == "aligned" and r["explicitness"] == e)
                    b = next(r for r in rows if r["config_id"] == c and r["family_id"] == fam and r["qtype"] == "Q2"
                             and r["relation"] == "conflicting" and r["explicitness"] == e)
                    ka, kb = a["score"] == "correct", b["score"] == "correct"
                    cells[(ka, kb)] += 1
                    tot += 1
                    both += ka and kb
            scope = expl or "implicit+explicit pooled"
            add("Paired Q2 Consistency (both aligned & conflicting Q2 correct)", c, scope, "pairs both correct", (both, tot),
                "all pairs", (tot, tot), "分母=家族数（pooled 时为 24 对）；差值列无意义，仅看 pairs both correct 的比例")
            for (ka, kb), n in sorted(cells.items(), reverse=True):
                add("Paired Q2 pattern", c, scope, f"aligned {'✓' if ka else '✗'} / conflicting {'✓' if kb else '✗'}", (n, tot),
                    "all pairs", (tot, tot), "四种组合的计数")
    # Thinking Benefit = Thinking - Non-thinking（同一模型家族）
    for fam in fams:
        for q in ("Q0", "Q1", "Q2", "Q3"):
            if q == "Q0":
                add("Thinking Benefit (Thinking-Non-thinking)", fam, "Q0", "thinking", tally(sel(rows, q=q, family=fam, mode="thinking")),
                    "non_thinking", tally(sel(rows, q=q, family=fam, mode="non_thinking")), "分母 12 vs 12")
                continue
            for rel, expl in CONDS:
                add("Thinking Benefit (Thinking-Non-thinking)", fam, f"{q}, {rel}/{expl}", "thinking",
                    tally(sel(rows, q=q, rel=rel, expl=expl, family=fam, mode="thinking")), "non_thinking",
                    tally(sel(rows, q=q, rel=rel, expl=expl, family=fam, mode="non_thinking")), "分母 12 vs 12")
            add("Thinking Benefit (Thinking-Non-thinking)", fam, f"{q}, four conditions pooled", "thinking",
                tally(sel(rows, q=q, family=fam, mode="thinking")), "non_thinking",
                tally(sel(rows, q=q, family=fam, mode="non_thinking")), "分母 48 vs 48")
    return M


def technical_rows(rows, configs, cfg):
    mc = {m.condition_id: m for m in cfg.evaluated_models}
    out = []
    tot = Counter()
    for c in configs:
        rs = sel(rows, c)
        m = mc[c]
        prov = Counter(r["provider"] for r in rs if r["provider"])
        ok = sum(r["request_ok"] for r in rs)
        fails = [f"{r['item_id']}: {r['error']}" for r in rs if not r["request_ok"]]
        pt = sum(r["prompt_tokens"] or 0 for r in rs)
        ct = sum(r["completion_tokens"] or 0 for r in rs)
        rt = sum(r["reasoning_tokens"] or 0 for r in rs)
        cost = sum(r["cost_usd"] or 0 for r in rs)
        retried = sum(1 for r in rs if (r["attempts"] or 1) > 1)
        trunc = sum(1 for r in rs if r["finish_reason"] == "length")
        el = [r["elapsed_s"] for r in rs if r["elapsed_s"]]
        out.append([c, m.model_id, m.pinned_provider, "; ".join(f"{k}×{v}" for k, v in prov.items()),
                    f"reasoning.enabled={m.thinking}", m.temperature if m.temperature is not None else "provider default",
                    len(rs), ok, len(rs) - ok, trunc, retried, pt, ct, rt, round(cost, 6),
                    round(sum(el) / len(el), 1) if el else "", " | ".join(fails)[:600]])
        tot.update(requests=len(rs), ok=ok, failed=len(rs) - ok, prompt=pt, completion=ct, reasoning=rt, cost=cost)
    out.append(["TOTAL", "", "", "", "", "", tot["requests"], tot["ok"], tot["failed"], "", "", tot["prompt"], tot["completion"],
                tot["reasoning"], round(tot["cost"], 6), "", ""])
    return out


def esc(s) -> str:
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ⏎ ").strip()


def clip(s, n=110) -> str:
    s = esc(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def error_markdown(rows, configs) -> str:
    L: list[str] = []
    a = L.append
    errs = [r for r in rows if r["score"] != "correct"]
    a("# Pilot 错误分析\n")
    a("> 自动归因只是**启发式**，类别后缀 `_candidate` 表示“可能是”；无法确定的都标为 `needs_manual_review` / `scoring_ambiguity`，没有强行归类。"
      "完整的模型原始回答、reference、评分结果见 `item_level_scores.csv`，完整 API 响应见 `raw_responses.jsonl`。\n")
    a("## 类别说明\n")
    a("| 类别 | 含义 |\n|---|---|")
    a(f"| `{REALITY}` | 现实干扰（候选）：conflicting 题里，Q1 答成了真实世界的答案而不是角色的信念；或 Q1 答对、Q2 却做了符合现实的行动 |")
    a(f"| `{BELIEF}` | 信念归因错误（候选）：aligned 题 Q1 答成了错误信念；或 Q1/Q2 同时出错且不属于上一类 |")
    a(f"| `{NONTOM}` | 非 ToM 推理错误（候选）：Q1 答对，Q2 给出的具体数值/日期/坐标不属于任何 gold（可能是计算、映射、格式问题） |")
    a(f"| `{Q3FALSE}` | Q3 把故事里的错误主张当成了现实 |")
    a(f"| `{Q0ERR}` | Q0（无故事）就答错：知识缺口，或评分歧义 |")
    a(f"| `{AMBIG}` | 评分歧义：裁判认为“两者都像”或“无法判断”，待人工复核 |")
    a(f"| `{MANUAL}` | 答案不匹配任何 gold，原因无法确定，待人工复核 |")
    a(f"| `{FAILED}` | 请求失败（没有可评分的回答） |\n")
    a("## 1. 各配置错误数量（按类别）\n")
    cats = [REALITY, BELIEF, NONTOM, Q3FALSE, Q0ERR, AMBIG, MANUAL, FAILED]
    a("| 配置 | 总错误/待复核 | " + " | ".join(f"`{c}`" for c in cats) + " |")
    a("|---|---|" + "---|" * len(cats))
    for c in configs:
        e = [r for r in errs if r["config_id"] == c]
        cnt = Counter(r["error_category"] for r in e)
        a(f"| {c} | {len(e)}/{len(sel(rows, c))} | " + " | ".join(str(cnt.get(k, 0)) for k in cats) + " |")
    a("")
    a("## 2. Q1 正确但 Q2 错误（Application Gap 的来源）\n")
    a("同一配置、同一家族、同一条件下，Q1 评为正确而 Q2 评为错误/待复核。\n")
    by = {(r["config_id"], r["item_id"]): r for r in rows}
    gap_rows = []
    for r in rows:
        if r["qtype"] == "Q2" and r["score"] != "correct":
            q1 = by[(r["config_id"], r["item_id"].rsplit("_", 1)[0] + "_Q1")]
            if q1["score"] == "correct":
                gap_rows.append(r)
    a(f"共 {len(gap_rows)} 条。\n")
    a("| 配置 | 家族/条件 | Q2 模型回答 | Q2 reference | 另一条件答案 | 类别 | 说明 |\n|---|---|---|---|---|---|---|")
    for r in sorted(gap_rows, key=lambda x: (x["config_id"], x["family_id"], x["relation"], x["explicitness"])):
        a(f"| {r['config_id']} | {r['family_id']} {r['relation'][:4]}/{r['explicitness'][:4]} ({r['fact_id']}) | {clip(r['model_answer'], 90)} | "
          f"{clip(r['reference'], 60)} | {clip(r['alternative'], 60)} | `{r['error_category']}` | {clip(r['note'], 80)} |")
    a("")
    a("## 3. 全部错误与待复核题目（按配置）\n")
    for c in configs:
        e = sorted([r for r in errs if r["config_id"] == c], key=lambda x: (x["qtype"] != "Q0", x["family_id"], x["qtype"], x["relation"], x["explicitness"]))
        a(f"### {c}（{len(e)} 条）\n")
        a("| item | 模型回答 | reference | 评分方式 | 类别 | 说明 |\n|---|---|---|---|---|---|")
        for r in e:
            a(f"| {r['item_id']} | {clip(r['model_answer'], 100)} | {clip(r['reference'], 60)} | {r['method']}"
              f"{'/' + r['judge_verdict'] if r['judge_verdict'] else ''} | `{r['error_category']}` | {clip(r['note'], 80)} |")
        a("")
    a("## 4. 评分说明与已知的评分歧义来源\n")
    meth = Counter(r["method"] for r in rows)
    a(f"- 评分方式统计：{dict(meth)}。`rule` = 规则评分；`llm_judge` = 规则无法确定后由 LLM 裁判（只比较语义，不判断事实）；`rule_undecided` = 未调用裁判。")
    amb = [r for r in rows if r["score"] == "pending"]
    a(f"- 待人工复核（pending）共 {len(amb)} 条，**不计入正确**；这些条目已在上面的表里标出。")
    jd = [r for r in rows if r["method"] == "llm_judge"]
    a(f"- 由裁判判定的有 {len(jd)} 条，其中判为 neither 的 {sum(r['judge_verdict'] == 'neither' for r in jd)} 条（记为错误）；建议抽查这部分。")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, nargs="+", default=[RES / "raw_responses.jsonl"])
    ap.add_argument("--raw-override", type=Path, nargs="*", default=[],
                    help="其中的请求整体替换 --raw 里同名请求（例如用 F002 新版本的响应替换旧版本）")
    ap.add_argument("--pilot-dir", type=Path, default=PILOT,
                    help="含 eval_input/、answer_keys/、items_final.jsonl 的数据目录")
    ap.add_argument("--judge-seed", type=Path, nargs="*", default=[], help="只读的裁判缓存（命中则不重新调用裁判）")
    ap.add_argument("--out-dir", type=Path, default=RES)
    ap.add_argument("--judge-model", default="gpt-6.1-sol")
    ap.add_argument("--no-judge", action="store_true")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    rows, configs = score_all(args)
    classify_errors(rows)
    cfg = load_config()
    out = args.out_dir
    write_csv(out / "accuracy_summary.csv",
              ["config_id", "model_family", "thinking_mode", "question", "knowledge_relation", "explicitness", "group",
               "correct", "total", "accuracy_pct", "pending_manual_review", "request_failures"], accuracy_csv(rows, configs))
    write_csv(out / "key_metrics.csv",
              ["metric", "scope", "condition_spec", "group_a", "a_correct", "a_total", "a_pct", "group_b", "b_correct", "b_total",
               "b_pct", "diff_pp (a-b)", "denominator_note"], key_metrics(rows, configs))
    write_csv(out / "technical_report.csv",
              ["config_id", "model_id", "pinned_provider", "providers_seen", "reasoning_setting", "temperature", "requests", "ok",
               "failed", "truncated(finish=length)", "requests_with_retries", "prompt_tokens", "completion_tokens",
               "reasoning_tokens", "cost_usd", "avg_elapsed_s", "failures"], technical_rows(rows, configs, cfg))
    cols = ["config_id", "item_id", "family_id", "fact_id", "qtype", "relation", "explicitness", "question", "model_answer",
            "reference", "alternative", "score", "method", "judge_verdict", "judge_reason", "matched_alt", "error_category",
            "note", "q0_correct", "provider", "finish_reason", "prompt_tokens", "completion_tokens", "reasoning_tokens",
            "cost_usd", "request_ok", "error"]
    write_csv(out / "item_level_scores.csv", cols, [[r.get(c) for c in cols] for r in rows])
    (out / "error_analysis.md").write_text(error_markdown(rows, configs), encoding="utf-8", newline="\n")
    print("已写出：accuracy_summary.csv, key_metrics.csv, technical_report.csv, item_level_scores.csv, error_analysis.md ->", out)
    for c in configs:
        n, d, p, f = tally(sel(rows, c, "Q0"))
        print(f"  {c}: Q0 {fmt(n, d)} | " + " | ".join(f"{q} {fmt(*tally(sel(rows, c, q))[:2])}" for q in ("Q1", "Q2", "Q3"))
              + f" | pending {sum(r['score'] == 'pending' for r in sel(rows, c))} failed {sum(r['score'] == 'request_failed' for r in sel(rows, c))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
