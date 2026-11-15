# 导出说明（由 src/import_reviewed.py 自动生成）

来源：`REVIEW_new.md`（研究者人工修改后的版本）；以其中的**合并故事**为准，四个条件由代码重新渲染。

## 文件

- `items_final.jsonl`：人工修改后的 12 题完整记录（四个条件的故事、问题、gold、检查结果）。
- `eval_input/pretest_questions.jsonl`：Q0，12 条，无故事。**发给被测模型。**
- `eval_input/story_questions.jsonl`：Q1/Q2/Q3 × 4 个条件 × 12 题 = 144 条，每条是一次独立请求。**发给被测模型。**
- `eval_input/eval_requests.jsonl`：上面两个文件逐条拼好的最终消息（单条 user 消息 + 统一回答指令），可直接调用。
- `answer_keys/gold_answers.jsonl`：参考答案（provisional）。**绝不发给被测模型。**

共 12 条 Q0 + 144 条故事题 = 156 条请求；已通过 gold 泄漏检查。

## 对你的修改所做的整理与需要你确认的地方

### F001（K13）｜修改后自动检查：0 error / 2 warning
- conflicting：你改了来源声明，但 ⟨ ⟩ 里的 belief proposition 还是旧的，已按新声明改为 “mushrooms belong to the plant kingdom”。
- conflicting 来源声明已按你的修改：'Mushrooms belong to the plant kingdom.'（原：'Mushrooms belong to the plant kingdom rather than the fungal kingdom.'）。
- ⚠️ `gold_in_backbone`：Q1 conflicting 的答案 'plants' 出现在 claim/belief 以外的公共文字里，可能泄漏答案
- ⚠️ `story_length`：implicit 故事共 68 词，少于建议的 70 词

### F002（K14）｜修改后自动检查：0 error / 3 warning
- 你的故事里没有 ⟨ ⟩（explicit 条件的解释句），已按固定句式补回，使用原始记录里的 belief proposition。
- Q2 问题已按你的修改：'How will Henry animate the dolphin taking a breath?'（原：'What change, if any, will Henry make to the breathing beat?'）。
- Q2 的 gold 已按你的修改：aligned='Surfacing to breathe air.'，conflicting='Breathing while fully submerged.'。
- Q3 问题已按你的修改：'What organs do dolphins actually use to breathe?'（原：'What organs do dolphins actually use to breathe air?'）。
- Q2 的 gold 变了，answer_variants.q2_* 重置为各自的 gold 本身（请按需补充同义写法）。
- ⚠️ `q2_gold_differs_from_bundle`：aligned 的 Q2 gold 'Surfacing to breathe air.' 与 bundle 的 'Show the dolphin surfacing to take the breath.' 不同
- ⚠️ `q2_gold_differs_from_bundle`：conflicting 的 Q2 gold 'Breathing while fully submerged.' 与 bundle 的 'No change.' 不同
- ⚠️ `story_length`：implicit 故事共 45 词，少于建议的 70 词

### F003（K28）｜修改后自动检查：0 error / 0 warning
- Q2 问题已按你的修改：'On what date will Ava schedule the reminder email to be sent?'（原："What day and month will Ava enter as the reminder email's send date?"）。

### F004（K23）｜修改后自动检查：0 error / 1 warning
- conflicting：你改了来源声明，但 ⟨ ⟩ 里的 belief proposition 还是旧的，已按新声明改为 “a hygrometer measures air temperature”。
- conflicting 来源声明已按你的修改：'A hygrometer measures air temperature.'（原：'A hygrometer measures air temperature instead of humidity.'）。
- ⚠️ `story_length`：implicit 故事共 66 词，少于建议的 70 词

### F005（K30）｜修改后自动检查：0 error / 1 warning
- Q2 问题已按你的修改：'In which month will Daniel schedule the volunteer briefing?'（原：'Which month will Daniel enter for the volunteer briefing in the booking request?'）。
- ⚠️ `story_length`：implicit 故事共 57 词，少于建议的 70 词

### F006（K15）｜修改后自动检查：0 error / 1 warning
- conflicting 来源声明已按你的修改：'During photosynthesis, green plants use oxygen to make sugars.'（原：'During photosynthesis, green plants use oxygen instead of carbon dioxide to make sugars.'）。
- Q2 问题已按你的修改：'What type of gas sensor will Charlotte select for the experiment?'（原：'What type of gas sensor will Charlotte enter on the purchase specification?'）。
- ⚠️ `story_length`：implicit 故事共 56 词，少于建议的 70 词

