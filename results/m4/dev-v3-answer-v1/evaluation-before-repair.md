历史报告归档：下文原始零缺陷结论已被 2026-10-03 Codex 复核否定，不代表当前验收。v1 缺少完整消息/运行源码身份，不能用修复后的源码补造历史证据。当前报告见 results/dev-v3-m4-answer-evaluation.md。

# dev-v3 M4 回答质量评估（Development）

记录日期：2026-10-02。范围：M4-04 SD1–SD3。本文是 M4 回答质量的可复查报告主体；实际运行数据保存在 [results/m4/dev-v3-answer-v1/](m4/dev-v3-answer-v1/)，本文不覆盖 M3 产物，也不产生新的正式 Ground Truth。

评估对象是 **完整链路**（当前已知信息 → R3 检索 → 历史证据上下文 → DeepSeek 生成 → 引用守卫 → 历史参考回答）在合门五条 dev-v3 Query 上的真实输出，用于区分**检索问题**与**生成问题**，并为 M5 交接接口。五条 Query、9 条语料、qrels 与指标口径都属 **Development**，不构成泛化结论，也不使用 Locked Test。

## 1 运行身份与配置

| 项目 | 值 |
|---|---|
| 数据 | `data/dev/demo-v3.json`，`dataset_sha256 = 0a29041a…8f0b` |
| 主数据 | `data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx`，`reference_sha256 = f5001bdd…1c85` |
| qrels | `data/evaluation/dev-v3/qrels.json`，`dev-qrels-v3` / revision 2（`human_confirmed`，2026-09-26） |
| 快照 | `dev-v3-2026-09-15`（模拟约定，只支持记录在案的单一快照） |
| 检索 | R3 `bm25_drop_negation_labels`（BM25 + Query 过滤），`top_k=4` |
| 模型 | `deepseek-flash`，非思考模式 + JSON Output，`temperature=0`，`max_tokens=2048` |
| 提示词 | `grounded_answer_v1`（`src/casetrace/answer/prompts/grounded_answer_v1.md`） |
| 运行 | `uv run python tmp/m4_04_run_all.py`（复用 `casetrace answer` 同款应用函数） |
| 产物 | `results/m4/dev-v3-answer-v1/q00X.json`（运行记录）+ `q00X.cli.txt`（文本） |

凭据只从本机环境读取，**未进入任何产物**。

## 2 五条真实回答汇总

| Query | 状态 | 耗时 | tokens | 引用检查 | 引用问题 | 采用候选 | 跳过候选 |
|---|---|---|---|---|---|---|---|
| Q001 | ok | 6.42s | 4409 | 28 | 0 | C001 C003 C004 C007 | — |
| Q002 | ok（守卫修复后重跑） | 4.50s | 3812 | 14 | 0 | C005 C008 | C002 C006 |
| Q003 | ok | 4.50s | 3779 | 9 | 0 | C006 | C009 C005 C008 |
| Q004 | ok | 5.38s | 3961 | 14 | 0 | C008 C005 | C002 C003 |
| Q005 | ok | 5.75s | 4182 | 19 | 0 | C007 C001 C003 | C004 |

合计 5 条 / 20143 tokens / 引用检查 84 条。耗时是单次本机读数，不支持效率结论。

「采用」= `case_answers`（模型给出相关理由），「跳过」= `skipped_candidates`（模型明确证据不足）。二者与检索排名分开记录：排名是候选，采用/跳过是模型的判断，都不等于已确认相关。

## 3 评估侧检索命中核对（qrels 仅在评估侧，不进生成上下文）

| Query | R3 候选（前 4） | 命中正例 | 遗漏 |
|---|---|---|---|
| Q001 | C001 C003 C004 C007 | 4/5 | C002（第 5 名） |
| Q002 | C005 C008 C002 C006 | 2/2 | — |
| Q003 | C006 C009 C005 C008 | 2/2 | — |
| Q004 | C008 C005 C002 C003 | 2/2 | — |
| Q005 | C007 C001 C004 C003 | 4/4 | — |

Recall@4 = (0.8 + 1 + 1 + 1 + 1) / 5 = **0.96**，与 M3-07 选型一致。唯一检索遗漏是 **Q001×C002**（同产品同批次，已确认 Relevant，落在第 5 名被 `top_k=4` 截断）。M4 不调参，此项记为**检索遗漏**而非生成问题。

复现：`uv run python tmp/m4_04_run_all.py --check-only`

## 4 逐条语义审阅

