# Generator Guideline — World Knowledge × Agent Belief ToM Items

**Version:** 1.1 (pilot candidate-generation specification)  
> **How to use this document:** **Part A** is the instruction specification for the candidate-generating LLM. **Part B** is for the researcher, Claude Code/Codex, and the calling Python pipeline; **do not attach Part B to every generation API request.** The script should select only Part A plus the relevant task-mode section and the current locked fact/bundle. Supply a strict JSON Schema separately. The worked example in Part B must **not** be included in routine generation prompts.

---

# Part A — Model-facing generation instructions

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
| **T4C** | Established Routines | Agent repeatedly observes a practice → may generalize → acts independently elsewhere; distinguish a local filing/routine convention from a general-world belief. The claim span must still restate the locked claim itself; do not replace it with an indirect description of what the practice implies. |
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

**Story style:** aim for **70–110 words**; **110 is a hard upper limit** (see A8). Use idiomatic adult English and a believable task. Prefer carefully framed questions over unnatural lists of exceptions. Avoid repetitive disclaimers, formulaic “takes notes”, strong unconditional trust, and staged action explanations. Do not introduce the answer through an earlier identical action.

**Q3 answer-leakage rule:** In a **conflicting** story, do not inadvertently reveal the true answer in independent narrator/background text, preliminary drafts, diagrams, labels, corrections, or irrelevant details. Keep the intended source claim as specified. If the locked `conflicting_claim` itself contains the real answer (or its synonym), **flag** the risk; do not silently rewrite the knowledge record. For **aligned** stories, the true source claim necessarily reveals the actual fact by design; this is **inherent condition-specific availability**, not something that can be removed while retaining aligned. Mark the limitation for later interpretation rather than falsely claiming aligned Q3 isolates retained parametric knowledge.

**Q3 Leakage Prevention**

- Prefer false claims stated positively, without mentioning the true answer as a rejected alternative.
- Avoid phrases such as "instead of X" or "rather than X" when X is the real answer.
- If a locked claim contains the real answer, flag it for researcher review. Do not rewrite it.
- Unavoidable exposure in comparative claims should be flagged, not silently removed.

Q3 should ask about reality without reproducing an explanatory true answer in the question. Q1–Q3 use short-answer generation, not multiple-choice. Design answers as a number, word, or short phrase, allowing harmless synonyms/units. Do not expose gold or explanations to the **evaluated** LLM.

## A7. Renderable story contract and output metadata

For `generate_family`, provide:

- **Exactly one** `story_backbone` with one `{{CLAIM_SPAN}}` and one `{{BELIEF_INSERTION}}` (the latter directly after the source-encounter sentence).
- `claim_span_aligned`, `claim_span_conflicting`, both fitting the **same** surrounding grammar and faithfully representing the locked claims. Each span must **restate the locked claim itself** (same content and qualifiers, same wording as far as the grammar allows); never substitute an indirect or behavioural paraphrase (e.g. a routine or marking that merely implies the fact), in any template.
- `belief_proposition_aligned`, `belief_proposition_conflicting` for code to insert with the **fixed explicit template**.
- One shared `belief_question`, `action_question`, `reality_question` for all four versions.
- `proposed_gold` for aligned/conflicting Q1/Q2 and fixed Q3; `answer_variants`; action constraints/rule; the supplied `agent_name`, `setting_domain` and assigned template/action metadata.
- `risk_flags` (zero or more values **only** from the controlled vocabulary below) plus exactly one free-text `risk_notes` string explaining *specific* issues; use an empty string and `[]` if no issue is detected. Do not invent new flag names.

**Controlled `risk_flags` vocabulary:**

`agent_prior_knowledge_risk`, `source_acceptance_ambiguity`, `source_vs_belief_ambiguity`, `action_ambiguity`, `q2_copy_shortcut`, `q2_non_tom_difficulty`, `overconstrained_story`, `unnatural_redundancy`, `q3_answer_leakage`, `world_fact_scope_risk`, `template_task_mismatch`, `near_duplicate_structure`, `implicit_belief_leakage`.

Assign flags only when a **concrete** risk is present. The absence of flags is not validation. If `status` is `needs_revision`, briefly provide `failure_reason` and relevant flags. **Never output `validated`, `approved`, or `human_gold_confirmed`.** All intended Q1/Q2/Q3 answers remain provisional.

The selected `agent_name` and `setting_domain` are **inputs**, not creative choices. Do not substitute “Emma” or another familiar name out of habit. Avoid stereotypical connections between a name and a role, occupation, competence or nationality.

## A8. Naturalness and open-response actions

