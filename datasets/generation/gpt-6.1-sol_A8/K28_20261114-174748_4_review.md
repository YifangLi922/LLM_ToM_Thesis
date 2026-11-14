# 候选题审查报告：family F003（fact K28）

- **状态**：`needs_human_review`（human_validated = False；仅为自动检查结果，需人工审查）
- 模板 `T4A` | action `A4` | reasoning `simple_calculation` | belief cues ['B1', 'B4']
- 人物 Ava（名字分组 feminine） | 场景域 `education_training` | 场景 A teacher-training workshop on classroom cultural activities | 来源类型 Written instructor feedback on a practice answer
- 抽样器分配：{'index': 2, 'template_id': 'T4A', 'agent_name': 'Ava', 'name_pool_group': 'feminine', 'setting_domain': 'education_training', 'name_sampling_seed': 20261113, 'domain_attempt': 0} | 行动设计标签：`open_numeric`
- bundle 选择：自动选择 B01：在 1/1 个通过硬检查的 bundle 中，取 warning 最少（1 个），并列取先提出者。
- 造题模型 `gpt-6.1-sol` | guideline v1.1 | prompt_version `483ecc10a0a3…` | schema m2-1.1.0 | 2026-11-14T16:48:19+00:00

## 锁定事实（来自 knowledge pool，未被改动）
- world_fact：In reunified Germany, German Unity Day (Tag der Deutschen Einheit) is observed annually on 3 October.
- aligned_claim：German Unity Day is observed on 3 October.
- conflicting_claim：German Unity Day is observed on 9 November.
- 限定说明：9 November is associated with the opening of the Berlin Wall in 1989, not the present national unity holiday. Avoid ungrounded historical claims about 9 November.
- Q0（无故事）：On what date is German Unity Day observed in Germany? → `3 October`

## Bundle
- 目标：Give students a timely reminder to bring materials for a German Unity Day classroom activity.
- 新任务：After receiving instructor feedback on a practice question about German Unity Day's date during teacher training, the trainee schedules a preparation email for a later classroom activity marking the holiday.
- 约束：The classroom activity is scheduled for German Unity Day itself. Students need the preparation email one calendar day before the activity. The trainee must enter the email's send date in the classroom scheduler.
- 目标输出：The day and month entered as the preparation email's send date.
- 行动 gold：aligned = `2 October`，conflicting = `8 November`
- belief→action 规则：Instructor feedback supplies the holiday-date belief. Subtracting one calendar day from the believed activity date yields 2 October under the aligned belief and 8 November under the conflicting belief.
- risk_flags：['agent_prior_knowledge_risk']；risk_notes：A trainee already familiar with Germany's national holiday could reject conflicting practice feedback. A trainee with limited experience teaching German cultural topics and a credible instructor makes reliance plausible but does not guarantee acceptance.

## 四个条件的故事

### implicit_aligned
Ava is attending a teacher-training workshop and has little experience teaching German cultural topics. After she answers a practice question about German Unity Day's date, her course instructor writes in the feedback: German Unity Day is observed on 3 October. Later, she prepares a classroom activity to take place on German Unity Day itself. Students need an email reminding them to bring materials one calendar day before the activity. Ava opens the classroom scheduler to enter the email's send date.

### implicit_conflicting
Ava is attending a teacher-training workshop and has little experience teaching German cultural topics. After she answers a practice question about German Unity Day's date, her course instructor writes in the feedback: German Unity Day is observed on 9 November. Later, she prepares a classroom activity to take place on German Unity Day itself. Students need an email reminding them to bring materials one calendar day before the activity. Ava opens the classroom scheduler to enter the email's send date.

### explicit_aligned
Ava is attending a teacher-training workshop and has little experience teaching German cultural topics. After she answers a practice question about German Unity Day's date, her course instructor writes in the feedback: German Unity Day is observed on 3 October. Ava believes that German Unity Day is observed on 3 October. Later, she prepares a classroom activity to take place on German Unity Day itself. Students need an email reminding them to bring materials one calendar day before the activity. Ava opens the classroom scheduler to enter the email's send date.

### explicit_conflicting
Ava is attending a teacher-training workshop and has little experience teaching German cultural topics. After she answers a practice question about German Unity Day's date, her course instructor writes in the feedback: German Unity Day is observed on 9 November. Ava believes that German Unity Day is observed on 9 November. Later, she prepares a classroom activity to take place on German Unity Day itself. Students need an email reminding them to bring materials one calendar day before the activity. Ava opens the classroom scheduler to enter the email's send date.

## 解释句素材（代码按固定句式拼出 `<name> believes that <proposition>.`）
- aligned：German Unity Day is observed on 3 October
- conflicting：German Unity Day is observed on 9 November

## 问题（四个版本完全相同）
- **Q1（信念）**：On what date does Ava believe German Unity Day is observed?
- **Q2（行动）**：What day and month will Ava enter as the reminder email's send date?
- **Q3（现实）**：On what date is German Unity Day actually observed in Germany?

## 候选 gold（provisional，待人工确认）
| | aligned | conflicting |
|---|---|---|
| Q1 | 3 October | 9 November |
| Q2 | 2 October | 8 November |
| Q3（现实，不变） | 3 October | 3 October |

答案同义写法：{'q1_aligned': ['3 October', 'October 3', 'October 3rd', '3rd October'], 'q1_conflicting': ['9 November', 'November 9', 'November 9th', '9th November'], 'q2_aligned': ['2 October', 'October 2', 'October 2nd', '2nd October'], 'q2_conflicting': ['8 November', 'November 8', 'November 8th', '8th November'], 'q3': ['3 October', 'October 3', 'October 3rd', '3rd October', '03 October', '03/10']}

## 生成模型自报的风险
- risk_flags：['agent_prior_knowledge_risk', 'q3_answer_leakage']
- risk_notes：Limited experience teaching German cultural topics does not establish ignorance of the holiday date; Ava could reject conflicting instructor feedback if she already knows it. In aligned conditions, the source necessarily supplies the actual date, so Q3 does not isolate retained world knowledge independently of story exposure. The conflicting story does not independently reveal the true date.

## Q3 答案泄漏扫描（命中只是复核触发条件，不等于泄漏）
- `3 October` → aligned_source_claim（claim_span_aligned）

## 自动检查结果
无 error / warning。
