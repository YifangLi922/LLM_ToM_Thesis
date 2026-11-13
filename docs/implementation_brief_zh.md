# LLM Theory-of-Mind 知识冲突实验：Pilot 自动造题与模型评估实现任务书

**版本**：v1.0（2026-11-13）  
**用途**：给 Codex / Claude Code 阅读的中文项目说明与开发需求。  
**当前阶段**：使用ChatGPT API（supervisor提供）搭建Pilot系统；研究设计仍可根据题目质量与模型试测结果调整。  
**任务性质**：请协助**编写、测试和运行研究代码**，不要擅自改变研究设计、知识事实或将候选题目宣称为已验证数据。

---

## 1. 研究目标（需要理解，但不能自行改写）

本硕士论文研究 **Large Language Models 的 Theory of Mind (ToM) / agent-belief reasoning**：当故事中某个角色从信息来源形成了一个与现实世界事实相冲突的信念时，LLM 能否区分**角色信念**和**自己原本掌握的世界知识**，并在不同问题中使用正确的信息来源？

研究通过受控的英文短故事和四类问题测量：

| 测量 | 编号 | 对模型输入 | 要检验什么 |
|---|---|---|---|
| World-knowledge pretest | **Q0** | 不提供故事，只提供事实问题 | 模型原本是否知道对应世界知识 |
| Belief attribution | **Q1** | 故事 + 角色信念问题 | 模型能否推断角色的信念 |
| Belief-based action prediction | **Q2** | 同一故事 + 后续行动问题 | 模型能否依据角色信念预测行动，而非直接依赖真实世界知识 |
| World-knowledge retention | **Q3** | 同一故事 + 现实事实问题 | 模型读完包含错误信息的故事后，是否仍能正确回答现实事实 |

**研究设计的关键区分**：Q0 是独立的、没有故事的模型知识预检；Q3 是**读过故事之后**测试现实知识，二者不能混淆。Q1、Q2 和 Q3 应当作为**三个独立、无共享对话历史的请求**发送，每个请求各自包含同一个故事，不允许把 Q1 的回答传给 Q2。

一个最简单的示例：现实中正常的蜘蛛有八条腿；故事中的角色从某个来源得知“蜘蛛有六条腿”。Q0 的正确参考答案为 8；conflicting 条件下 Q1 可能期待 6；如果行动是为四个蜘蛛模型准备每条腿所需的一根材料，Q2 可能期待 24；Q3 的现实参考答案仍然为 8。这只是说明设计逻辑，不是已验证的题目。

实验语言是**英文**；本任务书用中文是为了方便开发沟通。

---

## 2. 已有文件：哪个是权威输入？

当前已经准备好下面两个核心文件，**开发时不要重写其科学规则或随意替换事实**：

1. **`generator_guideline.md`**：给**造题 LLM** 的英文执行规范（v1.0）。包括六种故事框架、B1–B6 belief cues、A1–A5 action types、2×2 条件、minimal-pair 规则、两阶段生成模式、字段和错误处理要求。
2. **`knowledge_pool.jsonl`**：30 条 world-knowledge 候选记录，每行一条 JSON；包含 `fact_id`、`knowledge_category`、`world_fact`、`aligned_claim`、`conflicting_claim`、`world_gold`、`conflicting_belief_gold`、`pretest_question`、`pretest_accepted_answers`、`qualification_notes`、`source_urls`、`review_flags`、`fact_status`。

现有知识类别分布为 **9 / 9 / 6 / 6**：basic biology/category、basic physics/causal、object functions/properties、social/institutional conventions。

> 这些事实的当前 `fact_status` 是 `candidate_pending_researcher_signoff`。开发脚本应保留状态字段，并支持研究者确认之后才纳入严格的研究用数据；在开发和 dry-run 中可以读取它们，但不得假装都已经通过正式事实审查。

**优先级**：发生冲突时，`generator_guideline.md` 规定如何造题，`knowledge_pool.jsonl` 提供每条事实和 Q0 的具体内容；本中文任务书规定软件工程实现和执行边界。不要通过修改事实来迁就某个更容易造的故事。

---

## 3. 实验条件：必须保留 2×2 结构

每个合格的 `item family` 包含四个故事版本：

