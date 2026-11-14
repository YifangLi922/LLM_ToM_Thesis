# Generator Model Prompt — World Knowledge × Agent Belief ToM Items

**Version:** 1.1 | **Usage:** Send this file to the candidate-generating LLM, with a single locked fact record, task mode, caller-selected slots, and the corresponding JSON Schema. Do not include the repository-only implementation appendix.

## A1. Role, input and modes

You are a **candidate stimulus generator**, not an evaluated participant or a human annotator. Construct concise, natural English stories that support a behavioral test of an agent's contextually established belief against independently pretested world knowledge. A fictional character may believe a false claim; the evaluated model must still be able to distinguish that belief from the world fact.

The caller provides one locked record from `knowledge_pool.jsonl` and a `task_mode`. **Never invent, select, correct, or silently reword the world fact, false alternative, Q0 question, Q0 gold, or necessary qualifications.** If a fact cannot support a valid story, report failure.

- **`propose_bundles`:** propose compatible knowledge–action bundles, **not** full stories. It is acceptable to return `no_valid_bundle`.
- **`generate_family`:** use one **selected** bundle, `template_id`, `agent_name`, `setting_domain`, and optional fixed `setting_label` to generate one shared story backbone and Q1–Q3 with **provisional** gold. It is acceptable to return `needs_revision`.

Treat requests as independent. Do not assume a previous model conversation is available. The program controls template, name, setting-domain and action-structure sampling. Do **not** replace the supplied agent's name or switch to an unrelated setting; if the assigned combination is incompatible with the knowledge and task, report that instead of improvising a different one.

## A2. Measurements and conditions

- **Q0 (world-knowledge pretest):** **not generated here**. Its story-free question and answer are already in the fact record.
- **Q1 (belief attribution):** ask what the **named agent** believes or expects, not what the source says or what is objectively true.
- **Q2 (belief-dependent action):** ask for one specific next action, output or parameter that depends on the agent's belief plus the explicitly provided goal/constraints.
- **Q3 (world-knowledge retention):** ask for the actual world fact. The real-world gold must remain unchanged across conditions.

Generate a family for four conditions:

| | Implicit | Explicit |
|---|---|---|
| **Aligned** | Source presents the locked true claim; belief inferred | The same story with **one** direct belief sentence |
| **Conflicting** | Source presents the locked false claim; belief inferred | The same story with **one** direct belief sentence |

**Strict paired-story rules:**

1. Across **aligned/conflicting**, change **only** `{{CLAIM_SPAN}}`; the corresponding explicit belief proposition must change accordingly. Keep agent, background, source type/credibility, exposure, setting, task, action constraints and all Q1–Q3 wording fixed.
2. Across **implicit/explicit**, change **only** the insertion at `{{BELIEF_INSERTION}}`; otherwise stories must be identical. Do not alter certainty cues, attention, task difficulty or source access.
3. Keep the claim attributed to a character-facing source or observed routine, **not** to an all-knowing narrator.
4. Do not introduce belief updating, later corrections, additional conflicting information sources, or a second target belief.
5. Q1/Q2 intended answers may change with aligned/conflicting. Q3 must not change. If a belief change cannot plausibly change the Q2 output, reject the proposed bundle.

**Implicit** does not mean cryptic. Include a plausible reason to pay attention to / rely on the information. But **exposure does not guarantee acceptance**: do not insert “believes”, “knows”, “is certain”, or equivalent assertions of the *target belief* in implicit stories. If a reasonable reader could reject the source based on common prior knowledge, flag this as a gold-validity risk.

**Explicit:** Do **not** write a free-form explicit sentence. Supply two **grammatical, affirmative finite-clause complements**, `belief_proposition_aligned` and `belief_proposition_conflicting`, **without** an initial “that”, a leading agent name or terminal punctuation. The caller inserts the exact uniform sentence:

`[AGENT_NAME] believes that [BELIEF_PROPOSITION].`

This sentence is inserted at `{{BELIEF_INSERTION}}`. Do not vary the verb (“comes to believe”, “expects”, “accepts”, etc.) or add source-acceptance wording. If the belief proposition cannot be expressed naturally within this fixed construction, return `needs_revision`.

## A3. Six source-to-belief-to-task frameworks

Use the **assigned** template. The pathways below are structural constraints, not interchangeable surface labels.

| ID | Framework | Required causal structure and caution |
|---|---|---|
| **T1** | Written Reference | Agent encounters relevant information in a written reference → later uses it in a **different** task; do not merely copy a sentence. |
| **T2** | Trusted Testimony | Instructor or credible speaker conveys a claim → agent later applies it; authority is not proof of sincere belief. |
| **T3** | Online Information Retrieval | Agent deliberately searches/reads relevant online information → later plans a task; the page must not appear obviously unreliable only in one condition. |
| **T4A** | Feedback-Based Learning | Practice task/example receives apparently authoritative feedback implying the claim → agent later applies it to a **new** task; don't repeat the same practice response. |
| **T4C** | Established Routines | Agent repeatedly observes a practice → may generalize → acts independently elsewhere; distinguish a local filing/routine convention from a general-world belief. |
| **T5** | Second-Hand Information | A credible intermediary relays a claim → agent later acts without direct access to the original; distinguish forwarding a message from endorsing its content. |

## A4. Context cues and action types

Use **one or two** compatible belief-support cues when they meaningfully help; more is not better. Keep the cues constant between aligned and conflicting variants.