审阅方法：逐条记录 claim、引用、原文依据与 supported / unsupported / uncertain；**可定位性**（守卫已查）与**语义支持**（人工核对）分开判断，不把字符串命中当语义正确。原文取自 `data/dev/demo-v3.json`，可用 `uv run python tmp/m4_04_dump_sources.py` 复现。

### 4.1 历史原因与检查结果：12/12 supported

12 条 `historical_root_cause` 与 12 条 `historical_evidences[].result` 与语料原文**逐字一致**，无改写、无跨 Case、无凭空补充：

| Query | Case | 历史原因 | 历史检查 |
|---|---|---|---|
| Q001 | C001 | ✓ | E001 ✓ |
| Q001 | C003 | ✓ | E003 ✓ |
| Q001 | C004 | ✓ | E004 ✓（"未观察到 pad 界面剥离或污染"保留） |
| Q001 | C007 | ✓ | E007 ✓ |
| Q002 | C005 | ✓ | E005 ✓ |
| Q002 | C008 | ✓ | E008 ✓ |
| Q003 | C006 | ✓ | E006 ✓ |
| Q004 | C008 | ✓ | E008 ✓ |
| Q004 | C005 | ✓ | E005 ✓ |
| Q005 | C007 | ✓ | E007 ✓ |
| Q005 | C001 | ✓ | E001 ✓ |
| Q005 | C003 | ✓ | E003 ✓ |

### 4.2 相关理由：11/12 supported，1 weak

| Query | Case | 相关理由要点 | 审阅 |
|---|---|---|---|
| Q001 | C001 | 同产品 PROD_001 + 同批 DEV_PL_001 + 同异常 | supported |
| Q001 | C003 | 同异常（焊点剥离、焊线从 pad 脱落） | supported |
| Q001 | C004 | "同工序 P004、同异常类型 00010，同工序同异常类型的对照案例" | **weak**：未指出与当前 Query 的相同依据；共享 `failure_mode_id` 不自动等于同异常（Current Plan §4），qrels 的实际依据是类似产品 PF_001，模型未抓到 |
| Q001 | C007 | 同异常（键合金球自焊盘分离，键合界面） | supported |
| Q002 | C005 | 同异常（声学扫描塑封空洞 molding void） | supported |
| Q002 | C008 | 同异常（声学扫描塑封空洞） | supported |
| Q003 | C006 | 同异常 + 同位置特征（托盘边缘碰伤） | supported |
| Q004 | C008 | 同产品 PROD_009 + 同批 DEV_PL_009 + 同异常 | supported |
| Q004 | C005 | 同异常（塑封空洞）+ 同工序 P007 | supported |
| Q005 | C007 | 同异常（焊线自焊盘脱开、键合界面） | supported |
| Q005 | C001 | 同异常（die pad 界面剥离、wire bond lift） | supported |
| Q005 | C003 | 同异常（焊点剥离、第一焊点界面） | supported |

跳过候选的理由（Q002×C002/C006、Q003×C009/C005/C008、Q004×C002/C003、Q005×C004）逐条核对异常表现、异常类型与工序，均有原文支持；无"为证据不足的候选硬编理由"。

**`query_facts` 选取（用户 2026-10-02 指出）**：Q005 等条在 `query_facts` 里列入了"原因尚未确认"。它不是支持相关理由的事实，属模型对**非支持性背景**的误归纳。**检索层不受影响**——R3 的 H1 规则已把含"未"的小句整句排除计分（`query_filter.strip_negation_clauses`）；把完整 Query（含否定/背景）保留给**生成器**是 M4-01 的既定设计，因此问题在生成层（`query_facts` 应只放支持该理由的事实），不在检索策略。归因：生成/提示词契约。

### 4.3 生成判断与 qrels 的相关性差异（登记，不改 qrels）

| Query | Case | qrels（用户确认） | 模型判断 | 归因 |
|---|---|---|---|---|
| Q001 | C002 | Relevant（同产品同批次） | 未进候选（第 5 名） | **检索遗漏**（`top_k=4` 截断），非生成问题 |
| Q003 | C005 | Relevant（类似产品 PF_003） | 跳过（异常不同） | **上下文装配缺漏**：当前 Query 只给产品 ID，未把当前产品的产品族补进上下文，模型无法判断「类似产品」；模型以「同异常」为主要判据 |
| Q005 | C004 | Relevant（弱相关，二值口径） | 跳过（失效位置不一致） | **生成判断更严格**：模型用「同异常（同失效位置）」标准，比用户确认的弱相关更保守 |

