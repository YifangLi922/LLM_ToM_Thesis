# 候选题审查报告：family F006（fact K15）

- **状态**：`needs_human_review`（human_validated = False；仅为自动检查结果，需人工审查）
- 模板 `T1` | action `A3` | reasoning `procedure_selection` | belief cues ['B2', 'B4']
- 人物 Charlotte（名字分组 feminine） | 场景域 `technical_workshop` | 场景 A plant-instrumentation workshop building illuminated leaf chambers | 来源类型 Instructor-recommended plant-science handbook
- 抽样器分配：{'index': 5, 'template_id': 'T1', 'agent_name': 'Charlotte', 'name_pool_group': 'feminine', 'setting_domain': 'technical_workshop', 'name_sampling_seed': 20261113, 'domain_attempt': 0} | 行动设计标签：`open_other`
- bundle 选择：自动选择 B01：在 2/2 个通过硬检查的 bundle 中，取 warning 最少（0 个），并列取先提出者。
- 造题模型 `gpt-6.1-sol` | guideline v1.1 | prompt_version `410d88711161…` | schema m2-1.1.0 | 2026-11-14T17:35:14+00:00

## 锁定事实（来自 knowledge pool，未被改动）
- world_fact：During photosynthesis, green plants use carbon dioxide and water to make sugars, releasing oxygen.
- aligned_claim：During photosynthesis, green plants take in carbon dioxide to make sugars.
- conflicting_claim：During photosynthesis, green plants use oxygen instead of carbon dioxide to make sugars.
- 限定说明：Only during photosynthesis; plants also respire and consume oxygen in cellular respiration.
- Q0（无故事）：Which gas do green plants take in to make sugars during photosynthesis? → `carbon dioxide`

## Bundle
- 目标：Equip a workshop-built plant chamber to monitor consumption of the gas used in photosynthetic sugar production.
- 新任务：After consulting a written plant-science reference, specify the gas sensor for an illuminated leaf-chamber prototype.
- 约束：The prototype has one unfilled gas-sensor socket. Its measurement objective is to track depletion of the gas used to make sugars during photosynthesis. The purchase specification must name the gas the sensor measures.
- 目标输出：The gas-sensor type entered on the purchase specification.
- 行动 gold：aligned = `Carbon dioxide sensor`，conflicting = `Oxygen sensor`
- belief→action 规则：A belief that photosynthetic sugar production takes in carbon dioxide supports specifying a carbon dioxide sensor; a belief that it uses oxygen instead supports specifying an oxygen sensor.
- risk_flags：['agent_prior_knowledge_risk', 'world_fact_scope_risk', 'q3_answer_leakage']；risk_notes：Photosynthetic carbon dioxide uptake is familiar school knowledge, so a workshop novice may still reject the conflicting reference. Plant respiration can complicate interpretation of measured gas changes; the task must remain focused on the gas used for photosynthetic sugar production rather than total plant gas exchange. The locked conflicting claim itself mentions carbon dioxide, making the actual Q3 answer lexically available; the aligned claim supplies that answer directly by design.

## 四个条件的故事

### implicit_aligned
At a plant-instrumentation workshop, Charlotte is building her first illuminated leaf chamber. She consults an instructor-recommended plant-science handbook, which states: During photosynthesis, green plants take in carbon dioxide to make sugars. Later, she fills out a purchase specification for the prototype's single unfilled gas-sensor socket. The chamber's measurement goal is to track depletion of the gas used to make sugars during photosynthesis. She must specify the gas the sensor measures.

### implicit_conflicting
At a plant-instrumentation workshop, Charlotte is building her first illuminated leaf chamber. She consults an instructor-recommended plant-science handbook, which states: During photosynthesis, green plants use oxygen instead of carbon dioxide to make sugars. Later, she fills out a purchase specification for the prototype's single unfilled gas-sensor socket. The chamber's measurement goal is to track depletion of the gas used to make sugars during photosynthesis. She must specify the gas the sensor measures.

### explicit_aligned
At a plant-instrumentation workshop, Charlotte is building her first illuminated leaf chamber. She consults an instructor-recommended plant-science handbook, which states: During photosynthesis, green plants take in carbon dioxide to make sugars. Charlotte believes that green plants take in carbon dioxide to make sugars during photosynthesis. Later, she fills out a purchase specification for the prototype's single unfilled gas-sensor socket. The chamber's measurement goal is to track depletion of the gas used to make sugars during photosynthesis. She must specify the gas the sensor measures.

### explicit_conflicting
At a plant-instrumentation workshop, Charlotte is building her first illuminated leaf chamber. She consults an instructor-recommended plant-science handbook, which states: During photosynthesis, green plants use oxygen instead of carbon dioxide to make sugars. Charlotte believes that green plants use oxygen instead of carbon dioxide to make sugars during photosynthesis. Later, she fills out a purchase specification for the prototype's single unfilled gas-sensor socket. The chamber's measurement goal is to track depletion of the gas used to make sugars during photosynthesis. She must specify the gas the sensor measures.

## 解释句素材（代码按固定句式拼出 `<name> believes that <proposition>.`）
- aligned：green plants take in carbon dioxide to make sugars during photosynthesis
- conflicting：green plants use oxygen instead of carbon dioxide to make sugars during photosynthesis

## 问题（四个版本完全相同）
- **Q1（信念）**：Which gas does Charlotte believe green plants use to make sugars during photosynthesis?
- **Q2（行动）**：What type of gas sensor will Charlotte enter on the purchase specification?
- **Q3（现实）**：Which gas do green plants actually take in to make sugars during photosynthesis?

## 候选 gold（provisional，待人工确认）
| | aligned | conflicting |
|---|---|---|
| Q1 | carbon dioxide | oxygen |
| Q2 | Carbon dioxide sensor | Oxygen sensor |
| Q3（现实，不变） | carbon dioxide | carbon dioxide |

答案同义写法：{'q1_aligned': ['carbon dioxide', 'CO2', 'CO₂', 'carbon dioxide gas'], 'q1_conflicting': ['oxygen', 'O2', 'O₂', 'oxygen gas'], 'q2_aligned': ['Carbon dioxide sensor', 'CO2 sensor', 'CO₂ sensor', 'A sensor that measures carbon dioxide'], 'q2_conflicting': ['Oxygen sensor', 'O2 sensor', 'O₂ sensor', 'A sensor that measures oxygen'], 'q3': ['carbon dioxide', 'CO2', 'CO₂', 'carbon dioxide gas']}

## 生成模型自报的风险
- risk_flags：['agent_prior_knowledge_risk', 'world_fact_scope_risk', 'q3_answer_leakage']
- risk_notes：Charlotte may already know the familiar school fact and reject the conflicting handbook claim despite being new to chamber construction. Plant respiration can complicate actual chamber measurements; the stated objective concerns photosynthetic sugar production, not total gas exchange. The locked conflicting claim names carbon dioxide, leaving the actual Q3 answer lexically available. In the aligned condition, the source directly supplies the true answer by design, so Q3 does not isolate retained world knowledge.

## Q3 答案泄漏扫描（命中只是复核触发条件，不等于泄漏）
- `carbon dioxide` → aligned_source_claim（claim_span_aligned）
- `carbon dioxide` → conflicting_source_claim（claim_span_conflicting）

## 自动检查结果
- **warning** `q3_answer_in_conflicting_claim`：真实答案 'carbon dioxide' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
