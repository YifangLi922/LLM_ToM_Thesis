# Pilot 总结（写给自己看的，非正式材料）

## 1. 这次做了什么
- **被测配置（4 个）**：Qwen3-32B（DeepInfra）与 GLM-4.5-Air（Novita），各自 thinking / non-thinking。后端服务商都固定了，没有发生切换。
- **题目**：人工修订后的 12 个 family（K13、K14、K28、K23、K30、K15、K06、K18、K20、K25、K09、K27）。
  每个配置 156 条请求 = 12 条 Q0（无故事）+ 144 条故事题（12 题 × 4 个条件 × Q1/Q2/Q3），共 **624 条**。
- **独立性**：每条请求都是单条 user 消息、无历史（Q0 独立；Q1/Q2/Q3 各自 fresh context）；请求里没有 gold，gold 只在评分时使用。
- **每个配置只跑了 1 次**（用的是服务商默认的采样设置），所以下面所有数字都有随机波动；每个格子只有 12 题，**差 1 题 = 8.3 个百分点**。

## 2. 技术情况
- **624 条请求全部拿到了有效回答**。有 2 条 GLM 第一次返回了空内容（`glm-4.5-air__non_thinking` 的 F009 explicit conflicting Q2、`glm-4.5-air__thinking` 的 F010 implicit conflicting Q2），重试后成功；两次的原始记录都保留着。
- 没有被截断的回答，没有鉴权或额度问题；GLM thinking 有 2 条请求因临时错误经历过自动重试（最终成功）。
- **花费**：OpenRouter 合计约 **$0.173**，其中 GLM thinking 一个配置就占 $0.150。平均每条耗时：Qwen non-thinking 0.5 秒、GLM non-thinking 10.7 秒、Qwen thinking 16.7 秒、GLM thinking **50.6 秒**。
- 评分用的 LLM 裁判（gpt-6.1-sol）：79 次调用，约 3.4 万 token（计在你的 OpenAI 额度上）。
- 备注：不同服务商对 `reasoning_tokens` 和 `completion_tokens` 的统计口径不同（Qwen thinking 里 reasoning_tokens 反而比 completion_tokens 大），技术报告里的这两列只能看量级，不能相加。

## 3. 一眼看结果
| 配置 | Q0 | Q1 | Q2 | Q3 | Q2 aligned | Q2 conflicting | Paired Q2 一致 |
|---|---|---|---|---|---|---|---|
| Qwen3 non-thinking | 12/12, 100% | 40/48, 83% | 28/48, 58% | 44/48, 92% | 19/24, 79% | **9/24, 38%** | 7/24, 29% |
| Qwen3 thinking | 11/12, 92% | 46/48, 96% | 40/48, 83% | 47/48, 98% | 23/24, 96% | 17/24, 71% | 17/24, 71% |
| GLM non-thinking | 10/12, 83% | 38/48, 79% | 33/48, 69% | 47/48, 98% | 21/24, 88% | **12/24, 50%** | 11/24, 46% |
| GLM thinking | 11/12, 92% | 43/48, 90% | 43/48, 90% | 48/48, 100% | 24/24, 100% | 19/24, 79% | 19/24, 79% |

> 所有“待人工复核”的回答都按“不计为正确”处理（所以数字是下限），共 19 条（Qwen NT 7、Qwen T 3、GLM NT 8、GLM T 1）。

## 4. 主要现象（只是 pilot，样本很小）
1. **模型知道事实，故事也基本没有污染它们对现实的回答。** Q0 在 83–100%，Q3 在 92–100%。Q3 一共只错了 6 条：其中 5 条是把故事里的错误主张当成了现实（Qwen non-thinking 4 条：K28×2、K30、K18；GLM non-thinking 1 条：K18，都在 conflicting 条件下），另 1 条是 Qwen thinking 对 K14 答 “blowhole”（评分歧义，见第 5 节）。
2. **Application Gap（Q1−Q2，4 个条件合并，48 vs 48）**：Qwen NT **25.0 pp**、Qwen thinking 12.5 pp、GLM NT 10.4 pp、GLM thinking 0.0 pp。最大的缺口出现在 **conflicting + explicit**：Qwen NT 与 GLM NT 都是 **50.0 pp**（Q1 83%/100%，Q2 只有 33%/50%）。也就是说：明明说对了“角色相信什么”，行动却按真实世界来。
3. **Conflict Gap（Aligned−Conflicting）主要体现在 Q2**：non-thinking 的 Q2 差 33–42 pp，thinking 的差 17–33 pp；Q1 的差距小一些（合并后 0–25 pp），Q3 除 Qwen non-thinking（16.7 pp）外几乎没有。
4. **Explicitness Benefit（Explicit−Implicit）只救了 Q1，没救 Q2**：conflicting 的 Q1 提升 +17 到 +42 pp，但 conflicting 的 Q2 只在 −8 到 +8 pp 之间浮动。说明“把信念写明白”能解决归因，不能解决应用。
5. **Thinking Benefit（Thinking−Non-thinking，4 个条件合并）**：Qwen 的 Q1 +12.5、Q2 **+25.0**；GLM 的 Q1 +10.4、Q2 **+20.8**；Q0 没有稳定的收益（Qwen −8.3，GLM +8.4，都是一两题的差别，且与 K14/K06 的评分歧义有关，见下）。conflicting 的 Q2 受益最大（Qwen +25/+41.7 pp，GLM +25/+33.3 pp）。
6. **Q0-conditioned Conflicting Q2**：Q0 答对的事实上，conflicting Q2 的正确率为 Qwen NT 9/24（38%）、Qwen T 17/22（77%）、GLM NT 12/20（60%）、GLM T 19/22（86%）。Q0 答错的那一组只有 0–4 题，且全部来自 K14（“blowhole”）和 K06（“Nothing”）这两条有评分歧义的 Q0，所以**这次的 Q0 条件化对比没有实际意义**。

