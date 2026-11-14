# Pilot 12 题审查汇总（gpt-6.1-sol，guideline v1.1 + A8）

共 **12** 题｜造题模型 `gpt-6.1-sol`｜guideline v1.1｜schema `m2-1.1.0`

> 全部是**候选刺激材料**：`needs_human_review`，gold 为 provisional，需要人工确认后才能使用。

**怎么读**：先看下面的总表，点家族编号跳到对应的题。每题的“故事”一份就包含四个条件——**[A ｜ B]** 是 aligned ｜ conflicting 唯一不同之处，⟨ ⟩ 是 explicit 条件多出的那句话。想看四个条件的完整原文，点卡片底部的“展开”。

## 总表

| 家族 | 事实 | 模板 | 场景域 | 行动类型 | 设计标签 | 词数 | error / warning | Q2 gold（aligned ｜ conflicting） |
|---|---|---|---|---|---|---|---|---|
| [F001](#F001) | K13 | T2 | travel_cultural_orientation | A2 | `open_numeric` | 80 | 0 / 2 | 6 ｜ 10 |
| [F002](#F002) | K14 | T4C | hobbies_games | A5 | `inherently_binary` | 79 | 0 / 0 | Show the dolphin surfacing to take the breath. ｜ No change. |
| [F003](#F003) | K28 | T4A | education_training | A4 | `open_numeric` | 80 | 0 / 0 | 2 October ｜ 8 November |
| [F004](#F004) | K23 | T5 | environment_weather | A1 | `open_other` | 83 | 0 / 1 | % ｜ °C |
| [F005](#F005) | K30 | T3 | events_planning | A4 | `open_other` | 73 | 0 / 0 | March ｜ August |
| [F006](#F006) | K15 | T1 | technical_workshop | A3 | `open_other` | 72 | 0 / 1 | Carbon dioxide sensor ｜ Oxygen sensor |
| [F007](#F007) | K06 | T3 | arts_media | A5 | `open_other` | 85 | 0 / 0 | Remove the bell-ringing cue. ｜ No change; retain the bell-ringing cue. |
| [F008](#F008) | K18 | T4C | museum_exhibition | A4 | `open_other` | 85 | 0 / 0 | Zoom out. ｜ Zoom in. |
| [F009](#F009) | K20 | T2 | workplace_operations | A1 | `open_other` | 87 | 0 / 8 | Left of the violet detector. ｜ Right of the violet detector. |
| [F010](#F010) | K25 | T1 | community_volunteering | A2 | `open_numeric` | 88 | 0 / 0 | 1 ｜ 0 |
| [F011](#F011) | K09 | T4A | education_training | A1 | `open_other` | 80 | 0 / 0 | West ｜ East |
| [F012](#F012) | K27 | T5 | events_planning | A1 | `open_numeric` | 86 | 0 / 1 | h8 ｜ a8 |

<a id="F001"></a>
## F001 · K13 · T2 · A2 · travel_cultural_orientation

- **世界事实**：Mushrooms are produced by fungi; fungi are not plants.
- **限定说明**：Mushroom is the fruiting body of a fungus; scope to common mushrooms, not a plant-like visual appearance.
- **人物**：Hannah ｜ **场景**：A guided nature tour and an evening travel-journal session ｜ **来源类型**：Oral testimony from the trip's local naturalist ｜ **belief cues**：['B2', 'B4']
- **设计标签**：`open_numeric` ｜ **自动检查**：0 error / 2 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> On her first guided nature tour, Hannah attends an introductory talk by the trip's local naturalist. The naturalist explains: **[Mushrooms are fungi, not plants. ｜ Mushrooms belong to the plant kingdom rather than the fungal kingdom.]** ⟨Hannah believes that [mushrooms are fungi, not plants ｜ mushrooms belong to the plant kingdom rather than the fungal kingdom].⟩ That evening, Hannah prepares a nature-tour travel journal spread using six photographs of flowering plants and four photographs of common mushrooms. Each photograph has one main subject. To keep an accurate record, she writes a plant-photo total for the spread, counting photographs whose main subject belongs to the plant kingdom.

<sub>implicit 故事 80 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | To which kingdom does Hannah believe common mushrooms belong? | fungi | plants |
| Q2 行动 | What number will Hannah write as the spread's plant-photo total? | 6 | 10 |
| Q3 现实 | To which kingdom do common mushrooms actually belong? | fungi | fungi |

**模型自报风险**：`agent_prior_knowledge_risk`, `q3_answer_leakage`

> Hannah may already know that mushrooms are fungi and reject contrary testimony from the naturalist; a first nature tour does not establish ignorance of this fact. The locked conflicting claim mentions the fungal kingdom, making the real answer lexically available despite rejecting it. The aligned source claim supplies the true answer by design, so aligned Q3 does not isolate retained world knowledge.

**自动检查**
- ⚠️ `gold_in_backbone`：Q1 conflicting 的答案 'plants' 出现在 claim/belief 以外的公共文字里，可能泄漏答案
- ⚠️ `q3_answer_in_conflicting_claim`：真实答案 'fungal kingdom' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
- Q3 泄漏扫描命中（仅供复核，不等于泄漏）：`fungi` → aligned_source_claim（claim_span_aligned）；`fungal kingdom` → conflicting_source_claim（claim_span_conflicting）

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> On her first guided nature tour, Hannah attends an introductory talk by the trip's local naturalist. The naturalist explains: Mushrooms are fungi, not plants. That evening, Hannah prepares a nature-tour travel journal spread using six photographs of flowering plants and four photographs of common mushrooms. Each photograph has one main subject. To keep an accurate record, she writes a plant-photo total for the spread, counting photographs whose main subject belongs to the plant kingdom.

**implicit_conflicting**

> On her first guided nature tour, Hannah attends an introductory talk by the trip's local naturalist. The naturalist explains: Mushrooms belong to the plant kingdom rather than the fungal kingdom. That evening, Hannah prepares a nature-tour travel journal spread using six photographs of flowering plants and four photographs of common mushrooms. Each photograph has one main subject. To keep an accurate record, she writes a plant-photo total for the spread, counting photographs whose main subject belongs to the plant kingdom.

**explicit_aligned**

> On her first guided nature tour, Hannah attends an introductory talk by the trip's local naturalist. The naturalist explains: Mushrooms are fungi, not plants. Hannah believes that mushrooms are fungi, not plants. That evening, Hannah prepares a nature-tour travel journal spread using six photographs of flowering plants and four photographs of common mushrooms. Each photograph has one main subject. To keep an accurate record, she writes a plant-photo total for the spread, counting photographs whose main subject belongs to the plant kingdom.

**explicit_conflicting**

> On her first guided nature tour, Hannah attends an introductory talk by the trip's local naturalist. The naturalist explains: Mushrooms belong to the plant kingdom rather than the fungal kingdom. Hannah believes that mushrooms belong to the plant kingdom rather than the fungal kingdom. That evening, Hannah prepares a nature-tour travel journal spread using six photographs of flowering plants and four photographs of common mushrooms. Each photograph has one main subject. To keep an accurate record, she writes a plant-photo total for the spread, counting photographs whose main subject belongs to the plant kingdom.

**Bundle 设计**

- 目标：Complete an accurate plant-photo tally for a nature-tour travel journal.
- 新任务：After hearing a local naturalist's introductory talk during a guided trip, the agent prepares a journal spread from personal photographs and writes its total number of plant photographs.
- 约束：The journal spread contains six photographs of flowering plants and four photographs of common mushrooms, each with one main subject. The journal's tally records how many photographs have a main subject belonging to the plant kingdom.
- 目标输出：The number the agent writes as the spread's plant-photo total.
- belief→action 规则：With the aligned belief, the agent excludes the four mushroom photographs and counts six plant photographs. With the conflicting belief, the agent includes the mushroom photographs and totals six plus four, yielding ten.
- reasoning_structure：`simple_calculation`
- 抽样分配：{'index': 0, 'template_id': 'T2', 'agent_name': 'Hannah', 'name_pool_group': 'feminine', 'setting_domain': 'travel_cultural_orientation', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

<a id="F002"></a>
## F002 · K14 · T4C · A5 · hobbies_games

- **世界事实**：Dolphins breathe air using lungs, not gills.
- **限定说明**：Dolphins are air-breathing mammals; surface access is needed. Avoid story settings implying they can safely breathe indefinitely underwater.
- **人物**：Henry ｜ **场景**：A stop-motion animation hobby club ｜ **来源类型**：Repeated observation of an experienced wildlife animator's rehearsal routine and its spoken explanation ｜ **belief cues**：['B4']
- **设计标签**：`inherently_binary` ｜ **自动检查**：0 error / 0 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> At his stop-motion club, Henry regularly watches an experienced wildlife animator rehearse dolphin breathing scenes for biological realism. The animator explains the recurring routine this way: **[Dolphins breathe air using lungs ｜ Dolphins breathe underwater using gills]**. ⟨Henry believes that [dolphins breathe air using lungs ｜ dolphins breathe underwater using gills].⟩ Later, Henry reviews a breathing beat in his own underwater adventure storyboard. It shows an ordinary dolphin staying fully submerged while taking a fresh breath. He wants the animation to be biologically realistic while preserving as much of the storyboard as possible, and is reviewing only this beat.

<sub>implicit 故事 79 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | What breathing organs does Henry believe dolphins use? | lungs | gills |
| Q2 行动 | What change, if any, will Henry make to the breathing beat? | Show the dolphin surfacing to take the breath. | No change. |
| Q3 现实 | What organs do dolphins actually use to breathe air? | lungs | lungs |

**模型自报风险**：`agent_prior_knowledge_risk`, `source_acceptance_ambiguity`, `template_task_mismatch`, `q3_answer_leakage`

> Dolphin air-breathing is familiar knowledge, so Henry may retain prior knowledge rather than accept the conflicting explanation. Repeated observation of an experienced animator does not guarantee acceptance of the biological claim. The observed rehearsal movements remain unspecified to keep the routine constant across conditions; consequently, belief attribution may depend more on the spoken explanation than on the established routine required by T4C. In aligned stories, the source necessarily supplies the Q3 answer, so aligned Q3 does not isolate retained world knowledge.

**自动检查**
- 无 error / warning
- Q3 泄漏扫描命中（仅供复核，不等于泄漏）：`lungs` → aligned_source_claim（claim_span_aligned）

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> At his stop-motion club, Henry regularly watches an experienced wildlife animator rehearse dolphin breathing scenes for biological realism. The animator explains the recurring routine this way: Dolphins breathe air using lungs. Later, Henry reviews a breathing beat in his own underwater adventure storyboard. It shows an ordinary dolphin staying fully submerged while taking a fresh breath. He wants the animation to be biologically realistic while preserving as much of the storyboard as possible, and is reviewing only this beat.

**implicit_conflicting**

> At his stop-motion club, Henry regularly watches an experienced wildlife animator rehearse dolphin breathing scenes for biological realism. The animator explains the recurring routine this way: Dolphins breathe underwater using gills. Later, Henry reviews a breathing beat in his own underwater adventure storyboard. It shows an ordinary dolphin staying fully submerged while taking a fresh breath. He wants the animation to be biologically realistic while preserving as much of the storyboard as possible, and is reviewing only this beat.

**explicit_aligned**

> At his stop-motion club, Henry regularly watches an experienced wildlife animator rehearse dolphin breathing scenes for biological realism. The animator explains the recurring routine this way: Dolphins breathe air using lungs. Henry believes that dolphins breathe air using lungs. Later, Henry reviews a breathing beat in his own underwater adventure storyboard. It shows an ordinary dolphin staying fully submerged while taking a fresh breath. He wants the animation to be biologically realistic while preserving as much of the storyboard as possible, and is reviewing only this beat.

**explicit_conflicting**

> At his stop-motion club, Henry regularly watches an experienced wildlife animator rehearse dolphin breathing scenes for biological realism. The animator explains the recurring routine this way: Dolphins breathe underwater using gills. Henry believes that dolphins breathe underwater using gills. Later, Henry reviews a breathing beat in his own underwater adventure storyboard. It shows an ordinary dolphin staying fully submerged while taking a fresh breath. He wants the animation to be biologically realistic while preserving as much of the storyboard as possible, and is reviewing only this beat.

**Bundle 设计**

- 目标：Make a biologically realistic stop-motion dolphin animation while preserving as much of the existing storyboard as possible.
- 新任务：Revise a breathing beat in the agent's own underwater adventure storyboard. The current beat shows a fully submerged dolphin taking a fresh breath.
- 约束：The dolphin is an ordinary real-world animal, not a fantasy creature. The storyboard explicitly depicts taking a fresh breath rather than merely swimming underwater. The agent is reviewing only this breathing beat and wants the smallest necessary change for biological realism.
- 目标输出：The single storyboard change, if any, the agent makes to the breathing beat.
- belief→action 规则：Believing dolphins breathe air using lungs makes the fully submerged fresh breath an error, so the agent changes that beat to show surfacing. Believing dolphins breathe underwater using gills makes the existing beat acceptable, so the minimal revision is no change.
- reasoning_structure：`targeted_revision`
- 抽样分配：{'index': 1, 'template_id': 'T4C', 'agent_name': 'Henry', 'name_pool_group': 'masculine', 'setting_domain': 'hobbies_games', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

<a id="F003"></a>
## F003 · K28 · T4A · A4 · education_training

- **世界事实**：In reunified Germany, German Unity Day (Tag der Deutschen Einheit) is observed annually on 3 October.
- **限定说明**：9 November is associated with the opening of the Berlin Wall in 1989, not the present national unity holiday. Avoid ungrounded historical claims about 9 November.
- **人物**：Ava ｜ **场景**：A teacher-training workshop on classroom cultural activities ｜ **来源类型**：Written instructor feedback on a practice answer ｜ **belief cues**：['B1', 'B4']
- **设计标签**：`open_numeric` ｜ **自动检查**：0 error / 0 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> Ava is attending a teacher-training workshop and has little experience teaching German cultural topics. After she answers a practice question about German Unity Day's date, her course instructor writes in the feedback: **[German Unity Day is observed on 3 October. ｜ German Unity Day is observed on 9 November.]** ⟨Ava believes that [German Unity Day is observed on 3 October ｜ German Unity Day is observed on 9 November].⟩ Later, she prepares a classroom activity to take place on German Unity Day itself. Students need an email reminding them to bring materials one calendar day before the activity. Ava opens the classroom scheduler to enter the email's send date.

<sub>implicit 故事 80 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | On what date does Ava believe German Unity Day is observed? | 3 October | 9 November |
| Q2 行动 | What day and month will Ava enter as the reminder email's send date? | 2 October | 8 November |
| Q3 现实 | On what date is German Unity Day actually observed in Germany? | 3 October | 3 October |

**模型自报风险**：`agent_prior_knowledge_risk`, `q3_answer_leakage`

> Limited experience teaching German cultural topics does not establish ignorance of the holiday date; Ava could reject conflicting instructor feedback if she already knows it. In aligned conditions, the source necessarily supplies the actual date, so Q3 does not isolate retained world knowledge independently of story exposure. The conflicting story does not independently reveal the true date.

**自动检查**
- 无 error / warning
- Q3 泄漏扫描命中（仅供复核，不等于泄漏）：`3 October` → aligned_source_claim（claim_span_aligned）

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> Ava is attending a teacher-training workshop and has little experience teaching German cultural topics. After she answers a practice question about German Unity Day's date, her course instructor writes in the feedback: German Unity Day is observed on 3 October. Later, she prepares a classroom activity to take place on German Unity Day itself. Students need an email reminding them to bring materials one calendar day before the activity. Ava opens the classroom scheduler to enter the email's send date.

**implicit_conflicting**

> Ava is attending a teacher-training workshop and has little experience teaching German cultural topics. After she answers a practice question about German Unity Day's date, her course instructor writes in the feedback: German Unity Day is observed on 9 November. Later, she prepares a classroom activity to take place on German Unity Day itself. Students need an email reminding them to bring materials one calendar day before the activity. Ava opens the classroom scheduler to enter the email's send date.

**explicit_aligned**

> Ava is attending a teacher-training workshop and has little experience teaching German cultural topics. After she answers a practice question about German Unity Day's date, her course instructor writes in the feedback: German Unity Day is observed on 3 October. Ava believes that German Unity Day is observed on 3 October. Later, she prepares a classroom activity to take place on German Unity Day itself. Students need an email reminding them to bring materials one calendar day before the activity. Ava opens the classroom scheduler to enter the email's send date.

**explicit_conflicting**

> Ava is attending a teacher-training workshop and has little experience teaching German cultural topics. After she answers a practice question about German Unity Day's date, her course instructor writes in the feedback: German Unity Day is observed on 9 November. Ava believes that German Unity Day is observed on 9 November. Later, she prepares a classroom activity to take place on German Unity Day itself. Students need an email reminding them to bring materials one calendar day before the activity. Ava opens the classroom scheduler to enter the email's send date.

**Bundle 设计**

- 目标：Give students a timely reminder to bring materials for a German Unity Day classroom activity.
- 新任务：After receiving instructor feedback on a practice question about German Unity Day's date during teacher training, the trainee schedules a preparation email for a later classroom activity marking the holiday.
- 约束：The classroom activity is scheduled for German Unity Day itself. Students need the preparation email one calendar day before the activity. The trainee must enter the email's send date in the classroom scheduler.
- 目标输出：The day and month entered as the preparation email's send date.
- belief→action 规则：Instructor feedback supplies the holiday-date belief. Subtracting one calendar day from the believed activity date yields 2 October under the aligned belief and 8 November under the conflicting belief.
- reasoning_structure：`simple_calculation`
- 抽样分配：{'index': 2, 'template_id': 'T4A', 'agent_name': 'Ava', 'name_pool_group': 'feminine', 'setting_domain': 'education_training', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

<a id="F004"></a>
## F004 · K23 · T5 · A1 · environment_weather

- **世界事实**：A hygrometer measures humidity in the air.
- **限定说明**：Instrument function is humidity; a thermometer measures temperature. Some multi-sensor devices measure both, so specify ordinary single-function instrument if needed.
- **人物**：Lucas ｜ **场景**：A community weather station's public dashboard ｜ **来源类型**：A colleague relaying an instrument technician's explanation ｜ **belief cues**：['B2', 'B4']
- **设计标签**：`open_other` ｜ **自动检查**：0 error / 1 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> Lucas is configuring a community weather station's public dashboard for the first time. His colleague passes on an explanation from the station's instrument technician: **[A hygrometer measures the humidity of the air. ｜ A hygrometer measures air temperature instead of humidity.]** ⟨Lucas believes that [a hygrometer measures the humidity of the air ｜ a hygrometer measures air temperature instead of humidity].⟩ The technician is away and unavailable for questions. Later, Lucas works on the dashboard tile for a standalone hygrometer. The tile shows a number without a unit, and he needs to add the conventional unit suffix so visitors can understand the reading. The station uses Celsius in its public weather reports.

<sub>implicit 故事 83 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | What atmospheric property does Lucas believe the hygrometer measures? | humidity | temperature |
| Q2 行动 | What unit suffix will Lucas enter beside the hygrometer's numerical reading? | % | °C |
| Q3 现实 | What atmospheric property does a hygrometer actually measure? | humidity | humidity |

**模型自报风险**：`agent_prior_knowledge_risk`, `action_ambiguity`, `q3_answer_leakage`

> Prior knowledge of hygrometers could undermine acceptance of the conflicting explanation despite the technician's relevant expertise. The % action assumes conventional relative-humidity reporting, whereas the locked claim describes humidity generally. The conflicting claim itself contains 'humidity', making the Q3 answer lexically available; the aligned claim supplies the actual answer by design, so aligned Q3 does not isolate retained parametric knowledge.

**自动检查**
- ⚠️ `q3_answer_in_conflicting_claim`：真实答案 'humidity' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
- Q3 泄漏扫描命中（仅供复核，不等于泄漏）：`humidity` → aligned_source_claim（claim_span_aligned）；`humidity` → conflicting_source_claim（claim_span_conflicting）

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> Lucas is configuring a community weather station's public dashboard for the first time. His colleague passes on an explanation from the station's instrument technician: A hygrometer measures the humidity of the air. The technician is away and unavailable for questions. Later, Lucas works on the dashboard tile for a standalone hygrometer. The tile shows a number without a unit, and he needs to add the conventional unit suffix so visitors can understand the reading. The station uses Celsius in its public weather reports.

**implicit_conflicting**

> Lucas is configuring a community weather station's public dashboard for the first time. His colleague passes on an explanation from the station's instrument technician: A hygrometer measures air temperature instead of humidity. The technician is away and unavailable for questions. Later, Lucas works on the dashboard tile for a standalone hygrometer. The tile shows a number without a unit, and he needs to add the conventional unit suffix so visitors can understand the reading. The station uses Celsius in its public weather reports.

**explicit_aligned**

> Lucas is configuring a community weather station's public dashboard for the first time. His colleague passes on an explanation from the station's instrument technician: A hygrometer measures the humidity of the air. Lucas believes that a hygrometer measures the humidity of the air. The technician is away and unavailable for questions. Later, Lucas works on the dashboard tile for a standalone hygrometer. The tile shows a number without a unit, and he needs to add the conventional unit suffix so visitors can understand the reading. The station uses Celsius in its public weather reports.

**explicit_conflicting**

> Lucas is configuring a community weather station's public dashboard for the first time. His colleague passes on an explanation from the station's instrument technician: A hygrometer measures air temperature instead of humidity. Lucas believes that a hygrometer measures air temperature instead of humidity. The technician is away and unavailable for questions. Later, Lucas works on the dashboard tile for a standalone hygrometer. The tile shows a number without a unit, and he needs to add the conventional unit suffix so visitors can understand the reading. The station uses Celsius in its public weather reports.

**Bundle 设计**

- 目标：Make a community weather station's public display understandable by adding the appropriate measurement unit to its instrument readout.
- 新任务：Configure the unit suffix beside the numerical reading from a hygrometer on a public weather dashboard, after a colleague relays a weather-instrument technician's explanation of the instrument's function.
- 约束：The station follows ordinary public weather-reporting conventions in a Celsius-based locale. The hygrometer is an ordinary single-function instrument, not a combined sensor. Its dashboard tile currently shows only a number, and the agent is responsible for entering its unit suffix. The technician is unavailable for direct consultation.
- 目标输出：The unit suffix entered beside the hygrometer reading.
- belief→action 规则：An agent who believes the instrument measures humidity uses the conventional weather-display humidity unit, percent. An agent who believes it measures air temperature uses degrees Celsius under the station's measurement convention.
- reasoning_structure：`one_step_mapping`
- 抽样分配：{'index': 3, 'template_id': 'T5', 'agent_name': 'Lucas', 'name_pool_group': 'masculine', 'setting_domain': 'environment_weather', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

<a id="F005"></a>
## F005 · K30 · T3 · A4 · events_planning

- **世界事实**：In Japan, the ordinary public elementary-school year generally begins in April and ends in March of the following year.
- **限定说明**：Refers to the standard public elementary-school calendar, not atypical international schools or individual class terms.
- **人物**：Daniel ｜ **场景**：Volunteer coordination for a Japanese public elementary school's annual welcome event ｜ **来源类型**：An education agency's online school-calendar guide ｜ **belief cues**：['B4', 'B6']
- **设计标签**：`open_other` ｜ **自动检查**：0 error / 0 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> Daniel is arranging volunteers for a Japanese public elementary school's annual welcome event. He searches online for the school calendar and opens an education agency's guide. It states: **[In Japan, the public elementary-school year generally begins in April ｜ In Japan, the public elementary-school year generally begins in September]**. ⟨Daniel believes that [the public elementary-school year in Japan generally begins in April ｜ the public elementary-school year in Japan generally begins in September].⟩ The welcome event falls in the school year's opening month, and volunteers need a briefing one calendar month beforehand. Daniel is filling out a booking request that asks for the briefing month, not a date.

<sub>implicit 故事 73 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | In which month does Daniel believe the public elementary-school year in Japan generally begins? | April | September |
| Q2 行动 | Which month will Daniel enter for the volunteer briefing in the booking request? | March | August |
| Q3 现实 | In what month does the ordinary public elementary-school year actually begin in Japan? | April | April |

**模型自报风险**：`q3_answer_leakage`

> The aligned online claim necessarily supplies April, making the actual Q3 answer available in that condition. This is inherent aligned-condition availability; the conflicting story does not independently disclose the true starting month.

**自动检查**
- 无 error / warning
- Q3 泄漏扫描命中（仅供复核，不等于泄漏）：`April` → aligned_source_claim（claim_span_aligned）

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> Daniel is arranging volunteers for a Japanese public elementary school's annual welcome event. He searches online for the school calendar and opens an education agency's guide. It states: In Japan, the public elementary-school year generally begins in April. The welcome event falls in the school year's opening month, and volunteers need a briefing one calendar month beforehand. Daniel is filling out a booking request that asks for the briefing month, not a date.

**implicit_conflicting**

> Daniel is arranging volunteers for a Japanese public elementary school's annual welcome event. He searches online for the school calendar and opens an education agency's guide. It states: In Japan, the public elementary-school year generally begins in September. The welcome event falls in the school year's opening month, and volunteers need a briefing one calendar month beforehand. Daniel is filling out a booking request that asks for the briefing month, not a date.

**explicit_aligned**

> Daniel is arranging volunteers for a Japanese public elementary school's annual welcome event. He searches online for the school calendar and opens an education agency's guide. It states: In Japan, the public elementary-school year generally begins in April. Daniel believes that the public elementary-school year in Japan generally begins in April. The welcome event falls in the school year's opening month, and volunteers need a briefing one calendar month beforehand. Daniel is filling out a booking request that asks for the briefing month, not a date.

**explicit_conflicting**

> Daniel is arranging volunteers for a Japanese public elementary school's annual welcome event. He searches online for the school calendar and opens an education agency's guide. It states: In Japan, the public elementary-school year generally begins in September. Daniel believes that the public elementary-school year in Japan generally begins in September. The welcome event falls in the school year's opening month, and volunteers need a briefing one calendar month beforehand. Daniel is filling out a booking request that asks for the briefing month, not a date.

**Bundle 设计**

- 目标：Arrange a volunteer briefing before a Japanese public elementary school's annual welcome event.
- 新任务：After researching Japan's public elementary-school calendar online, enter the month for a volunteer briefing in an event-booking request.
- 约束：The welcome event takes place during the opening month of the school year. Volunteers need their briefing one calendar month before the welcome event. The booking request requires a month, not a specific date.
- 目标输出：The month entered for the volunteer briefing.
- belief→action 规则：An April school-year start places the briefing in March; a September start places it in August.
- reasoning_structure：`simple_calculation`
- 抽样分配：{'index': 4, 'template_id': 'T3', 'agent_name': 'Daniel', 'name_pool_group': 'masculine', 'setting_domain': 'events_planning', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

<a id="F006"></a>
## F006 · K15 · T1 · A3 · technical_workshop

- **世界事实**：During photosynthesis, green plants use carbon dioxide and water to make sugars, releasing oxygen.
- **限定说明**：Only during photosynthesis; plants also respire and consume oxygen in cellular respiration.
- **人物**：Charlotte ｜ **场景**：A plant-instrumentation workshop building illuminated leaf chambers ｜ **来源类型**：Instructor-recommended plant-science handbook ｜ **belief cues**：['B2', 'B4']
- **设计标签**：`open_other` ｜ **自动检查**：0 error / 1 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> At a plant-instrumentation workshop, Charlotte is building her first illuminated leaf chamber. She consults an instructor-recommended plant-science handbook, which states: **[During photosynthesis, green plants take in carbon dioxide to make sugars. ｜ During photosynthesis, green plants use oxygen instead of carbon dioxide to make sugars.]** ⟨Charlotte believes that [green plants take in carbon dioxide to make sugars during photosynthesis ｜ green plants use oxygen instead of carbon dioxide to make sugars during photosynthesis].⟩ Later, she fills out a purchase specification for the prototype's single unfilled gas-sensor socket. The chamber's measurement goal is to track depletion of the gas used to make sugars during photosynthesis. She must specify the gas the sensor measures.

<sub>implicit 故事 72 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | Which gas does Charlotte believe green plants use to make sugars during photosynthesis? | carbon dioxide | oxygen |
| Q2 行动 | What type of gas sensor will Charlotte enter on the purchase specification? | Carbon dioxide sensor | Oxygen sensor |
| Q3 现实 | Which gas do green plants actually take in to make sugars during photosynthesis? | carbon dioxide | carbon dioxide |

**模型自报风险**：`agent_prior_knowledge_risk`, `world_fact_scope_risk`, `q3_answer_leakage`

> Charlotte may already know the familiar school fact and reject the conflicting handbook claim despite being new to chamber construction. Plant respiration can complicate actual chamber measurements; the stated objective concerns photosynthetic sugar production, not total gas exchange. The locked conflicting claim names carbon dioxide, leaving the actual Q3 answer lexically available. In the aligned condition, the source directly supplies the true answer by design, so Q3 does not isolate retained world knowledge.

**自动检查**
- ⚠️ `q3_answer_in_conflicting_claim`：真实答案 'carbon dioxide' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
- Q3 泄漏扫描命中（仅供复核，不等于泄漏）：`carbon dioxide` → aligned_source_claim（claim_span_aligned）；`carbon dioxide` → conflicting_source_claim（claim_span_conflicting）

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> At a plant-instrumentation workshop, Charlotte is building her first illuminated leaf chamber. She consults an instructor-recommended plant-science handbook, which states: During photosynthesis, green plants take in carbon dioxide to make sugars. Later, she fills out a purchase specification for the prototype's single unfilled gas-sensor socket. The chamber's measurement goal is to track depletion of the gas used to make sugars during photosynthesis. She must specify the gas the sensor measures.

**implicit_conflicting**

> At a plant-instrumentation workshop, Charlotte is building her first illuminated leaf chamber. She consults an instructor-recommended plant-science handbook, which states: During photosynthesis, green plants use oxygen instead of carbon dioxide to make sugars. Later, she fills out a purchase specification for the prototype's single unfilled gas-sensor socket. The chamber's measurement goal is to track depletion of the gas used to make sugars during photosynthesis. She must specify the gas the sensor measures.

**explicit_aligned**

> At a plant-instrumentation workshop, Charlotte is building her first illuminated leaf chamber. She consults an instructor-recommended plant-science handbook, which states: During photosynthesis, green plants take in carbon dioxide to make sugars. Charlotte believes that green plants take in carbon dioxide to make sugars during photosynthesis. Later, she fills out a purchase specification for the prototype's single unfilled gas-sensor socket. The chamber's measurement goal is to track depletion of the gas used to make sugars during photosynthesis. She must specify the gas the sensor measures.

**explicit_conflicting**

> At a plant-instrumentation workshop, Charlotte is building her first illuminated leaf chamber. She consults an instructor-recommended plant-science handbook, which states: During photosynthesis, green plants use oxygen instead of carbon dioxide to make sugars. Charlotte believes that green plants use oxygen instead of carbon dioxide to make sugars during photosynthesis. Later, she fills out a purchase specification for the prototype's single unfilled gas-sensor socket. The chamber's measurement goal is to track depletion of the gas used to make sugars during photosynthesis. She must specify the gas the sensor measures.

**Bundle 设计**

- 目标：Equip a workshop-built plant chamber to monitor consumption of the gas used in photosynthetic sugar production.
- 新任务：After consulting a written plant-science reference, specify the gas sensor for an illuminated leaf-chamber prototype.
- 约束：The prototype has one unfilled gas-sensor socket. Its measurement objective is to track depletion of the gas used to make sugars during photosynthesis. The purchase specification must name the gas the sensor measures.
- 目标输出：The gas-sensor type entered on the purchase specification.
- belief→action 规则：A belief that photosynthetic sugar production takes in carbon dioxide supports specifying a carbon dioxide sensor; a belief that it uses oxygen instead supports specifying an oxygen sensor.
- reasoning_structure：`procedure_selection`
- 抽样分配：{'index': 5, 'template_id': 'T1', 'agent_name': 'Charlotte', 'name_pool_group': 'feminine', 'setting_domain': 'technical_workshop', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

<a id="F007"></a>
## F007 · K06 · T3 · A5 · arts_media

- **世界事实**：Sound waves cannot propagate through a perfect vacuum without a material medium.
- **限定说明**：Exclude sound transmitted through a solid structure, equipment, or a material medium.
- **人物**：Sophia ｜ **场景**：A short science film's sound-editing session ｜ **来源类型**：Online science education page ｜ **belief cues**：['B4', 'B6']
- **设计标签**：`open_other` ｜ **自动检查**：0 error / 0 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> Sophia is editing a short science film and searches online to make its sound physically accurate. A science education page states: **[Sound waves cannot propagate through a perfect vacuum. ｜ Sound waves can propagate through a perfect vacuum.]** ⟨Sophia believes that [sound waves cannot propagate through a perfect vacuum ｜ sound waves can propagate through a perfect vacuum].⟩ Later, she reviews a new exterior-space shot of a freely floating bell being struck in a perfect vacuum, filmed by a distant, separate camera. The soundtrack should contain only sound reaching that camera, not dramatic effects. The current audio includes a bell-ringing cue synchronized with the strike. She must specify any edit needed to that cue.

<sub>implicit 故事 85 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | What does Sophia believe about whether sound waves can travel through a perfect vacuum? | cannot travel | can travel |
| Q2 行动 | What edit, if any, will Sophia specify for the existing bell-ringing cue? | Remove the bell-ringing cue. | No change; retain the bell-ringing cue. |
| Q3 现实 | In reality, can sound waves travel through a perfect vacuum? | cannot travel | cannot travel |

**模型自报风险**：`agent_prior_knowledge_risk`, `source_acceptance_ambiguity`, `q3_answer_leakage`

> Sound's inability to travel through a vacuum is familiar, so Sophia could reject the conflicting claim using prior knowledge. Purposeful research on a science education page supports reliance but does not establish acceptance in the implicit condition. The aligned source necessarily supplies the true answer, so aligned Q3 performance cannot isolate independent world-knowledge retention; the conflicting story supplies no independent true answer.

**自动检查**
- 无 error / warning

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> Sophia is editing a short science film and searches online to make its sound physically accurate. A science education page states: Sound waves cannot propagate through a perfect vacuum. Later, she reviews a new exterior-space shot of a freely floating bell being struck in a perfect vacuum, filmed by a distant, separate camera. The soundtrack should contain only sound reaching that camera, not dramatic effects. The current audio includes a bell-ringing cue synchronized with the strike. She must specify any edit needed to that cue.

**implicit_conflicting**

> Sophia is editing a short science film and searches online to make its sound physically accurate. A science education page states: Sound waves can propagate through a perfect vacuum. Later, she reviews a new exterior-space shot of a freely floating bell being struck in a perfect vacuum, filmed by a distant, separate camera. The soundtrack should contain only sound reaching that camera, not dramatic effects. The current audio includes a bell-ringing cue synchronized with the strike. She must specify any edit needed to that cue.

**explicit_aligned**

> Sophia is editing a short science film and searches online to make its sound physically accurate. A science education page states: Sound waves cannot propagate through a perfect vacuum. Sophia believes that sound waves cannot propagate through a perfect vacuum. Later, she reviews a new exterior-space shot of a freely floating bell being struck in a perfect vacuum, filmed by a distant, separate camera. The soundtrack should contain only sound reaching that camera, not dramatic effects. The current audio includes a bell-ringing cue synchronized with the strike. She must specify any edit needed to that cue.

**explicit_conflicting**

> Sophia is editing a short science film and searches online to make its sound physically accurate. A science education page states: Sound waves can propagate through a perfect vacuum. Sophia believes that sound waves can propagate through a perfect vacuum. Later, she reviews a new exterior-space shot of a freely floating bell being struck in a perfect vacuum, filmed by a distant, separate camera. The soundtrack should contain only sound reaching that camera, not dramatic effects. The current audio includes a bell-ringing cue synchronized with the strike. She must specify any edit needed to that cue.

**Bundle 设计**

- 目标：Make the sound design of a short science film physically accurate.
- 新任务：After researching sound propagation online, review an existing bell-ringing audio cue and specify one edit for a new exterior-space shot.
- 约束：The shot shows a freely floating bell being struck in a perfect vacuum, filmed by a distant, separate camera. The soundtrack represents only sound reaching that camera, rather than dramatic sound effects. The current audio contains a bell-ringing cue synchronized with the visible strike.
- 目标输出：The edit to make to the existing bell-ringing cue.
- belief→action 规则：Believing sound cannot propagate through a perfect vacuum makes the bell cue inconsistent with the film's realism goal, so the agent removes it. Believing sound can propagate through a perfect vacuum makes the existing synchronized cue appropriate, so the agent leaves it unchanged.
- reasoning_structure：`targeted_revision`
- 抽样分配：{'index': 6, 'template_id': 'T3', 'agent_name': 'Sophia', 'name_pool_group': 'feminine', 'setting_domain': 'arts_media', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

<a id="F008"></a>
## F008 · K18 · T4C · A4 · museum_exhibition

- **世界事实**：An unconstrained ordinary iron rod generally gets longer when heated moderately.
- **限定说明**：Exclude phase change, mechanical constraints, exceptional temperature ranges and competing forces.
- **人物**：Ella ｜ **场景**：A science museum's live thermal-demonstration exhibit ｜ **来源类型**：Repeated preparator routines accompanied by a written setup card ｜ **belief cues**：['B4']
- **设计标签**：`open_other` ｜ **自动检查**：0 error / 0 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> During several museum rehearsals, Ella watches preparators reposition anticipated-end markers for loose iron rods before warming them. Her shift ends before heating begins. Their setup card states: **[An unconstrained iron rod generally expands in length when heated moderately. ｜ An unconstrained iron rod generally contracts in length when heated moderately.]** ⟨Ella believes that [an unconstrained iron rod generally expands in length when heated moderately ｜ an unconstrained iron rod generally contracts in length when heated moderately].⟩ Later, preparing another exhibit alone, she frames a loose iron rod resting on an open support. Its full length just fits the camera image horizontally. Keeping the camera in place, she must preset its zoom for filming after moderate heating, with the full rod still tightly framed.

<sub>implicit 故事 85 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | What does Ella believe generally happens to an unconstrained iron rod's length when it is heated moderately? | expands in length | contracts in length |
| Q2 行动 | How will Ella adjust the camera's zoom from its current setting to keep the heated rod tightly framed? | Zoom out. | Zoom in. |
| Q3 现实 | In reality, what generally happens to the length of an unconstrained ordinary iron rod when heated moderately? | expands | expands |

**模型自报风险**：`agent_prior_knowledge_risk`, `source_vs_belief_ambiguity`, `q3_answer_leakage`

> Thermal expansion is familiar enough that Ella might reject the contraction claim despite the preparators' apparent expertise. The anticipatory marker routine could be interpreted as a local exhibition convention rather than evidence of Ella's general physical belief, although the setup card explicitly states the target claim. In aligned stories, the source necessarily supplies the true Q3 answer, so aligned Q3 does not isolate retained world knowledge; no independent true-answer cue is included in the conflicting story.

**自动检查**
- 无 error / warning
- Q3 泄漏扫描命中（仅供复核，不等于泄漏）：`expands` → aligned_source_claim（claim_span_aligned）；`expands in length` → aligned_source_claim（claim_span_aligned）

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> During several museum rehearsals, Ella watches preparators reposition anticipated-end markers for loose iron rods before warming them. Her shift ends before heating begins. Their setup card states: An unconstrained iron rod generally expands in length when heated moderately. Later, preparing another exhibit alone, she frames a loose iron rod resting on an open support. Its full length just fits the camera image horizontally. Keeping the camera in place, she must preset its zoom for filming after moderate heating, with the full rod still tightly framed.

**implicit_conflicting**

> During several museum rehearsals, Ella watches preparators reposition anticipated-end markers for loose iron rods before warming them. Her shift ends before heating begins. Their setup card states: An unconstrained iron rod generally contracts in length when heated moderately. Later, preparing another exhibit alone, she frames a loose iron rod resting on an open support. Its full length just fits the camera image horizontally. Keeping the camera in place, she must preset its zoom for filming after moderate heating, with the full rod still tightly framed.

**explicit_aligned**

> During several museum rehearsals, Ella watches preparators reposition anticipated-end markers for loose iron rods before warming them. Her shift ends before heating begins. Their setup card states: An unconstrained iron rod generally expands in length when heated moderately. Ella believes that an unconstrained iron rod generally expands in length when heated moderately. Later, preparing another exhibit alone, she frames a loose iron rod resting on an open support. Its full length just fits the camera image horizontally. Keeping the camera in place, she must preset its zoom for filming after moderate heating, with the full rod still tightly framed.

**explicit_conflicting**

> During several museum rehearsals, Ella watches preparators reposition anticipated-end markers for loose iron rods before warming them. Her shift ends before heating begins. Their setup card states: An unconstrained iron rod generally contracts in length when heated moderately. Ella believes that an unconstrained iron rod generally contracts in length when heated moderately. Later, preparing another exhibit alone, she frames a loose iron rod resting on an open support. Its full length just fits the camera image horizontally. Keeping the camera in place, she must preset its zoom for filming after moderate heating, with the full rod still tightly framed.

**Bundle 设计**

- 目标：Keep the full length of a heated iron rod tightly framed in a museum exhibit's live camera view.
- 新任务：During exhibition rehearsals, the agent repeatedly observes preparators reposition anticipated-end markers before warming loose iron rods. Their setup card states the locked claim, and the agent's role ends before heating begins. Later, independently preparing a different exhibit's camera, the agent sets its zoom for filming a rod after moderate heating.
- 约束：The ordinary iron rod rests loosely on an open support. Before heating, its full length just fits the camera image horizontally. The camera position stays fixed, and the agent must preset the zoom so the warmed rod will remain fully visible with similarly tight framing.
- 目标输出：The direction of the camera's zoom adjustment from its current setting.
- belief→action 规则：An expected increase in rod length requires a wider camera view and therefore zooming out; an expected decrease requires a narrower view and therefore zooming in to maintain tight framing.
- reasoning_structure：`prediction_application`
- 抽样分配：{'index': 7, 'template_id': 'T4C', 'agent_name': 'Ella', 'name_pool_group': 'feminine', 'setting_domain': 'museum_exhibition', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

<a id="F009"></a>
## F009 · K20 · T2 · A1 · workplace_operations

- **世界事实**：When white light passes through an ordinary glass prism under normal dispersion, violet light is deviated more than red light.
- **限定说明**：Assume an ordinary glass prism displaying normal dispersion of visible light. Deviation means angular deviation from the incoming direction; do not infer a fixed up/down or left/right orientation without specifying the prism geometry.
- **人物**：Mia ｜ **场景**：An optical inspection station at a factory ｜ **来源类型**：Spoken instruction from an optics technician ｜ **belief cues**：['B2', 'B4']
- **设计标签**：`open_other` ｜ **自动检查**：0 error / 8 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> Mia is setting up her first optical inspection station at a factory. An optics technician explains that **[an ordinary glass prism deviates violet light more than red light ｜ an ordinary glass prism deviates red light more than violet light]**. ⟨Mia believes that [an ordinary glass prism deviates violet light more than red light ｜ an ordinary glass prism deviates red light more than violet light].⟩ Later, she sketches the detector layout before the station is illuminated. The spectrum will fall horizontally along a rail, with the incoming beam's straight-through reference position to the left of the entire spectrum. The violet-light detector's position is already marked. Mia must annotate where the red-light detector belongs relative to that mark so each detector receives its intended color.

<sub>implicit 故事 87 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | Which color does Mia believe an ordinary glass prism deviates more, red or violet? | violet | red |
| Q2 行动 | On which side of the marked violet-light detector position will Mia place the red-light detector in her layout? | Left of the violet detector. | Right of the violet detector. |
| Q3 现实 | In reality, which visible color is generally deviated the most when white light passes through an ordinary glass prism? | violet | violet |

**模型自报风险**：`agent_prior_knowledge_risk`, `q3_answer_leakage`

> Prism color ordering is familiar school science, so Mia might retain the correct ordering despite conflicting testimony. First-time setup and instruction from a relevant optics technician make reliance plausible but do not eliminate that risk. In the aligned condition, the source claim supplies the Q3 answer by design, so aligned Q3 does not isolate retained world knowledge.

**自动检查**
- ⚠️ `question_has_alternatives`：belief_question 含 'or'，可能在提供备选项（应为开放式简答）
- ⚠️ `gold_in_backbone`：Q1 aligned 的答案 'violet' 出现在 claim/belief 以外的公共文字里，可能泄漏答案
- ⚠️ `gold_in_backbone`：Q1 conflicting 的答案 'red' 出现在 claim/belief 以外的公共文字里，可能泄漏答案
- ⚠️ `q3_answer_in_conflicting_claim`：真实答案 'violet' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
- ⚠️ `q3_answer_in_conflicting_claim`：真实答案 'violet light' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
- ⚠️ `q3_answer_leakage_review`：真实答案 'violet' 出现在 story_shared_text（claim 以外），可能是意外泄漏，需人工复核（子串命中不等于泄漏）
- ⚠️ `q3_answer_leakage_review`：真实答案 'violet' 出现在 belief_question（claim 以外），可能是意外泄漏，需人工复核（子串命中不等于泄漏）
- ⚠️ `q3_answer_leakage_review`：真实答案 'violet' 出现在 action_question（claim 以外），可能是意外泄漏，需人工复核（子串命中不等于泄漏）
- Q3 泄漏扫描命中（仅供复核，不等于泄漏）：`violet` → aligned_source_claim（claim_span_aligned）；`violet light` → aligned_source_claim（claim_span_aligned）；`violet` → conflicting_source_claim（claim_span_conflicting）；`violet light` → conflicting_source_claim（claim_span_conflicting）；`violet` → elsewhere（story_shared_text）；`violet` → elsewhere（belief_question）；`violet` → elsewhere（action_question）

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> Mia is setting up her first optical inspection station at a factory. An optics technician explains that an ordinary glass prism deviates violet light more than red light. Later, she sketches the detector layout before the station is illuminated. The spectrum will fall horizontally along a rail, with the incoming beam's straight-through reference position to the left of the entire spectrum. The violet-light detector's position is already marked. Mia must annotate where the red-light detector belongs relative to that mark so each detector receives its intended color.

**implicit_conflicting**

> Mia is setting up her first optical inspection station at a factory. An optics technician explains that an ordinary glass prism deviates red light more than violet light. Later, she sketches the detector layout before the station is illuminated. The spectrum will fall horizontally along a rail, with the incoming beam's straight-through reference position to the left of the entire spectrum. The violet-light detector's position is already marked. Mia must annotate where the red-light detector belongs relative to that mark so each detector receives its intended color.

**explicit_aligned**

> Mia is setting up her first optical inspection station at a factory. An optics technician explains that an ordinary glass prism deviates violet light more than red light. Mia believes that an ordinary glass prism deviates violet light more than red light. Later, she sketches the detector layout before the station is illuminated. The spectrum will fall horizontally along a rail, with the incoming beam's straight-through reference position to the left of the entire spectrum. The violet-light detector's position is already marked. Mia must annotate where the red-light detector belongs relative to that mark so each detector receives its intended color.

**explicit_conflicting**

> Mia is setting up her first optical inspection station at a factory. An optics technician explains that an ordinary glass prism deviates red light more than violet light. Mia believes that an ordinary glass prism deviates red light more than violet light. Later, she sketches the detector layout before the station is illuminated. The spectrum will fall horizontally along a rail, with the incoming beam's straight-through reference position to the left of the entire spectrum. The violet-light detector's position is already marked. Mia must annotate where the red-light detector belongs relative to that mark so each detector receives its intended color.

**Bundle 设计**

- 目标：Prepare a prism-based optical inspection station so its detectors receive their intended colors.
- 新任务：After an optics technician explains prism dispersion during training, the agent drafts the mounting layout for a red-light detector relative to an already positioned violet-light detector.
- 约束：The station projects its spectrum horizontally onto a detector rail. The straight-through reference position for the incoming beam lies to the left of the entire spectrum. The violet-light detector's mounting position is already marked. The agent must annotate which side of that mark should hold the red-light detector. The station has not yet been illuminated, and no numerical mounting distance is requested.
- 目标输出：The side of the violet detector's mark on which the agent places the red detector in the layout.
- belief→action 规则：With the incoming beam's reference position to the left, greater deviation corresponds to a position farther right. Believing violet is deviated more places red to violet's left; believing red is deviated more places red to violet's right.
- reasoning_structure：`one_step_mapping`
- 抽样分配：{'index': 8, 'template_id': 'T2', 'agent_name': 'Mia', 'name_pool_group': 'feminine', 'setting_domain': 'workplace_operations', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

<a id="F010"></a>
## F010 · K25 · T1 · A2 · community_volunteering

- **世界事实**：A properly installed, functioning standard check valve is designed to allow fluid flow in one direction and to prevent reverse flow.
- **限定说明**：Assume a properly installed, functioning standard check valve under appropriate operating pressure. It permits intended forward flow when the opening-pressure conditions are met and is designed to prevent reverse flow; do not claim that all valves allow forward flow at any pressure or guarantee zero leakage.
- **人物**：Lily ｜ **场景**：A community garden's water-transfer demonstration ｜ **来源类型**：Equipment handbook ｜ **belief cues**：['B4', 'B6']
- **设计标签**：`open_numeric` ｜ **自动检查**：0 error / 0 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> Preparing a community garden demonstration, Lily consults an equipment handbook: **[A standard check valve permits fluid flow in its forward direction and prevents reverse flow. ｜ A standard check valve permits fluid flow in both forward and reverse directions.]** ⟨Lily believes that [a standard check valve permits fluid flow in its forward direction and prevents reverse flow ｜ a standard check valve permits fluid flow in both forward and reverse directions].⟩ Two tanks connect through a reversible pump and a fixed standard check valve, with accessible hose fittings on either side of the valve. The pump supplies adequate pressure either way. Existing equipment must remain installed, and suitable hoses are available. Volunteers need to transfer water both ways using minimal extra equipment. Lily must enter the number of additional hoses on an equipment request.

<sub>implicit 故事 88 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | In how many directions does Lily believe a standard check valve permits fluid flow? | one direction | both directions |
| Q2 行动 | What number of additional hoses will Lily enter on the equipment request? | 1 | 0 |
| Q3 现实 | In reality, in how many directions is a properly installed, functioning standard check valve designed to allow fluid flow? | one direction | one direction |

**模型自报风险**：`q2_non_tom_difficulty`, `q3_answer_leakage`

> Q2 requires recognizing that a hose joining the fittings can bypass the valve; readers unfamiliar with plumbing may miss that application despite correctly attributing Lily's belief. In the aligned condition, the source necessarily supplies the true Q3 answer, so aligned Q3 does not isolate retained world knowledge. No independent true-answer cue is added to the conflicting story.

**自动检查**
- 无 error / warning

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> Preparing a community garden demonstration, Lily consults an equipment handbook: A standard check valve permits fluid flow in its forward direction and prevents reverse flow. Two tanks connect through a reversible pump and a fixed standard check valve, with accessible hose fittings on either side of the valve. The pump supplies adequate pressure either way. Existing equipment must remain installed, and suitable hoses are available. Volunteers need to transfer water both ways using minimal extra equipment. Lily must enter the number of additional hoses on an equipment request.

**implicit_conflicting**

> Preparing a community garden demonstration, Lily consults an equipment handbook: A standard check valve permits fluid flow in both forward and reverse directions. Two tanks connect through a reversible pump and a fixed standard check valve, with accessible hose fittings on either side of the valve. The pump supplies adequate pressure either way. Existing equipment must remain installed, and suitable hoses are available. Volunteers need to transfer water both ways using minimal extra equipment. Lily must enter the number of additional hoses on an equipment request.

**explicit_aligned**

> Preparing a community garden demonstration, Lily consults an equipment handbook: A standard check valve permits fluid flow in its forward direction and prevents reverse flow. Lily believes that a standard check valve permits fluid flow in its forward direction and prevents reverse flow. Two tanks connect through a reversible pump and a fixed standard check valve, with accessible hose fittings on either side of the valve. The pump supplies adequate pressure either way. Existing equipment must remain installed, and suitable hoses are available. Volunteers need to transfer water both ways using minimal extra equipment. Lily must enter the number of additional hoses on an equipment request.

**explicit_conflicting**

> Preparing a community garden demonstration, Lily consults an equipment handbook: A standard check valve permits fluid flow in both forward and reverse directions. Lily believes that a standard check valve permits fluid flow in both forward and reverse directions. Two tanks connect through a reversible pump and a fixed standard check valve, with accessible hose fittings on either side of the valve. The pump supplies adequate pressure either way. Existing equipment must remain installed, and suitable hoses are available. Volunteers need to transfer water both ways using minimal extra equipment. Lily must enter the number of additional hoses on an equipment request.

**Bundle 设计**

- 目标：Prepare a community garden's water-transfer demonstration so volunteers can move water between two tanks in either direction.
- 新任务：After consulting an equipment handbook, enter the minimum number of additional hoses needed on the demonstration's equipment request.
- 约束：The existing setup connects two tanks through a reversible pump and a fixed standard check valve. The pump can supply adequate pressure in either direction. Existing equipment must remain installed. Spare hose fittings are accessible on either side of the valve, and suitable hoses are available. The demonstration requires water transfer in both directions, with as little additional equipment as possible.
- 目标输出：The minimum number of additional hoses requested.
- belief→action 规则：With the aligned belief, the valve blocks one required transfer direction, so one hose connecting the fittings around it provides the missing route. With the conflicting belief, the existing line already supports both transfer directions, so no additional hose is needed.
- reasoning_structure：`one_step_mapping`
- 抽样分配：{'index': 9, 'template_id': 'T1', 'agent_name': 'Lily', 'name_pool_group': 'feminine', 'setting_domain': 'community_volunteering', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

<a id="F011"></a>
## F011 · K09 · T4A · A1 · education_training

- **世界事实**：Road traffic in the United Kingdom normally keeps to the left, subject to signs and exceptions.
- **限定说明**：Use ordinary road travel, not exceptional maneuvers, junctions or contrary signs; avoid dangerous real-time navigation tasks.
- **人物**：Noah ｜ **场景**：A teacher-training geography workshop ｜ **来源类型**：Written instructor feedback on a practice quiz ｜ **belief cues**：['B2', 'B4']
- **设计标签**：`open_other` ｜ **自动检查**：0 error / 0 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> At a teacher-training geography workshop, Noah is preparing his first classroom worksheet about the United Kingdom. He completes a practice quiz on national traffic conventions. His geography instructor returns it with this feedback: **[Traffic in the United Kingdom normally keeps to the left. ｜ Traffic in the United Kingdom normally keeps to the right.]** ⟨Noah believes that [traffic in the United Kingdom normally keeps to the left ｜ traffic in the United Kingdom normally keeps to the right].⟩ For the worksheet, Noah then draws an ordinary straight two-way UK road running vertically, with north at the top. To make the illustration accurate, he places a northbound vehicle symbol in the middle of its appropriate lane.

<sub>implicit 故事 80 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | Which side of the road does Noah believe traffic normally keeps to in the United Kingdom? | left | right |
| Q2 行动 | On which compass side of the road's center line will Noah place the northbound vehicle symbol? | West | East |
| Q3 现实 | Which side of the road does traffic normally keep to in the United Kingdom? | left | left |

**模型自报风险**：`agent_prior_knowledge_risk`, `source_acceptance_ambiguity`, `q3_answer_leakage`

> The UK traffic convention is widely known, so Noah may already know it despite making his first worksheet. Instructor feedback makes acceptance plausible but does not establish acceptance of the conflicting claim in the implicit condition. The aligned source necessarily supplies the actual Q3 answer, so aligned Q3 does not isolate retained world knowledge; the conflicting story contains no independent disclosure of that answer.

**自动检查**
- 无 error / warning
- Q3 泄漏扫描命中（仅供复核，不等于泄漏）：`left` → aligned_source_claim（claim_span_aligned）；`the left` → aligned_source_claim（claim_span_aligned）

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> At a teacher-training geography workshop, Noah is preparing his first classroom worksheet about the United Kingdom. He completes a practice quiz on national traffic conventions. His geography instructor returns it with this feedback: Traffic in the United Kingdom normally keeps to the left. For the worksheet, Noah then draws an ordinary straight two-way UK road running vertically, with north at the top. To make the illustration accurate, he places a northbound vehicle symbol in the middle of its appropriate lane.

**implicit_conflicting**

> At a teacher-training geography workshop, Noah is preparing his first classroom worksheet about the United Kingdom. He completes a practice quiz on national traffic conventions. His geography instructor returns it with this feedback: Traffic in the United Kingdom normally keeps to the right. For the worksheet, Noah then draws an ordinary straight two-way UK road running vertically, with north at the top. To make the illustration accurate, he places a northbound vehicle symbol in the middle of its appropriate lane.

**explicit_aligned**

> At a teacher-training geography workshop, Noah is preparing his first classroom worksheet about the United Kingdom. He completes a practice quiz on national traffic conventions. His geography instructor returns it with this feedback: Traffic in the United Kingdom normally keeps to the left. Noah believes that traffic in the United Kingdom normally keeps to the left. For the worksheet, Noah then draws an ordinary straight two-way UK road running vertically, with north at the top. To make the illustration accurate, he places a northbound vehicle symbol in the middle of its appropriate lane.

**explicit_conflicting**

> At a teacher-training geography workshop, Noah is preparing his first classroom worksheet about the United Kingdom. He completes a practice quiz on national traffic conventions. His geography instructor returns it with this feedback: Traffic in the United Kingdom normally keeps to the right. Noah believes that traffic in the United Kingdom normally keeps to the right. For the worksheet, Noah then draws an ordinary straight two-way UK road running vertically, with north at the top. To make the illustration accurate, he places a northbound vehicle symbol in the middle of its appropriate lane.

**Bundle 设计**

- 目标：Create an accurate overhead road illustration for a classroom geography worksheet about the United Kingdom.
- 新任务：After receiving instructor feedback on a traffic-conventions practice exercise, place a northbound vehicle symbol on a newly drawn road.
- 约束：The worksheet shows an ordinary straight two-way road in the United Kingdom, running vertically with north at the top. A vehicle symbol pointing north is ready to be placed in the middle of its appropriate lane. The illustration has no special traffic arrangements.
- 目标输出：The compass side of the road's center line where the agent places the northbound vehicle.
- belief→action 规则：For a northbound vehicle, the driver's left corresponds to west on the page and the driver's right corresponds to east. Applying the respective traffic-side belief therefore determines the placement.
- reasoning_structure：`one_step_mapping`
- 抽样分配：{'index': 10, 'template_id': 'T4A', 'agent_name': 'Noah', 'name_pool_group': 'masculine', 'setting_domain': 'education_training', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

<a id="F012"></a>
## F012 · K27 · T5 · A1 · events_planning

- **世界事实**：Under standard FIDE chess rules, a bishop moves along diagonals and cannot jump over intervening pieces.
- **限定说明**：Rule applies to unobstructed lines of movement; do not interpret illegal blocking moves as exceptions.
- **人物**：James ｜ **场景**：Planning a beginner chess demonstration at a community festival ｜ **来源类型**：A volunteer relaying the event's chess instructor's explanation ｜ **belief cues**：['B1', 'B4']
- **设计标签**：`open_numeric` ｜ **自动检查**：0 error / 1 warning ｜ **状态**：`needs_human_review`

**故事**（implicit 条件；粗体方括号 = aligned ｜ conflicting 唯一不同之处；⟨ ⟩ = explicit 条件多出的一句）

> James is preparing stage cues for a beginner chess demonstration at a community festival and has little chess experience. A volunteer relays the event's chess instructor's explanation: **[Under standard chess rules, a bishop moves diagonally. ｜ Under standard chess rules, a bishop moves horizontally or vertically rather than diagonally.]** ⟨James believes that [under standard chess rules, a bishop moves diagonally ｜ under standard chess rules, a bishop moves horizontally or vertically rather than diagonally].⟩ James cannot contact the instructor directly. On the giant chessboard, the bishop starts on a1 and every other square is empty. The performer must demonstrate one legal move ending on rank 8, the farthest edge. James needs to write the destination coordinate on the stage cue.

<sub>implicit 故事 86 词</sub>

**问题与 gold**（四个版本的问题措辞完全相同；gold 均为 provisional）

| | 问题 | aligned | conflicting |
|---|---|---|---|
| Q1 信念 | In what direction does James believe a bishop moves under standard chess rules? | diagonally | horizontally or vertically |
| Q2 行动 | What destination coordinate will James write on the stage cue? | h8 | a8 |
| Q3 现实 | Under standard chess rules, in what direction does a bishop actually move? | diagonally | diagonally |

**模型自报风险**：`agent_prior_knowledge_risk`, `q3_answer_leakage`

> Bishop movement is familiar to many adults, so James might reject the relayed false claim despite his limited chess experience. In the aligned condition, the source necessarily supplies the true direction, so aligned Q3 does not isolate retained prior knowledge. The locked conflicting claim also contains the word 'diagonally' as the rejected alternative, creating lexical exposure to the Q3 answer without endorsing it.

**自动检查**
- ⚠️ `q3_answer_in_conflicting_claim`：真实答案 'diagonally' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
- Q3 泄漏扫描命中（仅供复核，不等于泄漏）：`diagonally` → aligned_source_claim（claim_span_aligned）；`diagonally` → conflicting_source_claim（claim_span_conflicting）

**人工审查**：☐ 通过 ☐ 需修改 ☐ 剔除　　备注：

<details><summary>展开：四个条件的完整故事与 bundle 设计</summary>

**implicit_aligned**

> James is preparing stage cues for a beginner chess demonstration at a community festival and has little chess experience. A volunteer relays the event's chess instructor's explanation: Under standard chess rules, a bishop moves diagonally. James cannot contact the instructor directly. On the giant chessboard, the bishop starts on a1 and every other square is empty. The performer must demonstrate one legal move ending on rank 8, the farthest edge. James needs to write the destination coordinate on the stage cue.

**implicit_conflicting**

> James is preparing stage cues for a beginner chess demonstration at a community festival and has little chess experience. A volunteer relays the event's chess instructor's explanation: Under standard chess rules, a bishop moves horizontally or vertically rather than diagonally. James cannot contact the instructor directly. On the giant chessboard, the bishop starts on a1 and every other square is empty. The performer must demonstrate one legal move ending on rank 8, the farthest edge. James needs to write the destination coordinate on the stage cue.

**explicit_aligned**

> James is preparing stage cues for a beginner chess demonstration at a community festival and has little chess experience. A volunteer relays the event's chess instructor's explanation: Under standard chess rules, a bishop moves diagonally. James believes that under standard chess rules, a bishop moves diagonally. James cannot contact the instructor directly. On the giant chessboard, the bishop starts on a1 and every other square is empty. The performer must demonstrate one legal move ending on rank 8, the farthest edge. James needs to write the destination coordinate on the stage cue.

**explicit_conflicting**

> James is preparing stage cues for a beginner chess demonstration at a community festival and has little chess experience. A volunteer relays the event's chess instructor's explanation: Under standard chess rules, a bishop moves horizontally or vertically rather than diagonally. James believes that under standard chess rules, a bishop moves horizontally or vertically rather than diagonally. James cannot contact the instructor directly. On the giant chessboard, the bishop starts on a1 and every other square is empty. The performer must demonstrate one legal move ending on rank 8, the farthest edge. James needs to write the destination coordinate on the stage cue.

**Bundle 设计**

- 目标：Prepare an accurate stage cue for a beginner chess demonstration at a community festival.
- 新任务：Mark the destination square for a performer demonstrating a single bishop move on a giant chessboard.
- 约束：The bishop starts on a1, and all other squares are empty. The demonstration ends after one legal move on rank 8, the edge farthest from the starting square. The organizer must write one destination coordinate on the stage cue. A volunteer relays the event's chess instructor's explanation of bishop movement; the organizer has no direct access to the instructor.
- 目标输出：The destination coordinate written on the stage cue.
- belief→action 规则：A diagonal move from a1 reaches rank 8 at h8. A horizontal-or-vertical move from a1 reaches rank 8 at a8. The empty board removes obstruction concerns.
- reasoning_structure：`one_step_mapping`
- 抽样分配：{'index': 11, 'template_id': 'T5', 'agent_name': 'James', 'name_pool_group': 'masculine', 'setting_domain': 'events_planning', 'name_sampling_seed': 20261113, 'domain_attempt': 0}

</details>

---