**Open response, not a hidden menu.** Q2 must have an open answer space: the agent writes, sets, schedules, labels, books, buys or builds something, and the answer is the value she produces. Never list the candidate actions, objects or values anywhere in the story (e.g., "Two controls are available: …", "The trays are 20 cm and 21 cm"). The two condition-specific golds are known to you, not shown to the reader. If the action can only be made determinate by enumerating options, choose a different task or return `needs_revision`.

**No rule puzzles.** Do not add instructions, if–then procedures or decision rules whose purpose is to force the answer ("preserve X if …; otherwise …"). The agent's ordinary goal should make the action obvious to a typical reader who knows what the agent believes.

**Qualifications constrain you, not the story.** The fact record's qualification notes tell you what must not become false or misleading; they do not need to be narrated. Add a condition to the story only if, without it, a typical adult reader would actually give a different Q2 answer. Do not narrate technical caveats (e.g., "exactly", "with no phase change or competing forces", "both are wide enough", "modeling ordinary physics").

**Put residual caution in metadata.** If an ambiguity remains that could only be removed by adding a technical clause, keep the story natural and describe the ambiguity in `risk_notes` with the matching flag. Human reviewers will decide. A natural story with a flagged risk is preferred over an over-specified story.

**Style and length.** Write like a few sentences from a realistic everyday or workplace anecdote, not a physics exam item, lab protocol or legal clause. Hard limit: 110 words for the backbone including the claim span. If over the limit, cut constraints and background first.

---

# Part B — Pipeline and coding specification (NOT sent to the generator each time)

## B1. Inputs, ownership and deterministic sampling

The program—not the model—owns: locked facts and Q0; per-family IDs; `agent_name`; `setting_domain` (and optionally `setting_label`); template and action-type quotas; schema validation; rendered four-condition stories; request exports; logs and experimental scoring. **Do not duplicate these instructions in each generator API prompt.**

### Fixed pool of 20 English given names

**Implementation note:** when designing the code, to make story generation more convenient and to keep the story's pronouns natural and consistent with the character's name, each name is deliberately bound to its group, and the group fixes the pronoun set the caller passes to the generator (masculine group → he/him; feminine group → she/her). This binding is a purely technical convenience for readable stories. It is **not** intended to tie names to gender stereotypes in any way: these are **name-sampling groups only**, not claims about any person's gender identity, knowledge or behavior. Use them as typical traditionally masculine/feminine names for the pilot; nothing about competence, profession, role, nationality or culture should depend on the group.

| Traditionally masculine (10) | Traditionally feminine (10) |
|---|---|
| James | Olivia |
| Oliver | Amelia |
| Daniel | Sophia |
| Henry | Charlotte |
| Thomas | Grace |
| Lucas | Hannah |
| Ethan | Lily |
| Noah | Ava |
| Benjamin | Ella |
| Jack | Mia |

**Required sampling behavior:** Assign `agent_name` **in code**, before `generate_family`. Shuffle with a recorded seed or use balanced sampling without replacement across a batch, then reshuffle/recycle once exhausted. Strive for approximately equal name-group usage across the corpus; do **not** use name-gender stereotypes in scenario design. Keep the assigned name identical in all four conditions of a family. Record `agent_name`, `name_pool_group`, `name_sampling_seed` (or run-level seed) for auditability. Randomization is at the **family** level, never separately for the four paired versions.

### Caller-assigned settings

The caller also chooses a `setting_domain` using **fact–task compatibility**, **not** unconstrained LLM invention. Suggested controlled domains (extend only by a versioned code change):

`education_training`, `museum_exhibition`, `community_volunteering`, `workplace_operations`, `arts_media`, `hobbies_games`, `environment_weather`, `travel_cultural_orientation`, `events_planning`, `technical_workshop`.

Optional `setting_label` can pin down a specific place/activity (e.g. `community music studio`) if the caller needs stricter control. Otherwise the generator may choose a **specific natural setting within the assigned domain**. Keep it unchanged across all four conditions. If assigned `setting_domain` is incompatible with the knowledge/action bundle, return `needs_revision` or `no_valid_bundle` rather than secretly switch domain. Maintain an allocation log for template × action × reasoning structure × setting-domain coverage; balancing is subordinate to validity.

`propose_bundles` may be given a domain constraint or allowed-domain list; `generate_family` must receive a **single fixed** `agent_name`, `setting_domain`, `template_id` and selected bundle. The code should allocate names and domains *after* bundle feasibility is evaluated, or reassign a domain before generation if compatibility screening fails.

## B2. Minimal-pair rendering: code owns the explicit sentence

