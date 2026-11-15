# 导入 REVIEW_new.md 后的修正记录与仍需你知道的事项

## A. 已按你的要求修正（已写入 `REVIEW_new.md`，并重新导出了评测文件）

### 1. 两处笔误
| 家族 | 原来 | 现在 |
|---|---|---|
| F010（K25） | `…handbook stating that a **[A standard check valve …]**`（渲染成 “a A standard…”） | `…handbook stating: **[A standard check valve …]**`（与其他题的冒号写法一致，来源声明的大小写和句号保持锁定写法） |
| F008（K18） | `she need to set up a camera` | `she needs to set up a camera` |

### 2. 问题里提到、但现在的故事里没有的内容（问题已改成与故事一致）
| 家族 | 原 Q2 | 现 Q2 | gold |
|---|---|---|---|
| F002（K14） | What change, if any, will Henry make to the **breathing beat**? | How will Henry animate the dolphin taking a breath? | **改了**：原来的 “Show the dolphin surfacing / No change.” 依赖已删除的 storyboard，现为 “Surfacing to breathe air.” ｜ “Breathing while fully submerged.” |
| F003（K28） | …enter as the reminder email's **send date**? | On what date will Ava schedule the reminder email to be sent? | 不变（2 October ｜ 8 November） |
| F005（K30） | …enter for the volunteer briefing **in the booking request**? | In which month will Daniel schedule the volunteer briefing? | 不变（March ｜ August） |
| F006（K15） | …enter **on the purchase specification**? | What type of gas sensor will Charlotte select for the experiment? | 不变 |
| F007（K06） | …for the existing **bell-ringing cue**? | What edit, if any, will Sophia make to the bell-ringing **sound effect**? | 措辞随之改为 “Remove the bell-ringing sound effect.” ｜ “No change; retain the bell-ringing sound effect.” |
| F009（K20） | On which **side of the marked** violet-light detector position will Mia place the red-light detector **in her layout**?（gold：Left ｜ Right） | Relative to the undeviated beam's position, where will Mia place the red-light detector compared with the violet-light detector? | **改了**：你删掉了故事里“参考位置在光谱左侧”的描述后，Left / Right 没有依据，现改为 “Closer to the undeviated beam than the violet detector.” ｜ “Farther from the undeviated beam than the violet detector.”（相信紫光偏折更多 → 红光离未偏折光束更近；相信红光偏折更多 → 更远） |
| F011（K09） | …compass side of the road's **center line** will Noah place the northbound **vehicle symbol**? | On which compass side of the road will Noah place the northbound car? | 不变（West ｜ East） |

### 3. 之前由我显式覆盖的两个 Q1，现在已直接写进 `REVIEW_new.md`
- F007（K06）Q1：What does Sophia believe happens to sound-wave propagation in a perfect vacuum?（原问题里含 “can travel”，被泄漏检查拦下）
- F009（K20）Q1：Which visible color of light does Mia believe is deviated the most when white light passes through an ordinary glass prism?（原问题把 “red or violet” 都列出来了）

顶部总表里的 Q2 gold 列也同步更新了（F002、F007、F009、F010）。

## B. 仍需你知道的（没有改动）
- **F004（K23）**：删掉 Celsius 之后，conflicting 的 Q2 答案 `°C` 没有依据，被测模型可能答 °F 或 K。
- **F010（K25）**：Q2 是 Yes / No，`answer_variants` 只有 `["Yes"]` / `["No"]`；bundle 里记的还是软管数量，所以有两个 `q2_gold_differs_from_bundle` 提示（F002、F007、F009 也因 gold 改动出现同样的提示），可忽略。
- **篇幅**：F001/F002/F004/F005/F006/F007/F009 的 implicit 故事低于 70 词（F002 只有 45 词）。只是提示，没有超过 110 词上限的。
- **F008**：`gold_in_backbone: 'Zoom in.'` 是误报（来自 “adjusts the zoom in advance”）。
- **F009**：自动检查里的 `q3_answer_*` 提示较多，是因为 K20 锁定的两个 claim 都同时含 red 和 violet，属于该事实的特点。
- `REVIEW_new.md` 卡片里折叠起来的“四个条件完整故事”、bundle 设计和自动检查结果是旧的，没有同步；评测文件以合并故事和问题表为准。
