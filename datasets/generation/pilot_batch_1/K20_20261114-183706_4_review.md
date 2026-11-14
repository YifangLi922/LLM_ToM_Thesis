# 候选题审查报告：family F009（fact K20）

- **状态**：`needs_human_review`（human_validated = False；仅为自动检查结果，需人工审查）
- 模板 `T2` | action `A1` | reasoning `one_step_mapping` | belief cues ['B2', 'B4']
- 人物 Mia（名字分组 feminine） | 场景域 `workplace_operations` | 场景 An optical inspection station at a factory | 来源类型 Spoken instruction from an optics technician
- 抽样器分配：{'index': 8, 'template_id': 'T2', 'agent_name': 'Mia', 'name_pool_group': 'feminine', 'setting_domain': 'workplace_operations', 'name_sampling_seed': 20261113, 'domain_attempt': 0} | 行动设计标签：`open_other`
- bundle 选择：自动选择 B01：在 1/1 个通过硬检查的 bundle 中，取 warning 最少（0 个），并列取先提出者。
- 造题模型 `gpt-6.1-sol` | guideline v1.1 | prompt_version `410d88711161…` | schema m2-1.1.0 | 2026-11-14T17:37:47+00:00

## 锁定事实（来自 knowledge pool，未被改动）
- world_fact：When white light passes through an ordinary glass prism under normal dispersion, violet light is deviated more than red light.
- aligned_claim：An ordinary glass prism deviates violet light more than red light.
- conflicting_claim：An ordinary glass prism deviates red light more than violet light.
- 限定说明：Assume an ordinary glass prism displaying normal dispersion of visible light. Deviation means angular deviation from the incoming direction; do not infer a fixed up/down or left/right orientation without specifying the prism geometry.
- Q0（无故事）：Which visible color of light is generally deviated the most when white light passes through an ordinary glass prism? → `violet`

## Bundle
- 目标：Prepare a prism-based optical inspection station so its detectors receive their intended colors.
- 新任务：After an optics technician explains prism dispersion during training, the agent drafts the mounting layout for a red-light detector relative to an already positioned violet-light detector.
- 约束：The station projects its spectrum horizontally onto a detector rail. The straight-through reference position for the incoming beam lies to the left of the entire spectrum. The violet-light detector's mounting position is already marked. The agent must annotate which side of that mark should hold the red-light detector. The station has not yet been illuminated, and no numerical mounting distance is requested.
- 目标输出：The side of the violet detector's mark on which the agent places the red detector in the layout.
- 行动 gold：aligned = `Left of the violet detector.`，conflicting = `Right of the violet detector.`
- belief→action 规则：With the incoming beam's reference position to the left, greater deviation corresponds to a position farther right. Believing violet is deviated more places red to violet's left; believing red is deviated more places red to violet's right.
- risk_flags：['agent_prior_knowledge_risk']；risk_notes：Prism color ordering is familiar school science, so an adult agent might retain the correct ordering despite conflicting testimony. A first-time station operator receiving instruction from a relevant optics technician makes reliance plausible but does not eliminate this risk.

## 四个条件的故事

### implicit_aligned
Mia is setting up her first optical inspection station at a factory. An optics technician explains that an ordinary glass prism deviates violet light more than red light. Later, she sketches the detector layout before the station is illuminated. The spectrum will fall horizontally along a rail, with the incoming beam's straight-through reference position to the left of the entire spectrum. The violet-light detector's position is already marked. Mia must annotate where the red-light detector belongs relative to that mark so each detector receives its intended color.

### implicit_conflicting
Mia is setting up her first optical inspection station at a factory. An optics technician explains that an ordinary glass prism deviates red light more than violet light. Later, she sketches the detector layout before the station is illuminated. The spectrum will fall horizontally along a rail, with the incoming beam's straight-through reference position to the left of the entire spectrum. The violet-light detector's position is already marked. Mia must annotate where the red-light detector belongs relative to that mark so each detector receives its intended color.

