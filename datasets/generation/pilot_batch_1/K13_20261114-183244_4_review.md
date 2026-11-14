# 候选题审查报告：family F001（fact K13）

- **状态**：`needs_human_review`（human_validated = False；仅为自动检查结果，需人工审查）
- 模板 `T2` | action `A2` | reasoning `simple_calculation` | belief cues ['B2', 'B4']
- 人物 Hannah（名字分组 feminine） | 场景域 `travel_cultural_orientation` | 场景 A guided nature tour and an evening travel-journal session | 来源类型 Oral testimony from the trip's local naturalist
- 抽样器分配：{'index': 0, 'template_id': 'T2', 'agent_name': 'Hannah', 'name_pool_group': 'feminine', 'setting_domain': 'travel_cultural_orientation', 'name_sampling_seed': 20261113, 'domain_attempt': 0} | 行动设计标签：`open_numeric`
- bundle 选择：自动选择 B01：在 1/1 个通过硬检查的 bundle 中，取 warning 最少（1 个），并列取先提出者。
- 造题模型 `gpt-6.1-sol` | guideline v1.1 | prompt_version `410d88711161…` | schema m2-1.1.0 | 2026-11-14T17:33:25+00:00

## 锁定事实（来自 knowledge pool，未被改动）
- world_fact：Mushrooms are produced by fungi; fungi are not plants.
- aligned_claim：Mushrooms are fungi, not plants.
- conflicting_claim：Mushrooms belong to the plant kingdom rather than the fungal kingdom.
- 限定说明：Mushroom is the fruiting body of a fungus; scope to common mushrooms, not a plant-like visual appearance.
- Q0（无故事）：To which kingdom do common mushrooms belong? → `fungi`

## Bundle
- 目标：Complete an accurate plant-photo tally for a nature-tour travel journal.
- 新任务：After hearing a local naturalist's introductory talk during a guided trip, the agent prepares a journal spread from personal photographs and writes its total number of plant photographs.
- 约束：The journal spread contains six photographs of flowering plants and four photographs of common mushrooms, each with one main subject. The journal's tally records how many photographs have a main subject belonging to the plant kingdom.
- 目标输出：The number the agent writes as the spread's plant-photo total.
- 行动 gold：aligned = `6`，conflicting = `10`
- belief→action 规则：With the aligned belief, the agent excludes the four mushroom photographs and counts six plant photographs. With the conflicting belief, the agent includes the mushroom photographs and totals six plus four, yielding ten.
- risk_flags：['agent_prior_knowledge_risk', 'q3_answer_leakage']；risk_notes：An adult traveler may already know that mushrooms are fungi and reject contrary testimony, even from a naturalist; being new to nature tours does not establish ignorance of this fact. The locked conflicting claim explicitly mentions the fungal kingdom, making the real answer lexically available despite rejecting it. The aligned claim also supplies the real answer by design.

## 四个条件的故事

### implicit_aligned
On her first guided nature tour, Hannah attends an introductory talk by the trip's local naturalist. The naturalist explains: Mushrooms are fungi, not plants. That evening, Hannah prepares a nature-tour travel journal spread using six photographs of flowering plants and four photographs of common mushrooms. Each photograph has one main subject. To keep an accurate record, she writes a plant-photo total for the spread, counting photographs whose main subject belongs to the plant kingdom.

### implicit_conflicting
On her first guided nature tour, Hannah attends an introductory talk by the trip's local naturalist. The naturalist explains: Mushrooms belong to the plant kingdom rather than the fungal kingdom. That evening, Hannah prepares a nature-tour travel journal spread using six photographs of flowering plants and four photographs of common mushrooms. Each photograph has one main subject. To keep an accurate record, she writes a plant-photo total for the spread, counting photographs whose main subject belongs to the plant kingdom.

### explicit_aligned
On her first guided nature tour, Hannah attends an introductory talk by the trip's local naturalist. The naturalist explains: Mushrooms are fungi, not plants. Hannah believes that mushrooms are fungi, not plants. That evening, Hannah prepares a nature-tour travel journal spread using six photographs of flowering plants and four photographs of common mushrooms. Each photograph has one main subject. To keep an accurate record, she writes a plant-photo total for the spread, counting photographs whose main subject belongs to the plant kingdom.

### explicit_conflicting
On her first guided nature tour, Hannah attends an introductory talk by the trip's local naturalist. The naturalist explains: Mushrooms belong to the plant kingdom rather than the fungal kingdom. Hannah believes that mushrooms belong to the plant kingdom rather than the fungal kingdom. That evening, Hannah prepares a nature-tour travel journal spread using six photographs of flowering plants and four photographs of common mushrooms. Each photograph has one main subject. To keep an accurate record, she writes a plant-photo total for the spread, counting photographs whose main subject belongs to the plant kingdom.

## 解释句素材（代码按固定句式拼出 `<name> believes that <proposition>.`）
- aligned：mushrooms are fungi, not plants
- conflicting：mushrooms belong to the plant kingdom rather than the fungal kingdom

## 问题（四个版本完全相同）
- **Q1（信念）**：To which kingdom does Hannah believe common mushrooms belong?
- **Q2（行动）**：What number will Hannah write as the spread's plant-photo total?
- **Q3（现实）**：To which kingdom do common mushrooms actually belong?

## 候选 gold（provisional，待人工确认）
| | aligned | conflicting |
|---|---|---|
| Q1 | fungi | plants |
| Q2 | 6 | 10 |
| Q3（现实，不变） | fungi | fungi |

答案同义写法：{'q1_aligned': ['fungi', 'fungus', 'fungal kingdom', 'kingdom fungi'], 'q1_conflicting': ['plants', 'plant kingdom', 'Plantae'], 'q2_aligned': ['6', 'six', '6 photographs'], 'q2_conflicting': ['10', 'ten', '10 photographs'], 'q3': ['fungi', 'fungus', 'fungal kingdom', 'kingdom fungi']}

## 生成模型自报的风险
- risk_flags：['agent_prior_knowledge_risk', 'q3_answer_leakage']
- risk_notes：Hannah may already know that mushrooms are fungi and reject contrary testimony from the naturalist; a first nature tour does not establish ignorance of this fact. The locked conflicting claim mentions the fungal kingdom, making the real answer lexically available despite rejecting it. The aligned source claim supplies the true answer by design, so aligned Q3 does not isolate retained world knowledge.

## Q3 答案泄漏扫描（命中只是复核触发条件，不等于泄漏）
- `fungi` → aligned_source_claim（claim_span_aligned）
- `fungal kingdom` → conflicting_source_claim（claim_span_conflicting）

## 自动检查结果
- **warning** `gold_in_backbone`：Q1 conflicting 的答案 'plants' 出现在 claim/belief 以外的公共文字里，可能泄漏答案
- **warning** `q3_answer_in_conflicting_claim`：真实答案 'fungal kingdom' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
