"""对已保存的造题输出重新运行确定性检查（不调用 API、不改动模型输出的任何文字）。

用途：检查代码修复/更新之后，复核之前保存的候选题，而不必重新付费生成。
用法：
    python src/recheck_candidate.py <*_2_family.json> <*_3_candidate.json>
会在同目录写出 *_5_rechecked_candidate.json 和 *_6_rechecked_review.md（不覆盖旧文件）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from candidates import build_candidate
from generation_prompts import prompt_version
from schemas import Bundle, GenerateFamilyOutput
from smoke_generate import render_review_md
from validate_knowledge import load_knowledge


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("family_log", type=Path)
    ap.add_argument("candidate_json", type=Path, help="同一次运行保存的 *_3_candidate.json（用来取 bundle / family_id / 生成模型）")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    log = json.loads(args.family_log.read_text(encoding="utf-8"))
    old = json.loads(args.candidate_json.read_text(encoding="utf-8"))
    out = GenerateFamilyOutput.model_validate_json(log["output_text"])      # 原样读取模型输出
    bundle = Bundle.model_validate(old["bundle"])
    fact = next(f for f in load_knowledge() if f.fact_id == old["fact_id"])
    rec = build_candidate(
        family_id=old["family_id"], fact=fact, bundle=bundle, family_out=out,
        generator_model=old["provenance"]["generator_model"], prompt_version=prompt_version(),
        created_at=old["provenance"]["created_at"],
        notes=f"rechecked from saved model output; original notes: {old['provenance'].get('notes')}",
    )
    stem = args.candidate_json.name.split("_3_candidate")[0]
    reason = (old["provenance"].get("notes") or "").split("bundle selection:")[-1].strip()
    (args.candidate_json.parent / f"{stem}_5_rechecked_candidate.json").write_text(
        json.dumps(json.loads(rec.model_dump_json()), ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    md = args.candidate_json.parent / f"{stem}_6_rechecked_review.md"
    md.write_text(render_review_md(rec, reason), encoding="utf-8", newline="\n")
    n_err = sum(i.severity == "error" for i in rec.issues)
    n_warn = sum(i.severity == "warning" for i in rec.issues)
    print(f"重新检查完成：validation_status = {rec.validation_status}（{n_err} error，{n_warn} warning）")
    print("报告：", md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