Given the unchanged `story_backbone`, render the four stories by deterministic substitution, never by four independent LLM rewrites:

```text
implicit_aligned     := backbone[CLAIM_SPAN := claim_span_aligned; BELIEF_INSERTION := empty]
implicit_conflicting := backbone[CLAIM_SPAN := claim_span_conflicting; BELIEF_INSERTION := empty]
explicit_aligned     := backbone[CLAIM_SPAN := claim_span_aligned; BELIEF_INSERTION :=
                        " " + agent_name + " believes that " + belief_proposition_aligned + "."]
explicit_conflicting := backbone[CLAIM_SPAN := claim_span_conflicting; BELIEF_INSERTION :=
                        " " + agent_name + " believes that " + belief_proposition_conflicting + "."]
```

Check exactly one occurrence of each backbone placeholder, proper sentence boundaries, no remaining tokens, fixed question text, proper statement capitalization, and no other string changes. Use the **original** backbone for every rendering. Keep optional whitespace normalization narrowly defined. Validate that propositions are clause complements (no leading “that” and no final period). Explicit condition always adds precisely one sentence.

**Migration from v1.0:** Replace `belief_sentence_aligned` / `belief_sentence_conflicting` in the generator schema with `belief_proposition_aligned` / `belief_proposition_conflicting`; move final sentence assembly into Python. If older candidates have full explicit sentences, preserve their original data and migrate in a separate versioned conversion rather than silently overwrite. The explicit change affects only the two explicit variants; implicit stories remain unaffected.

## B3. Controlled flags and schemas

Both `propose_bundles` and `generate_family` use:

```json
{
  "risk_flags": ["source_acceptance_ambiguity"],
  "risk_notes": "The agent may already know the correct fact despite consulting the guide."
}
```

This block shows the **two field shapes**, not a complete generation record. The complete worked record appears in B5.

- `risk_flags`: array of distinct enums from **A7**, `[]` when absent.
- `risk_notes`: a single free-text string; describe which part of the candidate causes each flagged risk and why. Use `""` if there are no flags; don't produce a long generic cautionary essay.
- Eliminate the old open-ended `risk_flags` labels and redundant `potential_ambiguities` from new schemas. If code has existing `potential_ambiguities`, migrate its content into `risk_notes` before dropping it from new records, and **preserve historical raw outputs**.
- Status: `candidates_proposed` / `no_valid_bundle` for bundle proposals, `candidate_generated` / `needs_revision` for families. `validation_status` is `needs_human_review` for generated candidates, never model-awarded approval.
- Use Structured Outputs or schema validation where supported; **schema-conforming JSON is not semantic validation**. Enforce cross-field gold logic, name/domain equality, risk enums and placeholder rendering with Python tests. A strict schema must enumerate fields, require appropriate keys and disallow extra properties; represent unavailable values with `null` as needed.

## B4. Separate deterministic and semantic QA

**Code checks:** fact ID and locked claims; implicit story length (more than 110 words is **rejected and regenerated**, fewer than 70 only warns); regex flags for hidden-menu / rule-puzzle / technical-caveat wording in the story (e.g. “exactly”, “single-function”, “available:”, “either … or”, “two options”, “otherwise”); claim spans that do not restate the locked claim (**rejected and regenerated**);  exact placeholder counts; four-condition invariants; fixed agent/setting; gold differences; consistent Q1–Q3 wording; allowed name/domain/flag enums; no unexpected added explicit words; answer normalization; no inadvertent narrator assertion of the world fact in **conflicting** variants; duplication tracking. Scan `world_gold`, `pretest_accepted_answers` and manually curated equivalents against the rendered story **including claim spans**; distinguish (a) appearance due to aligned source claim, (b) appearance inside locked conflicting source claim, (c) appearance elsewhere as accidental Q3 leakage. A simple substring match is a **review trigger**, not proof of leakage. Negation, units and paraphrases require semantic review.

**Semantic review:** agent's prior knowledge may undermine implicit gold; source exposure is not proof of belief; Q2 must be distinctly belief-dependent and reasonably predictable; no hidden rules; no excessive unnatural caveats; no forced action based on merely following a local convention. A potential failure should be flagged or rejected for review, not hidden by more elaborate writing. Q0 results belong to the later evaluation process, **not** candidate generation. A model's ability to answer Q0 does not establish the **character's** prior knowledge.

**Important Q3 interpretation:** With aligned source information, the true answer is necessarily present in the story. Do **not** claim that aligned-condition Q3 independently isolates retained parametric knowledge; focus any such retention inference on conditions without independent true-answer leakage, cross-referenced to story-free Q0. Preserve all versions and leakage flags in analysis metadata.

