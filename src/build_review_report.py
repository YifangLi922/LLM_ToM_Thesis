"""把一批候选题汇总成**一个**方便阅读的 Markdown 文件（GitHub 网页端直接渲染）。

每道题一张"卡片"：
  - 一份"合并故事"：把 aligned / conflicting 唯一不同的 claim 位置写成 **[aligned ｜ conflicting]**，
    explicit 条件多出的那句话写成 ⟨…⟩，所以一份故事就能看清四个条件；
  - Q1/Q2/Q3 的问题与两个条件下的 gold（provisional）；
  - 模型自报的风险、自动检查结果、Q3 泄漏扫描；
  - 一行人工审查勾选框；
  - 折叠的 <details>：四个条件的完整故事 + bundle 设计，需要时再展开。
顶部有总表（可点击跳转）。

用法：
    python src/build_review_report.py datasets/generation/pilot_12/candidates.jsonl
    python src/build_review_report.py datasets/generation/some_batch/            # 目录：自动收集 *_3_candidate.json
    python src/build_review_report.py A_dir B_dir --out report.md --title "第二批"
    python src/build_review_report.py A_dir B_dir --write-jsonl merged_candidates.jsonl

同一个事实在多个来源里出现时，取文件名里时间戳最新的那个。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schemas import CandidateRecord
from render_pairs import BELIEF_TOKEN, CLAIM_TOKEN

BAR = "｜"


# --------------------------------------------------------------------------- 读取
def load_records(paths: list[Path]) -> list[CandidateRecord]:
    """路径可以是 candidates.jsonl，也可以是含有 *_3_candidate.json 的目录。"""
    found: dict[str, tuple[str, dict]] = {}          # fact_id -> (排序键, 记录)
    for p in paths:
        if p.is_dir():
            files = sorted(p.glob("*_3_candidate.json"))
            raws = [(f.name, json.loads(f.read_text(encoding="utf-8"))) for f in files]
        elif p.suffix == ".jsonl":
            raws = [(f"{i:06d}", json.loads(line)) for i, line in
                    enumerate(p.read_text(encoding="utf-8").splitlines()) if line.strip()]
        else:
            raws = [(p.name, json.loads(p.read_text(encoding="utf-8")))]
        for key, raw in raws:
            # 目录里的文件名形如 K18_20261114-183604_3_candidate.json：时间戳在第二段
            stamp = key.split("_")[1] if key.count("_") >= 2 and key[0] == "K" else key
            fid = raw["fact_id"]
            if fid not in found or stamp >= found[fid][0]:
                found[fid] = (stamp, raw)
    recs = [CandidateRecord.model_validate(raw) for _, raw in found.values()]
    return sorted(recs, key=lambda r: r.family_id)


# --------------------------------------------------------------------------- 文本片段
def merged_story(r: CandidateRecord) -> str:
    """一份故事同时展示四个条件：claim 位置写成 [aligned｜conflicting]，explicit 多出的句子写成 ⟨…⟩。"""
    claim = f"**[{r.claim_span_aligned} {BAR} {r.claim_span_conflicting}]**"
    belief = f" ⟨{r.agent_name} believes that [{r.belief_proposition_aligned} {BAR} {r.belief_proposition_conflicting}].⟩"
    return r.story_backbone.replace(CLAIM_TOKEN, claim).replace(BELIEF_TOKEN, belief)


def _esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def story_words(r: CandidateRecord) -> int | None:
    if r.variants is None:
        return None
    return max(len(r.variants.implicit_aligned.split()), len(r.variants.implicit_conflicting.split()))


def n_issues(r: CandidateRecord) -> tuple[int, int]:
    return (sum(i.severity == "error" for i in r.issues), sum(i.severity == "warning" for i in r.issues))


def _quote(text: str) -> str:
    return "\n".join("> " + line if line.strip() else ">" for line in text.splitlines())


# --------------------------------------------------------------------------- 卡片
def render_card(r: CandidateRecord) -> str:
    e, w = n_issues(r)
    g, q = r.proposed_gold, r.questions
    L: list[str] = []
    a = L.append
    a(f'<a id="{r.family_id}"></a>')
    a(f"## {r.family_id} · {r.fact_id} · {r.template_id} · {r.action_type} · {r.setting_domain}\n")
    a(f"- **世界事实**：{r.fact.world_fact}")
    a(f"- **限定说明**：{r.fact.qualification_notes}")
    a(f"- **人物**：{r.agent_name} ｜ **场景**：{r.setting} ｜ **来源类型**：{r.source_type} ｜ **belief cues**：{r.belief_cue_ids or '无'}")
    a(f"- **设计标签**：`{r.design_tag}` ｜ **自动检查**：{e} error / {w} warning ｜ **状态**：`{r.validation_status}`\n")
    a("**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）\n")
    a(_quote(merged_story(r)) + "\n")
    wc = story_words(r)
    if wc is not None:
        a(f"<sub>implicit 故事 {wc} 词</sub>\n")
    a("**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）\n")
    a("| | 问题 | aligned | conflicting |")
    a("|---|---|---|---|")
    a(f"| Q1 信念 | {_esc(q.q1)} | {_esc(g.aligned.q1)} | {_esc(g.conflicting.q1)} |")
    a(f"| Q2 行动 | {_esc(q.q2)} | {_esc(g.aligned.q2)} | {_esc(g.conflicting.q2)} |")
    a(f"| Q3 现实 | {_esc(q.q3)} | {_esc(g.q3)} | {_esc(g.q3)} |\n")
    a(f"**模型自报风险**：{', '.join(f'`{f}`' for f in r.risk_flags) or '无'}")
    if r.risk_notes:
        a(f"\n> {r.risk_notes}")
    a("")
    a("**自动检查**")
    if r.issues:
        for i in r.issues:
            a(f"- {'❌' if i.severity == 'error' else '⚠️'} `{i.code}`：{i.message}")
    else:
        a("- 无 error / warning")
    if r.q3_leakage_scan:
        hits = "；".join(f"`{h.term}` → {h.category}（{h.where}）" for h in r.q3_leakage_scan)
        a(f"- Q3 泄漏扫描命中（仅供复核，不等于泄漏）：{hits}")
    a("")
    a("**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：\n")
    a("<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>\n")
    if r.variants is None:
        a("（渲染失败，没有可用的四条件故事）\n")
    else:
        for cond in ("implicit_aligned", "implicit_conflicting", "explicit_aligned", "explicit_conflicting"):
            a(f"**{cond}**\n")
            a(_quote(getattr(r.variants, cond)) + "\n")
    b = r.bundle
    a("**Bundle 设计**\n")
    a(f"- 目标：{b.agent_goal}\n- 新任务：{b.new_task}\n- 约束：{b.action_constraints}\n- 目标输出：{b.target_output}")
    a(f"- belief→action 规则：{b.belief_to_action_rule}")
    a(f"- reasoning_structure：`{r.reasoning_structure}`")
    a(f"- 抽样分配：{r.provenance.assignments}")
    a("\n</details>\n")
    a("---\n")
    return "\n".join(L)


# --------------------------------------------------------------------------- 总报告
def render_report(records: list[CandidateRecord], title: str = "候选题审查汇总") -> str:
    L: list[str] = []
    a = L.append
    a(f"# {title}\n")
    if records:
        p = records[0].provenance
        a(f"共 **{len(records)}** 题｜造题模型 `{p.generator_model}`｜guideline v{p.guideline_version}｜schema `{p.schema_version}`\n")
    a("> 全部是**候选刺激材料**：`needs_human_review`，gold 为 provisional，需要人工确认后才能使用。\n")
    a("**怎么读**：先看下面的总表，点家族编号跳到对应的题。每题的“故事”一份就包含四个条件——"
      "**[A ｜ B]** 是 aligned ｜ conflicting 唯一不同之处，⟨ ⟩ 是 explicit 条件多出的那句话。"
      "想看四个条件的完整原文，点卡片底部的“展开”。\n")
    a("## 总表\n")
    a("| 家族 | 事实 | 模板 | 场景域 | 行动类型 | 设计标签 | 词数 | error / warning | Q2 gold（aligned ｜ conflicting） |")
    a("|---|---|---|---|---|---|---|---|---|")
    for r in records:
        e, w = n_issues(r)
        a(f"| [{r.family_id}](#{r.family_id}) | {r.fact_id} | {r.template_id} | {r.setting_domain} | {r.action_type} | "
          f"`{r.design_tag}` | {story_words(r) or '-'} | {e} / {w} | "
          f"{_esc(r.proposed_gold.aligned.q2)} {BAR} {_esc(r.proposed_gold.conflicting.q2)} |")
    a("")
    for r in records:
        a(render_card(r))
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", type=Path, help="candidates.jsonl 或含 *_3_candidate.json 的目录（可多个）")
    ap.add_argument("--out", type=Path, default=None, help="输出的 .md；默认写在第一个输入路径旁边的 REVIEW.md")
    ap.add_argument("--title", default="候选题审查汇总")
    ap.add_argument("--write-jsonl", type=Path, default=None, help="同时把收集到的记录合并写成一个 candidates.jsonl")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    recs = load_records(args.paths)
    if not recs:
        print("没有找到任何候选题")
        return 1
    first = args.paths[0]
    out = args.out or ((first if first.is_dir() else first.parent) / "REVIEW.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(recs, args.title), encoding="utf-8", newline="\n")
    if args.write_jsonl:
        args.write_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with open(args.write_jsonl, "w", encoding="utf-8", newline="\n") as f:
            for r in recs:
                f.write(r.model_dump_json() + "\n")
    print(f"已汇总 {len(recs)} 题 -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
