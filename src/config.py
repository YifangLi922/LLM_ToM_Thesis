"""读取并校验 config/pilot.yaml（模型、采样、预算设置）。配置里**不放任何密钥**，只放环境变量名。"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from common import CONFIG_PATH


class _Cfg(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeneratorConfig(_Cfg):
    provider: str
    model_id: str
    api_key_env: str                       # 只存环境变量名，如 OPENAI_API_KEY
    access_verified: str | None = None     # 备注：何时、如何确认过该 key 能调用此模型
    n_bundles_per_fact: int                # propose_bundles 向模型要几个 bundle（由调用程序决定）
    max_retries: int
    max_output_tokens: int | None = None   # null = 待 smoke test 后决定
    temperature: float | None = None       # null = 使用模型默认


class EvalModelConfig(_Cfg):
    condition_id: str                      # 评测条件的唯一名字，如 qwen3-32b__thinking
    provider: str
    model_id: str
    thinking: bool | None                  # True/False = 开/关思考模式；None = 该模型无此开关
    api_key_env: str
    pinned_provider: str | None = None     # OpenRouter 的后端服务商；null = 待 capability check 后固定
    temperature: float | None = None
    max_tokens: int | None = None
    seed: int | None = None
    max_retries: int = 3


class PilotConfig(_Cfg):
    answer_instruction: str
    generator: GeneratorConfig
    evaluated_models: list[EvalModelConfig]
    eval_base_url: str

    @model_validator(mode="after")
    def _check(self) -> "PilotConfig":
        ids = [m.condition_id for m in self.evaluated_models]
        if len(set(ids)) != len(ids):
            raise ValueError(f"condition_id 重复: {ids}")
        if not self.evaluated_models:
            raise ValueError("evaluated_models 不能为空")
        gen = self.generator.model_id.strip().lower()
        clash = [m.condition_id for m in self.evaluated_models if m.model_id.strip().lower() == gen]
        if clash:
            raise ValueError(f"造题模型 {self.generator.model_id} 不得同时作为被测模型: {clash}")
        if any(m.provider.lower() == self.generator.provider.lower() and m.api_key_env == self.generator.api_key_env
               for m in self.evaluated_models):
            raise ValueError("被测模型不应与造题模型共用同一个 provider/api_key_env")
        return self


def load_config(path: Path = CONFIG_PATH) -> PilotConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return PilotConfig.model_validate(raw)
