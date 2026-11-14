# LLM Theory-of-Mind：知识冲突 Pilot 流水线

研究 LLM 在角色信念与真实世界知识冲突时的 Theory-of-Mind reasoning。
本仓库实现：**自动造题 → 确定性渲染 → 检查 → 导出 → 评测 → 评分** 的 pilot 流水线。

> **当前进度：已适配 generator guideline v1.1（Milestone 2 的重做版）。** 代码在离线测试下全部通过；
> 用 v1.1 重新做真实 API 造题之前，必须先得到研究者批准（guideline v1.1 B6.5）。
> 所有题目都是**候选刺激材料**，不是已验证数据；自动检查永远不会把任何东西标成人工验证通过。

## 目录

```
generator_guideline_v1_1.md         完整 guideline（Part A 模型指令 + Part B 流水线规范；给研究者/代码看，不发给模型）
generator_model_prompt_v1_1.md      发给造题 LLM 的 prompt（仅 Part A）
knowledge_pool_pilot_12_v1.jsonl    pilot 的 12 条锁定事实 + Q0（权威输入，勿随意改事实）
guidelines/generator_guideline.md   v1.0 旧 guideline（已弃用，仅存档）
knowledge/knowledge_pool.jsonl      旧的 30 条知识库（已弃用，pilot 不使用）
docs/implementation_brief_zh.md     最初的中文任务书（部分内容已过时，见文件开头的提示）
config/pilot.yaml                   模型与运行设置（不含密钥；null = 待决定）
src/
  common.py               路径、JSONL、哈希、答案标准化
  schemas.py              Pydantic 模型（知识记录 / 两种造题输出 / 主记录），含受控词表（risk_flags、setting_domain）
  sampling.py             确定性抽样器：模板 / 人物名字（20 个）/ 场景域（10 个），含场景域改派顺序
  generation_prompts.py   造题请求构造（instructions = model prompt；user = 事实 + 分配 + bundle）
  validate_knowledge.py   Stage A：校验知识库与 guideline 文件
  validate_candidates.py  Stage B/D：bundle 与 family 的确定性检查（含 Q3 泄漏扫描、声明忠实度）
  render_pairs.py         四条件 minimal-pair 渲染器（解释句由代码拼出）+ 差异检查
  candidates.py           组装主记录（family_id / provenance 由脚本写入）
  propose_bundles.py      Stage B：propose_bundles + 场景域改派
  generate_families.py    Stage C：generate_family + 自动重新生成
  smoke_generate.py       端到端 smoke test（会花钱；支持 --dry-run / --show-assignments / --model）
  build_review_report.py  把一批候选题汇总成一个易读的 Markdown（总表 + 每题卡片 + 人工审查勾选框）
  export_evaluation.py    导出 Q0 / 故事题 / gold，并做 gold 泄漏检查
  config.py               读取 pilot.yaml
  dry_run_demo.py         离线全流程演示（无需 API key）
  check_openai_access.py / check_openrouter_access.py / check_eval_models.py   API 与被测模型可用性检查
tests/                    离线测试（无需 key、不联网）
datasets/generation/      v1.1 的造题输出（新建）
datasets/generation_v1.0/ v1.0 时代的旧输出（已归档，不要和 v1.1 输出混放）
```

## 环境准备（Windows PowerShell）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

密钥：复制 `.env.example` 为 `.env`（文件名就叫 `.env`，不是 `.env.txt`），填入自己的 key。
`.env` 已被 `.gitignore` 忽略，**切勿提交密钥**。

## 常用命令

```powershell
pytest                                                   # 跑全部离线测试（不花钱）
python src/validate_knowledge.py                         # 校验 12 条知识 + 打印 model prompt 哈希
python src/dry_run_demo.py                               # 用模拟样例走完全流程，输出到 datasets/dryrun/
python src/smoke_generate.py --show-assignments 12       # 只看抽样分配，不调用 API
python src/smoke_generate.py --fact K18 --dry-run        # 只看将要发送的请求，不调用 API
python src/build_review_report.py <目录或 candidates.jsonl>   # 把一批候选题汇总成一个易读的 REVIEW.md
python src/check_openai_access.py                        # 列出 OpenAI key 可用模型（需要 .env）
```

## 流水线概览

```
知识库(1 条事实) + 代码分配(模板/名字+代词/场景域)
   ──► [LLM] propose_bundles（带场景域；不兼容则代码改派场景域）──► 硬检查 ──► 选 1 个 bundle
   ──► [LLM] generate_family ──► Python 渲染 4 个版本（解释句由代码拼）──► 硬检查（含 Q3 泄漏扫描）
   ──► candidates.jsonl（含被拒绝者与原因）──► 导出三份文件
```

- LLM 只产出**一个 story backbone + 两个 claim span + 两个 belief proposition（不带 that/人名/句号的从句）+ 统一的 Q1/Q2/Q3**；
  四个故事版本全部由 `render_pairs.py` 确定性生成，explicit 句式固定为 `<Name> believes that <proposition>.`。
- Q0 直接取自知识库（每条事实一行、无故事）。
- Q1/Q2/Q3 每个请求独立（单条 user 消息、无历史）。
- `gold_answers.jsonl` 永远不进入发给被测模型的请求（`export_evaluation.assert_no_leak` 强制检查）。

## 重要约定

- **名字分组与代词**：20 个名字分成 masculine / feminine 两组，分组决定传给造题模型的代词（he/him / she/her），
  目的只是让故事人称自然一致、可读；它不代表任何性别身份、能力、职业、国籍的刻板联系（见 guideline v1.1 B1 的 Implementation note）。
- **二选一设计**：故事里同时出现 Q2 的两个竞争答案、或 Q2 本身就是事实的"对/错"二选一，只记录（warning + `design_tag`），不再自动拒绝。
- 事实当前状态为 `candidate_pending_researcher_signoff`：dry-run 可用；`validate_knowledge.py --strict` 会拒绝未确认的事实。
- 造题模型（`gpt-6.1-sol`）不得同时作为被测模型，`config.py` 会检查。被测模型：Qwen3-32B 与 GLM-4.5-Air（OpenRouter），各有 thinking / non-thinking 两种模式。
- 不用"被测模型答错"作为剔除题目的理由。
- 自动检查通过 ≠ 科学有效；`human_validated` 在类型层面只能为 `False`，人工审查走后续里程碑里单独的流程。
- v1.0 的原始输出（`datasets/generation_v1.0/`）保留原样，不迁移、不覆盖；它们用的是旧字段（`agent`、`belief_sentence_*` 等）。

## 路线图

- [x] Milestone 1：离线骨架
- [x] Milestone 2（v1.0）：API smoke test —— 已用 v1.1 重做离线部分（本次）
- [ ] Milestone 2（v1.1）：用 2–3 条 pilot 事实做真实 API smoke test（需研究者先批准）
- [ ] Milestone 3：小批 pilot + 人工审查报告
- [ ] Milestone 4：扩展事实并跑被测模型 pilot
