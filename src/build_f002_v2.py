"""构建 F002 v2（研究者提供的新故事设计，K14 海豚）并生成评测文件。

输入：研究者给定的故事 backbone、claim、解释句、问题与 gold（含 Q0 新问法）。四个条件由 render_pairs 确定性渲染，
再套用与其他 family 相同的检查与导出（泄漏检查）。

输出：
  datasets/generation/pilot_12/f002_v2/   只含 F002 v2（Q0 + 12 条故事题）：eval_input/、answer_keys/、items_final.jsonl
  datasets/generation/pilot_12_v2/        完整 12 题数据集：用 F002 v2 与新的 K14 Q0 替换 pilot_12 里的 F002 v1 与旧 K14 Q0
注意：不修改知识库 knowledge_pool_pilot_12_v1.jsonl（K14 的 Q0 新问法只出现在上面两个评测目录里）。
"""
from __future__ import annotations

import json
import sys

from candidates import build_candidate
from common import REPO_ROOT, read_jsonl, write_jsonl
from config import load_config
from export_evaluation import assert_no_leak, build_messages, export_gold, export_story_questions
from sampling import Assignment
from schemas import Bundle, GenerateFamilyOutput
from validate_knowledge import load_knowledge

PILOT = REPO_ROOT / "datasets" / "generation" / "pilot_12"
V2 = PILOT / "f002_v2"
MERGED = REPO_ROOT / "datasets" / "generation" / "pilot_12_v2"

BACKBONE = (
    "Henry has just joined a stop-motion club and is working on his first dolphin animation. During several "
    "rehearsals, he watches an experienced animator demonstrate how to stage a dolphin's breathing. The animator "
    "explains the same rule each time: {{CLAIM_SPAN}}{{BELIEF_INSERTION}} Henry now works independently on a new scene. "
    "The dolphin is swimming several metres below the water's surface. His next frame must show the dolphin at the "
    "moment it takes a breath. He uses the explanation from the rehearsals to decide where to position it."
)
CLAIM_A, CLAIM_C = "Dolphins breathe air using lungs.", "Dolphins breathe underwater using gills."
PROP_A, PROP_C = "dolphins breathe air using lungs", "dolphins breathe underwater using gills"
Q0 = "Which internal organs do dolphins use to exchange oxygen and carbon dioxide?"
Q1 = "Which organs does Henry believe dolphins use for gas exchange?"
Q2 = "Where will Henry position the dolphin when it takes its next breath?"
Q3 = "Which organs do dolphins actually use for gas exchange?"
GOLD = {"aligned": {"q1": "lungs", "q2": "At the water's surface"},
        "conflicting": {"q1": "gills", "q2": "Below the surface, fully submerged"}, "q3": "lungs"}
# 同义答案：只收与问题语义匹配的说法（Q2 问的是"位置"）。不收过于宽泛的 "surface"（它同时出现在 "below the surface" 里）。
VARIANTS = {
    "q1_aligned": ["lung"], "q1_conflicting": ["gill"],
    "q2_aligned": ["At the surface", "At the water surface", "At the surface of the water", "Surfacing",
                   "To the surface", "Up to the surface", "Bring it up to the surface"],
    "q2_conflicting": ["Fully submerged", "Underwater", "Below the surface", "Beneath the surface", "Submerged",
                       "Under the water", "Stay underwater"],
    "q3": ["lung"],
}
Q0_VARIANTS = ["lung"]


def build():
    cfg = load_config()
    facts = load_knowledge()
    k14 = next(f for f in facts if f.fact_id == "K14")
    v1_items = {r["family_id"]: r for r in read_jsonl(PILOT / "items_final.jsonl")}
    orig = v1_items["F002"]
    bundle = Bundle.model_validate({
        **orig["bundle"],
        "action_type": "A4", "reasoning_structure": "prediction_application",
        "agent_goal": "Stage a dolphin's breathing correctly in a new stop-motion scene",
        "new_task": "Decide where to position the dolphin in the next frame, at the moment it takes a breath",
        "action_constraints": "The dolphin is swimming several metres below the water's surface and the next frame must show it taking a breath.",
        "target_output": "Where Henry positions the dolphin when it takes its next breath",
        "aligned_action_gold": GOLD["aligned"]["q2"], "conflicting_action_gold": GOLD["conflicting"]["q2"],
        "belief_to_action_rule": "A dolphin believed to breathe air with lungs must come up to the surface to breathe; one believed to "
                                 "breathe underwater with gills can stay fully submerged.",
        "risk_flags": ["agent_prior_knowledge_risk", "source_acceptance_ambiguity"],
        "risk_notes": "Henry may already know that dolphins are air-breathing mammals; repeated demonstration by an experienced "
                      "animator supports but does not establish acceptance of the conflicting rule.",
    })
    out = GenerateFamilyOutput.model_validate({
        "task_mode": "generate_family", "fact_id": "K14", "bundle_id": bundle.bundle_id, "status": "candidate_generated",
        "template_id": orig["template_id"], "agent_name": orig["agent_name"], "setting_domain": orig["setting_domain"],
        "setting": "A stop-motion club", "source_type": "Experienced animator's repeated demonstrations",
        "belief_cue_ids": ["B2", "B4"], "action_type": "A4", "reasoning_structure": "prediction_application",
        "story_backbone": BACKBONE, "claim_span_aligned": CLAIM_A, "claim_span_conflicting": CLAIM_C,
        "belief_proposition_aligned": PROP_A, "belief_proposition_conflicting": PROP_C,
        "belief_question": Q1, "action_question": Q2, "reality_question": Q3,
        "proposed_gold": {"aligned": GOLD["aligned"], "conflicting": GOLD["conflicting"], "q3": GOLD["q3"]},
        "answer_variants": VARIANTS, "action_constraints": bundle.action_constraints,
        "belief_to_action_rule": bundle.belief_to_action_rule, "risk_flags": bundle.risk_flags, "risk_notes": bundle.risk_notes,
        "validation_status": "needs_human_review", "failure_reason": None,
    })
    prov = orig["provenance"]
    rec = build_candidate(
        family_id="F002", fact=k14, bundle=bundle, family_out=out, generator_model=prov["generator_model"],
        prompt_version=prov["prompt_version"], created_at=prov["created_at"],
        notes="F002 v2: story/questions/golds provided by the researcher (replaces the v1 story); Q0 question also changed for K14.",
        assignment=Assignment(**prov["assignments"]),
    )
    return cfg, facts, k14, rec, v1_items