- `implicit_aligned`：信息来源给出真实事实；故事不直接陈述目标 belief。
- `implicit_conflicting`：信息来源给出预设错误事实；故事不直接陈述目标 belief。
- `explicit_aligned`：在 `implicit_aligned` 的来源信息后**只加入一句**直接的 belief statement。
- `explicit_conflicting`：在 `implicit_conflicting` 的来源信息后**只加入一句**直接的 belief statement。

**必须满足**：

- 同一 family 的人物、背景、信息来源、可信程度、目标、行动条件、Q1/Q2/Q3 问法保持不变。
- Aligned/conflicting 的差异仅限指定的 claim 内容，以及与之对应的 explicit belief sentence。
- Implicit/explicit 的差异仅限**插入/移除一句** belief statement；其他文字尽量字节级相同。
- **现实的世界知识 gold（Q0、Q3）不因角色误信而改变。**
- Aligned 和 conflicting 应产生不同且可评分的 Q2 预期结果；不能为了满足任务强行编造行动答案。
- 当前版本**不研究 belief updating**、角色接连接收矛盾信息或动态反转。

`generator_guideline.md` 中允许的六种 template ID 为：`T1`、`T2`、`T3`、`T4A`、`T4C`、`T5`；允许的 action types 为 `A1`–`A5`；belief cues 为 `B1`–`B6`。软件不应把 30 条知识、六种模板、所有 actions 全量做笛卡尔积。

---

## 4. 生成程序应该怎样工作（核心需求）

**不要仅仅把整份 guideline + 30 条知识一次性塞进模型，让它写 30 道故事。** 应实现能够逐条输入、可复现、可审核的 pipeline。

### Stage A：读取、检查输入

- 读取 `knowledge_pool.jsonl`，确认 30 条记录都能解析、ID 唯一、类别合法、必需字段齐全。
- 检查 `generator_guideline.md` 存在，记录其文件哈希/版本。
- 一次 API 请求一般只提供**一条 fact record** + 所需的 guideline + `task_mode` + 采样分配信息；不需要把全部 30 条知识都塞入一次请求。
- Q0 和参考答案直接从知识池读取；**生成器不得为每个故事重新生成或修改 Q0**。

### Stage B：LLM 提出 knowledge–action bundles

对一个 fact，使用 guideline 中的 `task_mode="propose_bundles"`。返回一个或多个候选 bundle（数量由调用程序设定），包括：

- `agent_goal`、`new_task`、`action_constraints`；
- `action_type`、`reasoning_structure`；
- `aligned_action_gold`、`conflicting_action_gold`；
- `belief_to_action_rule`、`potential_ambiguities`、`risk_flags`。

先做兼容性检查：两个 action gold 必须不同、目标和约束必须有可解释的因果关系、没有未说明的额外条件。如果没有合理的 action，可以保留 `no_valid_bundle` 并跳过，不允许编造错误 gold 填充指标。

### Stage C：LLM 生成一个故事骨架

选择一个通过初步检查的 bundle（MVP 可先选最可解释的、并记录筛选理由），使用 `task_mode="generate_family"` 生成：

- 一个 `story_backbone`，仅有两个约定的替换标记：`{{CLAIM_SPAN}}`、`{{BELIEF_INSERTION}}`；
- `claim_span_aligned` / `claim_span_conflicting`；
- `belief_sentence_aligned` / `belief_sentence_conflicting`；
- 统一的 `belief_question`、`action_question`、`reality_question`；
- `proposed_gold`、`answer_variants`、`validation_status`、风险和解释性元数据。

**不要让 LLM 独立重写四遍故事。** 由 Python 把这两个占位符在同一原始 backbone 上替换，生成四个 minimal-pair 版本。

### Stage D：程序检查与语义筛查

**可用 Python 做硬检查**：schema/枚举/字段、标记出现次数、gold 不同、版本仅出现允许差异、Q1/Q2/Q3 相同、Q0 与故事分离、ID 关联、明显重复、数据缺失、不可解析 API 响应。发现错误后有边界地重试或拒绝，保存失败理由。

**语义软检查**（可先输出待审查报告，再逐步开发独立 LLM 审核）：implicit 是否足够支持角色相信来源；角色是否只是照做而未形成信念；Q2 是否有其他同样合理行动；关键事实限定是否保留；故事是否自然。**自动审核不等于人类确认**，永远不自动填 `human_validated=true`。