**Prompt separation and caching:** In routine API calls pass **Part A (or a tested compact extraction of Part A)** plus only the current mode's relevant instructions, strict output schema, and one fact/selected bundle. Put stable instructions ahead of changing fact/name/domain inputs for better cache reuse; log prompt version and model settings. **Do not send the Part B implementation notes (Sections B1–B6) or the worked example (B5) as generator prose. The B1–B6 *belief cues* in Part A, however, remain required.**

**Exports:** Q0: exactly one story-free pretest per `fact_id` per evaluated model, drawn from the knowledge pool. Q1–Q3: one independent fresh evaluation request per `(family_id, condition, question_type)` containing that story plus that question, **without** answer keys. Store proposed/validated gold separately, attach validation status, provenance, generator version and run-level allocation seed. Do not expose internal risk notes or target answers to the evaluated model.

## B5. Complete worked example — NOT part of the experimental pool or API prompt

This **illustrative fact is deliberately outside `knowledge_pool.jsonl`**. Its ID uses the nonproduction prefix `DEMO_` so it cannot accidentally enter a production dataset. It uses a **real general piano-layout fact only to demonstrate output contracts**; it is **not** being added to the study's world-knowledge pool. It has no human gold validation. Source for the illustrative convention: Baylor University's *Piano Basics*, “Orientation to the Keyboard” (higher notes on the right).

**Locked demonstration input:**

```json
{
  "fact_id": "DEMO_PIANO",
  "world_fact": "On a standard piano keyboard, the higher notes are toward the right.",
  "aligned_claim": "The higher notes on a standard piano keyboard are toward the right-hand end.",
  "conflicting_claim": "The higher notes on a standard piano keyboard are toward the left-hand end.",
  "world_gold": "right",
  "conflicting_belief_gold": "left",
  "pretest_question": "Toward which end of a standard piano keyboard are the higher notes?",
  "agent_name": "Grace",
  "setting_domain": "arts_media",
  "setting_label": "community music studio",
  "template_id": "T1"
}
```

**Complete `propose_bundles` output:**

```json
{
  "task_mode": "propose_bundles",
  "fact_id": "DEMO_PIANO",
  "status": "candidates_proposed",
  "bundles": [
    {
      "bundle_id": "B01",
      "suggested_template_ids": ["T1"],
      "agent_goal": "Film a short lesson segment demonstrating the keyboard's higher notes.",
      "new_task": "Position a close-up camera to film one end of a piano keyboard.",
      "action_constraints": "The stationary camera can capture only one end of the keyboard; the lesson must show the end expected to contain higher notes.",
      "action_type": "A4",
      "reasoning_structure": "prediction_application",
      "target_output": "Which end of the keyboard Grace will film",
      "aligned_action_gold": "right",
      "conflicting_action_gold": "left",
      "belief_to_action_rule": "Grace aims the camera at the keyboard end she expects to have higher notes.",
      "risk_flags": ["agent_prior_knowledge_risk"],
      "risk_notes": "Grace might already know the direction of higher notes; the first-time studio role does not prove ignorance."
    }
  ],
  "failure_reason": null
}
```

**Complete `generate_family` output:**

```json
{
  "task_mode": "generate_family",
  "fact_id": "DEMO_PIANO",
  "bundle_id": "B01",
  "status": "candidate_generated",
  "template_id": "T1",
  "agent_name": "Grace",
  "setting_domain": "arts_media",
  "setting": "community music studio",
  "source_type": "studio teaching guide",
  "belief_cue_ids": ["B2", "B5"],
  "action_type": "A4",
  "reasoning_structure": "prediction_application",
  "story_backbone": "Grace is helping at a community music studio for the first time. Before recording a short lesson, she reads a studio guide that has helped the staff with earlier lessons. The guide says {{CLAIM_SPAN}}.{{BELIEF_INSERTION}} Later, Grace needs to film a close-up for a segment about higher piano notes. The camera can frame only one end of the keyboard, so Grace has to choose which end to record.",
  "claim_span_aligned": "that the higher notes on a standard piano keyboard are toward the right-hand end",
  "claim_span_conflicting": "that the higher notes on a standard piano keyboard are toward the left-hand end",
  "belief_proposition_aligned": "the higher notes on a standard piano keyboard are toward the right-hand end",
  "belief_proposition_conflicting": "the higher notes on a standard piano keyboard are toward the left-hand end",
  "belief_question": "At which end of the piano keyboard does Grace expect to find the higher notes?",
  "action_question": "Which end of the keyboard will Grace choose to film?",
  "reality_question": "On a standard piano keyboard, toward which end are the higher notes?",
  "proposed_gold": {
    "aligned": {"q1": "right", "q2": "right"},
    "conflicting": {"q1": "left", "q2": "left"},
    "q3": "right"
  },
  "answer_variants": {
    "q1_aligned": ["right-hand end"],
    "q1_conflicting": ["left-hand end"],
    "q2_aligned": ["right-hand end"],
    "q2_conflicting": ["left-hand end"],
    "q3": ["right-hand end"]
  },
  "action_constraints": "The camera frames only one end of the keyboard; Grace must choose the end she expects to contain higher notes.",
  "belief_to_action_rule": "Grace uses her expectation about note pitch to choose the end the camera will film.",
  "risk_flags": ["agent_prior_knowledge_risk"],
  "risk_notes": "Grace might already know the keyboard layout despite being new to the studio; conflicting implicit belief requires independent review.",
  "validation_status": "needs_human_review",
  "failure_reason": null
}
```