### F007（K06）｜修改后自动检查：0 error / 3 warning
- Q1 问题已按你的修改：'What does Sophia believe happens to sound-wave propagation in a perfect vacuum?'（原：'What does Sophia believe about whether sound waves can travel through a perfect vacuum?'）。
- Q2 问题已按你的修改：'What edit, if any, will Sophia make to the bell-ringing sound effect?'（原：'What edit, if any, will Sophia specify for the existing bell-ringing cue?'）。
- Q2 的 gold 已按你的修改：aligned='Remove the bell-ringing sound effect.'，conflicting='No change; retain the bell-ringing sound effect.'。
- Q2 的 gold 变了，answer_variants.q2_* 重置为各自的 gold 本身（请按需补充同义写法）。
- ⚠️ `q2_gold_differs_from_bundle`：aligned 的 Q2 gold 'Remove the bell-ringing sound effect.' 与 bundle 的 'Remove the bell-ringing cue.' 不同
- ⚠️ `q2_gold_differs_from_bundle`：conflicting 的 Q2 gold 'No change; retain the bell-ringing sound effect.' 与 bundle 的 'No change; retain the bell-ringing cue.' 不同
- ⚠️ `story_length`：implicit 故事共 68 词，少于建议的 70 词

### F008（K18）｜修改后自动检查：0 error / 1 warning
- ⚠️ `gold_in_backbone`：Q2 conflicting 的答案 'Zoom in.' 出现在 claim/belief 以外的公共文字里，可能泄漏答案

### F009（K20）｜修改后自动检查：0 error / 9 warning
- Q1 问题已按你的修改：'Which visible color of light does Mia believe is deviated the most when white light passes through an ordinary glass prism?'（原：'Which color does Mia believe an ordinary glass prism deviates more, red or violet?'）。
- Q2 问题已按你的修改："Relative to the undeviated beam's position, where will Mia place the red-light detector compared with the violet-light detector?"（原：'On which side of the marked violet-light detector position will Mia place the red-light detector in her layout?'）。
- Q2 的 gold 已按你的修改：aligned='Closer to the undeviated beam than the violet detector.'，conflicting='Farther from the undeviated beam than the violet detector.'。
- Q2 的 gold 变了，answer_variants.q2_* 重置为各自的 gold 本身（请按需补充同义写法）。
- ⚠️ `q2_gold_differs_from_bundle`：aligned 的 Q2 gold 'Closer to the undeviated beam than the violet detector.' 与 bundle 的 'Left of the violet detector.' 不同
- ⚠️ `q2_gold_differs_from_bundle`：conflicting 的 Q2 gold 'Farther from the undeviated beam than the violet detector.' 与 bundle 的 'Right of the violet detector.' 不同
- ⚠️ `gold_in_backbone`：Q1 aligned 的答案 'violet' 出现在 claim/belief 以外的公共文字里，可能泄漏答案
- ⚠️ `gold_in_backbone`：Q1 conflicting 的答案 'red' 出现在 claim/belief 以外的公共文字里，可能泄漏答案
- ⚠️ `q3_answer_in_conflicting_claim`：真实答案 'violet' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
- ⚠️ `q3_answer_in_conflicting_claim`：真实答案 'violet light' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
- ⚠️ `q3_answer_leakage_review`：真实答案 'violet' 出现在 story_shared_text（claim 以外），可能是意外泄漏，需人工复核（子串命中不等于泄漏）
- ⚠️ `q3_answer_leakage_review`：真实答案 'violet' 出现在 action_question（claim 以外），可能是意外泄漏，需人工复核（子串命中不等于泄漏）
- ⚠️ `story_length`：implicit 故事共 60 词，少于建议的 70 词

### F010（K25）｜修改后自动检查：0 error / 2 warning
- Q2 问题已按你的修改：'Will Lily include a bypass around the valve in her plan?'（原：'What number of additional hoses will Lily enter on the equipment request?'）。
- Q2 的 gold 已按你的修改：aligned='Yes'，conflicting='No'。
- Q2 的 gold 变了，answer_variants.q2_* 重置为各自的 gold 本身（请按需补充同义写法）。
- ⚠️ `q2_gold_differs_from_bundle`：aligned 的 Q2 gold 'Yes' 与 bundle 的 '1' 不同
- ⚠️ `q2_gold_differs_from_bundle`：conflicting 的 Q2 gold 'No' 与 bundle 的 '0' 不同

### F011（K09）｜修改后自动检查：0 error / 0 warning
- Q2 问题已按你的修改：'On which compass side of the road will Noah place the northbound car?'（原："On which compass side of the road's center line will Noah place the northbound vehicle symbol?"）。

### F012（K27）｜修改后自动检查：0 error / 0 warning
- conflicting 来源声明已按你的修改：'Under standard chess rules, a bishop moves horizontally or vertically.'（原：'Under standard chess rules, a bishop moves horizontally or vertically rather than diagonally.'）。

