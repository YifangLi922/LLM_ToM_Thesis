"""造题请求的构造（guideline v1.1）：
- instructions = generator_model_prompt_v1_1.md（仅 Part A，稳定内容放前面，利于缓存）；
  **不**发送 Part B 的实现说明与 B5 完整示例（那些只给研究者和代码看）。
- user 输入 = 单条锁定事实 + 任务模式 + 代码分配的槽位（模板 / 名字 / 代词 / 场景域）+（generate 时）所选 bundle。
- 严格的 JSON Schema 另行通过 Structured Outputs 提供（见 llm_client.call_structured）。

每个请求都自包含，一次只给一条事实。事实的 fact_status 是流水线元数据，不属于"锁定输入"，所以不发给造题模型；
其余字段（含 qualification_notes、review_flags）原样发送，不改写。
"""
from __future__ import annotations

from typing import Any

from common import MODEL_PROMPT_PATH, sha256_text
from schemas import Bundle, KnowledgeRecord

# 调用程序对 prompt 的补充说明：只解释 JSON 字段约定与槽位用法，不改变任何科学规则。
ADDENDUM_COMMON = (
    "Return only the JSON object required by the schema for the given task_mode. "
    "Every key in the schema must be present (use null or an empty list where the schema allows it). "
    "risk_flags may contain only values from the schema's controlled vocabulary; risk_notes is a single string "
    "(\"\" when risk_flags is empty). Do not output ellipses, placeholder text, or the words 'validated', "
    "'approved' or 'human_gold_confirmed'."
)
ADDENDUM_PROPOSE = (
    "task_mode=propose_bundles: return at most `max_bundles` bundles. "
    "Set failure_reason to null when status is candidates_proposed; when status is no_valid_bundle, "
    "bundles must be an empty list and failure_reason must be substantive. "
    "If assignments.template_id is non-null, suggested_template_ids in every bundle must be exactly that one ID. "
    "If assignments.action_type or assignments.reasoning_structure is non-null, every bundle must use it. "
    "assignments.setting_domain is the setting domain chosen by the caller: every bundle must be workable in a "
    "natural setting within that domain (and assignments.setting_label, if non-null, pins the exact setting). "
    "If the fact cannot be turned into a valid bundle in that domain, return no_valid_bundle and name the "
    "domain incompatibility in failure_reason instead of switching domain. "
    "Following A8, design every bundle around an OPEN answer space: the agent produces a value (writes, sets, "
    "schedules, labels, books, buys or builds something). Do not design a task whose answer can only be made "
    "determinate by listing the candidate actions or values in the story, and do not rely on if-then decision "
    "rules; if that is the only option, return no_valid_bundle."
)
ADDENDUM_GENERATE = (
    "task_mode=generate_family: use the selected_bundle exactly as given (same bundle_id, action_type, "
    "reasoning_structure and the two action golds). template_id must equal assignments.template_id. "
    "When status is candidate_generated, failure_reason must be null and validation_status must be exactly "
    "\"needs_human_review\". When status is needs_revision, put the concrete reason in failure_reason, set every "
    "nullable content field and validation_status to null and belief_cue_ids to [] (risk_flags/risk_notes may "
    "describe the problem). "
    "story_backbone must contain {{CLAIM_SPAN}} and {{BELIEF_INSERTION}} exactly once each; "
    "{{BELIEF_INSERTION}} must come immediately after the sentence that contains {{CLAIM_SPAN}} "
    "(directly after that sentence's final punctuation). Claim spans and belief propositions must not contain "
    "curly braces. Both claim spans must fit the same grammatical slot in the backbone, and each must restate the "
    "locked aligned_claim / conflicting_claim itself (same content and qualifiers, same wording as far as the "
    "grammar allows) -- never an indirect or behavioural paraphrase of it, in any template (including T4C routines). "
    "belief_proposition_aligned / belief_proposition_conflicting are affirmative finite-clause complements "
    "without an initial 'that', without the agent's name at the start and without final punctuation; the caller "
    "builds the sentence '[agent_name] believes that [proposition].' itself. "
    "The protagonist must be the person named in assignments.agent_name: set `agent_name` to exactly that name, "
    "use the name in the story, and use the pronouns in assignments.agent_pronouns whenever you refer to the "
    "protagonist with a pronoun, so the story reads naturally and consistently. "
    "Set `setting_domain` to exactly assignments.setting_domain and keep it unchanged; set `setting` to "
    "assignments.setting_label if it is non-null, otherwise to one specific natural setting within that domain. "
    "Follow A8: the story must not list the candidate actions or values anywhere, must contain no rule puzzle and no "
    "technical caveats, and the backbone including the claim span must not exceed 110 words (longer stories are "
    "rejected automatically). "
    "If `revision_feedback` is non-empty, your previous attempt failed automatic checks: fix every listed problem."
)

# Part B 的内容不得进入发给造题模型的 instructions。
_PART_B_MARKERS = ("DEMO_PIANO", "Part B")


def load_model_prompt() -> str:
    text = MODEL_PROMPT_PATH.read_text(encoding="utf-8")
    leaked = [m for m in _PART_B_MARKERS if m in text]
    if leaked:
        raise ValueError(f"{MODEL_PROMPT_PATH.name} 含有不应发送给造题模型的 Part B 内容: {leaked}")
    return text


def prompt_version(prompt_text: str | None = None) -> str:
    """model prompt + 补充说明 的哈希：任何一处改动都会改变版本号，写入每条记录的 provenance。"""
    g = prompt_text if prompt_text is not None else load_model_prompt()
    return sha256_text(g.replace("\r\n", "\n") + "\n" + ADDENDUM_COMMON + ADDENDUM_PROPOSE + ADDENDUM_GENERATE)


def fact_payload(fact: KnowledgeRecord) -> dict[str, Any]:
    return fact.model_dump(exclude={"fact_status"})


def propose_payload(
    fact: KnowledgeRecord, *, max_bundles: int, template_id: str | None = None,
    action_type: str | None = None, reasoning_structure: str | None = None,
    setting_domain: str | None = None, setting_label: str | None = None,
) -> dict[str, Any]:
    return {
        "task_mode": "propose_bundles",
        "max_bundles": max_bundles,
        "fact_record": fact_payload(fact),
        "assignments": {"template_id": template_id, "action_type": action_type,
                        "reasoning_structure": reasoning_structure,
                        "setting_domain": setting_domain, "setting_label": setting_label},
        "output_contract_notes": ADDENDUM_COMMON + " " + ADDENDUM_PROPOSE,
    }


def generate_payload(
    fact: KnowledgeRecord, bundle: Bundle, *, template_id: str,
    agent_name: str | None = None, agent_pronouns: str | None = None,
    setting_domain: str | None = None, setting_label: str | None = None,
    revision_feedback: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "task_mode": "generate_family",
        "fact_record": fact_payload(fact),
        "selected_bundle": bundle.model_dump(),
        "assignments": {"template_id": template_id, "action_type": bundle.action_type,
                        "reasoning_structure": bundle.reasoning_structure,
                        "agent_name": agent_name, "agent_pronouns": agent_pronouns,
                        "setting_domain": setting_domain, "setting_label": setting_label},
        "revision_feedback": list(revision_feedback or []),
        "output_contract_notes": ADDENDUM_COMMON + " " + ADDENDUM_GENERATE,
    }
