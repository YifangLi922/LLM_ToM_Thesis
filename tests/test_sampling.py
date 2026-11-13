from __future__ import annotations

from collections import Counter

import pytest

from config import load_config
from sampling import ALL_TEMPLATES, AssignmentSampler

MALE = [f"M{i}" for i in range(10)]
FEMALE = [f"F{i}" for i in range(10)]


def make(seed=1, templates=ALL_TEMPLATES):
    return AssignmentSampler(seed=seed, templates=templates, male_names=MALE, female_names=FEMALE)


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


def test_every_name_once_per_block_of_twenty_and_gender_balanced():
    s = make()
    first = s.preview(20)
    assert len({a.agent_name for a in first}) == 20
    assert Counter(a.agent_gender for a in first) == {"male": 10, "female": 10}
    assert Counter(a.agent_name for a in s.preview(60)) == {n: 3 for n in MALE + FEMALE}


def test_assignment_is_a_pure_function_of_seed_and_index():
    a, b = make(5), make(5)
    forward = [a.assignment_for(i) for i in range(30)]
    backward = [b.assignment_for(i) for i in reversed(range(30))][::-1]
    assert forward == backward                     # 与调用顺序无关（便于断点续跑）
    assert [x.as_dict() for x in forward] == [x.as_dict() for x in make(5).preview(30)]


def test_different_seeds_give_different_orders():
    assert [x.template_id for x in make(1).preview(12)] != [x.template_id for x in make(2).preview(12)]


def test_template_and_name_streams_are_independent():
    s = make()
    pairs = {}
    for a in s.preview(120):
        pairs.setdefault(a.agent_name, set()).add(a.template_id)
    assert any(len(v) > 1 for v in pairs.values())       # 同一个名字不会永远配同一个模板


def test_gender_matches_pool():
    for a in make().preview(40):
        assert (a.agent_name in MALE) == (a.agent_gender == "male")


@pytest.mark.parametrize("bad", [["T9"], ["T1", "T1"], []])
def test_invalid_template_lists_rejected(bad):
    with pytest.raises(ValueError):
        make(templates=bad)


def test_duplicate_or_empty_names_rejected():
    with pytest.raises(ValueError):
        AssignmentSampler(seed=1, templates=ALL_TEMPLATES, male_names=["A", "A"], female_names=[])
    with pytest.raises(ValueError):
        AssignmentSampler(seed=1, templates=ALL_TEMPLATES, male_names=[], female_names=[])


def test_negative_index_rejected():
    with pytest.raises(ValueError):
        make().assignment_for(-1)


# ------------------------------------------------------------------ 真实配置
def test_pilot_config_rotates_all_six_templates_with_20_names():
    cfg = load_config().sampling
    assert set(cfg.templates) == {"T1", "T2", "T3", "T4A", "T4C", "T5"}
    assert len(cfg.agent_names.male) == 10 and len(cfg.agent_names.female) == 10
    assert "Maya" not in cfg.agent_names.male + cfg.agent_names.female
    s = AssignmentSampler.from_config(cfg)
    assert {a.template_id for a in s.preview(6)} == set(cfg.templates)
    assert len({a.agent_name for a in s.preview(20)}) == 20
    assert cfg.binary_option_policy == "reject" and cfg.max_regenerations == 2
