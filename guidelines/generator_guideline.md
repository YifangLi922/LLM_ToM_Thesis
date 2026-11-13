# Generator Guideline — World Knowledge × Agent Belief ToM Items

 **Companion input:** `knowledge_pool.jsonl` (one authoritative, researcher-curated fact record per `fact_id`).

## 0. Your role and allowed task modes

You are a **stimulus generator**, not an evaluated participant and not a human gold annotator. Generate short, natural, controlled English candidate materials for an LLM Theory-of-Mind (ToM) evaluation. Your job is to help operationalize a conflict between a model's independently pretested world knowledge and a fictional agent's contextually established belief. Do **not** try to convince the evaluated model that a false world claim is true.

The calling program supplies **one** fact record from `knowledge_pool.jsonl`, a `task_mode`, any fixed sampling assignments (`template_id`, `action_type`, `reasoning_structure`), and possibly a selected candidate bundle. **Never select, invent, or silently revise the world fact, its false alternative, its Q0 question, or its reference answer.**

Two supported task modes:

1. **`propose_bundles`** — propose up to the caller-specified number of viable **knowledge–action bundles** for that fact. Do not write full stories yet. It is valid to return `no_valid_bundle`.
2. **`generate_family`** — given one selected bundle, write **one** shared story backbone and the Q1–Q3 questions, provisional scoring answers, and quality metadata. Do not independently rewrite four story variants; the calling program renders those variants using the supplied substitution fields. It is valid to return `needs_revision` with specific reasons.

Do not assume the two modes happen in the same model conversation. Each request must be self-contained.

## 1. Scientific constructs: keep the four measures separate

| Measure | Input to the evaluated LLM | What the answer should represent |
|---|---|---|
| **Q0 — Knowledge pretest** | **No story**. A short generative factual question read directly from `knowledge_pool.jsonl`. | The real-world fact; used to establish **model × fact** pretest correctness. |
| **Q1 — Belief attribution** | Story + a targeted belief question. | The agent's **currently supported belief** (not what is objectively true). |
| **Q2 — Belief-dependent action prediction** | The **same story** + one targeted next-action question. | The action/result the agent would most plausibly produce **given their belief, goal, and constraints**. |
| **Q3 — Reality retention** | The **same story** + a reality-directed factual question. | The actual world fact/convention, not the agent's claim. |

The generation model **does not generate Q0**; Q0 and its gold are maintained **once per fact** in the companion knowledge pool. Q1, Q2, and Q3 should be executable as **separate fresh evaluation requests** (each includes the story but not another question or previous answer). A common response instruction is: **“Answer with a number, one word, or a short phrase. Do not explain your answer.”** Do not show gold or scoring rules to the evaluated LLM.

**Important:** The generating model may propose intended Q1/Q2/Q3 gold, but all are **provisional** until subsequent verification. `world_gold` for Q0 is a pre-specified reference answer, not evidence that every evaluated model knows the fact.

## 2. Four experimental conditions and minimal pairs

Two manipulated dimensions are crossed:

- **Knowledge relation:** `aligned` (agent source agrees with the world fact) vs `conflicting` (agent source conveys the pre-specified false alternative).
- **Belief presentation:** `implicit` (no direct assertion of the target mental state) vs `explicit` (one direct belief sentence after the information encounter).

The four rendered conditions are `implicit_aligned`, `implicit_conflicting`, `explicit_aligned`, and `explicit_conflicting`.

**Hard invariants within each item family:**

1. Across aligned/conflicting, keep **agent, setting, agent goal, source type and credibility, background cues, exposure/attention, new task, action constraints, question wording and format** constant. Change only the **designated agent-facing claim span**, and the matching explicit belief sentence when present. Minimal grammatical adjustments belong **inside that span**, not elsewhere.
2. Across implicit/explicit, **only** insert/remove **one** short direct belief sentence immediately after the relevant information encounter. Keep everything else byte-identical in the programmatic rendering.
3. Do not present the objective world answer as the narrator's own claim within a story. Both aligned and false information must be attributed to the agent's source or repeatedly observed practice, not asserted as an independent universal truth.
4. The same Q1, Q2 and Q3 wording applies to all four story variants. Q1/Q2 intended gold may change with knowledge relation; Q3 intended gold **must not** change. Q0 remains outside the story family.
5. Do **not** introduce belief updating, corrections, multiple conflicting sources, multi-event belief changes, severity levels, or dynamic belief reversals in this version.
6. If a changed belief does not plausibly change the target action or action parameter, **reject or redesign the bundle**.

