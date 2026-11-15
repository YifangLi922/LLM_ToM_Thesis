# Pilot 错误分析

> 自动归因只是**启发式**，类别后缀 `_candidate` 表示“可能是”；无法确定的都标为 `needs_manual_review` / `scoring_ambiguity`，没有强行归类。完整的模型原始回答、reference、评分结果见 `item_level_scores.csv`，完整 API 响应见 `raw_responses.jsonl`。

## 类别说明

| 类别 | 含义 |
|---|---|
| `reality_intrusion_candidate` | 现实干扰（候选）：conflicting 题里，Q1 答成了真实世界的答案而不是角色的信念；或 Q1 答对、Q2 却做了符合现实的行动 |
| `belief_attribution_error_candidate` | 信念归因错误（候选）：aligned 题 Q1 答成了错误信念；或 Q1/Q2 同时出错且不属于上一类 |
| `non_tom_reasoning_error_candidate` | 非 ToM 推理错误（候选）：Q1 答对，Q2 给出的具体数值/日期/坐标不属于任何 gold（可能是计算、映射、格式问题） |
| `q3_false_claim_adopted` | Q3 把故事里的错误主张当成了现实 |
| `q0_knowledge_error` | Q0（无故事）就答错：知识缺口，或评分歧义 |
| `scoring_ambiguity` | 评分歧义：裁判认为“两者都像”或“无法判断”，待人工复核 |
| `needs_manual_review` | 答案不匹配任何 gold，原因无法确定，待人工复核 |
| `request_failed` | 请求失败（没有可评分的回答） |

## 1. 各配置错误数量（按类别）

| 配置 | 总错误/待复核 | `reality_intrusion_candidate` | `belief_attribution_error_candidate` | `non_tom_reasoning_error_candidate` | `q3_false_claim_adopted` | `q0_knowledge_error` | `scoring_ambiguity` | `needs_manual_review` | `request_failed` |
|---|---|---|---|---|---|---|---|---|---|
| qwen3-32b__non_thinking | 32/156 | 12 | 1 | 3 | 4 | 0 | 7 | 5 | 0 |
| qwen3-32b__thinking | 12/156 | 6 | 1 | 0 | 0 | 1 | 3 | 1 | 0 |
| glm-4.5-air__non_thinking | 28/156 | 12 | 3 | 1 | 1 | 1 | 8 | 2 | 0 |
| glm-4.5-air__thinking | 11/156 | 7 | 2 | 0 | 0 | 1 | 1 | 0 | 0 |

## 2. Q1 正确但 Q2 错误（Application Gap 的来源）

同一配置、同一家族、同一条件下，Q1 评为正确而 Q2 评为错误/待复核。

共 35 条。

