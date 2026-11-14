# Pilot 12 题：生成汇总（gpt-6.1-sol，guideline v1.1 + A8）

全部是**候选刺激材料**（`needs_human_review`，`human_validated=False`），gold 均为 provisional，需要人工审查后才能使用。

## 文件
- `candidates.jsonl`：12 题的完整主记录（四个条件的故事、问题、gold、风险标注、自动检查结果、抽样分配、来源信息）。
- `REVIEW.md`：**阅读用的汇总文件**——总表 + 12 张题目卡片（合并故事、Q1–Q3 与 gold、风险、自动检查、人工审查勾选框，四个条件的完整故事折叠在卡片底部）。由 `src/build_review_report.py` 自动生成。
- 原始响应与每次尝试的日志在各自的来源目录里（见下表最后一列）。

## 总表

| 家族 | 事实 | 模板 | 场景域 | 行动类型 | 设计标签 | 故事词数 | error / warning | 来源目录 |
|---|---|---|---|---|---|---|---|---|
| F001 | K13 | T2 | travel_cultural_orientation | A2/simple_calculation | open_numeric | 80 | 0 / 2 | `pilot_batch_1` |
| F002 | K14 | T4C | hobbies_games | A5/targeted_revision | inherently_binary | 79 | 0 / 0 | `pilot_batch_1` |
| F003 | K28 | T4A | education_training | A4/simple_calculation | open_numeric | 80 | 0 / 0 | `gpt-6.1-sol_A8` |
| F004 | K23 | T5 | environment_weather | A1/one_step_mapping | open_other | 83 | 0 / 1 | `gpt-6.1-sol_A8_round2` |
| F005 | K30 | T3 | events_planning | A4/simple_calculation | open_other | 73 | 0 / 0 | `gpt-6.1-sol_A8_round2` |
| F006 | K15 | T1 | technical_workshop | A3/procedure_selection | open_other | 72 | 0 / 1 | `pilot_batch_1` |
| F007 | K06 | T3 | arts_media | A5/targeted_revision | open_other | 85 | 0 / 0 | `pilot_batch_1` |
| F008 | K18 | T4C | museum_exhibition | A4/prediction_application | open_other | 85 | 0 / 0 | `pilot_batch_1` |
| F009 | K20 | T2 | workplace_operations | A1/one_step_mapping | open_other | 87 | 0 / 8 | `pilot_batch_1` |
| F010 | K25 | T1 | community_volunteering | A2/one_step_mapping | open_numeric | 88 | 0 / 0 | `pilot_batch_1` |
| F011 | K09 | T4A | education_training | A1/one_step_mapping | open_other | 80 | 0 / 0 | `pilot_batch_1` |
| F012 | K27 | T5 | events_planning | A1/one_step_mapping | open_numeric | 86 | 0 / 1 | `pilot_batch_1` |

设计标签统计：{'open_numeric': 4, 'inherently_binary': 1, 'open_other': 7}。模板各 2 题（T1/T2/T3/T4A/T4C/T5），10 个场景域全部用到，均由代码分配。

保留的三题：K28（`gpt-6.1-sol_A8`）、K23 与 K30（`gpt-6.1-sol_A8_round2`）。其余 9 题（含 K18）是本轮 `pilot_batch_1` 重新生成的。

## 整体质量概括

**做得好的地方**
- 12 题都是**第一次生成就通过自动检查**（0 error），没有触发过重新生成；故事 72–88 词，全部在 110 词硬上限以内。
- claim span 都逐字复述了锁定的事实；故事里没有再出现上一轮那种把候选行动/数值列成选项的写法，也没有命中“available:”“either … or”“two options”等正则。
- 抽样分配（模板、名字、场景域）全部被遵守，代词与名字一致，没有场景域改派。

**明显的问题（需要你人工判断）**
1. **Q2 的答案空间大多仍是二选一。** 选项虽然不再写进故事，但答案本质上只有两个值：K14（改/不改）、K06（删除/保留）、K15（CO₂ 传感器/O₂ 传感器）、K18（zoom in/out）、K20（左/右）、K09（东/西）、K23（%/°C）。比较开放的只有 K13（照片数量 6/10）、K25（软管数 1/0）、K27（棋盘坐标 h8/a8）、K28（日期）、K30（月份）。
2. **F009（K20 棱镜）问题最多。** Q1 写成了“Which color does Mia believe … deviates more, **red or violet**?”，把两个选项写进了问题本身；故事里还出现了 “violet-light detector”，自动检查给了 8 个 warning（其中不少是因为该事实的两个 claim 本身就同时含 red 和 violet，属于噪音）。
3. **F010（K25 止回阀）像一道水管工程题。** 约束较多（“Existing equipment must remain installed”“suitable hoses are available”“pump supplies adequate pressure either way”），Q2 靠推水路得出软管数量，非 ToM 难度偏高（模型自己标了 `q2_non_tom_difficulty`）。
4. **F006（K15）的 Q2 基本是 Q1 换个说法**：相信“植物用 CO₂/O₂ 制糖”→ 选 “carbon dioxide / oxygen sensor”，容易退化成直接照抄（模型没有标 `q2_copy_shortcut`，我的二选一检测也没抓到，因为 gold 是 “Carbon dioxide sensor” 而不是 “carbon dioxide”）。
5. **模板贴合度**：F002（K14，T4C）模型自己标了 `template_task_mismatch`；F008（K18，T4C）写成“setup card states: …”，更像 T1 写成文字的参考资料，而不是“反复观察他人惯例”。
6. **部分故事仍带有叙述性的限定/设置**：F007（K06）的“The soundtrack should contain only sound reaching that camera, not dramatic effects”，F009 的光谱与参考位置描述，F010 的设备条件，F008 的“Her shift ends before heating begins”。这些没有命中正则，但读起来偏技术化。
7. **K23（已知，上轮已指出）**：故事结尾仍有 “The station uses Celsius in its public weather reports.”，给 °C 答案提供了依据。
8. **知识库本身的特点**：K13、K15、K20、K23、K27 的锁定 conflicting claim 里本身就含有真实答案（如 “rather than diagonally”“instead of humidity”），所以这些题都有 `q3_answer_in_conflicting_claim` 提示；这是知识库的特点，不是生成的错误，需要你决定是否接受。
9. **风险标注偏少**：像 K09（英国靠左行驶）、K13（蘑菇不是植物）这种家喻户晓的事实，conflicting 条件下角色/读者很可能不会相信来源，模型有的只标了 `agent_prior_knowledge_risk`，有的没标 `source_acceptance_ambiguity`。
10. 一些 Q2 需要多一步计算或推理（K13、K25、K28、K30），多数模型没有标 `q2_non_tom_difficulty`。

## 相对较好的几题（供你优先查看）
K30（月份，答案开放、无多余设定）、K28（日期）、K27（棋盘坐标）、K13（照片数量）。

## 说明
- 造题模型：`gpt-6.1-sol`；guideline v1.1（含 A8）；schema `m2-1.1.0`；每题约 1.2–1.4 万 token。
- 以上评价基于我对 12 题的通读与自动检查结果，只是初步判断，不是验证；所有 gold 仍待人工确认。