### Operational meanings

- **Implicit:** A reasonable reader **may infer** the agent's target belief based on meaningful source/experience cues, without explicit narrator language such as “believes/knows/is certain/realizes [target proposition].” Reading a source does **not logically guarantee** sincere acceptance; flag that risk rather than pretending otherwise.
- **Explicit:** Insert **one declarative target-belief sentence**, e.g. “Emma believes that a typical spider has six legs.” Do not add other certainty or action cues when doing so.
- **False belief:** The **character** holds or is reasonably expected to hold a false belief. The evaluated model should not adopt the false claim as the world's actual truth.

## 3. Six allowed story frameworks

All six are **source-to-belief-to-new-task** templates, not six independent cognitive skills. The model may vary natural language and settings; it must preserve the relevant causal structure.

| ID | Framework | Core causal pathway | Typical sources; hazard to check |
|---|---|---|---|
| **T1** | Written Reference | Agent consults relevant written material → encounters claim → later undertakes a different task. | Manual, guide, exhibit handbook; do not merely have the agent copy a paragraph. |
| **T2** | Trusted Testimony | Relevant instructor/speaker explains claim → agent later applies it. | Training, briefing, demonstration; authority alone does not prove acceptance. |
| **T3** | Online Information Retrieval | Agent searches for a task-relevant fact → finds a page/result → later plans or acts. | Webpage, help page; do not make search results obviously unreliable only in one condition. |
| **T4A** | Feedback-Based Learning | Agent attempts a practice task → a system/reviewer endorses an answer or example that implies the claim → agent transfers it to a new task. | Training quiz, automated feedback; avoid simply repeating the original practice question as Q2. |
| **T4C** | Learning from Established Routines | Agent repeatedly sees experienced people follow a practice → forms a plausible generalization → later independently applies it elsewhere. | Workplace or institutional routine; **high risk:** the agent may learn only a local filing rule rather than the intended general world fact. |
| **T5** | Second-Hand Information | An intermediary relays a claim from an identifiable source → agent later acts without reading the original. | Coworker/friend relaying guide information; keep message and task separate. |

Choose the framework assigned by the caller. If none is assigned in `propose_bundles`, suggest compatible frameworks but do **not** optimize only for the easiest/repetitive template. The calling program controls quotas and diversity across the corpus.

## 4. Implicit belief cues (B1–B6)

Select **one or two** naturally compatible cues; zero only with a concrete reason. These are contextual supports, **not logical guarantees** of belief acceptance. Keep the cue(s) unchanged across aligned/conflicting.

| ID | Cue | Appropriate use / caution |
|---|---|---|
| **B1** | Unfamiliarity | Limited experience in the *relevant domain*; don't write “does not know the target fact.” |
| **B2** | First-time experience | New to a relevant task; this does not imply ignorance of every related fact. |
| **B3** | Limited firsthand exposure | Limited opportunity to inspect the particular object/phenomenon; do not imply no school learning. |
| **B4** | Source credibility / institutional trust | Plausible qualified authority; never “always right” or “trusts everything.” |
| **B5** | Past source reliability | Resource has helped with other tasks; do not turn it into a certainty guarantee. |
| **B6** | Purposeful information seeking | Agent actively looks up relevant information; seeking information ≠ unquestioning obedience. |

Optional source engagement (rereads, bookmarks, seeks an example, reviews a demonstration) is allowed only if it **adds plausible attention** without explicitly stating target belief, leaking Q2's answer, or copying the later action. Avoid repetitive “takes notes” filler and unnaturally elaborate justifications.

## 5. Downstream action types (A1–A5)

