# 候选题审查报告：family F011（fact K09）

- **状态**：`needs_human_review`（human_validated = False；仅为自动检查结果，需人工审查）
- 模板 `T4A` | action `A1` | reasoning `one_step_mapping` | belief cues ['B2', 'B4']
- 人物 Noah（名字分组 masculine） | 场景域 `education_training` | 场景 A teacher-training geography workshop | 来源类型 Written instructor feedback on a practice quiz
- 抽样器分配：{'index': 10, 'template_id': 'T4A', 'agent_name': 'Noah', 'name_pool_group': 'masculine', 'setting_domain': 'education_training', 'name_sampling_seed': 20261113, 'domain_attempt': 0} | 行动设计标签：`open_other`
- bundle 选择：自动选择 B01：在 2/2 个通过硬检查的 bundle 中，取 warning 最少（0 个），并列取先提出者。
- 造题模型 `gpt-6.1-sol` | guideline v1.1 | prompt_version `410d88711161…` | schema m2-1.1.0 | 2026-11-14T17:39:35+00:00

## 锁定事实（来自 knowledge pool，未被改动）
- world_fact：Road traffic in the United Kingdom normally keeps to the left, subject to signs and exceptions.
- aligned_claim：Traffic in the United Kingdom normally keeps to the left.
- conflicting_claim：Traffic in the United Kingdom normally keeps to the right.
- 限定说明：Use ordinary road travel, not exceptional maneuvers, junctions or contrary signs; avoid dangerous real-time navigation tasks.
- Q0（无故事）：Which side of the road does traffic normally keep to in the United Kingdom? → `left`

## Bundle
- 目标：Create an accurate overhead road illustration for a classroom geography worksheet about the United Kingdom.
- 新任务：After receiving instructor feedback on a traffic-conventions practice exercise, place a northbound vehicle symbol on a newly drawn road.
- 约束：The worksheet shows an ordinary straight two-way road in the United Kingdom, running vertically with north at the top. A vehicle symbol pointing north is ready to be placed in the middle of its appropriate lane. The illustration has no special traffic arrangements.
- 目标输出：The compass side of the road's center line where the agent places the northbound vehicle.
- 行动 gold：aligned = `West`，conflicting = `East`
- belief→action 规则：For a northbound vehicle, the driver's left corresponds to west on the page and the driver's right corresponds to east. Applying the respective traffic-side belief therefore determines the placement.
- risk_flags：['agent_prior_knowledge_risk', 'source_acceptance_ambiguity']；risk_notes：The UK traffic convention is widely known, so an agent may reject conflicting practice feedback despite limited experience making geography materials. Apparently authoritative instructor feedback supports, but does not establish, acceptance in the implicit condition.

## 四个条件的故事

### implicit_aligned
At a teacher-training geography workshop, Noah is preparing his first classroom worksheet about the United Kingdom. He completes a practice quiz on national traffic conventions. His geography instructor returns it with this feedback: Traffic in the United Kingdom normally keeps to the left. For the worksheet, Noah then draws an ordinary straight two-way UK road running vertically, with north at the top. To make the illustration accurate, he places a northbound vehicle symbol in the middle of its appropriate lane.

### implicit_conflicting
At a teacher-training geography workshop, Noah is preparing his first classroom worksheet about the United Kingdom. He completes a practice quiz on national traffic conventions. His geography instructor returns it with this feedback: Traffic in the United Kingdom normally keeps to the right. For the worksheet, Noah then draws an ordinary straight two-way UK road running vertically, with north at the top. To make the illustration accurate, he places a northbound vehicle symbol in the middle of its appropriate lane.

### explicit_aligned
At a teacher-training geography workshop, Noah is preparing his first classroom worksheet about the United Kingdom. He completes a practice quiz on national traffic conventions. His geography instructor returns it with this feedback: Traffic in the United Kingdom normally keeps to the left. Noah believes that traffic in the United Kingdom normally keeps to the left. For the worksheet, Noah then draws an ordinary straight two-way UK road running vertically, with north at the top. To make the illustration accurate, he places a northbound vehicle symbol in the middle of its appropriate lane.

### explicit_conflicting
At a teacher-training geography workshop, Noah is preparing his first classroom worksheet about the United Kingdom. He completes a practice quiz on national traffic conventions. His geography instructor returns it with this feedback: Traffic in the United Kingdom normally keeps to the right. Noah believes that traffic in the United Kingdom normally keeps to the right. For the worksheet, Noah then draws an ordinary straight two-way UK road running vertically, with north at the top. To make the illustration accurate, he places a northbound vehicle symbol in the middle of its appropriate lane.

## 解释句素材（代码按固定句式拼出 `<name> believes that <proposition>.`）
- aligned：traffic in the United Kingdom normally keeps to the left
- conflicting：traffic in the United Kingdom normally keeps to the right

## 问题（四个版本完全相同）
- **Q1（信念）**：Which side of the road does Noah believe traffic normally keeps to in the United Kingdom?
- **Q2（行动）**：On which compass side of the road's center line will Noah place the northbound vehicle symbol?
- **Q3（现实）**：Which side of the road does traffic normally keep to in the United Kingdom?

## 候选 gold（provisional，待人工确认）
| | aligned | conflicting |
|---|---|---|
| Q1 | left | right |
| Q2 | West | East |
| Q3（现实，不变） | left | left |

答案同义写法：{'q1_aligned': ['left', 'the left', 'left side'], 'q1_conflicting': ['right', 'the right', 'right side'], 'q2_aligned': ['west', 'west side', 'west of the center line'], 'q2_conflicting': ['east', 'east side', 'east of the center line'], 'q3': ['left', 'left side', 'the left']}

## 生成模型自报的风险
- risk_flags：['agent_prior_knowledge_risk', 'source_acceptance_ambiguity', 'q3_answer_leakage']
- risk_notes：The UK traffic convention is widely known, so Noah may already know it despite making his first worksheet. Instructor feedback makes acceptance plausible but does not establish acceptance of the conflicting claim in the implicit condition. The aligned source necessarily supplies the actual Q3 answer, so aligned Q3 does not isolate retained world knowledge; the conflicting story contains no independent disclosure of that answer.

## Q3 答案泄漏扫描（命中只是复核触发条件，不等于泄漏）
- `left` → aligned_source_claim（claim_span_aligned）
- `the left` → aligned_source_claim（claim_span_aligned）

## 自动检查结果
无 error / warning。
