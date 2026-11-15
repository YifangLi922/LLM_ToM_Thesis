# Pilot 总结（写给自己看的，非正式材料）

> **本文已按 F002 v2 更新**：F002（K14 海豚）换成了新故事设计，K14 的 Q0 换成了新问法；其余 11 个 family 的回答与评分完全没动。
> 旧版（v1）的汇总文件保留在 `archive_v1_original/`，v1 与 v2 的逐项对比见 `f002_v2/F002_v1_vs_v2_comparison.md`，
> 所有指标的前后变化见 `METRIC_CHANGES_F002_v2.md`。

## 1. 这次做了什么
- **被测配置（4 个）**：Qwen3-32B（DeepInfra）与 GLM-4.5-Air（Novita），各自 thinking / non-thinking。后端服务商都固定了，没有发生切换。
- **题目**：人工修订后的 12 个 family（K13、K14、K28、K23、K30、K15、K06、K18、K20、K25、K09、K27），其中 F002 为 v2。
  每个配置 156 条请求 = 12 条 Q0（无故事）+ 144 条故事题（12 题 × 4 个条件 × Q1/Q2/Q3），共 **624 条**。
- **独立性**：每条请求都是单条 user 消息、无历史（Q0 独立；Q1/Q2/Q3 各自 fresh context）；请求里没有 gold，gold 只在评分时使用。
- **每个配置只跑了 1 次**（服务商默认采样设置），所以数字有随机波动；每个格子只有 12 题，**差 1 题 = 8.3 个百分点**。

## 2. 技术情况
- 第一轮 624 条全部拿到了有效回答（2 条 GLM 空回答重试后成功）；F002 v2 重跑的 52 条（4 配置 × 13 条）**全部一次成功**。没有截断，没有鉴权或额度问题。
- **花费**：第一轮 OpenRouter 约 $0.173，F002 v2 重跑约 $0.007。注意：当前顶层 `technical_report.csv` 只统计“替换后这套 624 条”所用的请求（$0.169），被替换掉的 F002 v1 请求（13×4 条）没有计入；它们的原始响应仍在 `raw_responses.jsonl` 里。
- 平均每条耗时：Qwen non-thinking 约 0.5 秒、GLM non-thinking 约 11 秒、Qwen thinking 约 17 秒、GLM thinking 约 **51 秒**（GLM thinking 占了约 87% 的花费）。
- 评分用的 LLM 裁判（gpt-6.1-sol）：第一轮 79 次调用约 3.4 万 token，F002 v2 新增 1 次。
- 备注：不同服务商对 `reasoning_tokens` 与 `completion_tokens` 的统计口径不同，技术报告里这两列只能看量级，不能相加。

## 3. 一眼看结果（替换 F002 之后）
| 配置 | Q0 | Q1 | Q2 | Q3 | Q2 aligned | Q2 conflicting | Paired Q2 一致 |
|---|---|---|---|---|---|---|---|
| Qwen3 non-thinking | 12/12, 100% | 40/48, 83% | 29/48, 60% | 44/48, 92% | 19/24, 79% | **10/24, 42%** | 8/24, 33% |
| Qwen3 thinking | 12/12, 100% | 46/48, 96% | 43/48, 90% | 48/48, 100% | 24/24, 100% | 19/24, 79% | 19/24, 79% |
| GLM non-thinking | 11/12, 92% | 40/48, 83% | 35/48, 73% | 47/48, 98% | 21/24, 88% | **14/24, 58%** | 13/24, 54% |
| GLM thinking | 12/12, 100% | 45/48, 94% | 45/48, 94% | 48/48, 100% | 24/24, 100% | 21/24, 88% | 21/24, 88% |

> “待人工复核”的回答按“不计为正确”处理（所以数字是下限），共 15 条（Qwen NT 5、Qwen T 1、GLM NT 8、GLM T 1）。