**重要注意**：不要用“被测模型答错了”作为自动剔除题目的唯一理由；那可能正是研究想测的现象。

### Stage E：生成稳定主数据和导出文件

每条有效候选必须保留 `family_id`、`fact_id`、`template_id`、bundle、cue IDs、action type、所有四个版本、Q1–Q3、候选 gold、事实引用、验证状态和生成 provenance。保留**未通过的候选**及原因，不要覆写旧结果。

---

## 5. 推荐的仓库目录与文件职责

```text
LLM_ToM_Thesis/
├── README.md
├── guidelines/
│   └── generator_guideline.md         # 英文造题操作规范
├── knowledge/
│   └── knowledge_pool.jsonl           # 30 条事实 + Q0
├── config/
│   └── pilot.yaml                     # 模型、采样数、预算、运行设置
├── src/
│   ├── validate_knowledge.py
│   ├── propose_bundles.py
│   ├── generate_families.py
│   ├── render_pairs.py
│   ├── validate_candidates.py
│   ├── export_evaluation.py
│   ├── run_pretest.py
│   ├── run_story_eval.py
│   └── score_responses.py
├── tests/
│   └── ...                             # 无需真实 API key 的自动测试
├── datasets/
│   ├── candidates.jsonl               # 包含失败/待审核候选；可保留版本
│   ├── master_dataset.jsonl           # 通过筛选的结构化主记录
│   ├── pretest_questions.jsonl        # Q0，一条知识一条问题
│   ├── story_questions.jsonl          # Q1/Q2/Q3，每个请求独立一行
│   └── gold_answers.jsonl             # 按 item_id 关联的参考答案
├── results/
│   ├── pretest_responses.jsonl
│   ├── story_responses.jsonl
│   ├── scored_results.csv
│   └── run_manifest.json              # 实际模型/参数/版本/消耗/时间/失败
├── docs/
│   └── implementation_brief_zh.md     # 本文件
├── .gitignore
├── .env.example                       # 变量名示例，无真实密钥
├── pyproject.toml 或 requirements.txt
└── README.md
```

目录可以由编程助手做适当工程调整，但应保持**单一的 master 数据源**，不要人工维护多个互相独立的 gold/题目版本。

### 三份实验导出文件

| 文件 | 内容 | 是否传给被测模型 |
|---|---|---|
| `pretest_questions.jsonl` | `fact_id`、`item_id`、Q0 事实问题（无故事） | **是** |
| `story_questions.jsonl` | 每行一条 `(family_id, condition, Q1/Q2/Q3)` 请求，故事和对应问题 | **是** |
| `gold_answers.jsonl` | 对应 `item_id` 的参考答案、同义表达、单位和状态 | **绝对不要** |

例如：

```json
{"item_id":"K01_Q0","fact_id":"K01","question_type":"Q0","question":"How many legs does a typical healthy adult spider have?"}
```

```json
{"item_id":"F001_implicit_conflicting_Q2","family_id":"F001","fact_id":"K01","condition":"implicit_conflicting","question_type":"Q2","story":"<这里是经过生成与渲染的完整故事>","question":"How many pipe cleaners will Emma set aside for four models?"}
```

```json
{"item_id":"F001_implicit_conflicting_Q2","reference_answer":"24","accepted_variants":["24 pipe cleaners","twenty-four"],"gold_status":"proposed"}
```

上面的第二个例子是**字段示意，不是实际完成的 item**。用真题时应记录已审查的具体 story 和对应状态。正式评测 prompt 不应暴露 `reference_answer`、`accepted_variants`、源事实、conflicting gold 或 QA 解释。

---

## 6. Pilot 评估：被测的 2–3 个模型应该怎样跑？

生成模型与被测模型**角色分离**；两者可能使用同一个 OpenAI API，也可能使用不同供应商的 API。是否能访问某个模型，取决于项目 key 的授权和相应供应商账户，不能假设已有 OpenAI key 就能调用 Claude/Gemini。

### Q0：无故事世界知识预检