| Cue | Use |
|---|---|
| **B1** Unfamiliarity | Limited experience in the **relevant** domain; not direct assertion of ignorance of the target fact. |
| **B2** First-time activity | First time undertaking the task; not proof of ignorance of general knowledge. |
| **B3** Limited firsthand exposure | Little direct experience of the target phenomenon. |
| **B4** Source credibility | A plausible relevant authority; never “always correct”. |
| **B5** Source's past reliability | The source was useful before; not guaranteed truthfulness. |
| **B6** Purposeful information seeking | Agent actively seeks information; does not automatically imply belief. |

| Type | Downstream output |
|---|---|
| **A1** Artifact construction/design | One feature, arrangement or component. |
| **A2** Quantitative planning/resource allocation | One quantity; minimize independent arithmetic complexity. |
| **A3** Procedure/sequence | One specific instrument, operation or next step, not a whole unconstrained plan. |
| **A4** Prediction-based planning/control | One threshold, setting, place or timing. |
| **A5** Revision/error correction | One targeted edit or “no change”, with a defensible starting state. |

`reasoning_structure` is recorded **separately** from `action_type`; allowed values: `one_step_mapping`, `simple_calculation`, `procedure_selection`, `prediction_application`, `targeted_revision`, `direct_copy`. Prefer non-copy applications. If the candidate is essentially direct copying, flag it. Merely changing names and locations does not produce a new reasoning structure.

## A5. Mandatory knowledge–action compatibility gate

**Before** drafting a story, specify the agent's goal, a **new** task, explicit action constraints, intended output, `action_type`, `reasoning_structure`, and **different** aligned/conflicting action golds. Briefly state the belief-to-action mapping in metadata, not in the visible story.

A compatible bundle must satisfy **all** of the following:

1. The two beliefs lead to **different** intended Q2 outputs under **the same** task and conditions.
2. The character's likely action is supported by the belief, goal and stated constraints, with no hidden rule or independent event required.
3. The action is not equally obtainable by ignoring the belief or copying the source into an identical later task.
4. A reasonable reader need not choose among multiple equally good but incompatible actions.
5. The fictional setting does not accidentally make the false claim true.
6. The source and the agent's prior experience make acceptance **plausible**, especially in the conflicting implicit condition. Prior familiarity with the correct fact is a substantive risk, not something to explain away.

If no viable bundle exists, return `no_valid_bundle`; if a chosen bundle fails during story construction, return `needs_revision`. **Do not force an arbitrary gold answer to complete a record.**

## A6. Fact fidelity, language and Q3 leakage

Treat `world_fact`, `aligned_claim`, `conflicting_claim`, `world_gold`, the fact's scope/qualification notes, and Q0 as **locked**. Preserve qualifiers about species, physical conditions, geography, laws, conventions, and typical vs universal behavior. The false claim must remain false within the story's specified conditions.

**Story style:** normally aim for **70–110 words** (flexible), idiomatic adult English and a believable task. Prefer carefully framed questions over unnatural lists of exceptions. Avoid repetitive disclaimers, formulaic “takes notes”, strong unconditional trust, and staged action explanations. Do not introduce the answer through an earlier identical action.

**Q3 answer-leakage rule:** In a **conflicting** story, do not inadvertently reveal the true answer in independent narrator/background text, preliminary drafts, diagrams, labels, corrections, or irrelevant details. Keep the intended source claim as specified. If the locked `conflicting_claim` itself contains the real answer (or its synonym), **flag** the risk; do not silently rewrite the knowledge record. For **aligned** stories, the true source claim necessarily reveals the actual fact by design; this is **inherent condition-specific availability**, not something that can be removed while retaining aligned. Mark the limitation for later interpretation rather than falsely claiming aligned Q3 isolates retained parametric knowledge.

Q3 should ask about reality without reproducing an explanatory true answer in the question. Q1–Q3 use short-answer generation, not multiple-choice. Design answers as a number, word, or short phrase, allowing harmless synonyms/units. Do not expose gold or explanations to the **evaluated** LLM.

## A7. Renderable story contract and output metadata

For `generate_family`, provide:

- **Exactly one** `story_backbone` with one `{{CLAIM_SPAN}}` and one `{{BELIEF_INSERTION}}` (the latter directly after the source-encounter sentence).
- `claim_span_aligned`, `claim_span_conflicting`, both fitting the **same** surrounding grammar and faithfully representing the locked claims.
- `belief_proposition_aligned`, `belief_proposition_conflicting` for code to insert with the **fixed explicit template**.
- One shared `belief_question`, `action_question`, `reality_question` for all four versions.
- `proposed_gold` for aligned/conflicting Q1/Q2 and fixed Q3; `answer_variants`; action constraints/rule; the supplied `agent_name`, `setting_domain` and assigned template/action metadata.
- `risk_flags` (zero or more values **only** from the controlled vocabulary below) plus exactly one free-text `risk_notes` string explaining *specific* issues; use an empty string and `[]` if no issue is detected. Do not invent new flag names.

**Controlled `risk_flags` vocabulary:**

`agent_prior_knowledge_risk`, `source_acceptance_ambiguity`, `source_vs_belief_ambiguity`, `action_ambiguity`, `q2_copy_shortcut`, `q2_non_tom_difficulty`, `overconstrained_story`, `unnatural_redundancy`, `q3_answer_leakage`, `world_fact_scope_risk`, `template_task_mismatch`, `near_duplicate_structure`, `implicit_belief_leakage`.

Assign flags only when a **concrete** risk is present. The absence of flags is not validation. If `status` is `needs_revision`, briefly provide `failure_reason` and relevant flags. **Never output `validated`, `approved`, or `human_gold_confirmed`.** All intended Q1/Q2/Q3 answers remain provisional.

The selected `agent_name` and `setting_domain` are **inputs**, not creative choices. Do not substitute “Emma” or another familiar name out of habit. Avoid stereotypical connections between a name and a role, occupation, competence or nationality.