| 配置 | 家族/条件 | Q2 模型回答 | Q2 reference | 另一条件答案 | 类别 | 说明 |
|---|---|---|---|---|---|---|
| glm-4.5-air__non_thinking | F002 conf/expl (K14) | Surface | Breathing while fully submerged. | Surfacing to breathe air. | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| glm-4.5-air__non_thinking | F004 conf/expl (K23) | %RH | °C | % | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| glm-4.5-air__non_thinking | F007 conf/expl (K06) | Remove | No change; retain the bell-ringing sound effect. | Remove the bell-ringing sound effect. | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| glm-4.5-air__non_thinking | F008 alig/expl (K18) | Increase | Zoom out. | Zoom in. | `needs_manual_review` | aligned 题的 Q2 做了 conflicting 的行动，原因不明 |
| glm-4.5-air__non_thinking | F010 conf/expl (K25) | Yes | No | Yes | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| glm-4.5-air__non_thinking | F010 conf/impl (K25) | Yes | No | Yes | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| glm-4.5-air__non_thinking | F011 alig/expl (K09) | Left | West | East | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| glm-4.5-air__non_thinking | F011 alig/impl (K09) | left | West | East | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| glm-4.5-air__non_thinking | F011 conf/expl (K09) | Left | East | West | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| glm-4.5-air__non_thinking | F012 conf/expl (K27) | h1 | a8 | h8 | `non_tom_reasoning_error_candidate` | Q1 答对，Q2 给出了一个不属于任何 gold 的具体数值/日期/坐标：可能是计算/映射错误 |
| glm-4.5-air__non_thinking | F012 conf/impl (K27) | h8 | a8 | h8 | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| glm-4.5-air__thinking | F002 conf/expl (K14) | surfacing | Breathing while fully submerged. | Surfacing to breathe air. | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| glm-4.5-air__thinking | F006 conf/impl (K15) | CO2 | Oxygen sensor | Carbon dioxide sensor | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| glm-4.5-air__thinking | F007 conf/expl (K06) | remove | No change; retain the bell-ringing sound effect. | Remove the bell-ringing sound effect. | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| qwen3-32b__non_thinking | F002 conf/expl (K14) | Incorrectly | Breathing while fully submerged. | Surfacing to breathe air. | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| qwen3-32b__non_thinking | F002 conf/impl (K14) | incorrectly, with lungs, not gills | Breathing while fully submerged. | Surfacing to breathe air. | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| qwen3-32b__non_thinking | F003 alig/expl (K28) | 30 September | 2 October | 8 November | `non_tom_reasoning_error_candidate` | Q1 答对，Q2 给出了一个不属于任何 gold 的具体数值/日期/坐标：可能是计算/映射错误 |
| qwen3-32b__non_thinking | F003 conf/expl (K28) | 9 November | 8 November | 2 October | `non_tom_reasoning_error_candidate` | Q1 答对，Q2 给出了一个不属于任何 gold 的具体数值/日期/坐标：可能是计算/映射错误 |
| qwen3-32b__non_thinking | F004 conf/expl (K23) | °F or °C (depending on regional convention) | °C | % | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| qwen3-32b__non_thinking | F007 conf/expl (K06) | remove it | No change; retain the bell-ringing sound effect. | Remove the bell-ringing sound effect. | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| qwen3-32b__non_thinking | F008 conf/expl (K18) | Zoom out | Zoom in. | Zoom out. | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| qwen3-32b__non_thinking | F008 conf/impl (K18) | Zoom out | Zoom in. | Zoom out. | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| qwen3-32b__non_thinking | F009 alig/expl (K20) | further from the undeviated beam than | Closer to the undeviated beam than the violet detector. | Farther from the undeviated beam than the violet detector. | `needs_manual_review` | aligned 题的 Q2 做了 conflicting 的行动，原因不明 |
| qwen3-32b__non_thinking | F009 alig/impl (K20) | farther from the undeviated beam | Closer to the undeviated beam than the violet detector. | Farther from the undeviated beam than the violet detector. | `needs_manual_review` | aligned 题的 Q2 做了 conflicting 的行动，原因不明 |
| qwen3-32b__non_thinking | F010 conf/expl (K25) | Yes | No | Yes | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| qwen3-32b__non_thinking | F011 alig/expl (K09) | left | West | East | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| qwen3-32b__non_thinking | F011 alig/impl (K09) | Left | West | East | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| qwen3-32b__non_thinking | F011 conf/impl (K09) | left side | East | West | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| qwen3-32b__non_thinking | F012 conf/expl (K27) | b8 | a8 | h8 | `non_tom_reasoning_error_candidate` | Q1 答对，Q2 给出了一个不属于任何 gold 的具体数值/日期/坐标：可能是计算/映射错误 |
| qwen3-32b__thinking | F002 alig/expl (K14) | blowhole | Surfacing to breathe air. | Breathing while fully submerged. | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| qwen3-32b__thinking | F002 conf/expl (K14) | blowhole | Breathing while fully submerged. | Surfacing to breathe air. | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| qwen3-32b__thinking | F002 conf/impl (K14) | surface to breathe | Breathing while fully submerged. | Surfacing to breathe air. | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| qwen3-32b__thinking | F006 conf/expl (K15) | carbon dioxide sensor | Oxygen sensor | Carbon dioxide sensor | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| qwen3-32b__thinking | F006 conf/impl (K15) | carbon dioxide sensor | Oxygen sensor | Carbon dioxide sensor | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| qwen3-32b__thinking | F007 conf/expl (K06) | remove | No change; retain the bell-ringing sound effect. | Remove the bell-ringing sound effect. | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |

## 3. 全部错误与待复核题目（按配置）

### qwen3-32b__non_thinking（32 条）

| item | 模型回答 | reference | 评分方式 | 类别 | 说明 |
|---|---|---|---|---|---|
| F001_implicit_aligned_Q1 | plant kingdom | fungi | rule | `belief_attribution_error_candidate` | aligned 题的 Q1 答成了 conflicting 的信念 |
| F002_explicit_conflicting_Q2 | Incorrectly | Breathing while fully submerged. | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F002_implicit_conflicting_Q2 | incorrectly, with lungs, not gills | Breathing while fully submerged. | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F003_implicit_conflicting_Q1 | 10 November | 9 November | llm_judge/neither | `needs_manual_review` | Q1 答案不匹配任何 gold，可能是信念归因错误或措辞差异 |
| F003_explicit_aligned_Q2 | 30 September | 2 October | llm_judge/neither | `non_tom_reasoning_error_candidate` | Q1 答对，Q2 给出了一个不属于任何 gold 的具体数值/日期/坐标：可能是计算/映射错误 |
| F003_explicit_conflicting_Q2 | 9 November | 8 November | llm_judge/neither | `non_tom_reasoning_error_candidate` | Q1 答对，Q2 给出了一个不属于任何 gold 的具体数值/日期/坐标：可能是计算/映射错误 |
| F003_implicit_conflicting_Q2 | 10 November | 8 November | llm_judge/neither | `needs_manual_review` | Q2 答案不匹配任何 gold |
| F003_explicit_conflicting_Q3 | 9 November | 3 October | rule | `q3_false_claim_adopted` | 把故事里的错误主张当成了现实（该模型 Q0 答对，说明是故事干扰） |
| F003_implicit_conflicting_Q3 | 9 November | 3 October | rule | `q3_false_claim_adopted` | 把故事里的错误主张当成了现实（该模型 Q0 答对，说明是故事干扰） |
| F004_implicit_conflicting_Q1 | Humidity | temperature | rule | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F004_explicit_conflicting_Q2 | °F or °C (depending on regional convention) | °C | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F005_implicit_conflicting_Q3 | September | April | rule | `q3_false_claim_adopted` | 把故事里的错误主张当成了现实（该模型 Q0 答对，说明是故事干扰） |
| F007_implicit_conflicting_Q1 | Sophia believes it is not possible. | can travel | llm_judge/matches_alternative | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F007_explicit_conflicting_Q2 | remove it | No change; retain the bell-ringing sound effect. | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F007_implicit_conflicting_Q2 | Remove it. | No change; retain the bell-ringing sound effect. | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 已是现实干扰，Q2 延续 |
| F008_explicit_conflicting_Q2 | Zoom out | Zoom in. | rule | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F008_implicit_conflicting_Q2 | Zoom out | Zoom in. | rule | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F008_implicit_conflicting_Q3 | contracts | expands | rule | `q3_false_claim_adopted` | 把故事里的错误主张当成了现实（该模型 Q0 答对，说明是故事干扰） |
| F009_explicit_conflicting_Q1 | violet | red | rule | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F009_explicit_aligned_Q2 | further from the undeviated beam than | Closer to the undeviated beam than the violet detector. | llm_judge/matches_alternative | `needs_manual_review` | aligned 题的 Q2 做了 conflicting 的行动，原因不明 |
| F009_implicit_aligned_Q2 | farther from the undeviated beam | Closer to the undeviated beam than the violet detector. | llm_judge/matches_alternative | `needs_manual_review` | aligned 题的 Q2 做了 conflicting 的行动，原因不明 |
| F010_implicit_conflicting_Q1 | One direction | both directions | rule | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F010_explicit_conflicting_Q2 | Yes | No | rule | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F010_implicit_conflicting_Q2 | Yes | No | rule | `reality_intrusion_candidate` | Q1 已是现实干扰，Q2 延续 |
| F011_explicit_conflicting_Q1 | Left | right | rule | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F011_explicit_aligned_Q2 | left | West | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F011_implicit_aligned_Q2 | Left | West | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F011_explicit_conflicting_Q2 | left side | East | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F011_implicit_conflicting_Q2 | left side | East | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F012_implicit_conflicting_Q1 | Diagonally | horizontally or vertically | rule | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F012_explicit_conflicting_Q2 | b8 | a8 | llm_judge/neither | `non_tom_reasoning_error_candidate` | Q1 答对，Q2 给出了一个不属于任何 gold 的具体数值/日期/坐标：可能是计算/映射错误 |
| F012_implicit_conflicting_Q2 | b8 | a8 | llm_judge/neither | `needs_manual_review` | Q2 答案不匹配任何 gold |

