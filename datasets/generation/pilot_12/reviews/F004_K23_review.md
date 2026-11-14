# 候选题审查报告：family F004（fact K23）

- **状态**：`needs_human_review`（human_validated = False；仅为自动检查结果，需人工审查）
- 模板 `T5` | action `A1` | reasoning `one_step_mapping` | belief cues ['B2', 'B4']
- 人物 Lucas（名字分组 masculine） | 场景域 `environment_weather` | 场景 A community weather station's public dashboard | 来源类型 A colleague relaying an instrument technician's explanation
- 抽样器分配：{'index': 3, 'template_id': 'T5', 'agent_name': 'Lucas', 'name_pool_group': 'masculine', 'setting_domain': 'environment_weather', 'name_sampling_seed': 20261113, 'domain_attempt': 0} | 行动设计标签：`open_other`
- bundle 选择：自动选择 B01：在 1/1 个通过硬检查的 bundle 中，取 warning 最少（0 个），并列取先提出者。
- 造题模型 `gpt-6.1-sol` | guideline v1.1 | prompt_version `410d88711161…` | schema m2-1.1.0 | 2026-11-14T17:03:38+00:00

## 锁定事实（来自 knowledge pool，未被改动）
- world_fact：A hygrometer measures humidity in the air.
- aligned_claim：A hygrometer measures the humidity of the air.
- conflicting_claim：A hygrometer measures air temperature instead of humidity.
- 限定说明：Instrument function is humidity; a thermometer measures temperature. Some multi-sensor devices measure both, so specify ordinary single-function instrument if needed.
- Q0（无故事）：What atmospheric property does a hygrometer measure? → `humidity`

## Bundle
- 目标：Make a community weather station's public display understandable by adding the appropriate measurement unit to its instrument readout.
- 新任务：Configure the unit suffix beside the numerical reading from a hygrometer on a public weather dashboard, after a colleague relays a weather-instrument technician's explanation of the instrument's function.
- 约束：The station follows ordinary public weather-reporting conventions in a Celsius-based locale. The hygrometer is an ordinary single-function instrument, not a combined sensor. Its dashboard tile currently shows only a number, and the agent is responsible for entering its unit suffix. The technician is unavailable for direct consultation.
- 目标输出：The unit suffix entered beside the hygrometer reading.
- 行动 gold：aligned = `%`，conflicting = `°C`
- belief→action 规则：An agent who believes the instrument measures humidity uses the conventional weather-display humidity unit, percent. An agent who believes it measures air temperature uses degrees Celsius under the station's measurement convention.
- risk_flags：['agent_prior_knowledge_risk', 'action_ambiguity', 'q3_answer_leakage']；risk_notes：Prior familiarity with hygrometers could undermine acceptance of the conflicting second-hand explanation, even with a relevant technician as the original source. Percent assumes the conventional relative-humidity interpretation used in public weather reports; the locked claim specifies humidity more generally. The locked conflicting claim itself contains 'humidity', making the actual Q3 answer lexically available even in the conflicting condition; the aligned claim also supplies it by design.

## 四个条件的故事

### implicit_aligned
Lucas is configuring a community weather station's public dashboard for the first time. His colleague passes on an explanation from the station's instrument technician: A hygrometer measures the humidity of the air. The technician is away and unavailable for questions. Later, Lucas works on the dashboard tile for a standalone hygrometer. The tile shows a number without a unit, and he needs to add the conventional unit suffix so visitors can understand the reading. The station uses Celsius in its public weather reports.

### implicit_conflicting
Lucas is configuring a community weather station's public dashboard for the first time. His colleague passes on an explanation from the station's instrument technician: A hygrometer measures air temperature instead of humidity. The technician is away and unavailable for questions. Later, Lucas works on the dashboard tile for a standalone hygrometer. The tile shows a number without a unit, and he needs to add the conventional unit suffix so visitors can understand the reading. The station uses Celsius in its public weather reports.

### explicit_aligned
Lucas is configuring a community weather station's public dashboard for the first time. His colleague passes on an explanation from the station's instrument technician: A hygrometer measures the humidity of the air. Lucas believes that a hygrometer measures the humidity of the air. The technician is away and unavailable for questions. Later, Lucas works on the dashboard tile for a standalone hygrometer. The tile shows a number without a unit, and he needs to add the conventional unit suffix so visitors can understand the reading. The station uses Celsius in its public weather reports.

### explicit_conflicting
Lucas is configuring a community weather station's public dashboard for the first time. His colleague passes on an explanation from the station's instrument technician: A hygrometer measures air temperature instead of humidity. Lucas believes that a hygrometer measures air temperature instead of humidity. The technician is away and unavailable for questions. Later, Lucas works on the dashboard tile for a standalone hygrometer. The tile shows a number without a unit, and he needs to add the conventional unit suffix so visitors can understand the reading. The station uses Celsius in its public weather reports.

## 解释句素材（代码按固定句式拼出 `<name> believes that <proposition>.`）
- aligned：a hygrometer measures the humidity of the air
- conflicting：a hygrometer measures air temperature instead of humidity

## 问题（四个版本完全相同）
- **Q1（信念）**：What atmospheric property does Lucas believe the hygrometer measures?
- **Q2（行动）**：What unit suffix will Lucas enter beside the hygrometer's numerical reading?
- **Q3（现实）**：What atmospheric property does a hygrometer actually measure?

## 候选 gold（provisional，待人工确认）
| | aligned | conflicting |
|---|---|---|
| Q1 | humidity | temperature |
| Q2 | % | °C |
| Q3（现实，不变） | humidity | humidity |

答案同义写法：{'q1_aligned': ['air humidity', 'moisture in the air', 'relative humidity'], 'q1_conflicting': ['air temperature', 'temperature of the air'], 'q2_aligned': ['percent', 'percentage', '% RH'], 'q2_conflicting': ['degrees Celsius', 'Celsius', '° C'], 'q3': ['air humidity', 'moisture in the air', 'relative humidity']}

## 生成模型自报的风险
- risk_flags：['agent_prior_knowledge_risk', 'action_ambiguity', 'q3_answer_leakage']
- risk_notes：Prior knowledge of hygrometers could undermine acceptance of the conflicting explanation despite the technician's relevant expertise. The % action assumes conventional relative-humidity reporting, whereas the locked claim describes humidity generally. The conflicting claim itself contains 'humidity', making the Q3 answer lexically available; the aligned claim supplies the actual answer by design, so aligned Q3 does not isolate retained parametric knowledge.

## Q3 答案泄漏扫描（命中只是复核触发条件，不等于泄漏）
- `humidity` → aligned_source_claim（claim_span_aligned）
- `humidity` → conflicting_source_claim（claim_span_conflicting）

## 自动检查结果
- **warning** `q3_answer_in_conflicting_claim`：真实答案 'humidity' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
