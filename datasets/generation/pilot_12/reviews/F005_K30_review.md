# 候选题审查报告：family F005（fact K30）

- **状态**：`needs_human_review`（human_validated = False；仅为自动检查结果，需人工审查）
- 模板 `T3` | action `A4` | reasoning `simple_calculation` | belief cues ['B4', 'B6']
- 人物 Daniel（名字分组 masculine） | 场景域 `events_planning` | 场景 Volunteer coordination for a Japanese public elementary school's annual welcome event | 来源类型 An education agency's online school-calendar guide
- 抽样器分配：{'index': 4, 'template_id': 'T3', 'agent_name': 'Daniel', 'name_pool_group': 'masculine', 'setting_domain': 'events_planning', 'name_sampling_seed': 20261113, 'domain_attempt': 0} | 行动设计标签：`open_other`
- bundle 选择：自动选择 B01：在 2/2 个通过硬检查的 bundle 中，取 warning 最少（1 个），并列取先提出者。
- 造题模型 `gpt-6.1-sol` | guideline v1.1 | prompt_version `410d88711161…` | schema m2-1.1.0 | 2026-11-14T17:04:34+00:00

## 锁定事实（来自 knowledge pool，未被改动）
- world_fact：In Japan, the ordinary public elementary-school year generally begins in April and ends in March of the following year.
- aligned_claim：In Japan, the public elementary-school year generally begins in April.
- conflicting_claim：In Japan, the public elementary-school year generally begins in September.
- 限定说明：Refers to the standard public elementary-school calendar, not atypical international schools or individual class terms.
- Q0（无故事）：In what month does the ordinary public elementary-school year begin in Japan? → `April`

## Bundle
- 目标：Arrange a volunteer briefing before a Japanese public elementary school's annual welcome event.
- 新任务：After researching Japan's public elementary-school calendar online, enter the month for a volunteer briefing in an event-booking request.
- 约束：The welcome event takes place during the opening month of the school year. Volunteers need their briefing one calendar month before the welcome event. The booking request requires a month, not a specific date.
- 目标输出：The month entered for the volunteer briefing.
- 行动 gold：aligned = `March`，conflicting = `August`
- belief→action 规则：An April school-year start places the briefing in March; a September start places it in August.
- risk_flags：['q3_answer_leakage']；risk_notes：The aligned online claim necessarily supplies April, making the actual Q3 answer available in that condition. This is inherent aligned-condition availability; the conflicting task constraints do not independently disclose the true starting month.

## 四个条件的故事

### implicit_aligned
Daniel is arranging volunteers for a Japanese public elementary school's annual welcome event. He searches online for the school calendar and opens an education agency's guide. It states: In Japan, the public elementary-school year generally begins in April. The welcome event falls in the school year's opening month, and volunteers need a briefing one calendar month beforehand. Daniel is filling out a booking request that asks for the briefing month, not a date.

### implicit_conflicting
Daniel is arranging volunteers for a Japanese public elementary school's annual welcome event. He searches online for the school calendar and opens an education agency's guide. It states: In Japan, the public elementary-school year generally begins in September. The welcome event falls in the school year's opening month, and volunteers need a briefing one calendar month beforehand. Daniel is filling out a booking request that asks for the briefing month, not a date.

### explicit_aligned
Daniel is arranging volunteers for a Japanese public elementary school's annual welcome event. He searches online for the school calendar and opens an education agency's guide. It states: In Japan, the public elementary-school year generally begins in April. Daniel believes that the public elementary-school year in Japan generally begins in April. The welcome event falls in the school year's opening month, and volunteers need a briefing one calendar month beforehand. Daniel is filling out a booking request that asks for the briefing month, not a date.

### explicit_conflicting
Daniel is arranging volunteers for a Japanese public elementary school's annual welcome event. He searches online for the school calendar and opens an education agency's guide. It states: In Japan, the public elementary-school year generally begins in September. Daniel believes that the public elementary-school year in Japan generally begins in September. The welcome event falls in the school year's opening month, and volunteers need a briefing one calendar month beforehand. Daniel is filling out a booking request that asks for the briefing month, not a date.

## 解释句素材（代码按固定句式拼出 `<name> believes that <proposition>.`）
- aligned：the public elementary-school year in Japan generally begins in April
- conflicting：the public elementary-school year in Japan generally begins in September

## 问题（四个版本完全相同）
- **Q1（信念）**：In which month does Daniel believe the public elementary-school year in Japan generally begins?
- **Q2（行动）**：Which month will Daniel enter for the volunteer briefing in the booking request?
- **Q3（现实）**：In what month does the ordinary public elementary-school year actually begin in Japan?

## 候选 gold（provisional，待人工确认）
| | aligned | conflicting |
|---|---|---|
| Q1 | April | September |
| Q2 | March | August |
| Q3（现实，不变） | April | April |

答案同义写法：{'q1_aligned': ['April', 'Apr', 'the month of April'], 'q1_conflicting': ['September', 'Sep', 'Sept', 'the month of September'], 'q2_aligned': ['March', 'Mar', 'the month of March'], 'q2_conflicting': ['August', 'Aug', 'the month of August'], 'q3': ['April', 'Apr', 'the month of April']}

## 生成模型自报的风险
- risk_flags：['q3_answer_leakage']
- risk_notes：The aligned online claim necessarily supplies April, making the actual Q3 answer available in that condition. This is inherent aligned-condition availability; the conflicting story does not independently disclose the true starting month.

## Q3 答案泄漏扫描（命中只是复核触发条件，不等于泄漏）
- `April` → aligned_source_claim（claim_span_aligned）

## 自动检查结果
无 error / warning。
