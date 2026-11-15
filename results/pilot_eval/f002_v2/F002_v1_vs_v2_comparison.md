# F002（K14 海豚）v1 与 v2 对比

✓ 正确　✗ 错误　? 待人工复核。v1 = 人工修订后的旧故事（“visiting marine biologist”，Q2 问怎么动画）；v2 = 新故事（“experienced animator 的 rehearsals”，Q2 问“海豚在下一次呼吸时放在哪里”）。

## 1. 正确数对比（每个配置，v1 → v2）

| 配置 | Q0 | Q1（4 个条件） | Q2（4 个条件） | Q3（4 个条件） |
|---|---|---|---|---|
| qwen3-32b__non_thinking | 1/1 → **1/1** | 4/4 → **4/4** | 2/4 → **3/4** | 4/4 → **4/4** |
| qwen3-32b__thinking | 0/1 → **1/1** | 4/4 → **4/4** | 1/4 → **4/4** | 3/4 → **4/4** |
| glm-4.5-air__non_thinking | 0/1 → **1/1** | 2/4 → **4/4** | 2/4 → **4/4** | 4/4 → **4/4** |
| glm-4.5-air__thinking | 0/1 → **1/1** | 2/4 → **4/4** | 2/4 → **4/4** | 4/4 → **4/4** |

合计（4 个配置）：Q0 1/4 → 4/4；Q1 12/16 → 16/16；Q2 7/16 → 15/16；Q3 15/16 → 16/16

## 2. 逐条模型回答（Q0 与四个条件的 Q1/Q2/Q3）

### qwen3-32b__non_thinking

| item | v1 回答 | v1 | v2 回答 | v2 | v2 评分方式 | v2 错误类别 |
|---|---|---|---|---|---|---|
| K14_Q0 | Lungs | ✓ | Lungs | ✓ | rule |  |
| implicit_aligned_Q1 | Lungs | ✓ | lungs | ✓ | rule |  |
| explicit_aligned_Q1 | lungs | ✓ | lungs | ✓ | rule |  |
| implicit_conflicting_Q1 | gills | ✓ | gills | ✓ | rule |  |
| explicit_conflicting_Q1 | gills | ✓ | gills | ✓ | rule |  |
| implicit_aligned_Q2 | Surface to breathe. | ✓ | At the surface | ✓ | rule |  |
| explicit_aligned_Q2 | Surface for air | ✓ | At the water's surface. | ✓ | rule |  |
| implicit_conflicting_Q2 | incorrectly, with lungs, not gills | ? | At the surface | ✗ | rule | reality_intrusion_candidate |
| explicit_conflicting_Q2 | Incorrectly | ? | underwater | ✓ | rule |  |
| implicit_aligned_Q3 | Lungs | ✓ | Lungs | ✓ | rule |  |
| explicit_aligned_Q3 | Lungs | ✓ | Lungs | ✓ | rule |  |
| implicit_conflicting_Q3 | lungs | ✓ | Lungs | ✓ | rule |  |
| explicit_conflicting_Q3 | Lungs | ✓ | Lungs | ✓ | rule |  |

### qwen3-32b__thinking

| item | v1 回答 | v1 | v2 回答 | v2 | v2 评分方式 | v2 错误类别 |
|---|---|---|---|---|---|---|
| K14_Q0 | blowhole | ✗ | lungs | ✓ | rule |  |
| implicit_aligned_Q1 | lungs | ✓ | lungs | ✓ | rule |  |
| explicit_aligned_Q1 | lungs | ✓ | lungs | ✓ | rule |  |
| implicit_conflicting_Q1 | gills | ✓ | gills | ✓ | rule |  |
| explicit_conflicting_Q1 | gills | ✓ | gills | ✓ | rule |  |
| implicit_aligned_Q2 | surface and inhale through blowhole | ✓ | surface | ✓ | llm_judge/matches_reference |  |
| explicit_aligned_Q2 | blowhole | ? | at the surface | ✓ | rule |  |
| implicit_conflicting_Q2 | surface to breathe | ✗ | underwater | ✓ | rule |  |
| explicit_conflicting_Q2 | blowhole | ? | underwater | ✓ | rule |  |
| implicit_aligned_Q3 | lungs | ✓ | lungs | ✓ | rule |  |
| explicit_aligned_Q3 | lungs | ✓ | Lungs | ✓ | rule |  |
| implicit_conflicting_Q3 | lungs | ✓ | lungs | ✓ | rule |  |
| explicit_conflicting_Q3 | blowhole | ✗ | lungs | ✓ | rule |  |