def export_v2(cfg, k14, rec):
    instr = cfg.answer_instruction
    story = export_story_questions([rec], include_rejected=True)
    pretest = [{"fact_id": "K14", "item_id": "K14_Q0", "question_type": "Q0", "question": Q0}]
    gold = [g for g in export_gold([k14], [rec], include_rejected=True) if g["item_id"] != "K14_Q0"]
    gold.insert(0, {"item_id": "K14_Q0", "fact_id": "K14", "question_type": "Q0", "reference_answer": "lungs",
                    "accepted_variants": Q0_VARIANTS, "gold_status": "pre_specified", "fact_status": k14.fact_status})
    assert_no_leak(pretest + story, gold)
    requests = [{"item_id": r["item_id"], "messages": build_messages(r, instr)} for r in pretest + story]
    return pretest, story, gold, requests


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cfg, facts, k14, rec, v1_items = build()
    words = max(len(rec.variants.implicit_aligned.split()), len(rec.variants.implicit_conflicting.split()))
    errors = [i for i in rec.issues if i.severity == "error"]
    print(f"F002 v2：implicit 故事 {words} 词；状态 {rec.validation_status}；自动检查 {len(errors)} error / "
          f"{sum(i.severity == 'warning' for i in rec.issues)} warning")
    for i in rec.issues:
        print(f"   [{i.severity}] {i.code}: {i.message}")
    if errors:
        return 1
    pretest, story, gold, requests = export_v2(cfg, k14, rec)

    item = {**json.loads(rec.model_dump_json()), "human_edited": True, "edit_source": "researcher-provided F002 v2 design",
            "edit_notes": ["完整替换 v1 的 F002 故事与问题；K14 的 Q0 评测问法改为 "
                           f"“{Q0}”（知识库文件未改）。"]}
    write_jsonl(V2 / "items_final.jsonl", [item])
    write_jsonl(V2 / "eval_input" / "pretest_questions.jsonl", pretest)
    write_jsonl(V2 / "eval_input" / "story_questions.jsonl", story)
    write_jsonl(V2 / "eval_input" / "eval_requests.jsonl", requests)
    write_jsonl(V2 / "answer_keys" / "gold_answers.jsonl", gold)

    # ---- 完整 12 题数据集：替换 F002 与 K14 Q0
    new_item_ids = {r["item_id"] for r in pretest + story}
    items = [item if r["family_id"] == "F002" else r for r in read_jsonl(PILOT / "items_final.jsonl")]
    pre = [pretest[0] if r["item_id"] == "K14_Q0" else r for r in read_jsonl(PILOT / "eval_input" / "pretest_questions.jsonl")]
    by_story = {r["item_id"]: r for r in story}
    sq = [by_story.get(r["item_id"], r) for r in read_jsonl(PILOT / "eval_input" / "story_questions.jsonl")]
    by_req = {r["item_id"]: r for r in requests}
    rq = [by_req.get(r["item_id"], r) for r in read_jsonl(PILOT / "eval_input" / "eval_requests.jsonl")]
    by_gold = {g["item_id"]: g for g in gold}
    gd = [by_gold.get(g["item_id"], g) for g in read_jsonl(PILOT / "answer_keys" / "gold_answers.jsonl")]
    assert {r["item_id"] for r in sq} >= {i for i in new_item_ids if i != "K14_Q0"} and len(sq) == 144 and len(rq) == 156 and len(gd) == 156
    write_jsonl(MERGED / "items_final.jsonl", items)
    write_jsonl(MERGED / "eval_input" / "pretest_questions.jsonl", pre)
    write_jsonl(MERGED / "eval_input" / "story_questions.jsonl", sq)
    write_jsonl(MERGED / "eval_input" / "eval_requests.jsonl", rq)
    write_jsonl(MERGED / "answer_keys" / "gold_answers.jsonl", gd)
    assert_no_leak(pre + sq, gd)
    print(f"已写出：{V2}（{len(requests)} 条请求）与 {MERGED}（{len(rq)} 条请求）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
