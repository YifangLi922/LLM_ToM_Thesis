"""离线 dry-run：不需要 API key，不产生任何收费调用。

读取真实的知识库 + tests/fixtures 里的模拟 bundle/backbone，走完
"校验 -> 渲染四版本 -> 硬检查 -> 组装主记录 -> 导出三份文件 -> 泄漏检查"全流程，
并把四个版本打印出来供肉眼检查。

用法：
    python src/dry_run_demo.py                     # 输出到 datasets/dryrun/（已被 .gitignore 忽略）
    python src/dry_run_demo.py --out some/dir
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from candidates import build_candidate, make_family_id
from common import REPO_ROOT, write_jsonl
from export_evaluation import build_messages, write_exports
from schemas import CONDITIONS, GenerateFamilyOutput, ProposeBundlesOutput
from validate_candidates import check_propose_output
from validate_knowledge import check_guideline, load_knowledge

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "mock_k01_family.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "datasets" / "dryrun")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    facts = load_knowledge()
    prompt_version = check_guideline()
    print(f"[A] 知识库 OK：{len(facts)} 条；guideline SHA-256 = {prompt_version[:16]}…")

    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
    propose = ProposeBundlesOutput.model_validate(fx["propose_output"])
    fact = next(f for f in facts if f.fact_id == propose.fact_id)
    issues = check_propose_output(propose, fact, max_bundles=3)
    print(f"[B] bundle 检查：{len(propose.bundles)} 个 bundle，issues = {[i.code for i in issues] or '无'}")

    family_out = GenerateFamilyOutput.model_validate(fx["family_output"])
    record = build_candidate(
        family_id=make_family_id(1), fact=fact, bundle=propose.bundles[0], family_out=family_out,
        generator_model="MOCK_FIXTURE", prompt_version=prompt_version, notes="dry-run 模拟样例，非真题",
    )
    print(f"[C/D] family {record.family_id} -> validation_status = {record.validation_status}, "
          f"human_validated = {record.human_validated}")
    for i in record.issues:
        print(f"      [{i.severity}] {i.code}: {i.message}")

    print("\n--- 四个条件的故事 ---")
    for cond in CONDITIONS:
        print(f"\n## {cond}\n{getattr(record.variants, cond)}")

    out = args.out
    write_jsonl(out / "candidates.jsonl", [json.loads(record.model_dump_json())])
    counts = write_exports(out, facts, [record])
    print("\n[E] 导出完成（已通过泄漏检查）：", out)
    for name, n in counts.items():
        print(f"      {name}: {n} 行")

    sample = json.loads((out / "story_questions.jsonl").read_text(encoding="utf-8").splitlines()[4])  # implicit_conflicting 的 Q2
    print("\n--- 示例：一个 Q2 请求实际发给被测模型的内容（单条 user 消息，无历史）---")
    print(f"item_id = {sample['item_id']}")
    print(build_messages(sample)[0]["content"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