## 4. F002 换成 v2 之后的变化
- **F002 本身**（4 个配置合计，v1 → v2）：Q0 1/4 → **4/4**；Q1 12/16 → **16/16**；Q2 7/16 → **15/16**；Q3 15/16 → **16/16**。52 条里只有 1 条错：Qwen non-thinking 在 implicit conflicting 的 Q2 答了 “At the surface”（按现实而不是按角色的信念）。
- **v1 的问题基本消失**：v1 里 “blowhole”“Incorrectly” 这类答非所问的回答没有了（待人工复核从 4 条降到 0 条），Q0 的 “blowhole” 歧义也没有了（新 Q0 “Which internal organs … exchange oxygen and carbon dioxide?” 4 个配置都答对）。
- **对完整结果的影响**：只有单个格子变动了 1–2 题（±8 个百分点以内），合并指标的变化都在约 ±8 pp 以内，**整体结论没有变**。主要变化：
  - Application Gap（Q1−Q2，合并）：Qwen NT 25.0 → 22.9，Qwen thinking 12.5 → **6.2**，GLM NT 10.4 → 10.4，GLM thinking 0.0 → 0.0。
  - Conflict Gap（Q2，合并）：Qwen NT 37.5 → 37.5，Qwen thinking 25.0 → 20.8，GLM NT 37.5 → **29.2**，GLM thinking 20.8 → **12.5**。
  - Thinking Benefit（Q2，4 个条件合并）：Qwen 25.0 → **29.2**，GLM 20.8 → 20.9；Q0 的 Thinking Benefit 变成 Qwen 0.0、GLM +8.3（v1 时 Qwen 是 −8.3，只是 “blowhole” 的评分歧义造成的）。
  - Q0 准确率：Qwen thinking 92% → 100%，GLM NT 83% → 92%，GLM thinking 92% → 100%。

## 5. 主要现象（只是 pilot，样本很小）
1. **模型知道事实，故事也基本没有污染它们对现实的回答。** Q0 在 92–100%，Q3 在 92–100%。Q3 一共只错了 5 条，全部是把故事里的错误主张当成了现实（Qwen non-thinking 4 条：K28×2、K30、K18；GLM non-thinking 1 条：K18，都在 conflicting 条件下）。
2. **Application Gap（Q1−Q2，4 个条件合并，48 vs 48）**：Qwen NT **22.9 pp**、Qwen thinking 6.2 pp、GLM NT 10.4 pp、GLM thinking 0.0 pp。最大的缺口在 **conflicting + explicit**：Qwen NT 41.6 pp、GLM NT 41.7 pp（Q1 83%/100%，Q2 只有 42%/58%）；thinking 配置只有 16.7 / 8.3 pp。也就是说，non-thinking 模型能说对“角色相信什么”，行动却常按现实来。
3. **Conflict Gap（Aligned−Conflicting）主要体现在 Q2**：合并后 Qwen NT 37.5、Qwen thinking 20.8、GLM NT 29.2、GLM thinking 12.5 pp；Q1 的差距较小（25.0 / 8.3 / 0.0 / 4.1 pp），Q3 除 Qwen non-thinking（16.7 pp）外几乎没有。
4. **Explicitness Benefit（Explicit−Implicit）只救了 Q1，没救 Q2**：conflicting 的 Q1 提升 +16.7 到 +33.3 pp，conflicting 的 Q2 只在 0 到 +8.4 pp 之间。说明“把信念写明白”能解决归因，不能解决应用。
5. **Thinking Benefit（Thinking−Non-thinking，4 个条件合并）**：Qwen 的 Q1 +12.5、Q2 **+29.2**；GLM 的 Q1 +10.5、Q2 **+20.9**。conflicting 的 Q2 受益最大（Qwen +33.3/+41.6 pp，GLM +25.0/+33.4 pp，分别对应 implicit/explicit）。
6. **Q0-conditioned Conflicting Q2**：Q0 答对的事实上，conflicting Q2 的正确率为 Qwen NT 10/24（42%）、Qwen T 19/24（79%）、GLM NT 14/22（64%）、GLM T 21/24（88%）。Q0 答错的组几乎是空的（只有 GLM NT 的 K06 一条，0/2），所以**这次的 Q0 条件化对比仍然没有实际意义**。

## 6. 暴露出来的问题（比模型分数更重要）
### 题目设计
- **F007（K06 真空）的 conflicting Q2 依然是 0/8**，现在是唯一一个全军覆没的题。故事里有“要符合现实”的目标（“reproduce only sounds that could reach the camera”），模型即使 Q1 答对（explicit 条件下），Q2 仍按现实去做（“remove”）。这类题测到的更像“任务目标调用了真实知识”，而不是“用角色的信念做预测”。
- **F002 v2 现在几乎人人答对（51/52），要留意是不是变得太容易**：故事里写明了“海豚现在在水面下几米”，conflicting 的答案（“fully submerged / underwater”）正好就是故事交代的当前状态，模型可能只是复述故事里的位置，而不是在用角色的信念推理；aligned 才需要把海豚移到水面。这一题的 conflicting Q2 因此可能偏高估计。
- **F007 的 Q1 是我们重写过的问法，仍有歧义**：“…happens to sound-wave propagation…” 让 GLM non-thinking 回答 “Nothing”“None”（3 条待复核，并连带 K06 的 Q0 也出现 “Nothing”）。
- **F011（K09）Q2 问的是 compass side，但模型常答 “left”/“left side”**（Qwen NT 与 GLM NT 共 8 条待复核）：问题没有把“用东/西作答”说清楚。
- **Q2 的答案空间大多是两个值**（12 题里约 8 题），随机猜也有 50%。像 Qwen NT 的 conflicting Q2（42%）低于 50%，说明是**系统性地**偏向现实，而不只是猜的；但对 thinking 配置，高分里有多少是猜的，无法从这批数据分开。
- 其他 conflicting Q2 偏低的题：F012（K27，3/8，含 “b8”“h1” 这类疑似非 ToM 的棋盘坐标错误）、F010（K25，4/8）、F006（K15，5/8）、F004（K23，5/8，包含回答 “%RH”“°F or °C”）。
- **implicit conflicting 的 Q1 本身就偏低**（non-thinking 只有 58%）：不确定是角色信念没被推断出来，还是模型的先验知识压过了故事。

