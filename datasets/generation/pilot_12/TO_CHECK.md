# 导入 REVIEW_new.md 时发现的、建议你再看一眼的地方

以下是我在把你修改后的 `REVIEW_new.md` 还原并渲染四个条件时注意到的问题。**我没有改动你写的任何文字**（只有最后一节里的两处问题是我用显式覆盖改的，原因见那一节）。
如果要改，直接编辑 `REVIEW_new.md` 里对应卡片的“合并故事”或问题表，然后告诉我，我重新导出即可（一条命令）。

## 1. 疑似笔误（会原样发给被测模型）
| 家族 | 位置 | 现状 | 说明 |
|---|---|---|---|
| F010（K25） | 来源句 | `…handbook stating that a **[A standard check valve …]**` | 多了一个 “a”，渲染出来是 “stating that **a A** standard check valve permits …” |
| F008（K18） | 故事后半 | `she need to set up a camera` | 应为 “she needs to” |

## 2. 故事改了，但问题没跟着改（问题里提到了故事里已经没有的东西）
| 家族 | 问题 | 故事现状 |
|---|---|---|
| F002（K14） | Q2：“What change, if any, will Henry make to the **breathing beat**?”（gold：Show the dolphin surfacing / No change.） | 新故事里已经没有 storyboard 和“breathing beat”，只有“considers whether to change the scene”。Q2 的 gold 也依赖原来那个画面，现在读者无从判断。故事只有 45 词。 |
| F005（K30） | Q2：“…enter for the volunteer briefing **in the booking request**?” | 故事末尾的 booking request 那句被删掉了。 |
| F006（K15） | Q2：“…enter **on the purchase specification**?” | 故事改成 “She needs to select a gas sensor for the experiment.”，没有 purchase specification。 |
| F007（K06） | Q2：“…for the existing **bell-ringing cue**?” | 故事里现在叫 “bell-ringing sound effect”（意思相同，只是措辞不同）。 |
| F011（K09） | Q2：“…place the northbound **vehicle symbol**?”（问的是 compass side，gold：West / East） | 故事里现在是 “place a northbound car in the appropriate lane”。 |
| F003（K28） | Q2：“…enter as the reminder email's **send date**?” | 故事里现在是 “schedules a reminder email for the day before”（意思相同）。 |

## 3. 其他需要知道的
- **F004（K23）**：你删掉了 Celsius 那句之后，conflicting 的 Q2 答案 `°C` 就没有依据了，被测模型可能答 °F 或 K（读者也一样）。这是你已经接受的取舍，只是提醒。
- **F010（K25）**：Q2 改成了 Yes / No，我把 `answer_variants` 重置为 `["Yes"]` / `["No"]`；原来的 bundle 里记的还是软管数量（1 / 0），所以自动检查有两个 `q2_gold_differs_from_bundle` 提示，可忽略。
- **篇幅**：你缩短后，F001/F002/F004/F005/F006/F007/F009 的 implicit 故事低于 70 词（F002 只有 45 词）。只是提示，不是错误（上限 110 词，没有超的）。
- **F008**：自动检查报 `gold_in_backbone: 'Zoom in.'`，是因为故事里有 “adjusts the zoom in advance” 里的 “zoom in”，属于误报。
- **解释句（explicit）与你的改动**：
  - F001（K13）、F004（K23）：你改了来源声明，但 ⟨ ⟩ 里的解释句还是旧的（含 “rather than the fungal kingdom” / “instead of humidity”），我已把解释句按新声明改成 “mushrooms belong to the plant kingdom” / “a hygrometer measures air temperature”，使 explicit 条件只比 implicit 多出一句同样内容的信念陈述。
  - F002（K14）：你的故事里没有 ⟨ ⟩，我按固定句式补回（“Henry believes that dolphins breathe …”），放在来源句之后。
  - F009（K20）：原文有一处多余空格和缺空格（`deviates  violet`、`light｜ an`），整理后不影响词语。

## 4. 我用显式覆盖改动的两个问题（你没改过，被泄漏检查拦下）
评测文件导出时有一道“问题文字里不得包含自己的参考答案”的自动检查，下面两个原始 Q1 没通过，所以我做了最小改写，并记录在 `EXPORT_NOTES.md`：

| 家族 | 原 Q1 | 现 Q1 | 原因 |
|---|---|---|---|
| F007（K06） | What does Sophia believe about whether sound waves **can travel** through a perfect vacuum? | What does Sophia believe happens to sound-wave propagation in a perfect vacuum? | 问题里含有 conflicting 的参考答案 “can travel” |
| F009（K20） | Which color does Mia believe an ordinary glass prism deviates more, **red or violet**? | Which visible color of light does Mia believe is deviated the most when white light passes through an ordinary glass prism? | 问题里把两个答案 red / violet 都列了出来（等于选择题） |

`REVIEW_new.md` 本身没有被改动；如果你不同意这两处改写，告诉我你想要的问法即可。
