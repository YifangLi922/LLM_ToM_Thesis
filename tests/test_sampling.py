from __future__ import annotations

from collections import Counter

import pytest

from config import load_config
from sampling import ALL_TEMPLATES, PRONOUNS, AssignmentSampler
from schemas import SETTING_DOMAINS

MASC = [f"M{i}" for i in range(10)]
FEM = [f"F{i}" for i in range(10)]

# guideline v1.1 B1 的固定名字池（逐字核对）
GUIDELINE_MASC = ["James", "Oliver", "Daniel", "Henry", "Thomas", "Lucas", "Ethan", "Noah", "Benjamin", "Jack"]
GUIDELINE_FEM = ["Olivia", "Amelia", "Sophia", "Charlotte", "Grace", "Hannah", "Lily", "Ava", "Ella", "Mia"]


def make(seed=1, templates=ALL_TEMPLATES, domains=SETTING_DOMAINS):
    return AssignmentSampler(seed=seed, templates=templates, masculine_names=MASC, feminine_names=FEM, domains=domains)


@pytest.mark.parametrize("seed", [0, 1, 7, 20261113])
def test_every_template_appears_once_per_block_of_six(seed):
    s = make(seed)
    for block in range(5):
        got = [s.assignment_for(block * 6 + k).template_id for k in range(6)]
        assert sorted(got) == sorted(ALL_TEMPLATES), (seed, block, got)


def test_templates_are_perfectly_balanced_over_many_families():
    s = make()
    counts = Counter(a.template_id for a in s.preview(60))
    assert counts == {t: 10 for t in ALL_TEMPLATES}


def test_every_name_once_per_block_of_twenty_and_group_balanced():
    s = make()
    first = s.preview(20)
    assert len({a.agent_name for a in first}) == 20
    assert Counter(a.name_pool_group for a in first) == {"masculine": 10, "feminine": 10}
    assert Counter(a.agent_name for a in s.preview(60)) == {n: 3 for n in MASC + FEM}


def test_every_setting_domain_once_per_block_of_ten():
    s = make()
    for block in range(3):
        got = [s.assignment_for(block * 10 + k).setting_domain for k in range(10)]
        assert sorted(got) == sorted(SETTING_DOMAINS)
    assert Counter(a.setting_domain for a in s.preview(50)) == {d: 5 for d in SETTING_DOMAINS}


def test_assignment_is_a_pure_function_of_seed_and_index():
    a, b = make(5), make(5)
    forward = [a.assignment_for(i) for i in range(30)]
    backward = [b.assignment_for(i) for i in reversed(range(30))][::-1]
    assert forward == backward                     # 与调用顺序无关（便于断点续跑）
    assert [x.as_dict() for x in forward] == [x.as_dict() for x in make(5).preview(30)]


def test_assignment_records_the_run_seed_for_audit():
    a = make(42).assignment_for(3)
    assert a.name_sampling_seed == 42 and a.domain_attempt == 0
    assert set(a.as_dict()) == {"index", "template_id", "agent_name", "name_pool_group", "setting_domain",
                                "name_sampling_seed", "domain_attempt"}


def test_different_seeds_give_different_orders():
    assert [x.template_id for x in make(1).preview(12)] != [x.template_id for x in make(2).preview(12)]


def test_template_name_and_domain_streams_are_independent():
    s = make()
    tpl, dom = {}, {}
    for a in s.preview(120):
        tpl.setdefault(a.agent_name, set()).add(a.template_id)
        dom.setdefault(a.agent_name, set()).add(a.setting_domain)
    assert any(len(v) > 1 for v in tpl.values())       # 同一个名字不会永远配同一个模板
    assert any(len(v) > 1 for v in dom.values())       # 也不会永远配同一个场景域


def test_group_matches_pool_and_fixes_pronouns():
    for a in make().preview(40):
        assert (a.agent_name in MASC) == (a.name_pool_group == "masculine")
        assert a.pronouns == PRONOUNS[a.name_pool_group]
    assert PRONOUNS == {"masculine": "he/him", "feminine": "she/her"}


# ------------------------------------------------------------------ 场景域改派（guideline v1.1 B1）
def test_domain_order_starts_with_initial_domain_and_covers_all_once():
    s = make()
    for i in range(25):
        order = s.domain_order(i)
        assert order[0] == s.assignment_for(i).setting_domain
        assert sorted(order) == sorted(SETTING_DOMAINS)


def test_reassignment_changes_only_the_domain():
    s = make()
    a = s.assignment_for(7)
    b = a.with_domain(s.domain_order(7)[1], 1)
    assert (b.agent_name, b.template_id, b.name_pool_group, b.index) == (a.agent_name, a.template_id, a.name_pool_group, a.index)
    assert b.setting_domain != a.setting_domain and b.domain_attempt == 1


@pytest.mark.parametrize("bad", [["T9"], ["T1", "T1"], []])
def test_invalid_template_lists_rejected(bad):
    with pytest.raises(ValueError):
        make(templates=bad)


@pytest.mark.parametrize("bad", [["nonsense"], ["arts_media", "arts_media"], []])
def test_invalid_domain_lists_rejected(bad):
    with pytest.raises(ValueError):
        make(domains=bad)


def test_duplicate_or_empty_names_rejected():
    with pytest.raises(ValueError):
        AssignmentSampler(seed=1, templates=ALL_TEMPLATES, masculine_names=["A", "A"], feminine_names=[])
    with pytest.raises(ValueError):
        AssignmentSampler(seed=1, templates=ALL_TEMPLATES, masculine_names=[], feminine_names=[])


def test_negative_index_rejected():
    with pytest.raises(ValueError):
        make().assignment_for(-1)


# ------------------------------------------------------------------ 真实配置
def test_pilot_config_uses_the_guideline_v1_1_name_pool():
    cfg = load_config().sampling
    assert cfg.agent_names.masculine == GUIDELINE_MASC and cfg.agent_names.feminine == GUIDELINE_FEM
    assert "Emma" not in cfg.agent_names.masculine + cfg.agent_names.feminine     # v1.1：不要凭习惯用 Emma


def test_pilot_config_rotates_all_six_templates_and_ten_domains():
    cfg = load_config().sampling
    assert set(cfg.templates) == {"T1", "T2", "T3", "T4A", "T4C", "T5"}
    s = AssignmentSampler.from_config(cfg)
    assert {a.template_id for a in s.preview(6)} == set(cfg.templates)
    assert len({a.agent_name for a in s.preview(20)}) == 20
    assert {a.setting_domain for a in s.preview(10)} == set(SETTING_DOMAINS)
    assert cfg.max_regenerations == 2 and cfg.max_domain_reassignments == 2
