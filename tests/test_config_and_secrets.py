from __future__ import annotations

import re
import subprocess

import pytest
from pydantic import ValidationError

from common import REPO_ROOT
from config import PilotConfig, load_config
from export_evaluation import ANSWER_INSTRUCTION


def test_pilot_config_loads_and_matches_decisions():
    cfg = load_config()
    assert cfg.generator.model_id == "gpt-6.1-sol"
    assert [m.condition_id for m in cfg.evaluated_models] == [
        "qwen3-32b__non_thinking", "qwen3-32b__thinking", "glm-4.5-air__non_thinking", "glm-4.5-air__thinking",
    ]
    assert {m.model_id for m in cfg.evaluated_models} == {"qwen/qwen3-32b", "z-ai/glm-4.5-air"}
    assert cfg.answer_instruction == ANSWER_INSTRUCTION


def test_generator_cannot_be_an_evaluated_model():
    raw = load_config().model_dump()
    raw["evaluated_models"][0]["model_id"] = raw["generator"]["model_id"]
    with pytest.raises(ValidationError, match="不得同时作为被测模型"):
        PilotConfig.model_validate(raw)


def test_generator_and_eval_may_not_share_credentials():
    raw = load_config().model_dump()
    raw["evaluated_models"][0]["provider"] = raw["generator"]["provider"]
    raw["evaluated_models"][0]["api_key_env"] = raw["generator"]["api_key_env"]
    with pytest.raises(ValidationError):
        PilotConfig.model_validate(raw)


def test_duplicate_condition_ids_rejected():
    raw = load_config().model_dump()
    raw["evaluated_models"][1]["condition_id"] = raw["evaluated_models"][0]["condition_id"]
    with pytest.raises(ValidationError, match="重复"):
        PilotConfig.model_validate(raw)


def test_config_contains_env_var_names_not_keys():
    text = (REPO_ROOT / "config" / "pilot.yaml").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" in text and "OPENROUTER_API_KEY" in text
    assert not re.search(r"sk-[A-Za-z0-9_\-]{16,}", text)


# ------------------------------------------------------------------ 仓库里不能有密钥
_SECRET = re.compile(r"sk-[A-Za-z0-9_\-]{20,}|sk-or-[A-Za-z0-9_\-]{10,}")


def _tracked_and_untracked_files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                         cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
    return [REPO_ROOT / p for p in out.splitlines() if p]


def test_no_api_key_like_strings_in_repo_files():
    hits = []
    for p in _tracked_and_untracked_files():
        if not p.is_file() or p.suffix in {".png", ".jpg", ".pdf"}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if _SECRET.search(text):
            hits.append(str(p.relative_to(REPO_ROOT)))
    assert not hits, f"疑似 API key 出现在: {hits}"


def test_dotenv_is_not_tracked_or_unignored():
    files = {p.name for p in _tracked_and_untracked_files()}
    assert ".env" not in files, ".env 不应被 git 跟踪，也不应处于未忽略状态"