### qwen3-32b__thinking（12 条）

| item | 模型回答 | reference | 评分方式 | 类别 | 说明 |
|---|---|---|---|---|---|
| K14_Q0 | blowhole | lungs | llm_judge/neither | `q0_knowledge_error` | 答案不匹配任何 gold（可能是知识缺口或评分歧义） |
| F002_explicit_aligned_Q2 | blowhole | Surfacing to breathe air. | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F002_explicit_conflicting_Q2 | blowhole | Breathing while fully submerged. | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F002_implicit_conflicting_Q2 | surface to breathe | Breathing while fully submerged. | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F002_explicit_conflicting_Q3 | blowhole | lungs | llm_judge/neither | `needs_manual_review` | Q3 答案不匹配任何 gold |
| F006_explicit_conflicting_Q2 | carbon dioxide sensor | Oxygen sensor | rule | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F006_implicit_conflicting_Q2 | carbon dioxide sensor | Oxygen sensor | rule | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F007_implicit_conflicting_Q1 | Sound cannot propagate in a vacuum. | can travel | llm_judge/matches_alternative | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F007_explicit_conflicting_Q2 | remove | No change; retain the bell-ringing sound effect. | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F007_implicit_conflicting_Q2 | remove the bell-ringing sound effect | No change; retain the bell-ringing sound effect. | rule | `reality_intrusion_candidate` | Q1 已是现实干扰，Q2 延续 |
| F012_implicit_conflicting_Q1 | vertically | horizontally or vertically | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F012_implicit_conflicting_Q2 | h8 | a8 | rule | `belief_attribution_error_candidate` | Q1 也错（非现实干扰类），Q2 的错误可能由信念归因错误传递 |

### glm-4.5-air__non_thinking（28 条）

