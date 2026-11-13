"""Milestone 2 smoke test：对 1 条事实走一遍  propose_bundles -> 选 bundle -> generate_family -> 渲染/检查。

会真实调用造题模型（共 2 次请求，费用很低）。所有原始响应、检查结果和一份可读的审查报告都会保存。

用法：
    python src/smoke_generate.py --fact K03 --template T1 --dry-run   # 只打印将要发送的内容，不调用 API
    python src/smoke_generate.py --fact K03 --template T1             # 真实调用
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from candidates import make_family_id
from common import REPO_ROOT
from config import load_config
from generate_families import generate_with_regeneration
from generation_prompts import generate_payload, load_guideline, prompt_version, propose_payload
from llm_client import make_client
from propose_bundles import run_propose, select_bundle
from sampling import AssignmentSampler
from dataclasses import replace
from schemas import CONDITIONS, CandidateRecord
from validate_knowledge import load_knowledge

DEFAULT_OUT = REPO_ROOT / "datasets" / "generation"


def render_review_md(rec: CandidateRecord, selection_reason: str) -> str:
    L: list[str] = []
    a = L.append
    a(f"# 候选题审查报告：family {rec.family_id}（fact {rec.fact_id}）\n")
    a(f"- **状态**：`{rec.validation_status}`（human_validated = {rec.human_validated}；仅为自动检查结果，需人工审查）")
    a(f"- 模板 `{rec.template_id}` | action `{rec.action_type}` | reasoning `{rec.reasoning_structure}` | belief cues {rec.belief_cue_ids}")
    a(f"- 人物 {rec.agent} | 场景 {rec.setting} | 来源类型 {rec.source_type}")
    a(f"- 抽样器分配：{rec.provenance.assignments} | 行动设计标签：`{rec.design_tag}`")
    a(f"- bundle 选择：{selection_reason}")
    a(f"- 造题模型 `{rec.provenance.generator_model}` | prompt_version `{rec.provenance.prompt_version[:12]}…` | {rec.provenance.created_at}\n")
    a("## 锁定事实（来自 knowledge_pool.jsonl，未被改动）")
    a(f"- world_fact：{rec.fact.world_fact}\n- aligned_claim：{rec.fact.aligned_claim}\n- conflicting_claim：{rec.fact.conflicting_claim}")
    a(f"- Q0（无故事）：{rec.fact.pretest_question} → `{rec.fact.world_gold}`\n")
    a("## Bundle")
    b = rec.bundle
    a(f"- 目标：{b.agent_goal}\n- 新任务：{b.new_task}\n- 约束：{b.action_constraints}\n- 目标输出：{b.target_output}")
    a(f"- 行动 gold：aligned = `{b.aligned_action_gold}`，conflicting = `{b.conflicting_action_gold}`")
    a(f"- belief→action 规则：{b.belief_to_action_rule}")
    a(f"- risk_flags：{b.risk_flags or '无'}；potential_ambiguities：{b.potential_ambiguities or '无'}\n")
    a("## 四个条件的故事")
    for cond in CONDITIONS:
        a(f"\n### {cond}\n{getattr(rec.variants, cond) if rec.variants else '（渲染失败）'}")
    a("\n## 问题（四个版本完全相同）")
    a(f"- **Q1（信念）**：{rec.questions.q1}\n- **Q2（行动）**：{rec.questions.q2}\n- **Q3（现实）**：{rec.questions.q3}\n")
    g = rec.proposed_gold
    a("## 候选 gold（provisional，待人工确认）")
    a("| | aligned | conflicting |\n|---|---|---|")
    a(f"| Q1 | {g.aligned.q1} | {g.conflicting.q1} |\n| Q2 | {g.aligned.q2} | {g.conflicting.q2} |\n| Q3（现实，不变） | {g.q3} | {g.q3} |")
    a(f"\n答案同义写法：{rec.answer_variants.model_dump()}\n")
    a("## 自动检查结果")
    if not rec.issues:
        a("无 error / warning。")
    for i in rec.issues:
        a(f"- **{i.severity}** `{i.code}`：{i.message}")
    return "\n".join(L) + "\n"


def _save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fact", default=None, help="如 K03")
    ap.add_argument("--template", default=None, help="可选：覆盖抽样器分配的模板 T1/T2/T3/T4A/T4C/T5")
    ap.add_argument("--show-assignments", type=int, default=0, metavar="N", help="只打印前 N 个 family 的抽样分配，不调用 API")
    ap.add_argument("--action-type", default=None)
    ap.add_argument("--reasoning-structure", default=None)
    ap.add_argument("--family-number", type=int, default=1)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true", help="只打印请求内容，不调用 API")
    ap.add_argument("--propose-only", action="store_true", help="只做 propose_bundles（约 7 千 token），不写故事")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    cfg = load_config()
    gen = cfg.generator
    sampler = AssignmentSampler.from_config(cfg.sampling)
    if args.show_assignments:
        print("family  模板   人物（性别）")
        for a in sampler.preview(args.show_assignments):
            print(f"F{a.index + 1:03d}    {a.template_id:<5}  {a.agent_name} ({a.agent_gender})")
        return 0
    if not args.fact:
        print("请用 --fact 指定事实（如 K03）")
        return 1
    asg = sampler.assignment_for(args.family_number - 1)
    if args.template:
        asg = replace(asg, template_id=args.template)
    facts = load_knowledge()
    fact = next((f for f in facts if f.fact_id == args.fact), None)
    if fact is None:
        print(f"找不到事实 {args.fact}")
        return 1
    max_tokens = gen.max_output_tokens or 16000

    if args.dry_run:
        pv = prompt_version()
        print(f"[dry-run] 不会调用 API。造题模型 = {gen.model_id}，max_output_tokens = {max_tokens}，prompt_version = {pv[:12]}…")
        print(f"[dry-run] instructions = guideline 全文（{len(load_guideline())} 字符）")
        print("[dry-run] 第 1 次请求（propose_bundles）的 user 输入：")
        print(json.dumps(propose_payload(fact, max_bundles=gen.n_bundles_per_fact, template_id=asg.template_id,
                                         action_type=args.action_type, reasoning_structure=args.reasoning_structure),
                         ensure_ascii=False, indent=2))
        return 0

    client = make_client()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = args.out_dir
    tag = f"{fact.fact_id}_{ts}"
    print(f"造题模型 {gen.model_id} | 事实 {fact.fact_id} | family F{args.family_number:03d} | "
          f"模板 {asg.template_id} | 人物 {asg.agent_name} ({asg.agent_gender})")

    # ------------------------------------------------------------ Stage B
    print("\n[1/2] propose_bundles …")
    pr = run_propose(client, model=gen.model_id, fact=fact, max_bundles=gen.n_bundles_per_fact,
                     max_output_tokens=max_tokens, max_retries=gen.max_retries, template_id=asg.template_id,
                     action_type=args.action_type, reasoning_structure=args.reasoning_structure)
    _save(out / f"{tag}_1_propose.json", {**pr.call.log_dict(), "checks": [i.model_dump() for i in pr.issues]})
    print(f"      用时 {pr.call.elapsed_s:.1f}s | 用量 {pr.call.usage and {k: v for k, v in pr.call.usage.items() if k in ('input_tokens', 'output_tokens', 'total_tokens')}}")
    if not pr.call.ok:
        print(f"      失败 [{pr.call.error_type}]：{pr.call.error_detail}\n      已保存日志到 {out}")
        return 2
    proposal = pr.call.parsed
    print(f"      status = {proposal.status}，返回 {len(proposal.bundles)} 个 bundle")
    if proposal.status != "candidates_proposed":
        print(f"      no_valid_bundle：{proposal.failure_reason}")
        return 3
    for b in proposal.bundles:
        errs = [i.code for i in pr.per_bundle_issues[b.bundle_id] if i.severity == 'error']
        warns = [i.code for i in pr.per_bundle_issues[b.bundle_id] if i.severity == 'warning']
        print(f"      - {b.bundle_id} [{','.join(b.suggested_template_ids)}/{b.action_type}/{b.reasoning_structure}] "
              f"aligned={b.aligned_action_gold!r} conflicting={b.conflicting_action_gold!r} errors={errs} warnings={warns}")
    bundle, reason = select_bundle(proposal, pr.per_bundle_issues)
    print("      ", reason)
    if bundle is None:
        return 3
    if args.propose_only:
        print(f"\n--propose-only：只做了第一步，日志已保存到 {out}")
        return 0

    # ------------------------------------------------------------ Stage C/D
    print(f"\n[2/2] generate_family（bundle {bundle.bundle_id}，模板 {asg.template_id}，人物 {asg.agent_name}；"
          f"被检查拒绝时最多重新生成 {cfg.sampling.max_regenerations} 次）…")
    attempts = generate_with_regeneration(
        client, model=gen.model_id, fact=fact, bundle=bundle, assignment=asg,
        family_id=make_family_id(args.family_number), max_output_tokens=max_tokens, max_retries=gen.max_retries,
        max_regenerations=cfg.sampling.max_regenerations, binary_policy=cfg.sampling.binary_option_policy,
        notes=f"smoke test; bundle selection: {reason}",
    )
    for at in attempts:
        _save(out / f"{tag}_2_family_attempt{at.number}.json",
              {**at.call.log_dict(), "feedback_given": at.feedback_given,
               "checks": [i.model_dump() for i in at.record.issues] if at.record else []})
        u = at.call.usage and {k: v for k, v in at.call.usage.items() if k in ("input_tokens", "output_tokens", "total_tokens")}
        status = (f"{at.record.validation_status}，design_tag={at.record.design_tag}，"
                  f"errors={[i.code for i in at.record.issues if i.severity == 'error']}") if at.record else (
            f"失败 [{at.call.error_type}]：{at.call.error_detail}" if not at.call.ok else
            f"needs_revision：{at.call.parsed.revision_reasons}")
        print(f"      第 {at.number} 次：用时 {at.call.elapsed_s:.1f}s | 用量 {u} | {status}")
    last = attempts[-1]
    rec = last.record
    if rec is None:
        print("      没有得到可用的候选；各次尝试的日志已保存到", out)
        return 3 if last.call.ok else 2

    _save(out / f"{tag}_3_candidate.json", json.loads(rec.model_dump_json()))
    md_path = out / f"{tag}_4_review.md"
    md_path.write_text(render_review_md(rec, reason), encoding="utf-8", newline="\n")
    n_err = sum(i.severity == "error" for i in rec.issues)
    n_warn = sum(i.severity == "warning" for i in rec.issues)
    print(f"\n完成：validation_status = {rec.validation_status}（{n_err} error，{n_warn} warning）")
    print(f"审查报告：{md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
