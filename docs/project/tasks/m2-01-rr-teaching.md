# M2-01 — 接续 RR 讲解

创建：2026-09-20。状态：accepted；用户已明确表示理解，进入下一份 nDCG 任务包。

## Codex Plan

**目标与范围：** Cline 讲解已实现的 `reciprocal_rank_at_k`，衔接用户已理解的 Recall / Precision。本包是一次讲解交付；实现步骤、新接口、新测试均不适用。只允许在本文件的 Cline Report 回报交付，代码、测试、数据和总计划保持原样。

**权威来源与阅读顺序：** 先读 [AGENTS.md](../../../AGENTS.md)、[Cline 入口](../../../.clinerules/rules.md)，再核对 [Current Plan](../current-plan.md) 第 4、6 节，最后读 [metrics.py](../../../src/casetrace/evaluation/metrics.py) 和 [指标测试](../../../tests/evaluation/test_metrics.py)。总计划仍以 Current Plan 为准，本包不另列项目路线图。

**当前事实：** Recall / Precision 已实现且用户已表示理解；RR 已实现并自测，但具体代码尚未讲解。nDCG、MRR 汇总、runner、评估 CLI 和正式结果尚未完成。dev-v2 版本与 18 对标签已确认，无需重新索取确认。旧 qrels 归档问题留待 Codex 单独处理，细节按需读 [v2 核对记录](../../../data/evaluation/dev-v2/README.md)。

**接口与行为：**

```python
reciprocal_rank_at_k(
    ranked_case_ids: list[str],
    relevant_case_ids: set[str],
    k: int,
) -> float | None
```

现行行为以 Current Plan 第 4 节及函数为准：取前 K 条，按原排名找首个正例，返回倒数排名；有正例但未命中返回 `0.0`，无正例返回 `None`，非法 K 抛出 `ValueError`。M2 使用 K=4。runner 将来对有效 RR@4 等权平均得到 MRR@4，`None` 单列并排除该均值；汇总代码尚不存在。未标注处理是后续输入校验的职责。

**Cline 执行与教学步骤：**

1. 检查下节基线，只读相关代码。如有接手间修改，先在 Report 说明差异；只在变化影响本包目标或规则时交回 Codex。
2. 按“做什么 → 为什么需要 → 怎样运行”讲解：三个输入和输出、保留排名顺序、`enumerate(..., start=1)`、首个命中时 `return`、循环结束后的 `0.0`。可省略用户已熟悉的 K 校验细节。
3. 使用一个短例子：`["C001", "C005", "C002"]`、`{"C005"}`、`k=4`，结果 `0.5`。明确这是手算教学输入，不是实际 BM25 排名。再用一句话说明多条 Query 的 RR 平均才是 MRR。
4. 简要解释 `0.0` 与 `None` 的区别，指明文件位置和后续调用关系。完成后停止，引导用户消化或提问；根据反馈仅澄清本概念。
5. 在 Cline Report 写下实际讲解、例子、用户反馈及未讲内容，交回 Codex。用户表示“理解 / 继续”后，记录状态，由 Codex 验收并安排下一份 nDCG 小任务包。

**测试入口与命令：** 现有测试直接调用指标函数，不新增 test seam。本包为讲解，默认不运行命令、临时脚本或创建示例工程。仅当接手间代码变化造成正确性疑问时，按需运行 `uv run pytest -q tests/evaluation/test_metrics.py` 并记录实际结果；旧记录不写成本次自测结果。

**验收标准与停止点：**

- 讲解包含输入、输出、关键语法、手算 `0.5`、RR / MRR 调用关系及空返回 / 无正例区别；不把未实现的 runner 或汇总描述成已有功能。
- 本包文件之外无 Cline 修改；报告已教和待教内容、真实用户反馈，不能把“已讲解”自动记为“用户已理解”。
- 停在 RR 讲解及其澄清；nDCG、哈希修复、runner 和其他构建工作由后续任务包承接。

**选择的 skills（均服从 AGENTS 的项目适配）：** Codex 成包使用 [to-spec](../../../.agents/skills/to-spec/SKILL.md)、[handoff](../../../.agents/skills/handoff/SKILL.md)、[writing-for-agents](../../../.agents/skills/writing-for-agents/SKILL.md)；Cline 本包只读 [teach](../../../.agents/skills/teach/SKILL.md)，采用小概念和反馈原则；回交验收时 Codex 使用 [code-review](../../../.agents/skills/code-review/SKILL.md)。本包无需 implement / tdd、tracker、HTML 教学工作区或 subagents。

## Handoff Baseline