## 5. 暴露出来的问题（比模型分数更重要）
### 题目设计
- **有两题的 conflicting Q2 在 4 个配置、8 个格子里全军覆没（0/8）：F002（K14 海豚）和 F007（K06 真空）。** 它们的故事里都有“要符合现实”的目标（“reflect how real dolphins breathe”“reproduce only sounds that could reach the camera”），模型即使在 explicit 条件下 Q1 答对了（知道角色相信海豚用鳃/声音能在真空传播），Q2 仍按现实去做（“surface”“remove”）。这类题测到的更像是“任务目标让模型调用真实知识”，而不是“能不能用角色的信念做预测”。
- **F002 的 Q2、F007 的 Q1 是我们重写过的问题，也带来了歧义：** F002 的 Q2 “How will Henry animate the dolphin taking a breath?” 收到了 “blowhole”“Incorrectly” 这类答非所问的回答（4 条待复核）；F007 的 Q1 “…happens to sound-wave propagation…” 让 GLM non-thinking 回答 “Nothing”“None”（3 条待复核）。
- **F011（K09）Q2 问的是 compass side，但模型常答 “left”/“left side”**（Qwen NT 与 GLM NT 共 8 条待复核）：问题没有把“用东/西作答”说清楚。
- **Q2 的答案空间大多是两个值**（12 题里有 8 题：K14、K23、K15、K06、K18、K20、K25、K09），随机猜也有 50%。像 Qwen NT 的 conflicting Q2（38%）低于 50% 说明是**系统性地**偏向现实，而不只是猜的；但对 thinking 配置，高分里有多少是猜的，无法从这批数据分开。
- 其他 conflicting Q2 偏低的题：F012（K27，3/8，含 “b8”“h1” 这类疑似非 ToM 的棋盘坐标错误）、F010（K25，4/8）、F006（K15，5/8）、F004（K23，5/8，包含回答 “%RH”“°F or °C”）。
- **implicit conflicting 的 Q1 本身就偏低**（non-thinking 只有 58%）：不确定是角色信念没被推断出来，还是模型的先验知识压过了故事。

### 评分
- 119/624 条规则无法直接判定，交给了 LLM 裁判；裁判之后仍有 **19 条待人工复核**（模型答案含糊、只回答了一半、或答成了别的维度，如 “9” 对 “9 November”、“vertically” 对 “horizontally or vertically”）。
- **K14 的 Q0 被判错**（Qwen thinking、GLM NT、GLM T 都答 “blowhole”）：这是 Q0 问法（“What organs … breathe air?”）与 “blowhole” 之间的歧义，不一定是模型不知道；它也影响了所有 Q0 相关数字。建议你人工看一下这 3 条是否该判对。
- 错误归因（现实干扰 / 信念归因 / 非 ToM 推理）只是**启发式**，都带 `_candidate` 标记；无法确定的已标 `needs_manual_review` 或 `scoring_ambiguity`。判为现实干扰的共 37 条，建议至少抽查 Q1 正确但 Q2 错误的那 35 条（错误分析第 2 节）。

### 流程 / 统计
- 每个格子 12 题、每个配置 1 次采样：**不能做统计显著性的结论**，只能看趋势；要看稳定性需要多次采样或更多题目。
- GLM thinking 又慢又占成本（约 87% 的花费），后续放大规模时要考虑。

## 6. 建议的下一步
1. 先处理上面几道“设计有问题”的题（K14、K06、K09 的 Q2 / Q1 措辞，K14/K06 故事里的“要符合现实”目标），再决定要不要扩大规模。
2. 人工看一眼 19 条待复核回答和 K14 的 Q0 评分，再决定评分规则要不要加人工覆盖。
3. 打算做统计比较时，每个配置至少多跑几次，并把 Q2 尽量改成答案空间更大的开放题。

## 7. 文件在哪里（`results/pilot_eval/`）
| 文件 | 内容 |
|---|---|
| `accuracy_summary.csv` | 每个配置的 Q0 准确率；Q1/Q2/Q3 按 4 种条件及合并后的正确数/总数/百分比，附待复核数和请求失败数 |
| `key_metrics.csv` | Application Gap、Conflict Gap、Explicitness Benefit、Thinking Benefit、Q0-conditioned Conflicting Q2、Paired Q2 Consistency；每行写明条件、两边的分子/分母和百分点差 |
| `item_level_scores.csv` | 624 条的模型回答、reference、另一条件的答案、评分结果与方式、裁判理由、错误类别 |
| `error_analysis.md` | 全部错误（含“Q1 对 Q2 错”专节）与待复核条目 |
| `technical_report.csv` | 模型 ID、服务商、reasoning 设置、token、费用、请求失败 |
| `raw_responses.jsonl` | **完整原始 API 响应**（含 reasoning 文本、失败的那 2 条） |
| `judge_raw.jsonl` | LLM 裁判的输入输出（兼缓存） |