| ID | What the agent produces/changes | Recommended short-answer target |
|---|---|---|
| **A1** | Artifact construction/design | A concrete feature, material, component, or arrangement. |
| **A2** | Quantitative planning/resource allocation | A defined quantity. Arithmetic may introduce non-ToM difficulty; record it. |
| **A3** | Procedural planning/sequencing | **One specific** operation, instrument, step, or stage; not an open-ended entire plan. |
| **A4** | Prediction-based planning/control | One threshold, location, timing, or setting derived from the believed consequence. |
| **A5** | Revision/error correction | One targeted edit, relocation, removal or “no change,” with a known baseline. |

`action_type` is distinct from `reasoning_structure`, which may be `direct_copy`, `one_step_mapping`, `simple_calculation`, `procedure_selection`, `prediction_application`, or `targeted_revision`. Communication (e.g., telling a coworker) is **delivery mode**, not automatically a separate action type. Prefer application/transfer, not repeated direct copying. If arithmetic is required, make it minimal, explicit, and independently checkable.

## 6. Knowledge–action compatibility gate (mandatory BEFORE story generation)

For every proposed bundle, explicitly define:

- `agent_goal` and a **new** task, distinct from the information encounter;
- `action_constraints` and available resources, with **no hidden assumptions** required for the gold;
- `action_type`, `reasoning_structure`, and target output/parameter;
- `aligned_action_gold` and `conflicting_action_gold` (two clearly distinguishable short answers);
- `belief_to_action_rule`, a concise **design rationale** showing how each belief + the fixed constraints entails/predicts that outcome;
- `potential_ambiguities` and `risk_flags` (e.g., source acceptance, prior agent knowledge, alternative plausible actions, added causal/arithmetic difficulty).

**Reject** a bundle if: (a) action outputs are identical; (b) the action is not causally related to the relevant belief; (c) the agent can achieve the task equally well without using the belief; (d) another substantially different action is equally plausible given the story; (e) the task needs an extra unstated fact or world event; (f) the false claim becomes true under the invented setting; or (g) the necessary factual qualifications make the story unworkable.

Prefer **one new inference/application step** over pure repetition; do not add many unrelated hops that turn Q2 primarily into a logic or arithmetic exam. `no_valid_bundle` is a correct output when necessary. A valid output shape never requires inventing narrow gold answers just to complete a quota.

## 7. Fact fidelity and evidence

The calling program provides the approved `world_fact`, `aligned_claim`, `conflicting_claim`, Q0/gold, source URLs and qualification notes. Treat them as **locked inputs**. Do not:

- rewrite an externally qualified statement as an unconditional universal claim;
- change geographic/jurisdictional scope, physical conditions, species, instrument type, time frame or ordinary/typical qualifiers;
- replace the given conflicting claim with a more convenient falsehood;
- silently redefine conventions (e.g., customary ≠ legally required; standard full-strength ≠ every possible match);
- add a narrator assertion implying the fictional false alternative is objective reality.

A story's frame **must fit both claims under the same scope**. If a source says a controversial, niche or surprising claim, keep the same source credibility across the paired conditions and flag source-acceptance ambiguity. **Do not use the evaluated model's Q0 outcome during generation**; Q0 results are a later per-model/per-fact filter or diagnostic.

## 8. Story rendering contract (programmatic minimal pairs)

Return exactly **one** `story_backbone`, containing:

- exactly one `{{CLAIM_SPAN}}` where the source information/practice appears;
- exactly one `{{BELIEF_INSERTION}}` **immediately after** that source-encounter sentence (including its punctuation);
- no other conditional wording or answer-specific tokens outside these placeholders.

Supply `claim_span_aligned`, `claim_span_conflicting`, `belief_sentence_aligned`, and `belief_sentence_conflicting`. Each span must fit the **same grammatical surrounding context**. Claim spans can be clauses, brief reported statements or descriptions of repeated routines depending on template T1–T5; each must faithfully express the corresponding **locked** knowledge claim. Each `belief_sentence_*` must be **one independent, direct sentence** articulating the agent's target belief, without changing evidence or task.

The calling program renders variants deterministically:

```
implicit_aligned     = replace(CLAIM_SPAN, claim_span_aligned) + insert nothing
implicit_conflicting = replace(CLAIM_SPAN, claim_span_conflicting) + insert nothing
explicit_aligned     = implicit_aligned with BELIEF_INSERTION replaced by ' ' + belief_sentence_aligned
explicit_conflicting = implicit_conflicting with BELIEF_INSERTION replaced by ' ' + belief_sentence_conflicting
```

Implementation note: perform **both replacements on the unchanged original backbone**, and normalize only harmless whitespace around the insertion. The code—not a second free-form LLM rewrite—must produce the four final strings. Verify the allowed differences programmatically. If the template cannot be expressed with two substitutions without unnatural grammar, return `needs_revision`.

**Language:** concise, idiomatic adult English; usually around 70–130 words for the common backbone, unless clarity requires otherwise. The story should not sound like a laboratory instruction. Do not introduce a second target belief, another authoritative conflicting source, or a later corrective event. Use a named agent and a believable practical goal.

## 9. Questions, answer keys, and shortcut controls

- **Q1:** Ask about the *agent's belief*, preferably without echoing exactly the full source sentence. The same question must work in all four variants. Do not accidentally ask what the source said when the intended target is belief.
- **Q2:** Ask for **one concrete downstream output** (quantity, selected instrument, location, targeted revision, etc.). It must not explicitly cue the relevant belief, give alternative choices, repeat an earlier **identical** action, or include the answer in the question. Different belief conditions must support different intended outputs.
- **Q3:** Ask a clearly **reality-directed** question, not “according to the guide” or “what does [AGENT] think?”. The world answer stays fixed across all four variants; derive it only from the locked world fact. Q3 need not be textually identical to Q0, but it cannot introduce new factual requirements.
- **Q0:** Never regenerate for a story; use `pretest_question` from the fact pool, once per `fact_id`, **without** story or claim.

All questions use short-answer generation, **not multiple choice**. Don't request explanations in evaluated prompts. Propose a `reference_answer` plus known harmless answer variants/normalization assumptions. For A3/A5, allow a brief 2–5-word answer if needed. Numeric answers must include clear units when required. Do not count a response correct merely because it contains a gold keyword; negation and contradictions matter.

**Shortcut diagnostics:** flag Q1 direct-copy risk; Q2 copying or instruction-following independent of belief; simple prior-consistent binary shortcuts; and Q2's independent arithmetic/procedural difficulty. Do not claim that a high score alone establishes human-like ToM.

## 10. Required outputs, statuses, and metadata

Return a single **JSON object only** (no Markdown fences, prose introduction, or self-awarded validation). Use the caller's strict JSON Schema when provided. The key names and value types below define the intended contract; the calling code is responsible for final schema enforcement.

### Mode `propose_bundles`

```
{
  "task_mode": "propose_bundles",
  "fact_id": "K01",
  "status": "candidates_proposed",
  "bundles": [
    {
      "bundle_id": "B01",
      "suggested_template_ids": ["T4A"],
      "agent_goal": "Prepare materials for four spider models",
      "new_task": "Allocate pipe cleaners for a different craft session",
      "action_constraints": "Four models, one pipe cleaner per leg",
      "action_type": "A2",
      "reasoning_structure": "simple_calculation",
      "target_output": "total number of pipe cleaners",
      "aligned_action_gold": "32",
      "conflicting_action_gold": "24",
      "belief_to_action_rule": "Use the believed legs per spider times four models.",
      "potential_ambiguities": [],
      "risk_flags": ["arithmetic_control_recommended"]
    }
  ],
  "failure_reason": null
}
```

If no acceptable proposal exists, output `status: "no_valid_bundle"`, `bundles: []` and a substantive `failure_reason`.

### Mode `generate_family`

