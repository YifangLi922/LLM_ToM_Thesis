from __future__ import annotations

import json
from collections import Counter

import pytest

from common import KNOWLEDGE_PATH, canonical_json, read_jsonl, sha256_text
from validate_knowledge import KnowledgeValidationError, check_guideline, load_knowledge

# K23 / K28 的"约定内容"指纹（不含 fact_status，所以研究者确认状态时不会误报）。
# 如果你是有意修改这两条事实，请同时更新这里的哈希。
FROZEN = {
    "K23": "c77accd0faba35eec6f329ba26a1a1fe0f83317a88a334bec3fb447927833ff3",
    "K28": "1cf2927fb4ed3e21e44a2d17455f4ab30c0e65b0878c8fe1cec15074c4bbabca",
}


PILOT_IDS = {"K13", "K14", "K15", "K06", "K18", "K20", "K23", "K25", "K09", "K27", "K28", "K30"}


def test_loads_pilot_12_facts_with_expected_distribution(facts):
    assert len(facts) == 12
    assert {f.fact_id for f in facts} == PILOT_IDS
    assert Counter(f.knowledge_category for f in facts) == {
        "basic_biology_category": 3, "basic_physics_causal": 3,
        "object_functions_properties": 2, "social_institutional_conventions": 4,
    }


def test_knowledge_path_is_the_v1_pilot_file():
    assert KNOWLEDGE_PATH.name == "knowledge_pool_pilot_12_v1.jsonl"


def test_fact_status_preserved_and_strict_mode_refuses_pending(facts):
    assert {f.fact_status for f in facts} == {"candidate_pending_researcher_signoff"}
    with pytest.raises(KnowledgeValidationError) as e:
        load_knowledge(strict=True)
    assert "尚未被研究者确认" in str(e.value)


@pytest.mark.parametrize("fid", sorted(FROZEN))
def test_frozen_facts_unchanged(fid):
    row = next(r for r in read_jsonl(KNOWLEDGE_PATH) if r["fact_id"] == fid)
    body = {k: v for k, v in row.items() if k != "fact_status"}
    assert sha256_text(canonical_json(body)) == FROZEN[fid], f"{fid} 的内容被改动了"


def test_guideline_hash_is_stable_hex():
    sha = check_guideline()
    assert len(sha) == 64 and int(sha, 16) >= 0


def test_guideline_files_exist_and_model_prompt_has_no_part_b():
    from common import GUIDELINE_PATH, MODEL_PROMPT_PATH
    from generation_prompts import load_model_prompt

    assert GUIDELINE_PATH.name == "generator_guideline_v1_1.md" and GUIDELINE_PATH.is_file()
    assert MODEL_PROMPT_PATH.name == "generator_model_prompt_v1_1.md"
    text = load_model_prompt()                       # 内部会拒绝含 Part B / DEMO 示例的文件
    assert "A7. Renderable story contract" in text and "DEMO_PIANO" not in text
    assert "Implementation note" not in text         # 名字分组的实现说明只在完整 guideline 里，不发给模型


# ----------------------------------------------------------------------- 错误检测
def _write(tmp_path, rows):
    p = tmp_path / "pool.jsonl"
    p.write_text("\n".join(json.dumps(r) if isinstance(r, dict) else r for r in rows) + "\n", encoding="utf-8")
    return p


def _row(fid="K91", **over):
    base = read_jsonl(KNOWLEDGE_PATH)[0] | {"fact_id": fid}
    return base | over


def _load(p):
    return load_knowledge(p, expected_n=None, expected_category_counts=None)


def test_duplicate_id_detected(tmp_path):
    with pytest.raises(KnowledgeValidationError, match="重复"):
        _load(_write(tmp_path, [_row("K91"), _row("K91")]))


def test_missing_field_detected(tmp_path):
    r = _row()
    del r["pretest_question"]
    with pytest.raises(KnowledgeValidationError, match="pretest_question"):
        _load(_write(tmp_path, [r]))


def test_bad_category_detected(tmp_path):
    with pytest.raises(KnowledgeValidationError, match="knowledge_category"):
        _load(_write(tmp_path, [_row(knowledge_category="made_up")]))


def test_unknown_field_detected(tmp_path):
    with pytest.raises(KnowledgeValidationError, match="typo_field"):
        _load(_write(tmp_path, [_row(typo_field="x")]))


def test_identical_claims_detected(tmp_path):
    r = _row()
    r["conflicting_claim"] = r["aligned_claim"]
    with pytest.raises(KnowledgeValidationError, match="不能相同"):
        _load(_write(tmp_path, [r]))


def test_unparseable_line_reports_line_number(tmp_path):
    with pytest.raises(KnowledgeValidationError, match=r":2:"):
        _load(_write(tmp_path, [_row(), "{not json"]))


def test_wrong_count_detected(tmp_path):
    with pytest.raises(KnowledgeValidationError, match="应为 12"):
        load_knowledge(_write(tmp_path, [_row()]))
