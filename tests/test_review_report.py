"""汇总审查报告（build_review_report）：离线测试。"""
from __future__ import annotations

import json

import pytest

from build_review_report import load_records, merged_story, render_card, render_report
from candidates import build_candidate


@pytest.fixture()
def rec(k30, bundle, family_out, asg):
    return build_candidate(family_id="F001", fact=k30, bundle=bundle, family_out=family_out, generator_model="MOCK",
                           prompt_version="x", created_at="2026-01-01T00:00:00+00:00", assignment=asg)


def test_merged_story_shows_both_claims_and_the_explicit_insertion(rec):
    s = merged_story(rec)
    assert "{{" not in s
    assert "**[the public elementary-school year in Japan generally begins in April ｜ " \
           "the public elementary-school year in Japan generally begins in September]**" in s
    assert "⟨Grace believes that [" in s and s.count("⟨") == 1 and s.count("⟩") == 1
    assert s.index("**[") < s.index("⟨") < s.index("Later, Grace starts")      # 解释句紧跟在来源句之后


def test_card_contains_questions_gold_checks_and_a_review_checkbox(rec):
    c = render_card(rec)
    assert '<a id="F001"></a>' in c and "## F001 · K30 · T5 · A4 · travel_cultural_orientation" in c
    assert "| Q2 行动 |" in c and "| March | August |" in c
    assert "| Q3 现实 |" in c and "☐ 通过 ☐ 需修改 ☐ 剔除" in c
    assert "<details>" in c and "implicit_conflicting" in c and "explicit_aligned" in c
    assert "Bundle 设计" in c and "agent_prior_knowledge_risk" in c


def test_report_has_a_linked_summary_table_and_one_card_per_family(rec):
    other = rec.model_copy(update={"family_id": "F002", "fact_id": "K31"})
    rep = render_report([rec, other], title="测试批次")
    assert rep.startswith("# 测试批次") and "共 **2** 题" in rep
    assert "[F001](#F001)" in rep and "[F002](#F002)" in rep
    assert rep.count("<details>") == 2 and rep.count("**人工审查**") == 2


def test_failed_render_is_reported_without_crashing(rec):
    bad = rec.model_copy(update={"variants": None, "validation_status": "auto_rejected"})
    assert "渲染失败" in render_card(bad)


def test_load_records_from_jsonl_and_directory_prefers_latest(tmp_path, rec):
    older = json.loads(rec.model_dump_json())
    newer = {**older, "family_id": "F009"}
    d = tmp_path / "run"
    d.mkdir()
    (d / "K30_20260101-000000_3_candidate.json").write_text(json.dumps(older), encoding="utf-8")
    (d / "K30_20260202-000000_3_candidate.json").write_text(json.dumps(newer), encoding="utf-8")
    assert [r.family_id for r in load_records([d])] == ["F009"]            # 同一事实取时间戳最新
    j = tmp_path / "c.jsonl"
    j.write_text(json.dumps(older) + "\n" + json.dumps({**older, "fact_id": "K13", "family_id": "F002"}) + "\n",
                 encoding="utf-8")
    assert [r.family_id for r in load_records([j])] == ["F001", "F002"]
