"""F002 v1 与 v2 的对比，以及"用 v2 替换 v1 后"完整 12 题指标的前后变化。

输入（都是评分脚本的输出）：
  v1 完整结果：results/pilot_eval/archive_v1_original/{item_level_scores,accuracy_summary,key_metrics}.csv
  v2 单独结果：results/pilot_eval/f002_v2/item_level_scores.csv
  替换后的完整结果：results/pilot_eval/{accuracy_summary,key_metrics}.csv
输出：
  results/pilot_eval/f002_v2/F002_v1_vs_v2_comparison.csv / .md
  results/pilot_eval/METRIC_CHANGES_F002_v2.md
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from common import REPO_ROOT

RES = REPO_ROOT / "results" / "pilot_eval"
V1 = RES / "archive_v1_original"
CONFIGS = ["qwen3-32b__non_thinking", "qwen3-32b__thinking", "glm-4.5-air__non_thinking", "glm-4.5-air__thinking"]
CONDS = [("aligned", "implicit"), ("aligned", "explicit"), ("conflicting", "implicit"), ("conflicting", "explicit")]


def read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def short(s: str, n: int = 60) -> str:
    s = (s or "").replace("\n", " ").replace("|", "\\|").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def mark(r: dict) -> str:
    return {"correct": "✓", "incorrect": "✗", "pending": "?", "request_failed": "!"}[r["score"]]


# --------------------------------------------------------------------------- F002 v1 vs v2
def comparison() -> tuple[list[list], str]:
    v1 = {(r["config_id"], r["item_id"]): r for r in read(V1 / "item_level_scores.csv") if r["family_id"] == "F002" or r["item_id"] == "K14_Q0"}
    v2 = {(r["config_id"], r["item_id"]): r for r in read(RES / "f002_v2" / "item_level_scores.csv")}
    items = ["K14_Q0"] + [f"F002_{e}_{r}_{q}" for q in ("Q1", "Q2", "Q3") for r, e in CONDS]
    csv_rows: list[list] = []
    for c in CONFIGS:
        for it in items:
            a, b = v1[(c, it)], v2[(c, it)]
            csv_rows.append([c, it, a["qtype"], a["relation"], a["explicitness"], a["question"], a["model_answer"], a["reference"],
                             a["score"], a["error_category"], b["question"], b["model_answer"], b["reference"], b["score"],
                             b["method"] + (f"/{b['judge_verdict']}" if b["judge_verdict"] else ""), b["error_category"]])
    L = ["# F002（K14 海豚）v1 与 v2 对比\n",
         "✓ 正确　✗ 错误　? 待人工复核。v1 = 人工修订后的旧故事（“visiting marine biologist”，Q2 问怎么动画）；"
         "v2 = 新故事（“experienced animator 的 rehearsals”，Q2 问“海豚在下一次呼吸时放在哪里”）。\n",
         "## 1. 正确数对比（每个配置，v1 → v2）\n",
         "| 配置 | Q0 | Q1（4 个条件） | Q2（4 个条件） | Q3（4 个条件） |", "|---|---|---|---|---|"]
    for c in CONFIGS:
        cells = []
        for q in ("Q0", "Q1", "Q2", "Q3"):
            ids = ["K14_Q0"] if q == "Q0" else [f"F002_{e}_{r}_{q}" for r, e in CONDS]
            n1 = sum(v1[(c, i)]["score"] == "correct" for i in ids)
            n2 = sum(v2[(c, i)]["score"] == "correct" for i in ids)
            cells.append(f"{n1}/{len(ids)} → **{n2}/{len(ids)}**")
        L.append(f"| {c} | " + " | ".join(cells) + " |")
    L += ["", "合计（4 个配置）：" + "；".join(
        f"{q} {sum(v1[(c, i)]['score'] == 'correct' for c in CONFIGS for i in ([ 'K14_Q0'] if q == 'Q0' else [f'F002_{e}_{r}_{q}' for r, e in CONDS]))}"
        f"/{len(CONFIGS) * (1 if q == 'Q0' else 4)} → "
        f"{sum(v2[(c, i)]['score'] == 'correct' for c in CONFIGS for i in (['K14_Q0'] if q == 'Q0' else [f'F002_{e}_{r}_{q}' for r, e in CONDS]))}"
        f"/{len(CONFIGS) * (1 if q == 'Q0' else 4)}" for q in ("Q0", "Q1", "Q2", "Q3")) + "\n"]
    L += ["## 2. 逐条模型回答（Q0 与四个条件的 Q1/Q2/Q3）\n"]
    for c in CONFIGS:
        L.append(f"### {c}\n")
        L.append("| item | v1 回答 | v1 | v2 回答 | v2 | v2 评分方式 | v2 错误类别 |")
        L.append("|---|---|---|---|---|---|---|")
        for it in items:
            a, b = v1[(c, it)], v2[(c, it)]
            meth = b["method"] + (f"/{b['judge_verdict']}" if b["judge_verdict"] else "")
            L.append(f"| {it.replace('F002_', '')} | {short(a['model_answer'])} | {mark(a)} | {short(b['model_answer'])} | {mark(b)} | {meth} | {b['error_category']} |")
        L.append("")
    L += ["## 3. 两个版本的问题与 gold\n", "| | v1 | v2 |", "|---|---|---|"]
    for q in ("Q0", "Q1", "Q2", "Q3"):
        i = "K14_Q0" if q == "Q0" else f"F002_implicit_aligned_{q}"
        j = "F002_implicit_conflicting_" + q
        a, b = v1[(CONFIGS[0], i)], v2[(CONFIGS[0], i)]
        if q == "Q0":
            L.append(f"| {q} | {short(a['question'], 90)} → `{a['reference']}` | {short(b['question'], 90)} → `{b['reference']}` |")
        else:
            a2, b2 = v1[(CONFIGS[0], j)], v2[(CONFIGS[0], j)]
            L.append(f"| {q} | {short(a['question'], 90)} → aligned `{a['reference']}` / conflicting `{a2['reference']}` | "
                     f"{short(b['question'], 90)} → aligned `{b['reference']}` / conflicting `{b2['reference']}` |")
    return csv_rows, "\n".join(L) + "\n"


# --------------------------------------------------------------------------- 完整结果的前后变化
def metric_changes() -> str:
    a1, a2 = read(V1 / "accuracy_summary.csv"), read(RES / "accuracy_summary.csv")
    k1, k2 = read(V1 / "key_metrics.csv"), read(RES / "key_metrics.csv")

    def acc(rows, c, q, group):
        r = next(x for x in rows if x["config_id"] == c and x["question"] == q and x["group"] == group)
        return f"{r['correct']}/{r['total']}, {float(r['accuracy_pct']):.0f}%", float(r["accuracy_pct"]), int(r["pending_manual_review"])

    def km(rows, metric, scope, spec):
        r = next(x for x in rows if x["metric"].startswith(metric) and x["scope"] == scope and x["condition_spec"] == spec)
        return r

    L = ["# 用 F002 v2 替换 v1（及 K14 Q0）后，完整 12 题指标的前后变化\n",
         "v1 = 此前的 12 题结果（`archive_v1_original/`）；v2 = 把 F002 与 K14 的 Q0 换成新设计后重新计算的结果（当前 `results/pilot_eval/` 顶层文件）。"
         "其余 11 个 family 的原始回答与评分完全不变。差值单位为百分点（pp）。\n",
         "## 1. 准确率（正确数/总数，%）\n",
         "| 配置 | 指标 | v1 | v2 | 变化 pp |", "|---|---|---|---|---|"]
    for c in CONFIGS:
        for label, q, g in (("Q0", "Q0", "Q0 (no story)"), ("Q1 全部条件", "Q1", "all four conditions"), ("Q2 全部条件", "Q2", "all four conditions"),
                            ("Q3 全部条件", "Q3", "all four conditions"), ("Q2 conflicting", "Q2", "conflicting (implicit+explicit)"),
                            ("Q2 aligned", "Q2", "aligned (implicit+explicit)")):
            s1, p1, _ = acc(a1, c, q, g)
            s2, p2, _ = acc(a2, c, q, g)
            L.append(f"| {c} | {label} | {s1} | {s2} | {p2 - p1:+.1f} |")
    L += ["", "待人工复核数（pending，不计为正确）：" + "；".join(
        f"{c} {sum(int(r['pending_manual_review']) for r in a1 if r['config_id'] == c and r['group'] in ('Q0 (no story)', 'all four conditions'))}"
        f" → {sum(int(r['pending_manual_review']) for r in a2 if r['config_id'] == c and r['group'] in ('Q0 (no story)', 'all four conditions'))}" for c in CONFIGS) + "\n"]

    def diff_table(title, metric, spec_list, scopes, note):
        out = [f"## {title}\n", note + "\n", "| 范围 | 条件 | v1（a − b） | v2（a − b） | 变化 pp |", "|---|---|---|---|---|"]
        for sc in scopes:
            for spec in spec_list:
                try:
                    r1, r2 = km(k1, metric, sc, spec), km(k2, metric, sc, spec)
                except StopIteration:
                    continue
                f = lambda r: f"{r['a_correct']}/{r['a_total']} ({r['a_pct']}) − {r['b_correct']}/{r['b_total']} ({r['b_pct']}) = **{r['diff_pp (a-b)']}**"
                d = float(r2["diff_pp (a-b)"]) - float(r1["diff_pp (a-b)"])
                out.append(f"| {sc} | {spec} | {f(r1)} | {f(r2)} | {d:+.1f} |")
        return out + [""]

    L += diff_table("2. Application Gap（Q1 − Q2）", "Application Gap", ["aligned/implicit", "aligned/explicit", "conflicting/implicit",
                    "conflicting/explicit", "four conditions pooled"], CONFIGS, "分母：每个条件 12 vs 12（12 个家族）；合并为 48 vs 48。")
    L += diff_table("3. Conflict Gap（Aligned − Conflicting）", "Conflict Gap", ["Q1, implicit+explicit pooled", "Q2, implicit",
                    "Q2, explicit", "Q2, implicit+explicit pooled", "Q3, implicit+explicit pooled"], CONFIGS, "分母：单个解释方式 12 vs 12；合并 24 vs 24。")
    L += diff_table("4. Thinking Benefit（Thinking − Non-thinking，同一模型家族）", "Thinking Benefit", ["Q0", "Q1, four conditions pooled",
                    "Q2, four conditions pooled", "Q3, four conditions pooled", "Q2, conflicting/implicit", "Q2, conflicting/explicit"],
                    ["qwen3-32b", "glm-4.5-air"], "分母：Q0 为 12 vs 12；Q1/Q2/Q3 合并为 48 vs 48；单个条件 12 vs 12。")
    L += diff_table("5. Explicitness Benefit（Explicit − Implicit）", "Explicitness Benefit", ["Q1, conflicting", "Q2, conflicting",
                    "Q2, aligned+conflicting pooled"], CONFIGS, "分母：单个关系 12 vs 12；合并 24 vs 24。")
    out = ["## 6. Paired Q2 Consistency 与 Q0-conditioned Conflicting Q2\n", "| 配置 | 指标 | v1 | v2 |", "|---|---|---|---|"]
    for c in CONFIGS:
        r1, r2 = km(k1, "Paired Q2 Consistency", c, "implicit+explicit pooled"), km(k2, "Paired Q2 Consistency", c, "implicit+explicit pooled")
        out.append(f"| {c} | Paired Q2（aligned 与 conflicting 的 Q2 都对，24 对） | {r1['a_correct']}/{r1['a_total']} ({r1['a_pct']}%) | {r2['a_correct']}/{r2['a_total']} ({r2['a_pct']}%) |")
        r1, r2 = km(k1, "Q0-conditioned", c, "implicit+explicit pooled"), km(k2, "Q0-conditioned", c, "implicit+explicit pooled")
        out.append(f"| {c} | Q0 答对的事实上的 conflicting Q2 | {r1['a_correct']}/{r1['a_total']} ({r1['a_pct']}%)；Q0 答错组 {r1['b_correct']}/{r1['b_total']} | "
                   f"{r2['a_correct']}/{r2['a_total']} ({r2['a_pct']}%)；Q0 答错组 {r2['b_correct']}/{r2['b_total']} |")
    return "\n".join(L + out) + "\n"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows, md = comparison()
    out = RES / "f002_v2"
    with open(out / "F002_v1_vs_v2_comparison.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["config_id", "item_id", "qtype", "relation", "explicitness", "v1_question", "v1_model_answer", "v1_reference",
                    "v1_score", "v1_error_category", "v2_question", "v2_model_answer", "v2_reference", "v2_score",
                    "v2_scoring_method", "v2_error_category"])
        w.writerows(rows)
    (out / "F002_v1_vs_v2_comparison.md").write_text(md, encoding="utf-8", newline="\n")
    (RES / "METRIC_CHANGES_F002_v2.md").write_text(metric_changes(), encoding="utf-8", newline="\n")
    print("已写出 F002_v1_vs_v2_comparison.csv/.md 与 METRIC_CHANGES_F002_v2.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
