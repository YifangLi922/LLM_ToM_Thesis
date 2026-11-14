"""共享 fixtures。所有测试都不需要 API key，也不会联网。"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from sampling import Assignment
from schemas import GenerateFamilyOutput, ProposeBundlesOutput
from validate_knowledge import load_knowledge

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mock_k30_family.json"

# 与模拟样例一致的抽样器分配
MOCK_ASSIGNMENT = Assignment(index=0, template_id="T5", agent_name="Grace", name_pool_group="feminine",
                             setting_domain="travel_cultural_orientation", name_sampling_seed=1)


@pytest.fixture(scope="session")
def facts():
    return load_knowledge()


@pytest.fixture(scope="session")
def k30(facts):
    return next(f for f in facts if f.fact_id == "K30")


@pytest.fixture()
def asg() -> Assignment:
    return MOCK_ASSIGNMENT


@pytest.fixture()
def fixture_raw() -> dict:
    return copy.deepcopy(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


@pytest.fixture()
def propose_out(fixture_raw) -> ProposeBundlesOutput:
    return ProposeBundlesOutput.model_validate(fixture_raw["propose_output"])


@pytest.fixture()
def bundle(propose_out):
    return propose_out.bundles[0]


@pytest.fixture()
def family_dict(fixture_raw) -> dict:
    """可随意修改的 generate_family 输出 dict。"""
    return fixture_raw["family_output"]


@pytest.fixture()
def family_out(family_dict) -> GenerateFamilyOutput:
    return GenerateFamilyOutput.model_validate(family_dict)
