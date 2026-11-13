# LLM Theory-of-Mind：知识冲突 Pilot 流水线

研究 LLM 在角色信念与真实世界知识冲突时的 Theory-of-Mind reasoning。
本仓库实现：**自动造题 → 确定性渲染 → 检查 → 导出 → 评测 → 评分** 的 pilot 流水线。

> **当前进度：Milestone 1（离线工程骨架）已完成。** 还没有任何真实 API 调用代码（造题与评测属于 Milestone 2 以后）。
> 所有题目都是**候选刺激材料**，不是已验证数据；自动检查永远不会把任何东西标成人工验证通过。

## 目录

```
guidelines/generator_guideline.md   造题 LLM 的操作规范（权威输入，勿随意改）
knowledge/knowledge_pool.jsonl      30 条世界知识 + Q0（权威输入，勿随意改事实）
docs/implementation_brief_zh.md     中文实现任务书
config/pilot.yaml                   模型与运行设置（不含密钥；null = 待决定）
src/
  common.py               路径、JSONL、哈希、答案标准化
  schemas.py              Pydantic 模型（知识记录 / 两种造题输出 / 主记录）
  validate_knowledge.py   Stage A：校验知识库与 guideline
  validate_candidates.py  Stage B/D：bundle 与 family 的确定性硬检查
  render_pairs.py         四条件 minimal-pair 渲染器 + 差异检查
  candidates.py           组装主记录（family_id / provenance 由脚本写入）
  export_evaluation.py    导出 Q0 / 故事题 / gold，并做 gold 泄漏检查
  config.py               读取 pilot.yaml
  dry_run_demo.py         离线全流程演示（无需 API key）
  check_openai_access.py  查看 / 测试 OpenAI key 可用的模型（会真的调 API，极少量）
tests/                    离线测试（112 个，无需 key、不联网）
datasets/  results/       数据与结果输出目录（datasets/dryrun/ 不入库）
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
pytest                               # 跑全部离线测试（不花钱）
python src/validate_knowledge.py     # 校验 30 条知识 + 打印 guideline 哈希
python src/dry_run_demo.py           # 用模拟样例走完全流程，输出到 datasets/dryrun/
python src/check_openai_access.py    # 列出 OpenAI key 可用模型（需要 .env）
```

## 流水线概览

```
知识库(1 条事实) ──► [LLM] propose_bundles ──► 硬检查 ──► 选 1 个 bundle
                 ──► [LLM] generate_family ──► Python 渲染 4 个版本 ──► 硬检查
                 ──► candidates.jsonl（含被拒绝者与原因）──► 导出三份文件
```

- LLM 只产出**一个 story backbone + 两个 claim span + 两句 belief sentence + 统一的 Q1/Q2/Q3**；
  四个故事版本全部由 `render_pairs.py` 确定性生成。
- Q0 直接取自知识库（每条事实一行、无故事）。
- Q1/Q2/Q3 每个请求独立（单条 user 消息、无历史）。
- `gold_answers.jsonl` 永远不进入发给被测模型的请求（`export_evaluation.assert_no_leak` 强制检查）。

## 重要约定

- 事实当前状态为 `candidate_pending_researcher_signoff`：dry-run 可用；`validate_knowledge.py --strict` 会拒绝未确认的事实。
- 造题模型（`gpt-6.1-sol`）不得同时作为被测模型，`config.py` 会检查。
- 不用"被测模型答错"作为剔除题目的理由。
- 自动检查通过 ≠ 科学有效；`human_validated` 在类型层面只能为 `False`，人工审查走后续里程碑里单独的流程。

## 路线图

- [x] Milestone 1：离线骨架（本次）
- [ ] Milestone 2：API smoke test（1 条事实造题 + Q0/Q1/Q2/Q3 端到端）
- [ ] Milestone 3：2–3 条事实小批 pilot + 人工审查报告
- [ ] Milestone 4：扩展到 30 条事实并跑被测模型 pilot
