"""Stage A：读取并校验 knowledge_pool.jsonl 与 guideline。

用法：
    python src/validate_knowledge.py            # 开发 / dry-run：允许 candidate_pending_researcher_signoff
    python src/validate_knowledge.py --strict   # 研究用：要求每条事实都已被研究者确认（见 SIGNED_OFF_STATUSES）
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from common import GUIDELINE_PATH, KNOWLEDGE_PATH, JsonlError, file_sha256, read_jsonl
from schemas import EXPECTED_CATEGORY_COUNTS, FACT_STATUS_PENDING, KnowledgeRecord

EXPECTED_N_FACTS = 30
# 研究者确认后的状态名是一个约定，这里只是占位；真正确认事实时请直接改此常量与 jsonl。
SIGNED_OFF_STATUSES = {"researcher_signed_off"}


class KnowledgeValidationError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


def load_knowledge(
    path: Path = KNOWLEDGE_PATH,
    *,
    strict: bool = False,
    expected_n: int | None = EXPECTED_N_FACTS,
    expected_category_counts: dict[str, int] | None = EXPECTED_CATEGORY_COUNTS,
) -> list[KnowledgeRecord]:
    """读取并校验；有任何问题就抛 KnowledgeValidationError（一次列出所有问题）。不修改任何内容。"""
    problems: list[str] = []
    try:
        rows = read_jsonl(path)
    except JsonlError as e:
        raise KnowledgeValidationError([str(e)]) from e

    records: list[KnowledgeRecord] = []
    for i, row in enumerate(rows, start=1):
        try:
            records.append(KnowledgeRecord.model_validate(row))
        except ValidationError as e:
            fid = row.get("fact_id", f"第{i}条记录")
            for d in e.errors():
                loc = ".".join(str(x) for x in d["loc"]) or "(整条记录)"
                problems.append(f"{fid}: 字段 {loc}: {d['msg']}")

    ids = Counter(r.fact_id for r in records)
    problems += [f"fact_id 重复: {fid} 出现 {n} 次" for fid, n in ids.items() if n > 1]

    if expected_n is not None and len(rows) != expected_n:
        problems.append(f"事实条数应为 {expected_n}，实际为 {len(rows)}")
    if expected_category_counts is not None and not problems:
        got = Counter(r.knowledge_category for r in records)
        if dict(got) != expected_category_counts:
            problems.append(f"类别分布应为 {expected_category_counts}，实际为 {dict(got)}")

    if strict:
        bad = [r.fact_id for r in records if r.fact_status not in SIGNED_OFF_STATUSES]
        if bad:
            problems.append(f"--strict：以下事实尚未被研究者确认(fact_status): {bad}")

    if problems:
        raise KnowledgeValidationError(problems)
    return records


def check_guideline(path: Path = GUIDELINE_PATH) -> str:
    """确认 guideline 存在，返回其 SHA-256（作为 prompt_version 写入 provenance）。"""
    if not Path(path).is_file():
        raise KnowledgeValidationError([f"找不到 guideline: {path}"])
    return file_sha256(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="要求所有事实已由研究者确认")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        records = load_knowledge(strict=args.strict)
        sha = check_guideline()
    except KnowledgeValidationError as e:
        print("校验失败：")
        for p in e.problems:
            print("  -", p)
        return 1
    cats = Counter(r.knowledge_category for r in records)
    statuses = Counter(r.fact_status for r in records)
    print(f"OK：读取 {len(records)} 条事实，ID 唯一，字段完整。")
    print("类别分布：", dict(cats))
    print("fact_status：", dict(statuses))
    print("guideline SHA-256：", sha)
    if FACT_STATUS_PENDING in statuses:
        print("提示：部分事实仍是 candidate_pending_researcher_signoff，仅可用于开发 / dry-run。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
