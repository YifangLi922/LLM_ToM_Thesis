"""小型确定性抽样器：给每个 family 分配 模板 与 人物名字。

设计（对应 guideline §11：语料多样性由代码控制，而不是靠让模型"尽量多样"）：
- 纯函数：同一个 (seed, index) 永远得到同一个分配，便于断点续跑与复现（不依赖全局状态/调用顺序）。
- 分块洗牌（block shuffle）：每个长度为 N 的块里，N 个候选各出现恰好一次，块内顺序由 seed 决定。
  因此 6 个模板每 6 个 family 轮一遍，20 个名字每 20 个 family 轮一遍，长期占比完全均衡。
- 模板流和名字流相互独立（用不同的随机流），避免"某个名字总是配某个模板"。
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Sequence, TypeVar

T = TypeVar("T")

ALL_TEMPLATES: tuple[str, ...] = ("T1", "T2", "T3", "T4A", "T4C", "T5")


@dataclass(frozen=True)
class Assignment:
    index: int                # 从 0 开始的 family 序号（family_id F001 对应 index 0）
    template_id: str
    agent_name: str
    agent_gender: str         # "female" / "male"，用于让故事里的代词与名字一致

    def as_dict(self) -> dict[str, str | int]:
        return asdict(self)


def _block_permutation(items: Sequence[T], seed: int, stream: str, block: int) -> list[T]:
    rng = random.Random(f"{seed}|{stream}|{block}")      # 字符串种子在各 Python 版本下结果一致
    perm = list(items)
    rng.shuffle(perm)
    return perm


class AssignmentSampler:
    def __init__(self, *, seed: int, templates: Sequence[str], male_names: Sequence[str], female_names: Sequence[str]):
        if not templates:
            raise ValueError("templates 不能为空")
        unknown = [t for t in templates if t not in ALL_TEMPLATES]
        if unknown or len(set(templates)) != len(templates):
            raise ValueError(f"templates 必须是不重复的 {ALL_TEMPLATES} 子集，收到 {list(templates)}")
        names = [(n, "male") for n in male_names] + [(n, "female") for n in female_names]
        if not names or len({n for n, _ in names}) != len(names):
            raise ValueError("名字池不能为空，且名字不得重复")
        self.seed = seed
        self.templates = tuple(templates)
        self.names = tuple(names)

    @classmethod
    def from_config(cls, sampling) -> "AssignmentSampler":
        return cls(seed=sampling.seed, templates=sampling.templates,
                   male_names=sampling.agent_names.male, female_names=sampling.agent_names.female)

    def assignment_for(self, index: int) -> Assignment:
        if index < 0:
            raise ValueError("index 不能为负")
        tpl_block, tpl_pos = divmod(index, len(self.templates))
        name_block, name_pos = divmod(index, len(self.names))
        template = _block_permutation(self.templates, self.seed, "template", tpl_block)[tpl_pos]
        name, gender = _block_permutation(self.names, self.seed, "name", name_block)[name_pos]
        return Assignment(index=index, template_id=template, agent_name=name, agent_gender=gender)

    def preview(self, n: int) -> list[Assignment]:
        return [self.assignment_for(i) for i in range(n)]
