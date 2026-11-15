"""把研究者在 REVIEW_new.md 里**人工修改后**的题目导回流水线，并导出成"实际发给被测模型"的文件。

研究者主要修改的是每张卡片里的"合并故事"（**[aligned ｜ conflicting]** 与 ⟨解释句⟩）和个别问题；折叠起来的四个条件完整故事
没有同步修改，所以这里**以合并故事为准**：先把合并故事还原成 backbone（{{CLAIM_SPAN}} / {{BELIEF_INSERTION}}），
再用 render_pairs 的确定性渲染重新生成四个条件，最后跑同一套检查并导出。

还原规则（尽量不改动研究者的文字，只做必要的技术性整理，所有整理都会写进 EXPORT_NOTES.md）：
  - 空白整理：连续空格/换行合并为一个空格（不改任何词）；
  - claim 分隔符既接受 "｜" 也接受 " | "；
  - ⟨解释句⟩ 缺失时，按固定句式补回（紧跟在来源句之后），用原始记录里的 belief proposition；
  - 研究者改了 claim、但 ⟨ ⟩ 里的 proposition 还是旧的（没跟着改）时，proposition 按新 claim 重新推出
    （首字母小写、去句号），保证 explicit 句与来源句一致；
  - 不改写研究者的其他任何文字（包括疑似笔误，只在 EXPORT_NOTES.md 里提示）。
可用 --set-question FAM:q1=文本 显式覆盖某个问题（会记录在 EXPORT_NOTES.md）。

用法：
    python src/import_reviewed.py datasets/generation/pilot_12/REVIEW_new.md \
        --candidates datasets/generation/pilot_12/candidates.jsonl --out-dir datasets/generation/pilot_12
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from candidates import build_candidate
from common import read_jsonl, write_jsonl
from config import load_config
from export_evaluation import (
    LeakError, assert_no_leak, build_messages, export_gold, export_pretest, export_story_questions,
)
from render_pairs import BELIEF_TOKEN, CLAIM_TOKEN
from sampling import Assignment
from schemas import Bundle, CandidateRecord, GenerateFamilyOutput, KnowledgeRecord
from validate_knowledge import load_knowledge


class ReviewParseError(ValueError):
    pass


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()


def _split_pair(inner: str) -> tuple[str, str]:
    parts = inner.split("｜") if "｜" in inner else re.split(r"\s\|\s", inner)
    if len(parts) != 2:
        raise ReviewParseError(f"方括号里应恰好有两段（aligned ｜ conflicting），实际 {len(parts)} 段：{inner[:80]!r}")
    return _ws(parts[0]), _ws(parts[1])


def derive_proposition(claim: str) -> str:
    """由 claim 推出 belief proposition：去句末标点，首字母小写。"""
    s = _ws(claim).rstrip(".!?")
    return s[:1].lower() + s[1:]


# --------------------------------------------------------------------------- 解析 REVIEW 文件
@dataclass
class Card:
    family_id: str
    story: str
    rows: dict[str, tuple[str, str, str]]      # "Q1" -> (问题, aligned gold, conflicting gold)


def parse_review(text: str) -> dict[str, Card]:
    text = text.replace("\r\n", "\n")
    parts = re.split(r'<a id="(F\d+)"></a>', text)
    cards: dict[str, Card] = {}
    for i in range(1, len(parts), 2):
        fam, body = parts[i], parts[i + 1]
        m = re.search(r"\*\*故事\*\*[^\n]*\n\n((?:>[^\n]*\n?)+)", body)
        if not m:
            raise ReviewParseError(f"{fam}: 找不到“故事”引用块")
        story = " ".join(line[1:].strip() for line in m.group(1).splitlines())
        rows: dict[str, tuple[str, str, str]] = {}
        for line in body.splitlines():
            mm = re.match(r"\|\s*(Q[123])\s", line)
            if mm:
                cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
                if len(cells) != 4:
                    raise ReviewParseError(f"{fam}: {mm.group(1)} 行应有 4 列，实际 {len(cells)}")
                rows[mm.group(1)] = (cells[1], cells[2], cells[3])
        if set(rows) != {"Q1", "Q2", "Q3"}:
            raise ReviewParseError(f"{fam}: 问题表应包含 Q1/Q2/Q3，实际 {sorted(rows)}")
        cards[fam] = Card(fam, story, rows)
    return cards


@dataclass
class ParsedStory:
    backbone: str
    claim_aligned: str
    claim_conflicting: str
    prop_aligned: str | None
    prop_conflicting: str | None
    agent_name: str | None


def parse_story(story: str) -> ParsedStory:
    story = _ws(story)
    m = re.search(r"\*\*\[(.*?)\]\*\*", story, flags=re.S)
    if not m:
        raise ReviewParseError("故事里找不到 **[aligned ｜ conflicting]** 标记")
    ca, cc = _split_pair(m.group(1))
    pre, rest = story[: m.start()], story[m.end():]
    bm = re.search(r"\s*⟨(.*?)⟩", rest, flags=re.S)
    pa = pc = name = None
    if bm:
        mid, post = rest[: bm.start()].strip(), rest[bm.end():]
        mm = re.fullmatch(r"(.+?) believes that \[(.*)\]\.", _ws(bm.group(1)))
        if not mm:
            raise ReviewParseError(f"⟨ ⟩ 里应为 '<Name> believes that [A ｜ B].'，实际：{bm.group(1)[:80]!r}")
        name = mm.group(1)
        pa, pc = _split_pair(mm.group(2))
    elif rest.startswith("."):
        mid, post = ".", rest[1:]
    elif re.search(r"[.!?][\"')\]”’]*$", ca):
        mid, post = "", rest
    else:
        raise ReviewParseError("没有 ⟨ ⟩，且 claim 之后不是句末标点，无法确定解释句的插入位置")
    if mid not in ("", "."):
        raise ReviewParseError(f"claim 与解释句之间还有其他文字：{mid!r}")
    backbone = pre + CLAIM_TOKEN + mid + BELIEF_TOKEN + (" " + post.strip() if post.strip() else "")
    return ParsedStory(backbone, ca, cc, pa, pc, name)


# --------------------------------------------------------------------------- 重建候选
def rebuild(orig: dict[str, Any], card: Card, fact: KnowledgeRecord,
            set_q: dict[tuple[str, str], str]) -> tuple[CandidateRecord, list[str]]:
    fam = orig["family_id"]
    notes: list[str] = []
    ps = parse_story(card.story)
    if ps.agent_name and ps.agent_name != orig["agent_name"]:
        raise ReviewParseError(f"{fam}: ⟨ ⟩ 里的名字 {ps.agent_name!r} 与分配的 {orig['agent_name']!r} 不一致")

    props = {}
    for side, claim, new_prop in (("aligned", ps.claim_aligned, ps.prop_aligned),
                                  ("conflicting", ps.claim_conflicting, ps.prop_conflicting)):
        o_claim, o_prop = orig[f"claim_span_{side}"], orig[f"belief_proposition_{side}"]
        prop = new_prop if new_prop is not None else o_prop
        claim_changed = _ws(claim) != _ws(o_claim)
        if claim_changed and _ws(prop) == _ws(o_prop) and _ws(prop) != derive_proposition(claim):
            prop = derive_proposition(claim)
            notes.append(f"{side}：你改了来源声明，但 ⟨ ⟩ 里的 belief proposition 还是旧的，已按新声明改为 “{prop}”。")
        props[side] = prop
    if ps.prop_aligned is None:
        notes.append("你的故事里没有 ⟨ ⟩（explicit 条件的解释句），已按固定句式补回，使用原始记录里的 belief proposition。")
    for side, claim in (("aligned", ps.claim_aligned), ("conflicting", ps.claim_conflicting)):
        if _ws(claim) != _ws(orig[f"claim_span_{side}"]):
            notes.append(f"{side} 来源声明已按你的修改：{claim!r}（原：{orig[f'claim_span_{side}']!r}）。")

    og = orig["proposed_gold"]
    q = {k: v[0] for k, v in card.rows.items()}
    gold = {"Q1": (card.rows["Q1"][1], card.rows["Q1"][2]), "Q2": (card.rows["Q2"][1], card.rows["Q2"][2]),
            "Q3": (card.rows["Q3"][1], card.rows["Q3"][2])}
    for (f, key), text in set_q.items():
        if f == fam:
            q[key.upper()] = text
            notes.append(f"{key.upper()} 按 --set-question 覆盖为：{text!r}。")
    old_q = {"Q1": orig["questions"]["q1"], "Q2": orig["questions"]["q2"], "Q3": orig["questions"]["q3"]}
    old_g = {"Q1": (og["aligned"]["q1"], og["conflicting"]["q1"]), "Q2": (og["aligned"]["q2"], og["conflicting"]["q2"]),
             "Q3": (og["q3"], og["q3"])}
    for k in ("Q1", "Q2", "Q3"):
        if _ws(q[k]) != _ws(old_q[k]):
            notes.append(f"{k} 问题已按你的修改：{q[k]!r}（原：{old_q[k]!r}）。")
        if tuple(map(_ws, gold[k])) != tuple(map(_ws, old_g[k])):
            notes.append(f"{k} 的 gold 已按你的修改：aligned={gold[k][0]!r}，conflicting={gold[k][1]!r}。")

    av = dict(orig["answer_variants"])
    if gold["Q2"] != old_g["Q2"]:
        av["q2_aligned"], av["q2_conflicting"] = [gold["Q2"][0]], [gold["Q2"][1]]
        notes.append("Q2 的 gold 变了，answer_variants.q2_* 重置为各自的 gold 本身（请按需补充同义写法）。")
    if gold["Q1"] != old_g["Q1"]:
        av["q1_aligned"], av["q1_conflicting"] = [gold["Q1"][0]], [gold["Q1"][1]]

    b = orig["bundle"]
    out = GenerateFamilyOutput.model_validate({
        "task_mode": "generate_family", "fact_id": orig["fact_id"], "bundle_id": b["bundle_id"],
        "status": "candidate_generated", "template_id": orig["template_id"], "agent_name": orig["agent_name"],
        "setting_domain": orig["setting_domain"], "setting": orig["setting"], "source_type": orig["source_type"],
        "belief_cue_ids": orig["belief_cue_ids"], "action_type": orig["action_type"],
        "reasoning_structure": orig["reasoning_structure"], "story_backbone": ps.backbone,
        "claim_span_aligned": ps.claim_aligned, "claim_span_conflicting": ps.claim_conflicting,
        "belief_proposition_aligned": props["aligned"], "belief_proposition_conflicting": props["conflicting"],
        "belief_question": q["Q1"], "action_question": q["Q2"], "reality_question": q["Q3"],
        "proposed_gold": {"aligned": {"q1": gold["Q1"][0], "q2": gold["Q2"][0]},
                          "conflicting": {"q1": gold["Q1"][1], "q2": gold["Q2"][1]}, "q3": gold["Q3"][0]},
        "answer_variants": av, "action_constraints": b["action_constraints"], "belief_to_action_rule": b["belief_to_action_rule"],
        "risk_flags": orig["risk_flags"], "risk_notes": orig["risk_notes"],
        "validation_status": "needs_human_review", "failure_reason": None,
    })
    prov = orig["provenance"]
    rec = build_candidate(
        family_id=fam, fact=fact, bundle=Bundle.model_validate(b), family_out=out,
        generator_model=prov["generator_model"], prompt_version=prov["prompt_version"], created_at=prov["created_at"],
        notes=f"human-edited in REVIEW_new.md; original notes: {prov.get('notes')}",
        assignment=Assignment(**prov["assignments"]) if prov.get("assignments") else None,
    )
    return rec, notes


# --------------------------------------------------------------------------- 导出
def export_all(records: list[CandidateRecord], facts: list[KnowledgeRecord], instruction: str):
    pretest = export_pretest(facts)
    story = export_story_questions(records, include_rejected=True)      # 人工改过的题：error 不自动剔除，只报告
    gold = export_gold(facts, records, include_rejected=True)
    failures: list[str] = []
    seen: set[str] = set()
    for row in pretest + story:
        if row["item_id"] in seen:
            failures.append(f"{row['item_id']}: item_id 重复")
        seen.add(row["item_id"])
        try:
            assert_no_leak([row], gold)
        except LeakError as e:
            failures.append(str(e))
    requests = [{"item_id": r["item_id"], "messages": build_messages(r, instruction)} for r in pretest + story]
    return pretest, story, gold, requests, failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("review", type=Path, help="研究者修改后的 REVIEW_new.md")
    ap.add_argument("--candidates", type=Path, required=True, help="原始（未人工修改）的 candidates.jsonl")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--set-question", action="append", default=[], metavar="FAM:q1=文本",
                    help="显式覆盖某个问题（记录在 EXPORT_NOTES.md），可重复")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    set_q: dict[tuple[str, str], str] = {}
    for s in args.set_question:
        head, text = s.split("=", 1)
        fam, key = head.split(":", 1)
        set_q[(fam.strip(), key.strip().lower())] = text.strip()

    cfg = load_config()
    facts = load_knowledge()
    by_id = {f.fact_id: f for f in facts}
    cards = parse_review(args.review.read_text(encoding="utf-8"))
    origs = {r["family_id"]: r for r in read_jsonl(args.candidates)}
    if set(cards) != set(origs):
        print(f"REVIEW 与 candidates 的家族不一致：只在 REVIEW：{sorted(set(cards) - set(origs))}；只在 candidates：{sorted(set(origs) - set(cards))}")
        return 1

    records: list[CandidateRecord] = []
    all_notes: dict[str, list[str]] = {}
    for fam in sorted(origs):
        rec, notes = rebuild(origs[fam], cards[fam], by_id[origs[fam]["fact_id"]], set_q)
        records.append(rec)
        all_notes[fam] = notes
    pretest, story, gold, requests, failures = export_all(records, facts, cfg.answer_instruction)
    if failures:
        print("导出被泄漏检查拦下，未写出任何文件：")
        for f in failures:
            print("  -", f)
        return 2

    out = args.out_dir
    ev = out / "eval_input"
    write_jsonl(out / "items_final.jsonl", [{**json.loads(r.model_dump_json()), "human_edited": True,
                                             "edit_source": args.review.name, "edit_notes": all_notes[r.family_id]}
                                            for r in records])
    write_jsonl(ev / "pretest_questions.jsonl", pretest)
    write_jsonl(ev / "story_questions.jsonl", story)
    write_jsonl(ev / "eval_requests.jsonl", requests)
    write_jsonl(out / "answer_keys" / "gold_answers.jsonl", gold)

    L = ["# 导出说明（由 src/import_reviewed.py 自动生成）\n",
         f"来源：`{args.review.name}`（研究者人工修改后的版本）；以其中的**合并故事**为准，四个条件由代码重新渲染。\n",
         "## 文件\n",
         "- `items_final.jsonl`：人工修改后的 12 题完整记录（四个条件的故事、问题、gold、检查结果）。",
         "- `eval_input/pretest_questions.jsonl`：Q0，12 条，无故事。**发给被测模型。**",
         "- `eval_input/story_questions.jsonl`：Q1/Q2/Q3 × 4 个条件 × 12 题 = 144 条，每条是一次独立请求。**发给被测模型。**",
         "- `eval_input/eval_requests.jsonl`：上面两个文件逐条拼好的最终消息（单条 user 消息 + 统一回答指令），可直接调用。",
         "- `answer_keys/gold_answers.jsonl`：参考答案（provisional）。**绝不发给被测模型。**\n",
         f"共 {len(pretest)} 条 Q0 + {len(story)} 条故事题 = {len(requests)} 条请求；已通过 gold 泄漏检查。\n",
         "## 对你的修改所做的整理与需要你确认的地方\n"]
    for fam in sorted(all_notes):
        r = next(x for x in records if x.family_id == fam)
        n_err = [i for i in r.issues if i.severity == "error"]
        n_warn = [i for i in r.issues if i.severity == "warning"]
        L.append(f"### {fam}（{r.fact_id}）｜修改后自动检查：{len(n_err)} error / {len(n_warn)} warning")
        for n in all_notes[fam]:
            L.append(f"- {n}")
        for i in n_err + n_warn:
            L.append(f"- {'❌' if i.severity == 'error' else '⚠️'} `{i.code}`：{i.message}")
        if not all_notes[fam] and not r.issues:
            L.append("- 无")
        L.append("")
    (out / "EXPORT_NOTES.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"完成：{len(records)} 题 -> {out}；{len(requests)} 条请求；EXPORT_NOTES.md 已写出")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
