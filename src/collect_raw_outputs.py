"""把一批候选题对应的**原始**造题记录（模型当时的请求与原始输出文本）汇总成一个 raw_generator_outputs.jsonl。

这是"原始记录"：保持模型输出的原样，不含任何人工修改；人工修改后的版本见 items_final.jsonl。
对每个家族，按 family_id + created_at 在各来源目录里找到当时保存的日志：
    <fact>_<时间戳>_1_propose_domain<k>.json   （propose_bundles 的请求/输出）
    <fact>_<时间戳>_2_family_attempt<n>.json   （generate_family 每次尝试的请求/输出）
每行一个家族，包含两个阶段的 request_user_input、模型原始 output_text、token 用量；
完整的 API 原始响应（raw_response）很大，仍保留在各自的来源日志文件里，这里只给出文件路径。

用法：
    python src/collect_raw_outputs.py datasets/generation/pilot_12/candidates.jsonl \
        --search-root datasets/generation --out datasets/generation/pilot_12/raw_generator_outputs.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import REPO_ROOT, read_jsonl, write_jsonl


def _stage(path: Path) -> dict:
    log = json.loads(path.read_text(encoding="utf-8"))
    meta = log.get("request_meta") or {}
    return {
        "source_file": path.relative_to(REPO_ROOT).as_posix(),
        "ok": log.get("ok"), "error_type": log.get("error_type"), "attempts": log.get("attempts"),
        "elapsed_s": log.get("elapsed_s"), "usage": log.get("usage"),
        "model": meta.get("model"), "schema_name": meta.get("schema_name"),
        "max_output_tokens": meta.get("max_output_tokens"),
        "request_user_input": meta.get("user_input"),
        "output_text": log.get("output_text"),
        "feedback_given": log.get("feedback_given"),
    }


def find_prefix(rec: dict, search_root: Path) -> Path | None:
    """找到与候选记录对应的 *_3_candidate.json（family_id 与 created_at 都一致），返回去掉后缀的路径前缀。"""
    for cand in sorted(search_root.rglob(f"{rec['fact_id']}_*_3_candidate.json")):
        raw = json.loads(cand.read_text(encoding="utf-8"))
        if raw["family_id"] == rec["family_id"] and raw["provenance"]["created_at"] == rec["provenance"]["created_at"]:
            return Path(str(cand).removesuffix("_3_candidate.json"))
    return None


def collect(candidates: list[dict], search_root: Path) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    missing: list[str] = []
    for rec in candidates:
        prefix = find_prefix(rec, search_root)
        if prefix is None:
            missing.append(f"{rec['family_id']} ({rec['fact_id']})")
            continue
        proposes = sorted(prefix.parent.glob(prefix.name + "_1_propose_domain*.json"))
        families = sorted(prefix.parent.glob(prefix.name + "_2_family_attempt*.json"))
        rows.append({
            "family_id": rec["family_id"], "fact_id": rec["fact_id"],
            "generator_model": rec["provenance"]["generator_model"],
            "prompt_version": rec["provenance"]["prompt_version"],
            "guideline_version": rec["provenance"]["guideline_version"],
            "assignments": rec["provenance"]["assignments"],
            "created_at": rec["provenance"]["created_at"],
            "propose_bundles": [_stage(p) for p in proposes],
            "generate_family_attempts": [_stage(p) for p in families],
            "note": "原始记录，未包含任何人工修改；完整 API 响应见各 source_file。",
        })
    return rows, missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidates", type=Path, help="原始 candidates.jsonl")
    ap.add_argument("--search-root", type=Path, default=REPO_ROOT / "datasets" / "generation")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows, missing = collect(read_jsonl(args.candidates), args.search_root)
    write_jsonl(args.out, rows)
    print(f"写出 {len(rows)} 行 -> {args.out}")
    if missing:
        print("找不到原始日志的家族：", missing)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