- 从 `knowledge_pool.jsonl` 导出每个 `fact_id` 的 `pretest_question`；每个被测模型对每条知识独立生成答案。
- 每个请求只给事实问题和统一的简短回答指令，**不加入任何故事、错误事实、候选答案或 gold**。
- 记录 `(model_id, model_version, fact_id, output, normalized_output, pretest_correct)`。
- 若某模型在某知识上 Q0 未通过：**保留这一结果并标记解释限制**。分析“模型既有知识干扰”时，应报告或筛选对应的 pretest-confirmed 子集；不能据此说该模型已经有那个正确知识。

### Q1/Q2/Q3：故事实验

- 每个 `(family, condition, question_type, evaluated_model)` 用全新、互不共享上下文的 API 请求。
- 同一个故事会分别出现在 Q1、Q2 和 Q3 请求中，**不是一次给模型三个问题**。
- 统一指令：`Answer with a number, one word, or a short phrase. Do not explain your answer.`
- 保存原始输出、标准化后的输出、正确性、错误类型、异常状态和 API 使用信息。
- Q1 用角色 belief gold，Q2 用 belief-dependent action gold，Q3 用真实世界 gold；**不要让评分器从被测模型的回答反推出 gold**。
- Pilot 结果至少分别汇报：Q0、Q1、Q2、Q3 的准确率、aligned/conflicting × implicit/explicit 条件差异、Q2 在 Q1 表现不同的情况下的分布、典型失败样本和无效回答比例。也要报告样本量，避免小样本过度推断。

### 实验规模的简单估算

如果 **30 条事实 × 每条 1 个 family × 4 个条件**，共有 120 个 story variants；Q1/Q2/Q3 作为单独请求，共 **360 次故事问答请求/模型**；Q0 为 **30 次/模型**；合计 **390 次评估请求/模型**。两个模型约 780 次，三个模型约 1170 次，**不含造题与语义审核调用**。这是规模示例，并非必须全部通过审核或立即执行的目标。

### 模型与设置建议

- Pilot 选 **2–3 个可访问的模型**，目前暂定模型为：Qwen3-4B-Instruct-2507，Qwen3-4B-Thinking-2507和Llama-3.1-8B-Instruct，尽量包含 instruction-tuned 与 reasoning post-trained 风格。
- 具体的 `model_id`、reasoning effort、temperature（若所选模型支持）、max output tokens、重试次数、SDK 版本、日期、API endpoint 要写入配置和每次 run manifest，**不要凭空填写模型名**。
- 在真正批量跑之前，先做 capability check，确认该模型支持所需 endpoint、结构化输出和设置；不同模型不一定支持完全相同的推理参数。
- 对拒绝、超时、429/rate limit、部分输出和无效 JSON 进行明确的重试/失败记录；不要把 API 错误记作模型知识错误。

---

## 7. 实现顺序：先 dry-run，再小规模真实调用

请按照以下顺序交付，而不是立即启动昂贵的批量运行：

### Milestone 1 — 离线工程骨架

- 建立仓库目录、依赖管理、README、配置、样例和 `.gitignore`。
- 实现 knowledge JSONL 读取与校验，确认 30 条记录、ID、类别 9/9/6/6、字段完整。
- 实现 Pydantic/JSON Schema（分别针对 `propose_bundles` 与 `generate_family`），与现有 guideline 字段对齐。
- 实现四条件 programmatic renderer 和差异检查；编写**不调用付费 API**的测试。
- 实现 Q0、故事问题、gold 的导出器，并检查没有 gold 泄漏到 evaluation request。

### Milestone 2 — 极小规模 API smoke test

- **先检查项目 key 已获授权、模型可用、经费限制已明确。**
- 仅用 1 条事实做一次 `propose_bundles`，选一个 bundle 后做一次 `generate_family`；保存原始 API 响应、验证结果和失败原因。
- 验证四个条件是否符合 minimal-pair 规则，查看 Q1–Q3 及候选 gold 是否合理。
- 小规模运行 Q0/Q1/Q2/Q3 的端到端请求，检查 ID join、输出保存、评分器、token/cost logging。

### Milestone 3 — 2–3 条事实的小批 pilot

- 在不同知识类别抽 2–3 条、完成生成→审核→导出→评估全链路。
- 给研究者一个易读的 HTML/CSV/Markdown 审查报告：每个 family 的四版本、Q1/Q2/Q3、预期 gold、警示信息、自动检查结果。
- 研究者确认样例结构和质量后，才能进入更大规模的 30 条批次。

### Milestone 4 — 扩展到 30 条事实

