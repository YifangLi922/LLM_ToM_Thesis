"""小型确定性抽样器：给每个 family 分配 模板、人物名字 与 场景域（setting_domain）。

设计（对应 guideline v1.1 B1：名字 / 场景域 / 模板由代码分配，而不是让造题模型自己挑）：
- 纯函数：同一个 (seed, index) 永远得到同一个分配，便于断点续跑与复现（不依赖全局状态/调用顺序）。
- 分块洗牌（block shuffle）：每个长度为 N 的块里，N 个候选各出现恰好一次，块内顺序由 seed 决定。
  因此 6 个模板每 6 个 family 轮一遍，20 个名字每 20 个 family 轮一遍，10 个场景域每 10 个 family 轮一遍。
- 三个流（模板 / 名字 / 场景域）相互独立（用不同的随机流），避免"某个名字总是配某个模板"。
- 名字分组（masculine / feminine）：这是写代码时为了让故事更好生成而做的技术性绑定——分组决定传给造题模型的
  代词（he/him 或 she/her），使故事里的人称与人物名字一致、可读。它不代表任何关于性别身份、能力、职业、国籍的
  刻板联系（见 guideline v1.1 B1 的 Implementation note）。
- 场景域：这里只给出"初始分配"和一个确定性的备选顺序（domain_order）。guideline 要求域的选择服从事实–任务兼容性，
  所以调用方若在 propose_bundles 阶段发现该域不兼容，就按备选顺序改派下一个域并记录，而不是让模型偷偷换域。
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, replace
from typing import Sequence, TypeVar

from schemas import SETTING_DOMAINS

T = TypeVar("T")

ALL_TEMPLATES: tuple[str, ...] = ("T1", "T2", "T3", "T4A", "T4C", "T5")
PRONOUNS = {"masculine": "he/him", "feminine": "she/her"}


@dataclass(frozen=True)
class Assignment:
    index: int                # 从 0 开始的 family 序号（family_id F001 对应 index 0）
    template_id: str
    agent_name: str
    name_pool_group: str      # "masculine" / "feminine"，用于让故事里的代词与名字一致
    setting_domain: str
    name_sampling_seed: int | None = None     # 运行级随机种子（用于审计）
    domain_attempt: int = 0   # 0 = 初始分配；k>0 = 因不兼容而改派的第 k 次

    @property
    def pronouns(self) -> str:
        return PRONOUNS[self.name_pool_group]

    def as_dict(self) -> dict[str, str | int | None]:
        return asdict(self)

    def with_domain(self, domain: str, attempt: int) -> "Assignment":
        return replace(self, setting_domain=domain, domain_attempt=attempt)


def _block_permutation(items: Sequence[T], seed: int, stream: str, block: int) -> list[T]:
    rng = random.Random(f"{seed}|{stream}|{block}")      # 字符串种子在各 Python 版本下结果一致
    perm = list(items)
    rng.shuffle(perm)
    return perm


class AssignmentSampler:
    def __init__(self, *, seed: int, templates: Sequence[str], masculine_names: Sequence[str],
                 feminine_names: Sequence[str], domains: Sequence[str] = SETTING_DOMAINS):
        if not templates:
            raise ValueError("templates 不能为空")
        unknown = [t for t in templates if t not in ALL_TEMPLATES]
        if unknown or len(set(templates)) != len(templates):
            raise ValueError(f"templates 必须是不重复的 {ALL_TEMPLATES} 子集，收到 {list(templates)}")
        names = [(n, "masculine") for n in masculine_names] + [(n, "feminine") for n in feminine_names]
        if not names or len({n for n, _ in names}) != len(names):
            raise ValueError("名字池不能为空，且名字不得重复")
        bad_dom = [d for d in domains if d not in SETTING_DOMAINS]
        if not domains or bad_dom or len(set(domains)) != len(domains):
            raise ValueError(f"domains 必须是不重复的 {SETTING_DOMAINS} 子集，收到 {list(domains)}")
        self.seed = seed
        self.templates = tuple(templates)
        self.names = tuple(names)
        self.domains = tuple(domains)

    @classmethod
    def from_config(cls, sampling) -> "AssignmentSampler":
        return cls(seed=sampling.seed, templates=sampling.templates,
                   masculine_names=sampling.agent_names.masculine, feminine_names=sampling.agent_names.feminine)

    def domain_order(self, index: int) -> list[str]:
        """该 family 的场景域优先顺序：第 0 个是初始分配，其余是确定性的备选（同一块洗牌结果里循环向后）。"""
        if index < 0:
            raise ValueError("index 不能为负")
        block, pos = divmod(index, len(self.domains))
        perm = _block_permutation(self.domains, self.seed, "domain", block)
        return perm[pos:] + perm[:pos]

    def assignment_for(self, index: int) -> Assignment:
        if index < 0:
            raise ValueError("index 不能为负")
        tpl_block, tpl_pos = divmod(index, len(self.templates))
        name_block, name_pos = divmod(index, len(self.names))
        template = _block_permutation(self.templates, self.seed, "template", tpl_block)[tpl_pos]
        name, group = _block_permutation(self.names, self.seed, "name", name_block)[name_pos]
        return Assignment(index=index, template_id=template, agent_name=name, name_pool_group=group,
                          setting_domain=self.domain_order(index)[0], name_sampling_seed=self.seed)

    def preview(self, n: int) -> list[Assignment]:
        return [self.assignment_for(i) for i in range(n)]
