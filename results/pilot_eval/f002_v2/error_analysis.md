# Pilot 错误分析

> 自动归因只是**启发式**，类别后缀 `_candidate` 表示“可能是”；无法确定的都标为 `needs_manual_review` / `scoring_ambiguity`，没有强行归类。完整的模型原始回答、reference、评分结果见 `item_level_scores.csv`，完整 API 响应见 `raw_responses.jsonl`。

## 类别说明

| 类别 | 含义 |
|---|---|
| `reality_intrusion_candidate` | 现实干扰（候选）：conflicting 题里，Q1 答成了真实世界的答案而不是角色的信念；或 Q1 答对、Q2 却做了符合现实的行动 |
| `belief_attribution_error_candidate` | 信念归因错误（候选）：aligned 题 Q1 答成了错误信念；或 Q1/Q2 同时出错且不属于上一类 |
| `non_tom_reasoning_error_candidate` | 非 ToM 推理错误（候选）：Q1 答对，Q2 给出的具体数值/日期/坐标不属于任何 gold（可能是计算、映射、格式问题） |
| `q3_false_claim_adopted` | Q3 把故事里的错误主张当成了现实 |
| `q0_knowledge_error` | Q0（无故事）就答错：知识缺口，或评分歧义 |
| `scoring_ambiguity` | 评分歧义：裁判认为“两者都像”或“无法判断”，待人工复核 |
| `needs_manual_review` | 答案不匹配任何 gold，原因无法确定，待人工复核 |
| `request_failed` | 请求失败（没有可评分的回答） |

## 1. 各配置错误数量（按类别）

| 配置 | 总错误/待复核 | `reality_intrusion_candidate` | `belief_attribution_error_candidate` | `non_tom_reasoning_error_candidate` | `q3_false_claim_adopted` | `q0_knowledge_error` | `scoring_ambiguity` | `needs_manual_review` | `request_failed` |
|---|---|---|---|---|---|---|---|---|---|
| qwen3-32b__non_thinking | 1/13 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| qwen3-32b__thinking | 0/13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-4.5-air__non_thinking | 0/13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-4.5-air__thinking | 0/13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## 2. Q1 正确但 Q2 错误（Application Gap 的来源）

同一配置、同一家族、同一条件下，Q1 评为正确而 Q2 评为错误/待复核。

共 1 条。

| 配置 | 家族/条件 | Q2 模型回答 | Q2 reference | 另一条件答案 | 类别 | 说明 |
|---|---|---|---|---|---|---|
| qwen3-32b__non_thinking | F002 conf/impl (K14) | At the surface | Below the surface, fully submerged | At the water's surface | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |

## 3. 全部错误与待复核题目（按配置）

### qwen3-32b__non_thinking（1 条）

| item | 模型回答 | reference | 评分方式 | 类别 | 说明 |
|---|---|---|---|---|---|
| F002_implicit_conflicting_Q2 | At the surface | Below the surface, fully submerged | rule | `reality_intrusion_candidate` | Q1 答对（知道角色信念），Q2 却做了符合现实/aligned 的行动 |

### qwen3-32b__thinking（0 条）

| item | 模型回答 | reference | 评分方式 | 类别 | 说明 |
|---|---|---|---|---|---|

### glm-4.5-air__non_thinking（0 条）

| item | 模型回答 | reference | 评分方式 | 类别 | 说明 |
|---|---|---|---|---|---|

### glm-4.5-air__thinking（0 条）

| item | 模型回答 | reference | 评分方式 | 类别 | 说明 |
|---|---|---|---|---|---|

## 4. 评分说明与已知的评分歧义来源

- 评分方式统计：{'rule': 49, 'llm_judge': 3}。`rule` = 规则评分；`llm_judge` = 规则无法确定后由 LLM 裁判（只比较语义，不判断事实）；`rule_undecided` = 未调用裁判。
- 待人工复核（pending）共 0 条，**不计入正确**；这些条目已在上面的表里标出。
- 由裁判判定的有 3 条，其中判为 neither 的 0 条（记为错误）；建议抽查这部分。
