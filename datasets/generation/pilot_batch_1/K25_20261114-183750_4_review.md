# 候选题审查报告：family F010（fact K25）

- **状态**：`needs_human_review`（human_validated = False；仅为自动检查结果，需人工审查）
- 模板 `T1` | action `A2` | reasoning `one_step_mapping` | belief cues ['B4', 'B6']
- 人物 Lily（名字分组 feminine） | 场景域 `community_volunteering` | 场景 A community garden's water-transfer demonstration | 来源类型 Equipment handbook
- 抽样器分配：{'index': 9, 'template_id': 'T1', 'agent_name': 'Lily', 'name_pool_group': 'feminine', 'setting_domain': 'community_volunteering', 'name_sampling_seed': 20261113, 'domain_attempt': 0} | 行动设计标签：`open_numeric`
- bundle 选择：自动选择 B01：在 1/1 个通过硬检查的 bundle 中，取 warning 最少（0 个），并列取先提出者。
- 造题模型 `gpt-6.1-sol` | guideline v1.1 | prompt_version `410d88711161…` | schema m2-1.1.0 | 2026-11-14T17:38:50+00:00

## 锁定事实（来自 knowledge pool，未被改动）
- world_fact：A properly installed, functioning standard check valve is designed to allow fluid flow in one direction and to prevent reverse flow.
- aligned_claim：A standard check valve permits fluid flow in its forward direction and prevents reverse flow.
- conflicting_claim：A standard check valve permits fluid flow in both forward and reverse directions.
- 限定说明：Assume a properly installed, functioning standard check valve under appropriate operating pressure. It permits intended forward flow when the opening-pressure conditions are met and is designed to prevent reverse flow; do not claim that all valves allow forward flow at any pressure or guarantee zero leakage.
- Q0（无故事）：In how many directions is a standard check valve designed to allow fluid flow? → `one direction`

## Bundle
- 目标：Prepare a community garden's water-transfer demonstration so volunteers can move water between two tanks in either direction.
- 新任务：After consulting an equipment handbook, enter the minimum number of additional hoses needed on the demonstration's equipment request.
- 约束：The existing setup connects two tanks through a reversible pump and a fixed standard check valve. The pump can supply adequate pressure in either direction. Existing equipment must remain installed. Spare hose fittings are accessible on either side of the valve, and suitable hoses are available. The demonstration requires water transfer in both directions, with as little additional equipment as possible.
- 目标输出：The minimum number of additional hoses requested.
- 行动 gold：aligned = `1`，conflicting = `0`
- belief→action 规则：With the aligned belief, the valve blocks one required transfer direction, so one hose connecting the fittings around it provides the missing route. With the conflicting belief, the existing line already supports both transfer directions, so no additional hose is needed.
- risk_flags：无；risk_notes：无

## 四个条件的故事

### implicit_aligned
Preparing a community garden demonstration, Lily consults an equipment handbook: A standard check valve permits fluid flow in its forward direction and prevents reverse flow. Two tanks connect through a reversible pump and a fixed standard check valve, with accessible hose fittings on either side of the valve. The pump supplies adequate pressure either way. Existing equipment must remain installed, and suitable hoses are available. Volunteers need to transfer water both ways using minimal extra equipment. Lily must enter the number of additional hoses on an equipment request.

### implicit_conflicting
Preparing a community garden demonstration, Lily consults an equipment handbook: A standard check valve permits fluid flow in both forward and reverse directions. Two tanks connect through a reversible pump and a fixed standard check valve, with accessible hose fittings on either side of the valve. The pump supplies adequate pressure either way. Existing equipment must remain installed, and suitable hoses are available. Volunteers need to transfer water both ways using minimal extra equipment. Lily must enter the number of additional hoses on an equipment request.

### explicit_aligned
Preparing a community garden demonstration, Lily consults an equipment handbook: A standard check valve permits fluid flow in its forward direction and prevents reverse flow. Lily believes that a standard check valve permits fluid flow in its forward direction and prevents reverse flow. Two tanks connect through a reversible pump and a fixed standard check valve, with accessible hose fittings on either side of the valve. The pump supplies adequate pressure either way. Existing equipment must remain installed, and suitable hoses are available. Volunteers need to transfer water both ways using minimal extra equipment. Lily must enter the number of additional hoses on an equipment request.

### explicit_conflicting
Preparing a community garden demonstration, Lily consults an equipment handbook: A standard check valve permits fluid flow in both forward and reverse directions. Lily believes that a standard check valve permits fluid flow in both forward and reverse directions. Two tanks connect through a reversible pump and a fixed standard check valve, with accessible hose fittings on either side of the valve. The pump supplies adequate pressure either way. Existing equipment must remain installed, and suitable hoses are available. Volunteers need to transfer water both ways using minimal extra equipment. Lily must enter the number of additional hoses on an equipment request.

## 解释句素材（代码按固定句式拼出 `<name> believes that <proposition>.`）
- aligned：a standard check valve permits fluid flow in its forward direction and prevents reverse flow
- conflicting：a standard check valve permits fluid flow in both forward and reverse directions

## 问题（四个版本完全相同）
- **Q1（信念）**：In how many directions does Lily believe a standard check valve permits fluid flow?
- **Q2（行动）**：What number of additional hoses will Lily enter on the equipment request?
- **Q3（现实）**：In reality, in how many directions is a properly installed, functioning standard check valve designed to allow fluid flow?

## 候选 gold（provisional，待人工确认）
| | aligned | conflicting |
|---|---|---|
| Q1 | one direction | both directions |
| Q2 | 1 | 0 |
| Q3（现实，不变） | one direction | one direction |

答案同义写法：{'q1_aligned': ['one direction', 'one', '1', 'forward only', 'one way'], 'q1_conflicting': ['both directions', 'two directions', 'two', '2', 'forward and reverse'], 'q2_aligned': ['1', 'one', 'one hose', '1 additional hose'], 'q2_conflicting': ['0', 'zero', 'none', 'no additional hoses'], 'q3': ['one direction', 'one', '1', 'one way', 'one-way', 'unidirectional', 'a single direction']}

## 生成模型自报的风险
- risk_flags：['q2_non_tom_difficulty', 'q3_answer_leakage']
- risk_notes：Q2 requires recognizing that a hose joining the fittings can bypass the valve; readers unfamiliar with plumbing may miss that application despite correctly attributing Lily's belief. In the aligned condition, the source necessarily supplies the true Q3 answer, so aligned Q3 does not isolate retained world knowledge. No independent true-answer cue is added to the conflicting story.

## Q3 答案泄漏扫描（命中只是复核触发条件，不等于泄漏）
无命中。

## 自动检查结果
无 error / warning。