### explicit_aligned
Mia is setting up her first optical inspection station at a factory. An optics technician explains that an ordinary glass prism deviates violet light more than red light. Mia believes that an ordinary glass prism deviates violet light more than red light. Later, she sketches the detector layout before the station is illuminated. The spectrum will fall horizontally along a rail, with the incoming beam's straight-through reference position to the left of the entire spectrum. The violet-light detector's position is already marked. Mia must annotate where the red-light detector belongs relative to that mark so each detector receives its intended color.

### explicit_conflicting
Mia is setting up her first optical inspection station at a factory. An optics technician explains that an ordinary glass prism deviates red light more than violet light. Mia believes that an ordinary glass prism deviates red light more than violet light. Later, she sketches the detector layout before the station is illuminated. The spectrum will fall horizontally along a rail, with the incoming beam's straight-through reference position to the left of the entire spectrum. The violet-light detector's position is already marked. Mia must annotate where the red-light detector belongs relative to that mark so each detector receives its intended color.

## 解释句素材（代码按固定句式拼出 `<name> believes that <proposition>.`）
- aligned：an ordinary glass prism deviates violet light more than red light
- conflicting：an ordinary glass prism deviates red light more than violet light

## 问题（四个版本完全相同）
- **Q1（信念）**：Which color does Mia believe an ordinary glass prism deviates more, red or violet?
- **Q2（行动）**：On which side of the marked violet-light detector position will Mia place the red-light detector in her layout?
- **Q3（现实）**：In reality, which visible color is generally deviated the most when white light passes through an ordinary glass prism?

## 候选 gold（provisional，待人工确认）
| | aligned | conflicting |
|---|---|---|
| Q1 | violet | red |
| Q2 | Left of the violet detector. | Right of the violet detector. |
| Q3（现实，不变） | violet | violet |

答案同义写法：{'q1_aligned': ['violet', 'violet light'], 'q1_conflicting': ['red', 'red light'], 'q2_aligned': ['left', "to the left of the violet-light detector's mark", 'Left of the violet detector.'], 'q2_conflicting': ['right', "to the right of the violet-light detector's mark", 'Right of the violet detector.'], 'q3': ['violet', 'violet light', 'violet-colored light']}

## 生成模型自报的风险
- risk_flags：['agent_prior_knowledge_risk', 'q3_answer_leakage']
- risk_notes：Prism color ordering is familiar school science, so Mia might retain the correct ordering despite conflicting testimony. First-time setup and instruction from a relevant optics technician make reliance plausible but do not eliminate that risk. In the aligned condition, the source claim supplies the Q3 answer by design, so aligned Q3 does not isolate retained world knowledge.

## Q3 答案泄漏扫描（命中只是复核触发条件，不等于泄漏）
- `violet` → aligned_source_claim（claim_span_aligned）
- `violet light` → aligned_source_claim（claim_span_aligned）
- `violet` → conflicting_source_claim（claim_span_conflicting）
- `violet light` → conflicting_source_claim（claim_span_conflicting）
- `violet` → elsewhere（story_shared_text）
- `violet` → elsewhere（belief_question）
- `violet` → elsewhere（action_question）

## 自动检查结果
- **warning** `question_has_alternatives`：belief_question 含 'or'，可能在提供备选项（应为开放式简答）
- **warning** `gold_in_backbone`：Q1 aligned 的答案 'violet' 出现在 claim/belief 以外的公共文字里，可能泄漏答案
- **warning** `gold_in_backbone`：Q1 conflicting 的答案 'red' 出现在 claim/belief 以外的公共文字里，可能泄漏答案
- **warning** `q3_answer_in_conflicting_claim`：真实答案 'violet' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
- **warning** `q3_answer_in_conflicting_claim`：真实答案 'violet light' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
- **warning** `q3_answer_leakage_review`：真实答案 'violet' 出现在 story_shared_text（claim 以外），可能是意外泄漏，需人工复核（子串命中不等于泄漏）
- **warning** `q3_answer_leakage_review`：真实答案 'violet' 出现在 belief_question（claim 以外），可能是意外泄漏，需人工复核（子串命中不等于泄漏）
- **warning** `q3_answer_leakage_review`：真实答案 'violet' 出现在 action_question（claim 以外），可能是意外泄漏，需人工复核（子串命中不等于泄漏）