这三项是评估观察，m4 不据此调检索或 qrels；如需变更相关性口径仍由用户确认。

### 4.4 边界核对：全部通过（5/5）

- **历史/当前边界**：12 条历史原因都以"该历史 Case 的记录"表述（原文"结案确认：…"），没有写成当前 Incident 的原因、结论或建议。
- **否定与不确定保留**：Query 的"原因尚未确认"、C004/E004 的"未观察到"、C009/E009 的"未发现碰伤、缺球或掉球痕迹"均按原文保留。
- **当前 Root Cause 断言**：五条真实回答均无。
- **不足说明**：`current_gaps` / `insufficiency` 都以"当前缺少哪一项信息、影响什么判断"具体列出，未用空话带过。

## 5 发现并修复的问题：引用守卫与上下文不一致

首次运行五条时，**Q002 连续两次被判 `citation_failed`**，暴露引用守卫（M4-03）与证据上下文（M4-01）的字段约定不一致。两次失败产物都保留，未删除：

| 次 | 状态 | 失败引用 | 根因 |
|---|---|---|---|
| 1 | citation_failed | `case_answers[0].sources[4]` = `C005:background` | 守卫只认 Case 字段 / `detail:` / `checkpoint:` / 来源字段，漏了上下文随每条 Case 提供的 `background` / `processes` |
| 2 | citation_failed | `C005:source.failure_mode_id`、`C008:source.failure_mode_id` | 守卫只认扁平写法 `failure_mode_id`，而模型按上下文 JSON 结构写了 `source.<字段>` |

保留产物：`q002.citation-failed.json`（第 1 次）、`q002.citation-failed-2.json`（第 2 次），各带 `.cli.txt`。

**修复（`src/casetrace/answer/validation.py`）**：让守卫的可定位字段集与上下文 JSON 结构对齐——

- 新增 `LIST_FIELDS = ("background", "processes")`：随上下文提供的列表字段可定位（非空即通过）；
- 新增 `CONTAINER_PREFIXES = ("case.", "source.")`：`case.<字段>` / `source.<字段>` 等价于扁平写法。

这是守卫字段集与上下文结构的**一致化**，不改变"只判可定位、不判语义支持"的边界。新增测试 `test_background_field_is_locatable`、`test_processes_field_is_locatable`、`test_container_prefixed_field_is_locatable`。

**验证与重跑**：

- 两条旧失败回答在修复后的守卫下离线复核均通过：`ok: True`（第 1 次 15 条、第 2 次 18 条，0 问题），复现脚本 `uv run python tmp/m4_04_guard_recheck.py <记录>`。
- 重跑 Q002：`ok`，14 条引用检查，0 问题（`results/m4/dev-v3-answer-v1/q002.json`）。
- Q001/Q003/Q004/Q005 未受影响（修复前已通过；修复只增加接受度，不会让通过的引用变失败），保留原记录。

**范围说明**：这是对已验收的 M4-03 守卫代码的修复，属 M4-04「修复影响验收的问题」。根因是 M4-01 上下文 / M4-02 提示词契约 / M4-03 守卫对「可引用字段及写法」的约定不完整——提示词模板只举例了扁平字段与 `detail:` / `checkpoint:`，未规定 `source` 字段与 `background` / `processes` 的写法。是否进一步在提示词契约里显式声明写法，留待 Codex 验收判断。

## 6 验收门槛核对（真实分母）

| 门槛 | 结果 | 分母 |
|---|---|---|
| 伪造引用 / 无法定位的引用 | 0 | 84 条引用检查（5 条回答，守卫 0 问题） |
| 无依据关键事实（unsupported） | 0 | 12 条历史原因 + 12 条历史检查 + 12 条相关理由 |
| 当前 Root Cause 断言 | 0 | 5 条真实回答 |
| 输出项有内容或明确不足 | 是 | 每条 `insufficiency` / `current_gaps` 均有具体内容 |

相关理由 11/12 supported、1 weak（Q001×C004）；weak 不等于 unsupported（引用可定位、事实有原文），但理由依据不充分，如实保留。

**边界**：五条 Query、9 条语料是 Development 小样本，上述零缺陷**不构成泛化保证**，也不预设"回答准确率"。

## 7 边界与软件行为检查（隔离测试，不充当 Locked Test）

这些用例走离线替身与自造语料，不联网、不读写 qrels，属于软件/回答评估，不改写已确认 qrels。