| item | 模型回答 | reference | 评分方式 | 类别 | 说明 |
|---|---|---|---|---|---|
| K14_Q0 | Blowhole | lungs | llm_judge/neither | `q0_knowledge_error` | 答案不匹配任何 gold（可能是知识缺口或评分歧义） |
| K06_Q0 | Nothing. | cannot travel | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F001_implicit_aligned_Q1 | plant kingdom | fungi | rule | `belief_attribution_error_candidate` | aligned 题的 Q1 答成了 conflicting 的信念 |
| F002_implicit_aligned_Q1 | gills | lungs | rule | `belief_attribution_error_candidate` | aligned 题的 Q1 答成了 conflicting 的信念 |
| F002_implicit_conflicting_Q1 | Lungs | gills | rule | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F002_explicit_conflicting_Q2 | Surface | Breathing while fully submerged. | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F002_implicit_conflicting_Q2 | Surface | Breathing while fully submerged. | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 已是现实干扰，Q2 延续 |
| F003_implicit_aligned_Q1 | October 2nd | 3 October | llm_judge/neither | `needs_manual_review` | Q1 答案不匹配任何 gold，可能是信念归因错误或措辞差异 |
| F003_implicit_conflicting_Q1 | October 3rd | 9 November | rule | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F004_implicit_conflicting_Q1 | Humidity | temperature | rule | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F004_explicit_conflicting_Q2 | %RH | °C | rule | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F004_implicit_conflicting_Q2 | %RH | °C | rule | `reality_intrusion_candidate` | Q1 已是现实干扰，Q2 延续 |
| F007_explicit_aligned_Q1 | None | cannot travel | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F007_implicit_aligned_Q1 | None | cannot travel | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F007_implicit_conflicting_Q1 | Nothing | can travel | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F007_explicit_conflicting_Q2 | Remove | No change; retain the bell-ringing sound effect. | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F007_implicit_conflicting_Q2 | remove | No change; retain the bell-ringing sound effect. | llm_judge/matches_alternative | `belief_attribution_error_candidate` | Q1 也错（非现实干扰类），Q2 的错误可能由信念归因错误传递 |
| F008_explicit_aligned_Q2 | Increase | Zoom out. | llm_judge/matches_alternative | `needs_manual_review` | aligned 题的 Q2 做了 conflicting 的行动，原因不明 |
| F008_implicit_conflicting_Q3 | contracts | expands | rule | `q3_false_claim_adopted` | 把故事里的错误主张当成了现实（该模型 Q0 答对，说明是故事干扰） |
| F010_explicit_conflicting_Q2 | Yes | No | rule | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F010_implicit_conflicting_Q2 | Yes | No | rule | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F011_implicit_conflicting_Q1 | left | right | rule | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F011_explicit_aligned_Q2 | Left | West | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F011_implicit_aligned_Q2 | left | West | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F011_explicit_conflicting_Q2 | Left | East | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F011_implicit_conflicting_Q2 | left | East | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F012_explicit_conflicting_Q2 | h1 | a8 | llm_judge/neither | `non_tom_reasoning_error_candidate` | Q1 答对，Q2 给出了一个不属于任何 gold 的具体数值/日期/坐标：可能是计算/映射错误 |
| F012_implicit_conflicting_Q2 | h8 | a8 | rule | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |

### glm-4.5-air__thinking（11 条）

| item | 模型回答 | reference | 评分方式 | 类别 | 说明 |
|---|---|---|---|---|---|
| K14_Q0 | Blowhole | lungs | llm_judge/neither | `q0_knowledge_error` | 答案不匹配任何 gold（可能是知识缺口或评分歧义） |
| F001_implicit_aligned_Q1 | plant kingdom | fungi | rule | `belief_attribution_error_candidate` | aligned 题的 Q1 答成了 conflicting 的信念 |
| F002_implicit_aligned_Q1 | gills | lungs | rule | `belief_attribution_error_candidate` | aligned 题的 Q1 答成了 conflicting 的信念 |
| F002_implicit_conflicting_Q1 | lungs | gills | rule | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F002_explicit_conflicting_Q2 | surfacing | Breathing while fully submerged. | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F002_implicit_conflicting_Q2 | surfacing | Breathing while fully submerged. | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 已是现实干扰，Q2 延续 |
| F003_implicit_conflicting_Q1 | 9 | 9 November | llm_judge/unclear | `scoring_ambiguity` | 裁判认为两者都像/无法判断，或无裁判结果；待人工复核 |
| F006_implicit_conflicting_Q2 | CO2 | Oxygen sensor | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F007_implicit_conflicting_Q1 | cannot propagate | can travel | llm_judge/matches_alternative | `reality_intrusion_candidate` | conflicting 题的 Q1 答成了 aligned 的答案（现实/真实知识），而不是角色的信念 |
| F007_explicit_conflicting_Q2 | remove | No change; retain the bell-ringing sound effect. | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |
| F007_implicit_conflicting_Q2 | remove | No change; retain the bell-ringing sound effect. | llm_judge/matches_alternative | `reality_intrusion_candidate` | Q1 已是现实干扰，Q2 延续 |

## 4. 评分说明与已知的评分歧义来源

- 评分方式统计：{'rule': 505, 'llm_judge': 119}。`rule` = 规则评分；`llm_judge` = 规则无法确定后由 LLM 裁判（只比较语义，不判断事实）；`rule_undecided` = 未调用裁判。
- 待人工复核（pending）共 19 条，**不计入正确**；这些条目已在上面的表里标出。
- 由裁判判定的有 119 条，其中判为 neither 的 12 条（记为错误）；建议抽查这部分。
