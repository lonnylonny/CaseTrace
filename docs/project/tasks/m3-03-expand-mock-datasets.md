# M3-03 — Expand Mock Datasets

状态：**当前活动包，实施中，尚未验收**。新语料、loader 版本支持和 45 对 qrels 草稿已由 Cline 交付并自测；当前停在用户确认 **27 对新增标签**（含 Q005–C004 裁定）。随后完成用户回归测试与新版正式评估。

## Codex Plan

**目标：** 从 [M2 错误分析](../../../results/dev-v2-bm25-error-analysis.md)与 [M3-02 对照](../../../results/dev-v2-bm25-vs-embedding-m3-02.md)发现的缺口扩充 Development，发布完整、用户确认的新 benchmark，并重跑 BM25 / Embedding。范围及相关性沿用 [Current Plan](../current-plan.md)；协作按 [M3 工作流](../../../AGENTS.md#m3-delivery-workflow--user-confirmed-override)。

**已确认规模与路径（2026-09-25）：** 新增 3 Case + 2 Query，合计 9 × 5 = 45 对；旧 18 对沿用确认，新增 27 = 旧 Query × 新 Case（9）+ 新 Query × 旧 Case（12）+ 新 Query × 新 Case（6）。规划上限原为新增 4 Case / 2 Query，当前采用用户确认的较小方案，不自动扩充。

| 产物 | 路径与当前状态 |
|---|---|
| 独立语料 | [data/dev/demo-v3.json](../../../data/dev/demo-v3.json)，已生成；旧 6 Case / 3 Query 保留 |
| qrels | [data/evaluation/dev-v3/qrels.json](../../../data/evaluation/dev-v3/qrels.json)，45 对 draft，新增 27 对未确认 |
| 版本说明与确认记录 | 尚待完成；放在新 benchmark 目录，与 qrels 的来源哈希、确认范围和家族记录对应 |
| 正式结果 | `results/dev-v3-bm25-m3-03.json`、`results/dev-v3-embedding-m3-03.json`，尚未运行 |

**活动约束：**

- 生成与审阅依据：[结构](../../data/CaseTrace_Data_Structure_V2_No_Scenario.md)、[CR](../../data/CaseTrace_Case_Constraint_Rules_Frozen.md)、[GR](../../data/CaseTrace_Case_Generation_Rules_V1.md)。按 GR-10 先定事实与候选来源，再组织文本；复用确定性校验，另查影响可信度的语义，不扩建生成平台或 Validator。
- dev-v2 原件、标签与既有正式结果不覆盖；不修改既有 G001 / memberships。CLI 默认仍为 dev-v2，新版显式使用 `--qrels data/evaluation/dev-v3/qrels.json`。
- 新版绑定独立语料哈希；记录来源、改写父项及近重复家族，供 M6 隔离。扩充用于 Development，不按某个模型的输赢选样本或改标签。
- 完整配对涵盖旧 Query × 新 Case。旧判断未变则沿用确认；新增或变化判断由用户最终确认。Q005–C004 当前暂填 0 且标为 `needs_user_ruling`，**不是已确认负例**。未确认或 Ambiguous 保持 draft，正式 evaluator 继续拒绝。
- 必须明确新增历史内容在 Query 时点前已结案且完整可用的快照依据；detection_time 较早本身不证明结案可用。Query 不含后来得知的当前原因。
- loader 支持 v2 / v3，保留来源哈希、ID 唯一、完整配对、确认状态与 Development 守卫；未知版本明确拒绝，不用移除守卫实现兼容。

**覆盖清单（用户已确认）：**

| 缺口 | 样例与目的 |
|---|---|
| 同义表达 / 技术类比 | C007 相对 C001 改写、跨产品族与路线；C008 对 C005 作跨路线类比；相关性由实际已知事实判断，不仅依赖 failure_mode_id |
| 背景关联 | Q004 给出 DEV_PL_009，检查与 C008 的明确批号联系；不从历史记录间的关系推导当前事实 |
| 易混淆 / 否定表达 | C009 的探针压形与运输碰伤对照、Q005 的排除碰伤语境；满足充分相关条件的 Case 仍须 Relevant |

**用户亲手代码（未完成）：** 在 `tests/evaluation/test_benchmark.py` 写 loader 缺失配对回归测试，删除“旧 Query × 新 Case”一对，验证失败发生在配对检查而非哈希或确认状态。已提供 `load_benchmark(qrels_path, *, base_dir=None)`、`benchmark_inputs` fixture 与 `_dataset / _qrels / _save_qrels / _load` 帮手；Cline 仅给接口与提示，不写测试体。按当前教学安排在 SD4 确认后实施 SD3b；Ground Truth 审阅不替代编码。

**检查与验收：**

- 正常 v2 / v3 可加载；未知版本、draft、缺失/重复配对与哈希不符拒绝。运行 `uv run pytest -q tests/evaluation/test_benchmark.py tests/evaluation/test_runner.py tests/test_cli_evaluate.py` 及新增数据检查；CR / GR 语义未覆盖部分如实记录，不修复旧 dev-v1 归档失败。
- 标签确认后运行两条 `casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method <bm25|embedding> --output <对应新版结果>`，保存版本说明、实际命令、结果与比较边界。不得跨新旧 benchmark 宣称算法提升。
- 新基准可追溯、用户确认及用户测试可查、两方法同版正式运行与教学完成后，回报 ready for acceptance；Codex 审阅前不视为 accepted，不进入 M3-04。
- Skills：按需用 [implement](../../../.agents/skills/implement/SKILL.md)、[tdd](../../../.agents/skills/tdd/SKILL.md)、[teach](../../../.agents/skills/teach/SKILL.md)，验收用 [code-review](../../../.agents/skills/code-review/SKILL.md)，均服从 AGENTS 项目适配。

## Handoff Baseline

- **原实施起点保留：** HEAD `b8aaea4151b74d4b2bf80255a5cc22b5105a7205`，基线 `/tmp/casetrace-m3-03-codex-WRKTMs`；`head.txt`、`git-status.txt`、staged/unstaged patch、`files/`、`manifest.sha256` 与 `absent-targets.txt` 保存完整起点。激活时 M3-01 / M3-02 已 accepted 但未提交，不能仅按 HEAD 归因。
- 起点包含用户协作规则、已验收 M3-01 / M3-02 的代码/依赖/测试/结果及规划。这些不归于 M3-03；dev-v2 与两个方法的 M3-02 正式结果是需保留的输入。
- Cline 接手时记录 HEAD/状态一致、61 个快照全部匹配。编辑前补充快照根为 `/tmp/casetrace-m3-03-cline-20260925-0100/`：`before/` 为文件副本，manifest/head/absent-targets 位于根目录；事实与来源在 `facts/sd1-candidates.md`，生成/检查脚本也在 `facts/`。这些尚未验收的材料继续保留。
- **本次文档整理起点：** HEAD `a1437fde45df29c19181225b407b54d8316f8bd2`，工作树干净，M3-03 当前实现已进入该提交。文档编辑前快照 `/tmp/casetrace-doc-prune-22n4yyy3`；本次只精简文档，不替换原实施基线，不将后续 Git 提交或文档改动归于 Cline 实现。最终验收仍比较原基线与全部实际改动。

## Cline Report

以下是已有交付回报的摘要；本次文档整理仅核对实际文件与草稿状态，未重新执行软件测试或 AI 评估。

| 子交付 | 所有权与产物 | 当前状态与停点 |
|---|---|---|
| SD1 事实与来源 | Cline；主数据候选、事实表、来源/家族 | 已交付，详细设计的用户反馈未完整记录 |
| SD2 生成与校验 | Cline 生成新语料；用户审阅语义 | 已自测，教学反馈待记录 |
| SD3 loader + 用户测试 | Cline 完成版本支持；用户写缺配对测试 | Cline 部分已自测；SD3b 未完成，安排在 SD4 确认后 |
| SD4 qrels 与确认 | Cline 起草 45 对；用户裁定并确认新增 27 对 | 草稿已完成，**当前停点** |
| SD5 同版两方法运行 | Cline 运行与记录；用户核对读数边界 | 未开始，依赖 Ground Truth 确认 |

**已有自测证据：** 新语料两次生成字节一致，dev-v2 原件未变；relations/generation/source 检查与新版 demo 成功。草稿 loader 与 CLI 拒绝，CLI exit 2 且不落盘；临时确认副本可加载 45 对，不构成人工确认。定向测试 **67 passed**；全套 **320 passed、169 subtests passed、1 failed**，唯一失败为既有 dev-v1 归档哈希。尚未跑正式 dev-v3 指标、用户测试与 Codex 独立验收。

**未结事项：** Q005–C004（颈部断裂 vs 界面脱开）及全部新增标签确认阻塞正式评估；类似产品的 Product Family 判断仍需人工审阅，Validator 未自动覆盖。版本说明、可用时间快照依据和本批语义审阅结论须在回交前补齐。旧 dev-v1 哈希失败非阻塞，处理依据见 Current Plan。

**教学：** 已讲 SD1 事实先于文本；SD2 的配对数增长、跨版本不可直接比较与人工判断边界已讲但反馈待记录；SD3b 与正式结果讲解待完成。学习确认不由文档整理补记。

**下一步：** 向用户确认 27 对及疑难配对；按实际裁定更新对应标签/理由并记录确认日期、范围，未变判断保持原样；随后用户完成 SD3b，Cline 完成 SD5 与回报。不能仅改 `review_status` 就把待裁定标签变成 Ground Truth。

## Codex Acceptance

Spec / Standards 均未审阅，尚无独立验证或用户代码检查结论。**Verdict：待验收。** 文档整理不改变验收状态；仅 accepted 后激活 M3-04 并建立其实施基线。
