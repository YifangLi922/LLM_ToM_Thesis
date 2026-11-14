# 候选题审查报告：family F002（fact K14）

- **状态**：`needs_human_review`（human_validated = False；仅为自动检查结果，需人工审查）
- 模板 `T4C` | action `A5` | reasoning `targeted_revision` | belief cues ['B4']
- 人物 Henry（名字分组 masculine） | 场景域 `hobbies_games` | 场景 A stop-motion animation hobby club | 来源类型 Repeated observation of an experienced wildlife animator's rehearsal routine and its spoken explanation
- 抽样器分配：{'index': 1, 'template_id': 'T4C', 'agent_name': 'Henry', 'name_pool_group': 'masculine', 'setting_domain': 'hobbies_games', 'name_sampling_seed': 20261113, 'domain_attempt': 0} | 行动设计标签：`inherently_binary`
- bundle 选择：自动选择 B01：在 1/1 个通过硬检查的 bundle 中，取 warning 最少（1 个），并列取先提出者。
- 造题模型 `gpt-6.1-sol` | guideline v1.1 | prompt_version `410d88711161…` | schema m2-1.1.0 | 2026-11-14T17:34:25+00:00

## 锁定事实（来自 knowledge pool，未被改动）
- world_fact：Dolphins breathe air using lungs, not gills.
- aligned_claim：Dolphins breathe air using lungs.
- conflicting_claim：Dolphins breathe underwater using gills.
- 限定说明：Dolphins are air-breathing mammals; surface access is needed. Avoid story settings implying they can safely breathe indefinitely underwater.
- Q0（无故事）：What organs do dolphins use to breathe air? → `lungs`

## Bundle
- 目标：Make a biologically realistic stop-motion dolphin animation while preserving as much of the existing storyboard as possible.
- 新任务：Revise a breathing beat in the agent's own underwater adventure storyboard. The current beat shows a fully submerged dolphin taking a fresh breath.
- 约束：The dolphin is an ordinary real-world animal, not a fantasy creature. The storyboard explicitly depicts taking a fresh breath rather than merely swimming underwater. The agent is reviewing only this breathing beat and wants the smallest necessary change for biological realism.
- 目标输出：The single storyboard change, if any, the agent makes to the breathing beat.
- 行动 gold：aligned = `Show the dolphin surfacing to take the breath.`，conflicting = `No change.`
- belief→action 规则：Believing dolphins breathe air using lungs makes the fully submerged fresh breath an error, so the agent changes that beat to show surfacing. Believing dolphins breathe underwater using gills makes the existing beat acceptable, so the minimal revision is no change.
- risk_flags：['agent_prior_knowledge_risk', 'source_acceptance_ambiguity']；risk_notes：Dolphin air-breathing is familiar knowledge, so the conflicting implicit belief may be difficult to establish. For T4C, use repeated observation of an experienced hobby-club animator rehearsing dolphin breathing scenes, with the locked claim stated as the explanation of that recurring practice. Even with a natural-history focus, observing the routine does not establish that the agent accepts its biological explanation rather than treating it as an animation convention.

## 四个条件的故事

### implicit_aligned
At his stop-motion club, Henry regularly watches an experienced wildlife animator rehearse dolphin breathing scenes for biological realism. The animator explains the recurring routine this way: Dolphins breathe air using lungs. Later, Henry reviews a breathing beat in his own underwater adventure storyboard. It shows an ordinary dolphin staying fully submerged while taking a fresh breath. He wants the animation to be biologically realistic while preserving as much of the storyboard as possible, and is reviewing only this beat.

### implicit_conflicting
At his stop-motion club, Henry regularly watches an experienced wildlife animator rehearse dolphin breathing scenes for biological realism. The animator explains the recurring routine this way: Dolphins breathe underwater using gills. Later, Henry reviews a breathing beat in his own underwater adventure storyboard. It shows an ordinary dolphin staying fully submerged while taking a fresh breath. He wants the animation to be biologically realistic while preserving as much of the storyboard as possible, and is reviewing only this beat.

### explicit_aligned
At his stop-motion club, Henry regularly watches an experienced wildlife animator rehearse dolphin breathing scenes for biological realism. The animator explains the recurring routine this way: Dolphins breathe air using lungs. Henry believes that dolphins breathe air using lungs. Later, Henry reviews a breathing beat in his own underwater adventure storyboard. It shows an ordinary dolphin staying fully submerged while taking a fresh breath. He wants the animation to be biologically realistic while preserving as much of the storyboard as possible, and is reviewing only this beat.

### explicit_conflicting
At his stop-motion club, Henry regularly watches an experienced wildlife animator rehearse dolphin breathing scenes for biological realism. The animator explains the recurring routine this way: Dolphins breathe underwater using gills. Henry believes that dolphins breathe underwater using gills. Later, Henry reviews a breathing beat in his own underwater adventure storyboard. It shows an ordinary dolphin staying fully submerged while taking a fresh breath. He wants the animation to be biologically realistic while preserving as much of the storyboard as possible, and is reviewing only this beat.

## 解释句素材（代码按固定句式拼出 `<name> believes that <proposition>.`）
- aligned：dolphins breathe air using lungs
- conflicting：dolphins breathe underwater using gills

## 问题（四个版本完全相同）
- **Q1（信念）**：What breathing organs does Henry believe dolphins use?
- **Q2（行动）**：What change, if any, will Henry make to the breathing beat?
- **Q3（现实）**：What organs do dolphins actually use to breathe air?

## 候选 gold（provisional，待人工确认）
| | aligned | conflicting |
|---|---|---|
| Q1 | lungs | gills |
| Q2 | Show the dolphin surfacing to take the breath. | No change. |
| Q3（现实，不变） | lungs | lungs |

答案同义写法：{'q1_aligned': ['lungs', 'Lungs'], 'q1_conflicting': ['gills', 'Gills'], 'q2_aligned': ['Show the dolphin surfacing to breathe.', 'Have the dolphin come to the surface for the breath.', 'Move the breathing moment to the surface.'], 'q2_conflicting': ['No change.', 'Leave the breathing beat as it is.', 'Keep the dolphin submerged while it takes the breath.'], 'q3': ['lungs', 'lung']}

## 生成模型自报的风险
- risk_flags：['agent_prior_knowledge_risk', 'source_acceptance_ambiguity', 'template_task_mismatch', 'q3_answer_leakage']
- risk_notes：Dolphin air-breathing is familiar knowledge, so Henry may retain prior knowledge rather than accept the conflicting explanation. Repeated observation of an experienced animator does not guarantee acceptance of the biological claim. The observed rehearsal movements remain unspecified to keep the routine constant across conditions; consequently, belief attribution may depend more on the spoken explanation than on the established routine required by T4C. In aligned stories, the source necessarily supplies the Q3 answer, so aligned Q3 does not isolate retained world knowledge.

## Q3 答案泄漏扫描（命中只是复核触发条件，不等于泄漏）
- `lungs` → aligned_source_claim（claim_span_aligned）

## 自动检查结果
无 error / warning。