**Fully rendered four stories (output of code, not separate LLM generations):**

**Implicit aligned:**

> Grace is helping at a community music studio for the first time. Before recording a short lesson, she reads a studio guide that has helped the staff with earlier lessons. The guide says that the higher notes on a standard piano keyboard are toward the right-hand end. Later, Grace needs to film a close-up for a segment about higher piano notes. The camera can frame only one end of the keyboard, so Grace has to choose which end to record.

**Implicit conflicting:**

> Grace is helping at a community music studio for the first time. Before recording a short lesson, she reads a studio guide that has helped the staff with earlier lessons. The guide says that the higher notes on a standard piano keyboard are toward the left-hand end. Later, Grace needs to film a close-up for a segment about higher piano notes. The camera can frame only one end of the keyboard, so Grace has to choose which end to record.

**Explicit aligned:**

> Grace is helping at a community music studio for the first time. Before recording a short lesson, she reads a studio guide that has helped the staff with earlier lessons. The guide says that the higher notes on a standard piano keyboard are toward the right-hand end. Grace believes that the higher notes on a standard piano keyboard are toward the right-hand end. Later, Grace needs to film a close-up for a segment about higher piano notes. The camera can frame only one end of the keyboard, so Grace has to choose which end to record.

**Explicit conflicting:**

> Grace is helping at a community music studio for the first time. Before recording a short lesson, she reads a studio guide that has helped the staff with earlier lessons. The guide says that the higher notes on a standard piano keyboard are toward the left-hand end. Grace believes that the higher notes on a standard piano keyboard are toward the left-hand end. Later, Grace needs to film a close-up for a segment about higher piano notes. The camera can frame only one end of the keyboard, so Grace has to choose which end to record.

**Reference answers for the demonstration only:** Q0 = `right` (story-free); Q1 = `right` / `left`; Q2 = `right` / `left`; Q3 = `right` in all four. Q1/Q2 are intended answers requiring independent review; aligned Q3 contains the right answer in the source by design. The example is a structural illustration, **not** a quality-validated experimental item.

## B6. Versioning and rollout checklist

1. Save this file as **`generator_guideline_v1_1.md`** (do not overwrite v1.0 yet). Keep `knowledge_pool.jsonl` **unchanged**.
2. Update input contract so `generate_family` always gets a **code-assigned** `agent_name`, `setting_domain`, `template_id`, chosen bundle and locked fact. Set up 20-name sampling with a logged run seed and per-family allocation.
3. Update both mode-specific schemas and parsers: controlled `risk_flags` + `risk_notes`; no free-form extra flag names; remove/migrate `potential_ambiguities`; generate `belief_proposition_*` instead of final explicit belief sentences. Keep original candidate files intact.
4. Update deterministic story renderer and unit tests for exactly four minimal-pair variants. Add tests for fixed explicit sentence wording; no unexpected true-answer mentions in **conflicting** stories; name/domain preservation; scope qualifications; short-answer gold alignment.
5. Run **offline** sample/schema/renderer tests first. Then obtain approval before any paid API testing. Use 2–3 locked pilot facts, compare old/new candidate quality, and log all rejected or flagged cases. Do not regenerate the entire pool without a deliberate run/version change.
6. Record `prompt_version`, schema version, assigned slots and sampling seed with every family. Store evaluation prompts separately from reference answers. Keep API keys and secrets out of data, prompts and repository commits.

**Design boundary:** No-access/access-swap controls are **not** introduced by v1.1. The four main conditions, Q0–Q3 definitions, six templates and fact pool remain the current pilot design.
