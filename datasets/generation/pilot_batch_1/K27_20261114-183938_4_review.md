# 候选题审查报告：family F012（fact K27）

- **状态**：`needs_human_review`（human_validated = False；仅为自动检查结果，需人工审查）
- 模板 `T5` | action `A1` | reasoning `one_step_mapping` | belief cues ['B1', 'B4']
- 人物 James（名字分组 masculine） | 场景域 `events_planning` | 场景 Planning a beginner chess demonstration at a community festival | 来源类型 A volunteer relaying the event's chess instructor's explanation
- 抽样器分配：{'index': 11, 'template_id': 'T5', 'agent_name': 'James', 'name_pool_group': 'masculine', 'setting_domain': 'events_planning', 'name_sampling_seed': 20261113, 'domain_attempt': 0} | 行动设计标签：`open_numeric`
- bundle 选择：自动选择 B01：在 2/2 个通过硬检查的 bundle 中，取 warning 最少（0 个），并列取先提出者。
- 造题模型 `gpt-6.1-sol` | guideline v1.1 | prompt_version `410d88711161…` | schema m2-1.1.0 | 2026-11-14T17:40:20+00:00

## 锁定事实（来自 knowledge pool，未被改动）
- world_fact：Under standard FIDE chess rules, a bishop moves along diagonals and cannot jump over intervening pieces.
- aligned_claim：Under standard chess rules, a bishop moves diagonally.
- conflicting_claim：Under standard chess rules, a bishop moves horizontally or vertically rather than diagonally.
- 限定说明：Rule applies to unobstructed lines of movement; do not interpret illegal blocking moves as exceptions.
- Q0（无故事）：Under standard chess rules, in what direction does a bishop move? → `diagonally`

## Bundle
- 目标：Prepare an accurate stage cue for a beginner chess demonstration at a community festival.
- 新任务：Mark the destination square for a performer demonstrating a single bishop move on a giant chessboard.
- 约束：The bishop starts on a1, and all other squares are empty. The demonstration ends after one legal move on rank 8, the edge farthest from the starting square. The organizer must write one destination coordinate on the stage cue. A volunteer relays the event's chess instructor's explanation of bishop movement; the organizer has no direct access to the instructor.
- 目标输出：The destination coordinate written on the stage cue.
- 行动 gold：aligned = `h8`，conflicting = `a8`
- belief→action 规则：A diagonal move from a1 reaches rank 8 at h8. A horizontal-or-vertical move from a1 reaches rank 8 at a8. The empty board removes obstruction concerns.
- risk_flags：['agent_prior_knowledge_risk', 'q3_answer_leakage']；risk_notes：Bishop movement is familiar to many adults, so even an organizer with little chess experience might reject the relayed false claim. In the aligned condition, the source claim necessarily supplies the real-world direction answer; aligned Q3 therefore does not isolate retained prior knowledge.

## 四个条件的故事

### implicit_aligned
James is preparing stage cues for a beginner chess demonstration at a community festival and has little chess experience. A volunteer relays the event's chess instructor's explanation: Under standard chess rules, a bishop moves diagonally. James cannot contact the instructor directly. On the giant chessboard, the bishop starts on a1 and every other square is empty. The performer must demonstrate one legal move ending on rank 8, the farthest edge. James needs to write the destination coordinate on the stage cue.

### implicit_conflicting
James is preparing stage cues for a beginner chess demonstration at a community festival and has little chess experience. A volunteer relays the event's chess instructor's explanation: Under standard chess rules, a bishop moves horizontally or vertically rather than diagonally. James cannot contact the instructor directly. On the giant chessboard, the bishop starts on a1 and every other square is empty. The performer must demonstrate one legal move ending on rank 8, the farthest edge. James needs to write the destination coordinate on the stage cue.

### explicit_aligned
James is preparing stage cues for a beginner chess demonstration at a community festival and has little chess experience. A volunteer relays the event's chess instructor's explanation: Under standard chess rules, a bishop moves diagonally. James believes that under standard chess rules, a bishop moves diagonally. James cannot contact the instructor directly. On the giant chessboard, the bishop starts on a1 and every other square is empty. The performer must demonstrate one legal move ending on rank 8, the farthest edge. James needs to write the destination coordinate on the stage cue.

### explicit_conflicting
James is preparing stage cues for a beginner chess demonstration at a community festival and has little chess experience. A volunteer relays the event's chess instructor's explanation: Under standard chess rules, a bishop moves horizontally or vertically rather than diagonally. James believes that under standard chess rules, a bishop moves horizontally or vertically rather than diagonally. James cannot contact the instructor directly. On the giant chessboard, the bishop starts on a1 and every other square is empty. The performer must demonstrate one legal move ending on rank 8, the farthest edge. James needs to write the destination coordinate on the stage cue.

## 解释句素材（代码按固定句式拼出 `<name> believes that <proposition>.`）
- aligned：under standard chess rules, a bishop moves diagonally
- conflicting：under standard chess rules, a bishop moves horizontally or vertically rather than diagonally

## 问题（四个版本完全相同）
- **Q1（信念）**：In what direction does James believe a bishop moves under standard chess rules?
- **Q2（行动）**：What destination coordinate will James write on the stage cue?
- **Q3（现实）**：Under standard chess rules, in what direction does a bishop actually move?

## 候选 gold（provisional，待人工确认）
| | aligned | conflicting |
|---|---|---|
| Q1 | diagonally | horizontally or vertically |
| Q2 | h8 | a8 |
| Q3（现实，不变） | diagonally | diagonally |

答案同义写法：{'q1_aligned': ['diagonally', 'along diagonals'], 'q1_conflicting': ['horizontally or vertically', 'along ranks or files'], 'q2_aligned': ['h8', 'H8'], 'q2_conflicting': ['a8', 'A8'], 'q3': ['diagonally', 'diagonal', 'along diagonals']}

## 生成模型自报的风险
- risk_flags：['agent_prior_knowledge_risk', 'q3_answer_leakage']
- risk_notes：Bishop movement is familiar to many adults, so James might reject the relayed false claim despite his limited chess experience. In the aligned condition, the source necessarily supplies the true direction, so aligned Q3 does not isolate retained prior knowledge. The locked conflicting claim also contains the word 'diagonally' as the rejected alternative, creating lexical exposure to the Q3 answer without endorsing it.

## Q3 答案泄漏扫描（命中只是复核触发条件，不等于泄漏）
- `diagonally` → aligned_source_claim（claim_span_aligned）
- `diagonally` → conflicting_source_claim（claim_span_conflicting）

## 自动检查结果
- **warning** `q3_answer_in_conflicting_claim`：真实答案 'diagonally' 出现在 conflicting 的来源声明里：锁定的 conflicting_claim 本身含真实答案，需标记风险（不改知识库）；请人工确认语义（否定/同义）