| §7 第 3 条要求的边界 | 覆盖 | 用例 |
|---|---|---|
| 空命中（不调用模型） | ✓ | `test_empty_hits_skip_model_and_report_gap`、`test_cli_empty_hits_report_gap_without_model` |
| 伪造 / 跨 Case 引用 | ✓ | `test_answer_for_case_outside_context_is_rejected`、`test_source_borrowed_from_another_candidate_is_cross_case`、`test_checkpoint_of_another_case_is_rejected`、`test_case_in_corpus_but_not_retrieved_this_run_is_rejected` |
| 缺失 / 不确定证据（缺字段、缺内容、缺 ID） | ✓ | `test_missing_detail_or_checkpoint_is_rejected`、`test_unknown_field_name_is_rejected`、`test_case_field_without_content_is_not_locatable` |
| 源文本含指令只作数据 | ✓ | `test_source_text_instructions_are_sent_as_data_not_commands`、`test_default_rules_treat_source_text_instructions_as_data` |
| 调用 / 结构失败不伪装成功 | ✓ | `test_format_error_is_a_failure_state`、`test_model_call_error_is_a_failure_state`、`test_guard_reports_structure_only_not_semantic_support` |
| 可定位字段集与上下文一致（本次新增） | ✓ | `test_background_field_is_locatable`、`test_processes_field_is_locatable`、`test_container_prefixed_field_is_locatable` |

**未由确定性测试覆盖、靠 §4 人工审阅**的部分：相关依据不足、历史/当前混淆、语义支持——这类判断不可由字符串检查代替，本次由第 4 节逐条核对；`test_guard_reports_structure_only_not_semantic_support` 固定了"守卫不判语义"这一边界。

命令：`uv run pytest -q`（全套）、`uv run pytest -q tests/answer`（回答相关）。

## 8 用户分析（M4-04 用户实践，2026-10-02 完成）

用户亲自分析 **Q005**（3 条采用 + 1 条跳过）：

1. **支持来源**：用户核对 C007/C001/C003 三条采用 Case 的历史原因与检查结果，确认与语料原文一致，满意。
2. **历史/当前边界**：历史原因均表述为"该历史 Case 的记录"，未写成当前 Incident 的结论——用户认可。
3. **不足与潜在失败**：
   - 用户指出 `query_facts` 出现"原因尚未确认"这一**非支持性事实**，不应作为相关依据（归因见 §4.2 末，属生成层；检索层 R3 已排除该小句）。
   - 对 Q005×C004（qrels 弱相关、模型跳过）：用户判断**模型跳过是正常的**——C004 与 Query 在词面/语义上的重复度都低于 C007/C001/C003，其弱相关更偏"工程阶段可能有关"，检索排名也更靠后；模型优先给出更接近的三条，符合预期。
4. **输出建议（记为改进项，本包不实现）**：希望在回答 / CLI 输出中增加**历史改善措施**（`Case.corrective_action`）。该字段已在上下文内（属 Case 字段），但当前回答契约未包含；实现需给契约加字段、升提示词版本、重跑五条并重新审阅。用户决定不在 M4-04 内实现，记为改进项，交 Codex 决定纳入哪一步。

## 9 复现与运行说明

```bash
# 1) 配置凭据（不写入仓库）：cp .env.example .env 后填 DEEPSEEK_API_KEY，或 export
# 2) 五条真实调用（写入 results/m4/dev-v3-answer-v1/）：
uv run python tmp/m4_04_run_all.py
# 3) 只做检索命中核对，不调用模型：
uv run python tmp/m4_04_run_all.py --check-only
# 4) 单条重跑：
uv run python tmp/m4_04_run_all.py --query-id Q002
# 5) 复核失败回答在修复后守卫下的定位结果：
uv run python tmp/m4_04_guard_recheck.py results/m4/dev-v3-answer-v1/q002.citation-failed.json
# 6) 打印语料原文摘要（逐条核对用）：
uv run python tmp/m4_04_dump_sources.py
```

单条 CLI 入口：`uv run casetrace answer --query-id Q005 --json --output /tmp/q005.json`。

**可复现边界**：输入与配置可核对（数据/主数据哈希、Query、候选排名、上下文、模型身份、参数、提示词版本、token 用量都记在运行记录里）；**不承诺模型逐字复现**（同一输入重跑可能得到措辞不同的回答）。质量判断可复查：本节与第 4 节的 claim/引用/原文依据都可回到源文件。

M5 交接见 [docs/project/handoffs/m4-04-m5-handoff.md](../docs/project/handoffs/m4-04-m5-handoff.md)。