- 起始 HEAD：`1e691bca0e32f8edb9dc9ab05b6ce37793ab6b87`。
- 临时基线根目录：`/tmp/casetrace-m2-rr-handoff-f39n_t3w`，保留至验收结束。
- **Cline 接手比较基线：** 根目录下 `handoff/files/` 保存成包后的相关文件原字节，`handoff/manifest.json` 记录 SHA-256 和缺失目标，`handoff/git-status.txt` 保存交接时所有 staged / unstaged / untracked 路径；`handoff/staged.patch`、`handoff/unstaged.patch` 保存相关 tracked 文件相对 HEAD 的差异。审查 Cline 的增量以文件快照为准，不直接归因整个 `git diff HEAD`。
- **Codex 整理前快照：** `preparation/` 按相同方式记录生成本包前状态，当时有 25 个 tracked 修改、115 个 untracked 文件、0 个 staged 修改；完整路径见 `preparation/git-status.txt`。本次 Codex 仅新增本包并更新旧交接入口、Current Plan 和 practical-todo 的交接指针，不改变实现进度。
- 快照包含此前 untracked 的 `metrics.py`、指标测试、旧交接文件、v1/v2 qrels 和迁移测试，也包含 AGENTS、Cline 规则及进度文档。整理前本任务文件不存在；runner 整理前及交接时均不存在。详见两个 manifest，不把此前文件算成 Cline 新增。
- Cline 写 Report 前核对 HEAD、状态和相关快照；记录接手间变化。临时目录若丢失，报告比较限制，由 Codex 重新建立基线后再进行需写入的工作；不得补造历史基线或 commit。

**此前观察（Codex 历史记录，不是 Cline 自测或本包验收）：** 指标测试最近运行 `39 passed`；较早排除指标文件的其余测试为 `168 passed、169 subtests passed、1 failed`，唯一失败为旧 qrels 哈希断言。两个结果来自不同运行；本次重做交接未重跑测试。正式 evaluator 未运行，尚无正式质量结果。

## Cline Report

Cline 第一次填写（2026-09-20，讲解已交付，等待用户反馈）。本节只回报，不改变代码、测试、数据与总计划。

- 交付状态：**讲解已交付，等待用户反馈**。按本包第 5 步，用户回复“理解 / 继续”后才补记状态；因此本轮**不**标 `ready for acceptance`，也非 `blocked`（无阻塞）。Codex 现在不应把本轮视为可验收的完成态。
- 接手间变化与基线核对：无接手间变化。核对了交接快照 `/tmp/casetrace-m2-rr-handoff-f39n_t3w`（快照仍在，可继续比较）。
  - `handoff/head.txt` 与当前 `git rev-parse HEAD` 均为 `1e691bca0e32f8edb9dc9ab05b6ce37793ab6b87`。
  - 用 `handoff/manifest.json` 逐项重算 SHA-256 对照当前文件：12 个 `exists: true` 条目**全部 MATCH**，包括 `AGENTS.md`、`.clinerules/rules.md`、`docs/project/current-plan.md`、`docs/project/practical-todo.md`、`src/casetrace/evaluation/metrics.py`、`tests/evaluation/test_metrics.py`、`data/evaluation/dev-v2/qrels.json`、`tests/test_benchmark_migration.py` 及本任务包自身；`src/casetrace/evaluation/runner.py` 仍为 `ABSENT-BOTH`（当前确实不存在）。
  - 工作区状态对照：用 `git status --porcelain=v1 --untracked-files=all` 与 `handoff/git-status.txt` 排序后比较，结果 `NO DIFFERENCE`；当前为 25 个 tracked 修改、116 个 untracked、0 个 staged，与交接时的 115 + 本任务包一致。首次比较出现的差异只是我用了默认 `--untracked-files=normal`（折叠目录），改用相同参数后无差异。