### glm-4.5-air__non_thinking

| item | v1 回答 | v1 | v2 回答 | v2 | v2 评分方式 | v2 错误类别 |
|---|---|---|---|---|---|---|
| K14_Q0 | Blowhole | ✗ | Lungs | ✓ | rule |  |
| implicit_aligned_Q1 | gills | ✗ | lungs | ✓ | rule |  |
| explicit_aligned_Q1 | lungs | ✓ | lungs | ✓ | rule |  |
| implicit_conflicting_Q1 | Lungs | ✗ | gills | ✓ | rule |  |
| explicit_conflicting_Q1 | gills | ✓ | gills | ✓ | rule |  |
| implicit_aligned_Q2 | Surface | ✓ | At the water's surface. | ✓ | rule |  |
| explicit_aligned_Q2 | Surface | ✓ | At the surface. | ✓ | rule |  |
| implicit_conflicting_Q2 | Surface | ✗ | Underwater | ✓ | rule |  |
| explicit_conflicting_Q2 | Surface | ✗ | Underwater | ✓ | rule |  |
| implicit_aligned_Q3 | Lungs | ✓ | lungs | ✓ | rule |  |
| explicit_aligned_Q3 | lungs | ✓ | Lungs | ✓ | rule |  |
| implicit_conflicting_Q3 | Lungs | ✓ | lungs | ✓ | rule |  |
| explicit_conflicting_Q3 | Lungs | ✓ | lungs | ✓ | rule |  |

### glm-4.5-air__thinking

| item | v1 回答 | v1 | v2 回答 | v2 | v2 评分方式 | v2 错误类别 |
|---|---|---|---|---|---|---|
| K14_Q0 | Blowhole | ✗ | Lungs | ✓ | rule |  |
| implicit_aligned_Q1 | gills | ✗ | lungs | ✓ | rule |  |
| explicit_aligned_Q1 | lungs | ✓ | lungs | ✓ | rule |  |
| implicit_conflicting_Q1 | lungs | ✗ | gills | ✓ | rule |  |
| explicit_conflicting_Q1 | gills | ✓ | gills | ✓ | rule |  |
| implicit_aligned_Q2 | surfacing | ✓ | surface | ✓ | llm_judge/matches_reference |  |
| explicit_aligned_Q2 | surfacing | ✓ | surface | ✓ | llm_judge/matches_reference |  |
| implicit_conflicting_Q2 | surfacing | ✗ | underwater | ✓ | rule |  |
| explicit_conflicting_Q2 | surfacing | ✗ | underwater | ✓ | rule |  |
| implicit_aligned_Q3 | lungs | ✓ | lungs | ✓ | rule |  |
| explicit_aligned_Q3 | lungs | ✓ | lungs | ✓ | rule |  |
| implicit_conflicting_Q3 | lungs | ✓ | lungs | ✓ | rule |  |
| explicit_conflicting_Q3 | lungs | ✓ | Lungs | ✓ | rule |  |

## 3. 两个版本的问题与 gold

| | v1 | v2 |
|---|---|---|
| Q0 | What organs do dolphins use to breathe air? → `lungs` | Which internal organs do dolphins use to exchange oxygen and carbon dioxide? → `lungs` |
| Q1 | What breathing organs does Henry believe dolphins use? → aligned `lungs` / conflicting `gills` | Which organs does Henry believe dolphins use for gas exchange? → aligned `lungs` / conflicting `gills` |
| Q2 | How will Henry animate the dolphin taking a breath? → aligned `Surfacing to breathe air.` / conflicting `Breathing while fully submerged.` | Where will Henry position the dolphin when it takes its next breath? → aligned `At the water's surface` / conflicting `Below the surface, fully submerged` |
| Q3 | What organs do dolphins actually use to breathe? → aligned `lungs` / conflicting `lungs` | Which organs do dolphins actually use for gas exchange? → aligned `lungs` / conflicting `lungs` |
