"""造题请求的构造：guideline 全文做 instructions，单条事实 + 任务模式 + 抽样分配做 user 输入。

每个请求都自包含（guideline §0），一次只给一条事实。事实的 fact_status 是流水线元数据，不属于
"锁定输入"，所以不发给造题模型；其余字段原样发送，不改写。
"""
from __future__ import annotations

from typing import Any

from common import GUIDELINE_PATH, sha256_text
from schemas import Bundle, KnowledgeRecord

# 调用程序对 guideline 的补充说明：只解释 JSON 字段约定，不改变任何科学规则。
ADDENDUM_COMMON = (
    "Return only the JSON object required by the guideline for the given task_mode. "
    "Every key in the schema must be present (use null or an empty list where the schema allows it). "
    "Do not output ellipses, placeholder text, or the words 'validated' / 'human_gold_confirmed'."
)
ADDENDUM_PROPOSE = (
    "task_mode=propose_bundles: return at most `max_bundles` bundles. "
    "Set failure_reason to null when status is candidates_proposed; when status is no_valid_bundle, "
    "bundles must be an empty list and failure_reason must be substantive. "
    "If assignments.template_id is non-null, suggested_template_ids in every bundle must be exactly that one ID. "
    "If assignments.action_type or assignments.reasoning_structure is non-null, every bundle must use it. "
    "Following guideline section 9 (the action question must not give alternative choices), prefer bundles whose "
    "target_output is open-ended -- a quantity, a name, a time, a position, or a specific edit -- and can be produced "
    "without the story naming the competing answers. Do not propose a bundle whose whole design is a forced choice "
    "between the two competing answers (for example increase vs decrease, surface vs bottom, change vs no change) "
    "unless no better design exists without hidden assumptions; if you do propose one, include 'forced_binary_choice' "
    "in its risk_flags."
)
ADDENDUM_GENERATE = (
    "task_mode=generate_family: use the selected_bundle exactly as given (same bundle_id, action_type, "
    "reasoning_structure and the two action golds). template_id must equal assignments.template_id. "
    "The extra field `revision_reasons` must be [] when status is candidate_generated; when status is "
    "needs_revision, list the concrete reasons there, set every nullable content field to null and every "
    "list field to []. For candidate_generated, validation_status must be exactly \"needs_human_review\". "
    "story_backbone must contain {{CLAIM_SPAN}} and {{BELIEF_INSERTION}} exactly once each; "
    "{{BELIEF_INSERTION}} must come immediately after the sentence that contains {{CLAIM_SPAN}} "
    "(directly after that sentence's final punctuation). claim spans and belief sentences must not contain "
    "curly braces. Both claim spans must fit the same grammatical slot in the backbone. "
    "The protagonist must be the person named in assignments.agent_name: set `agent` to exactly that name, use the "
    "name in the story, and use pronouns consistent with assignments.agent_gender ('female' = she/her, 'male' = he/him). "
    "Following guideline section 9, the shared story text must not list, name or enumerate the competing answers to "
    "the action question (for example 'either X or Y', or a key that spells out both outputs); describe the decision "
    "generically (for example 'she must decide where to aim the camera') and let the answer follow from the "
    "protagonist's belief plus the stated constraints. The story may give constraints and resources, but the two "
    "action golds must not both appear in the text outside the claim spans and belief sentences. "
    "If `revision_feedback` is non-empty, your previous attempt failed automatic checks: fix every listed problem."
)


def load_guideline() -> str:
    return GUIDELINE_PATH.read_text(encoding="utf-8")


def prompt_version(guideline_text: str | None = None) -> str:
    """guideline + 补充说明 的哈希：任何一处改动都会改变版本号，写入每条记录的 provenance。"""
    g = guideline_text if guideline_text is not None else load_guideline()
    return sha256_text(g.replace("\r\n", "\n") + "\n" + ADDENDUM_COMMON + ADDENDUM_PROPOSE + ADDENDUM_GENERATE)


def fact_payload(fact: KnowledgeRecord) -> dict[str, Any]:
    return fact.model_dump(exclude={"fact_status"})


def propose_payload(
    fact: KnowledgeRecord, *, max_bundles: int, template_id: str | None = None,
    action_type: str | None = None, reasoning_structure: str | None = None,
) -> dict[str, Any]:
    return {
        "task_mode": "propose_bundles",
        "max_bundles": max_bundles,
        "fact_record": fact_payload(fact),
        "assignments": {"template_id": template_id, "action_type": action_type,
                        "reasoning_structure": reasoning_structure},
        "output_contract_notes": ADDENDUM_COMMON + " " + ADDENDUM_PROPOSE,
    }


def generate_payload(
    fact: KnowledgeRecord, bundle: Bundle, *, template_id: str,
    agent_name: str | None = None, agent_gender: str | None = None, revision_feedback: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "task_mode": "generate_family",
        "fact_record": fact_payload(fact),
        "selected_bundle": bundle.model_dump(),
        "assignments": {"template_id": template_id, "action_type": bundle.action_type,
                        "reasoning_structure": bundle.reasoning_structure,
                        "agent_name": agent_name, "agent_gender": agent_gender},
        "revision_feedback": list(revision_feedback or []),
        "output_contract_notes": ADDENDUM_COMMON + " " + ADDENDUM_GENERATE,
    }