- 实际改动：仅本文件的 Cline Report 一节。`src/casetrace/evaluation/metrics.py`、`tests/evaluation/test_metrics.py`、qrels、Current Plan 均未改动（哈希 MATCH 可证）。
- 执行命令与观察结果：只运行了只读核对命令（`git rev-parse HEAD`、`git status --porcelain=v1 [--untracked-files=all]`、`sha256sum` 与一段只读 Python 哈希对照脚本、`find src/casetrace/evaluation tests/evaluation -type f`、`ls`/`cat` 快照目录），以及一次内联 `uv run python` 计算核对（用于澄清三个指标的关系，见下条）。实际观察到：HEAD 匹配、12 项哈希 MATCH、状态与快照无差异、`evaluation/` 下只有 `__init__.py` 与 `metrics.py`（另有 `__pycache__`），`tests/evaluation/` 下只有 `test_metrics.py`。内联计算实测：`relevant={"C005"}`、`k=4` 时，排名 `["C001","C005","C002"]` → recall 1.0 / precision 0.25 / RR 0.5；`["C001","C002","C005"]` → 1.0 / 0.25 / 0.333…；`["C001","C002","C003","C004","C005"]` → 0.0 / 0.0 / 0.0；`relevant=set()` 时 → `None` / 0.0 / `None`。**未运行 pytest**，故本包无新的测试证据，也不引用历史的 `39 passed` 作为本次自测结果；上述内联计算只核对已有函数返回值，不改动任何文件。
- 未执行检查及原因：未运行 `uv run pytest -q tests/evaluation/test_metrics.py`（本包为讲解包，且接手间代码哈希与快照一致，无正确性疑问）；未运行 evaluator / CLI（尚不存在）；未改动或重跑 qrels 相关测试（非本包范围，旧版归档问题仍为已有问题）。
- 实际讲解与手算例子：按“做什么 → 为什么需要 → 怎样运行”讲解 `reciprocal_rank_at_k`，覆盖三个输入与输出类型、`ranked_case_ids[:k]` 切片保留原排名顺序（因此不能用 `set()`）、`enumerate(..., start=1)` 的名次含义、首个命中即 `return 1 / rank`、循环结束后的 `return 0.0`；K 校验沿用既有口径，仅一句带过。手算例子使用任务包指定输入 `ranked=["C001","C005","C002"]`、`relevant={"C005"}`、`k=4` → 第 1 名未命中、第 2 名命中 → **0.5**，并明确标注这是手算教学输入、不是实际 BM25 排名；补充对照例 `["C001","C002","C003","C004","C005"]` 配 `k=4` → 前 4 条未命中 → `0.0`，说明第 5 名不计入。另用一句话说明“多条 Query 的 RR 等权平均才是 MRR”，并写明汇总（runner）尚未实现。`0.0` 与 `None` 的区别按约定讲解：`0.0` = 有正例但前 K 条未命中（含空返回），参与平均；`None` = 该 Query 本身无正例、指标无定义，后续由 runner 单列并排除出 MRR 均值。最后指明文件位置（`src/casetrace/evaluation/metrics.py`，与 recall / precision 同属纯函数模块，不读文件、不调用 BM25）、当前唯一调用方（`tests/evaluation/test_metrics.py`）与将来调用链（runner 取排名 → 逐 Query 调用 → 对有效 RR 求均值 → CLI 保存），并声明 runner / CLI 尚不存在。
- 用户反馈、已教 / 待教：**用户已给出第一次反馈：追问三个指标的关系，并问“是否都是 recall@k”**，说明该处存在概念混同（把 RR 也归入 Recall 族）。已就地进行澄清：只有 `recall_at_k` 属于 Recall；三者只共享“单条 Query、只看前 K 条、相同三件套输入”的形式，追问的问题与分母口径不同；并用内联计算结果说明“命中相同、名次不同时 recall / precision 不变而 RR 改变”，以及 MRR 的 R 是 Reciprocal（倒数）而非 Recall。澄清只针对本概念，未扩展到 nDCG。**用户尚未表示“理解 / 继续”**，因此本轮仍不标 `ready for acceptance`；不得把“已讲解”或“已澄清”记为“用户已理解”。已讲：`reciprocal_rank_at_k` 的输入输出、有序遍历与首个命中、手算 0.5、`0.0` / `None` 区别、RR 与 MRR 的关系、三指标的分工与分母差异。待教：nDCG 及其实现（属后续 Codex 小任务包）、MRR 汇总与 runner、正式评估与错误分析。
- 偏离范围、剩余问题及阻塞：无范围偏离（未扩展指标实现、未触碰 nDCG / runner / 哈希问题），无本包阻塞。已有问题单列、不归因本任务：旧 `dev-v1/qrels.json` 归档哈希与 `previous_qrels.sha256` 不符，`tests/test_benchmark_migration.py` 旧哈希断言失败，仍待 Codex 处理。

## Codex Acceptance

验收日期：2026-09-20。Cline Report 保留其当时“等待用户反馈”的历史记录；用户在 Codex 会话中最新明确回复“已理解推进到下一步”，由 Codex 在此补记，无需让 Cline 重复收集确认。

- Spec findings：无影响验收的问题。回报覆盖三个输入、返回值、有序遍历、`enumerate`、首次命中返回、手算 0.5、`0.0` / `None` 和 RR / MRR 区别，并记录了三指标混同的澄清；未实现后续指标或汇总。
- Standards findings：无影响验收的问题。对照交接基线，仅任务包的 Cline Report 有变化，包内其余部分当时未变；已记录快照文件中的代码、测试、规则、进度与数据均匹配，HEAD 和完整 Git 状态匹配。Cline 将内联计算与未执行的 pytest 分开报告，未把历史测试当成新证据。
- 验证证据与比较限制：Codex 实际读取回报、逐项核对 `/tmp/casetrace-m2-rr-handoff-f39n_t3w/handoff/manifest.json` 的哈希并比较包内章节，未重跑测试。讲解内容以 Cline 回报及用户本轮反馈为据，未独立重放 Cline 会话；未快照的其他脏文件不作内容级归因。
- Verdict：**accepted**，范围仅为本包 RR 讲解交付；不表示 M2 或正式检索评估已完成。
- 用户学习状态与下一交付：用户已确认理解 RR 及相关澄清。下一步交给 Cline 的任务为 [M2-02 — nDCG 实现与讲解](m2-02-ndcg.md)，由 Codex 规划，Cline 实现、自测和讲解后回报。