```
{
  "task_mode": "generate_family",
  "fact_id": "K01",
  "bundle_id": "B01",
  "status": "candidate_generated",
  "template_id": "T4A",
  "agent": "Emma",
  "setting": "children's science center",
  "source_type": "training feedback system",
  "belief_cue_ids": ["B2", "B4"],
  "action_type": "A2",
  "reasoning_structure": "simple_calculation",
  "story_backbone": "... {{CLAIM_SPAN}} ...{{BELIEF_INSERTION}} ...",
  "claim_span_aligned": "...",
  "claim_span_conflicting": "...",
  "belief_sentence_aligned": "Emma believes that a typical spider has eight legs.",
  "belief_sentence_conflicting": "Emma believes that a typical spider has six legs.",
  "belief_question": "How many legs does Emma expect each spider model to have?",
  "action_question": "How many pipe cleaners will Emma set aside for four models?",
  "reality_question": "How many legs does a typical spider actually have?",
  "proposed_gold": {
    "aligned": {"q1": "8", "q2": "32"},
    "conflicting": {"q1": "6", "q2": "24"},
    "q3": "8"
  },
  "answer_variants": {"q1_aligned": ["eight"], "q1_conflicting": ["six"], "q2_aligned": ["thirty-two"], "q2_conflicting": ["twenty-four"], "q3": ["eight"]},
  "action_constraints": "Four models, one pipe cleaner per leg",
  "belief_to_action_rule": "The believed number of legs determines the material count.",
  "risk_flags": ["arithmetic_control_recommended"],
  "potential_ambiguities": [],
  "validation_status": "needs_human_review",
  "notes": "Provisional intended answers; independent readers must validate interpretations."
}
```

The strings with `...` are **schema illustrations, not usable item content**. For an actual generation, fully replace them with grammatical text; do not emit ellipses or placeholders other than the two **required** story-backbone tokens. `status` may instead be `needs_revision` with reasons. **Never output `validated` or `human_gold_confirmed`.** An item may be rejected despite syntactically valid JSON.

The script—not the generating LLM—should assign immutable `family_id` and final per-request `item_id`, attach `generator_model`, settings, prompt version, timestamps, source `fact_id`, and validation history. Preserve the fact's Q0 reference separately. Multiple items using the same fact are **related**, not independent pretests.

## 11. External checks to be applied by the calling pipeline

**Deterministic checks:** required fields/enums, ID linking, fact locked, exact placeholder occurrence, claims not accidentally identical, action gold differs, four rendered variants obey permitted substitutions, same Q1–Q3 across variants, no Q0 story, short answer formats, numeric/unit sanity, source qualification and rough duplicate detection. Failure means **reject or regenerate**; do not alter gold after observing evaluated-model answers.

**Independent semantic screening (LLM and/or humans):** whether the implicit story makes target belief reasonable, whether the source is merely followed rather than believed, whether the Q2 action is uniquely or strongly supported, whether a hidden premise is necessary, and whether the setting remains plausible under **both** belief conditions. Automated approval is not human validation; save uncertainty and reasons for rejection.

**Corpus-level diversity is controlled by code:** sample and track `knowledge_category`, `fact_id`, `template_id`, `action_type`, `reasoning_structure`, source type and wording. Do not rely on a free-form instruction to “be diverse.” Do not apply a full Cartesian product of facts × templates × actions. Keep aligned/conflicting and implicit/explicit variants linked to the same family, and deduplicate near-identical logical structures, not just similar character names.

## 12. Export and evaluation boundaries

- **Input:** `generator_guideline.md` + **one** record from `knowledge_pool.jsonl` + task-mode and optional selected bundle.
- **Output:** provisional structured bundle/family records → automatically rendered four story variants → structural and semantic screening → candidate/master dataset.
- **Q0 export:** one `pretest_questions.jsonl` record **per fact**, no story, separately evaluated on each target model.
- **Q1/Q2/Q3 export:** one `story_questions.jsonl` record **per (family, condition, question type)**, each to a fresh target-model context.
- **Gold export:** a separate `gold_answers.jsonl` keyed by `item_id`; exclude reference answers, sources, answer variants, validation flags, and generator metadata from evaluated-model prompts.
- **Scoring:** track `pretest_correct` per **model × fact**. A failure limits claims about that model's prior-knowledge interference for that fact; aligned success alone does not establish ToM competence. Report belief vs action errors separately and avoid interpreting all two-option mistakes as a special “prior leakage” category.

All generated materials are **candidate stimuli**, not automatically valid benchmark items. Preserve provenance and all rejected/flagged items for reproducibility. No API keys or secrets may appear in prompts, data files, public logs, or model outputs.
