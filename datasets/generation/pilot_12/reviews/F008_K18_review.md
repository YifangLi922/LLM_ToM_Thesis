# 候选题审查报告：family F008（fact K18）

- **状态**：`needs_human_review`（human_validated = False；仅为自动检查结果，需人工审查）
- 模板 `T4C` | action `A4` | reasoning `prediction_application` | belief cues ['B4']
- 人物 Ella（名字分组 feminine） | 场景域 `museum_exhibition` | 场景 A science museum's live thermal-demonstration exhibit | 来源类型 Repeated preparator routines accompanied by a written setup card
- 抽样器分配：{'index': 7, 'template_id': 'T4C', 'agent_name': 'Ella', 'name_pool_group': 'feminine', 'setting_domain': 'museum_exhibition', 'name_sampling_seed': 20261113, 'domain_attempt': 0} | 行动设计标签：`open_other`
- bundle 选择：自动选择 B01：在 1/1 个通过硬检查的 bundle 中，取 warning 最少（0 个），并列取先提出者。
- 造题模型 `gpt-6.1-sol` | guideline v1.1 | prompt_version `410d88711161…` | schema m2-1.1.0 | 2026-11-14T17:37:03+00:00

## 锁定事实（来自 knowledge pool，未被改动）
- world_fact：An unconstrained ordinary iron rod generally gets longer when heated moderately.
- aligned_claim：An unconstrained iron rod generally expands in length when heated moderately.
- conflicting_claim：An unconstrained iron rod generally contracts in length when heated moderately.
- 限定说明：Exclude phase change, mechanical constraints, exceptional temperature ranges and competing forces.
- Q0（无故事）：What generally happens to the length of an unconstrained ordinary iron rod when heated moderately? → `expands`

## Bundle
- 目标：Keep the full length of a heated iron rod tightly framed in a museum exhibit's live camera view.
- 新任务：During exhibition rehearsals, the agent repeatedly observes preparators reposition anticipated-end markers before warming loose iron rods. Their setup card states the locked claim, and the agent's role ends before heating begins. Later, independently preparing a different exhibit's camera, the agent sets its zoom for filming a rod after moderate heating.
- 约束：The ordinary iron rod rests loosely on an open support. Before heating, its full length just fits the camera image horizontally. The camera position stays fixed, and the agent must preset the zoom so the warmed rod will remain fully visible with similarly tight framing.
- 目标输出：The direction of the camera's zoom adjustment from its current setting.
- 行动 gold：aligned = `Zoom out.`，conflicting = `Zoom in.`
- belief→action 规则：An expected increase in rod length requires a wider camera view and therefore zooming out; an expected decrease requires a narrower view and therefore zooming in to maintain tight framing.
- risk_flags：['agent_prior_knowledge_risk', 'source_vs_belief_ambiguity']；risk_notes：Thermal expansion is familiar enough that an adult agent might reject the contraction claim despite observing the preparators' routine. Because the observed marker placements are anticipatory rather than measured outcomes, readers might also attribute them to an exhibition convention rather than infer the agent's general physical belief; the setup card must explicitly carry the locked claim.

## 四个条件的故事

### implicit_aligned
During several museum rehearsals, Ella watches preparators reposition anticipated-end markers for loose iron rods before warming them. Her shift ends before heating begins. Their setup card states: An unconstrained iron rod generally expands in length when heated moderately. Later, preparing another exhibit alone, she frames a loose iron rod resting on an open support. Its full length just fits the camera image horizontally. Keeping the camera in place, she must preset its zoom for filming after moderate heating, with the full rod still tightly framed.

### implicit_conflicting
During several museum rehearsals, Ella watches preparators reposition anticipated-end markers for loose iron rods before warming them. Her shift ends before heating begins. Their setup card states: An unconstrained iron rod generally contracts in length when heated moderately. Later, preparing another exhibit alone, she frames a loose iron rod resting on an open support. Its full length just fits the camera image horizontally. Keeping the camera in place, she must preset its zoom for filming after moderate heating, with the full rod still tightly framed.

### explicit_aligned
During several museum rehearsals, Ella watches preparators reposition anticipated-end markers for loose iron rods before warming them. Her shift ends before heating begins. Their setup card states: An unconstrained iron rod generally expands in length when heated moderately. Ella believes that an unconstrained iron rod generally expands in length when heated moderately. Later, preparing another exhibit alone, she frames a loose iron rod resting on an open support. Its full length just fits the camera image horizontally. Keeping the camera in place, she must preset its zoom for filming after moderate heating, with the full rod still tightly framed.

### explicit_conflicting
During several museum rehearsals, Ella watches preparators reposition anticipated-end markers for loose iron rods before warming them. Her shift ends before heating begins. Their setup card states: An unconstrained iron rod generally contracts in length when heated moderately. Ella believes that an unconstrained iron rod generally contracts in length when heated moderately. Later, preparing another exhibit alone, she frames a loose iron rod resting on an open support. Its full length just fits the camera image horizontally. Keeping the camera in place, she must preset its zoom for filming after moderate heating, with the full rod still tightly framed.

## 解释句素材（代码按固定句式拼出 `<name> believes that <proposition>.`）
- aligned：an unconstrained iron rod generally expands in length when heated moderately
- conflicting：an unconstrained iron rod generally contracts in length when heated moderately

## 问题（四个版本完全相同）
- **Q1（信念）**：What does Ella believe generally happens to an unconstrained iron rod's length when it is heated moderately?
- **Q2（行动）**：How will Ella adjust the camera's zoom from its current setting to keep the heated rod tightly framed?
- **Q3（现实）**：In reality, what generally happens to the length of an unconstrained ordinary iron rod when heated moderately?

## 候选 gold（provisional，待人工确认）
| | aligned | conflicting |
|---|---|---|
| Q1 | expands in length | contracts in length |
| Q2 | Zoom out. | Zoom in. |
| Q3（现实，不变） | expands | expands |

答案同义写法：{'q1_aligned': ['gets longer', 'lengthens', 'expands'], 'q1_conflicting': ['gets shorter', 'shortens', 'contracts'], 'q2_aligned': ['Zoom out', "Widen the camera's field of view", 'Decrease the zoom'], 'q2_conflicting': ['Zoom in', "Narrow the camera's field of view", 'Increase the zoom'], 'q3': ['gets longer', 'increases', 'lengthens', 'expands in length']}

## 生成模型自报的风险
- risk_flags：['agent_prior_knowledge_risk', 'source_vs_belief_ambiguity', 'q3_answer_leakage']
- risk_notes：Thermal expansion is familiar enough that Ella might reject the contraction claim despite the preparators' apparent expertise. The anticipatory marker routine could be interpreted as a local exhibition convention rather than evidence of Ella's general physical belief, although the setup card explicitly states the target claim. In aligned stories, the source necessarily supplies the true Q3 answer, so aligned Q3 does not isolate retained world knowledge; no independent true-answer cue is included in the conflicting story.

## Q3 答案泄漏扫描（命中只是复核触发条件，不等于泄漏）
- `expands` → aligned_source_claim（claim_span_aligned）
- `expands in length` → aligned_source_claim（claim_span_aligned）

## 自动检查结果
无 error / warning。