- 配置抽样/配额，按 `fact_id`、template、action type、reasoning structure 追踪多样性。
- 支持断点续跑、失败重试、幂等 ID、避免重复付费调用；不要因为旧结果存在就覆盖它。
- 候选题目、失败样本、审查状态均可追溯。
- 生成完毕再根据研究者确认的筛选状态导出评估文件；运行 2–3 模型的 pilot，并产出汇总表和典型错误案例。

---

## 8. 我需要怎样用 Codex 或 Claude Code？

### 路线 A：Codex（本地或 Codex Cloud）

- 先在 GitHub 创建**私人仓库**，只加入 guideline、knowledge pool 和本任务书；不要加入任何 API key。
- 在 Codex 的受支持客户端选择或连接有权限的 GitHub repository；如使用 Codex Cloud，建立包含该 repo 的环境，配置 Python 依赖、网络权限和 secrets。
- 让 Codex 先做离线工程实现与测试，查看代码 diff / pull request，再明确授权一次很小规模的真实 API smoke test。
- 普通 ChatGPT 中的 GitHub 读取连接与 Codex 的可编辑环境不是同一回事；需要修改或推送代码时，使用有仓库写入能力的 Codex 工作流。

参考：[Codex Cloud](https://learn.chatgpt.com/docs/cloud)、[Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments)。

### 路线 B：Claude Code（本地仓库；可选 GitHub Actions）

- 在电脑上安装 Claude Code，进入本地克隆的 GitHub 仓库，登录可使用 Claude Code 的账户。
- 将三份文件放入 repo；让 Claude Code 读取文件并编写 Python 程序、运行测试、生成提交或 pull request。
- 需要时可配置 Claude Code 的 GitHub Actions 集成，但不是第一阶段的必需项；先在本地完成和审核开发更简单。
- **Claude Code 自己使用的认证/订阅，不等于项目用于造题或测试的 OpenAI API key。** 即使用 Claude Code 编码，Python 仍可调用 OpenAI API，前提是相应项目 key 和运行环境已经配置好。

参考：[Claude Code Quickstart](https://code.claude.com/docs/en/quickstart)、[Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions)。

---

## 9. 验收标准：怎样判断编程助手的代码是否真正完成？

**离线阶段必须能演示**：

- 能正确加载 30 条 JSONL 知识；保持 K11、K23、K28 的约定内容不变。
- 任取一条已经提供的模拟 bundle 和 backbone，能确定性输出四个故事条件，并能检测“不允许的改写”。
- Q0 导出**每条 fact 仅一条**且没有故事；故事题是 `(family, condition, Q1/Q2/Q3)` 一行一请求。
- `gold_answers.jsonl` 不会出现在任何给被测模型的请求 payload 中。
- 若 bundle 行动 gold 相同、占位符缺失、schema 错误、对照条件差异超出约定，程序会明确拒绝并记录原因。
- `--dry-run` 和测试不需要真实 API key，不产生收费调用。
- 运行代码与非敏感配置可以放 GitHub，密钥不进入仓库；README 能让新研究助理复现。

**小规模真实调用阶段必须能演示**：

- 正确调用当前可用模型的 API，保存结构化输出及原始响应；对响应不完整、拒绝、429 和网络错误有清晰处理。
- 每个 candidate 都有可追踪的 `fact_id` / `family_id` / `item_id`，有 `validation_status` 和修改记录。
- 能运行一个 Q0 和至少一个 Q1/Q2/Q3 的 end-to-end 测试，且三个 story question 互不共享对话。
- 能输出一份人类可阅读的审查报告和调用量报告；不因为代码运行成功就宣称 scientific validity 已经获得验证。

---

## 参考技术资料（供编程助手核查最新接口，不是论文文献）

- [OpenAI API Quickstart](https://developers.openai.com/api/docs/quickstart)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI Batch API](https://developers.openai.com/api/docs/guides/batch)
- [OpenAI API Keys / Service Accounts](https://developers.openai.com/api/docs/guides/api-keys)
- [Codex Cloud](https://learn.chatgpt.com/docs/cloud)
- [Codex Cloud Environments](https://learn.chatgpt.com/docs/environments/cloud-environments)
- [Claude Code Quickstart](https://code.claude.com/docs/en/quickstart)
- [Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions)