### 评分
- 规则无法直接判定 102 条，交给了 LLM 裁判（去重后 65 个不同输入）；裁判之后仍有 **15 条待人工复核**（主要是 F011 “left”、F007 “Nothing/None”，以及 “9” 对 “9 November”、“vertically” 对 “horizontally or vertically” 这类只答了一半的回答）。
- 错误归因（现实干扰 / 信念归因 / 非 ToM 推理）只是**启发式**，都带 `_candidate` 标记；无法确定的已标 `needs_manual_review` 或 `scoring_ambiguity`。判为现实干扰的共 31 条（v1 时 37 条，减少的主要是 F002）；“Q1 正确但 Q2 错误” 29 条（v1 时 35 条），建议至少抽查这些（错误分析第 2 节）。

### 流程 / 统计
- 每个格子 12 题、每个配置 1 次采样：**不能做统计显著性的结论**，只能看趋势；要看稳定性需要多次采样或更多题目。
- GLM thinking 又慢又占成本，后续放大规模时要考虑。
- 注意：K14 的 Q0 新问法只用于评测文件（`datasets/generation/pilot_12_v2/`），**知识库 `knowledge_pool_pilot_12_v1.jsonl` 里 K14 的 `pretest_question` 还是旧问法**；如果以后要正式使用，需要决定是否同步改知识库。

## 7. 建议的下一步
1. 先处理还有设计问题的题：F007（K06）的“符合现实”目标与 Q1 问法，F011（K09）的 Q2 措辞；F002 v2 要确认“当前位置已在水下”的交代是否让 conflicting 变成了送分题。
2. 人工看一眼 15 条待复核回答，再决定评分规则要不要加人工覆盖。
3. 打算做统计比较时，每个配置至少多跑几次，并把 Q2 尽量改成答案空间更大的开放题。

## 8. 文件在哪里（`results/pilot_eval/`）
| 文件 | 内容 |
|---|---|
| `accuracy_summary.csv` | **（已更新为 F002 v2 版）** 每个配置的 Q0 准确率；Q1/Q2/Q3 按 4 种条件及合并后的正确数/总数/百分比，附待复核数和请求失败数 |
| `key_metrics.csv` | **（已更新）** Application Gap、Conflict Gap、Explicitness Benefit、Thinking Benefit、Q0-conditioned Conflicting Q2、Paired Q2 Consistency；每行写明条件、分子/分母和百分点差 |
| `item_level_scores.csv` | **（已更新）** 624 条的模型回答、reference、另一条件的答案、评分结果与方式、裁判理由、错误类别 |
| `error_analysis.md` | **（已更新）** 全部错误（含“Q1 对 Q2 错”专节）与待复核条目 |
| `technical_report.csv` | **（已更新）** 模型 ID、服务商、reasoning 设置、token、费用、请求失败（仅统计替换后这套 624 条） |
| `METRIC_CHANGES_F002_v2.md` | 替换前后所有关键指标的对比（v1 / v2 / 变化 pp） |
| `f002_v2/` | F002 v2 的单独结果：`raw_responses.jsonl`（完整原始响应）、`item_level_scores.csv`（逐条回答/评分/pending）、`F002_v1_vs_v2_comparison.csv/.md`、`judge_raw.jsonl` 等 |
| `archive_v1_original/` | 替换前（F002 v1）的原始汇总文件，原样保留 |
| `raw_responses.jsonl` | 第一轮 624 条的**完整原始 API 响应**（含 F002 v1，未改动） |
| `judge_raw.jsonl` | LLM 裁判的输入输出（兼缓存） |
