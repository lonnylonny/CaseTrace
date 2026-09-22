# M2-02 — nDCG 实现与讲解

创建：2026-09-20。状态：已随 M2 总审验收 accepted（2026-09-22）；原规格、基线与回报保留供追溯。

本包保留原规格和实际回报。后续执行范围及交接时机由 [M2 连续完成包](m2-completion.md) 和 AGENTS 的 M2 专用流程接续；下文旧的单函数停止/回交要求不再阻止继续。

## Codex Plan

**目标：** 在现有纯函数模块中加入二值 `ndcg_at_k`，用手算样例验证并讲解。用户已理解 Recall、Precision、RR；[M2-01](m2-01-rr-teaching.md) 已验收。

**范围与来源：** 先读 [AGENTS.md](../../../AGENTS.md)、[Cline 规则](../../../.clinerules/rules.md)、[Current Plan](../current-plan.md) 第 4、6 节，再读 [metrics.py](../../../src/casetrace/evaluation/metrics.py) 和[指标测试](../../../tests/evaluation/test_metrics.py)。允许改动这两个 Python 文件及本包的 Cline Report；不改现有三指标行为、qrels、BM25、CLI 或总计划。runner、汇总及旧版哈希问题均不在本包范围。

**接口：**

```python
def ndcg_at_k(
    ranked_case_ids: list[str],
    relevant_case_ids: set[str],
    k: int,
) -> float | None:
    ...
```

三个输入沿用现有函数含义：有序排名、该 Query 在整个语料中的全部正例集合、截断 K。前置条件仍由将来的 runner 负责：排名 ID 有效且唯一，标注完整；未标注不能当作不相关。本包不新增通用输入校验层。

**所需行为：**

- 沿用 K 校验：非正整数（含 bool、小数）抛出 `ValueError`，先校验 K 再处理无正例。
- 每个相关 Case 的 gain 为 1，不相关为 0；排名从 1 起。位置贡献为 `gain / log2(rank + 1)`。
- `DCG@K`：只累加实际返回前 K 条的贡献，使用原排名位置，不能去掉不相关项后重新编号。
- `IDCG@K`：假设全部正例尽可能靠前，累加第 1 至 `min(k, len(relevant_case_ids))` 名的贡献。分母使用全部正例数，不使用本次命中数或返回数量。
- `nDCG@K = DCG@K / IDCG@K`。有正例但空返回或前 K 条无命中时返回 `0.0`；无正例返回 `None`，将来由 runner 单列并排除 nDCG 均值。
- 返回不足 K 时 DCG 只计实际条目，IDCG 仍按全部正例及 K 计算。改变相关 Case 之间的内部顺序不改变二值 nDCG；位置折扣不是给不同 Case 分配阅读优先级权重。
- M2 报告 K=1、3、4，K=4 为主。函数保持通用正整数 K、无文件读写、无输入修改。

**实现步骤：**

1. 核对基线，按现有 public function 测试边界做小步 red–green。先用一个手算用例暴露缺失函数，再实现最小行为，逐步补边界；测试直接调用 `ndcg_at_k`，不 mock 内部步骤。
2. 用标准库 `math.log2`，优先采用易读的循环与局部变量 `dcg`、`ideal_dcg`，保留名次和得分含义。无需新依赖、指标类、注册表或为本步重构原三函数。
3. 运行指标测试，必要时修复本步问题，记录实际命令及结果；讲解后在本包回报并停止。

**手算依据与测试要求：**

基础样例：`ranked=["C001", "C005", "C003", "C006"]`，`relevant={"C001", "C003"}`。这是教学输入，不是实际 BM25 排名。

- K=1：DCG=IDCG=1，结果 `1.0`。
- K=3 和 K=4：DCG=`1 + 1/log2(4)`=`1.5`；IDCG=`1 + 1/log2(3)`≈`1.630929754`；结果约 `0.9197207891481876`。
- 仅返回 `["C001"]`，正例仍为两个，K=4：DCG=1，IDCG 不变，结果约 `0.6131471927654584`。此例检查分母不随漏检或少返回而缩小。

使用 `pytest.approx` 比较预先手算的常数，不在测试中复制生产函数的求和算法。还需覆盖理想排序为 1、首个相关结果仅在 K 外为 0、空返回为 0、无正例为 None、非法 K，以及相关 Case 互换排名不改变得分。既有 39 个指标用例必须继续通过。

**命令与验收标准：** `uv run pytest -q tests/evaluation/test_metrics.py`。本步按项目适配只要求指标测试，不为继承的旧 qrels 哈希失败扩大到全套修复；如另跑检查，原样报告失败与范围。验收看接口和上述行为、独立手算预期、既有行为保持、基线增量限于授权文件、实际验证及教学记录。自测通过不等于 Codex 验收或正式检索质量结果。

**教学重点与停止点：** 按“做什么 → 为什么需要 → 怎样运行”讲清 nDCG 关注前 K 条相关结果的整体位置，依次解释位置折扣、DCG、理想分数 IDCG 和两者相除；只用上面的样例走一遍，不展开对数推导。将 `log2(rank + 1)` 视为位置折扣规则即可。说明它与只看首个命中的 RR 的差别，指出将来的 runner 分别调用各指标，目前仍不存在。讲解完这一函数就停下；如用户困惑，留在当前概念澄清。单独记录用户是否理解，不提前进入 runner 或新指标汇总。

**选择的 skills：** Cline 读取 [implement](../../../.agents/skills/implement/SKILL.md)、[tdd](../../../.agents/skills/tdd/SKILL.md)（及其中相关测试指导）、[teach](../../../.agents/skills/teach/SKILL.md)；按 AGENTS 项目适配执行。Codex 使用 to-spec / handoff 成包，回交后用 [code-review](../../../.agents/skills/code-review/SKILL.md) 分别验收 Spec / Standards。测试边界已在本包确定；不重复要求确认，不创建 HTML 教学工作区、不自动提交或启动 agents。

## Handoff Baseline

- 起始 HEAD：`1e691bca0e32f8edb9dc9ab05b6ce37793ab6b87`。
- 基线根目录：`/tmp/casetrace-m2-ndcg-px71dp48`，保留到验收。`preparation/` 是 Codex 本轮编辑文档前状态；**Cline 应与成包后的 `handoff/` 比较**，避免把验收 RR、更新指针和创建本包归因于 Cline。
- `handoff/files/` 保存相关文件原字节，包括此前 untracked 的指标实现、测试、两个任务包和 qrels；`handoff/manifest.json` 记录 SHA-256 及缺失目标；`handoff/head.txt`、`git-status.txt` 记录 HEAD 和全部 tracked / untracked 状态；`staged.patch`、`unstaged.patch` 保存相关 tracked 差异。完整既有修改路径以这些文件为准，不能把整个脏工作区当成本包交付。
- 本包创建前不存在；runner 始终不存在；交接时 `ndcg_at_k` 尚未实现。代码验收相对 `handoff/files/src/casetrace/evaluation/metrics.py` 和 `handoff/files/tests/evaluation/test_metrics.py`，包含工作树中未提交或新增内容。
- Cline 编辑前检查快照与当前文件，记录接手间变化；基线丢失则报告比较限制，交给 Codex 重建后再编辑，不重建伪造历史。规则冲突、跨模块问题或两次有证据的修复失败按 AGENTS 交回 Codex。
- 历史验证：三个已有指标最近实测为 `39 passed`，本次规划未重跑 pytest；旧 qrels 哈希失败仍为已有问题，详见 [核对记录](../../../data/evaluation/dev-v2/README.md)。两项都不是本包的新自测或验收结论。

## Cline Report

2026-09-20 由 Cline 填写。

- **交付状态：`ready for acceptance`。** 依据：`ndcg_at_k` 已按接口与所需行为实现，新增边界测试全部通过，既有 39 个指标用例未受影响，改动只落在授权文件；教学讲解已在本轮给出，用户是否理解仍待其本人反馈。
- **基线核对及接手间变化：**
  - HEAD 实测仍为 `1e691bca0e32f8edb9dc9ab05b6ce37793ab6b87`，与包内记录一致。
  - 编辑前 `sha256sum` 对比：`metrics.py` = `7e6b73bc…c505`、`test_metrics.py` = `3fb9d53c…a57a2`，与 `handoff/files/` 两份原字节**逐字节相同**（`diff` 无输出）。
  - `git status --porcelain=v1 -uall`（排序后）与 `handoff/git-status.txt` 完全一致，未新增、未重命名路径；接手期间无其他 Agent 或用户改动。
  - 逐项复核 `manifest.json` 中 AGENTS.md、rules.md、current-plan.md、practical-todo.md、m2-agent-handoff.md、m2-01 包、bm25.py、dev-v2 qrels、demo.json 的 SHA-256，全部 `OK`；本包自身哈希 `14f54bd5…0aad` 与清单一致。
  - **比较限制：** `handoff/unstaged.patch` 只覆盖 5 个与本包相关的 tracked 路径，其余 20 个既有 ` M` 路径（README、docs/data 若干、data 模块、tests 若干）没有内容快照，因此对它们只能给出"路径集合未变 + 编辑前 mtime 早于交接"的间接证据，不能做内容级比对。本轮 Cline 仅用编辑工具改动 `src/casetrace/evaluation/metrics.py`、`tests/evaluation/test_metrics.py` 和本包的 Cline Report。
- **实际改动：**
  - `src/casetrace/evaluation/metrics.py`：顶部新增 `import math`；文件末尾新增 `ndcg_at_k(ranked_case_ids, relevant_case_ids, k) -> float | None`，含中文 docstring。实现为两个显式循环——DCG 用 `enumerate(ranked_case_ids[:k], start=1)` 遍历实际返回条目并按 `1 / math.log2(rank + 1)` 累加；IDCG 用 `range(1, min(k, len(relevant_case_ids)) + 1)` 按同样的折扣累加理想位置；末尾返回 `dcg / ideal_dcg`。
  - `tests/evaluation/test_metrics.py`：导入改为多行形式并加入 `ndcg_at_k`；文件末尾新增 9 个测试函数（共 15 个用例），全部用手算常数 `pytest.approx` 断言，不复制生产函数的求和算法。
- **实现选择及与计划偏差：**
  - 沿用现有三函数的 `type(k) is not int or k < 1` 校验写法，放在无正例判断之前，满足"先校验 K 再处理无正例"；返回 `None` 语义与 `recall_at_k` / `reciprocal_rank_at_k` 一致。
  - 使用标准库 `math.log2` 与局部变量 `dcg` / `ideal_dcg`，未引入新依赖、未新增指标类或注册表、未改动既有三函数行为（39 个既有用例全绿即为证据）。
  - **偏差（过程性，不改变交付口径）：** 计划把 K=3 / K=4、少返回、空返回、命中外 K、理想排序、互换顺序等作为逐步 red–green 展开；实际只有"无正例"与"非法 K / 先校验 K"两处出现真正的失败，其余用例在核心求和实现后直接通过。手算常数与计划一致，另用独立 Python 片段复核：K=1 → `1.0`，K=3 与 K=4 → 精确值 `0.9197207891481876`，仅返回 `["C001"]` → `0.6131471927654584`。
  - 未改 qrels、BM25、CLI、runner、总计划或文档，未扩展指标汇总。
- **red–green、最终命令和观察结果（均为本次实际运行，`uv run pytest -q tests/evaluation/test_metrics.py`，输出重定向到 `/tmp/cline-*.txt`）：**
  1. 实现前基线：`39 passed`。
  2. red：加入 K=1 手算用例 → `ImportError: cannot import name 'ndcg_at_k'`。
  3. green：加入 DCG / IDCG 循环 → `40 passed`。
  4. green：补 K=3 / K=4 手算、理想排序=1、正例互换不变、少返回分母不缩小 → `45 passed`。
  5. red：补空返回 / 命中外 K 与无正例 → `2 failed, 47 passed`，失败为 `ZeroDivisionError: float division by zero`（`metrics.py:105` 的相除），空返回/命中外 K 两条直接通过。
  6. green：加 `if not relevant_case_ids: return None` → 预期转绿（下一步已实测覆盖）。
  7. red：补非法 K 与"先校验 K 再处理无正例" → `5 failed, 49 passed`，失败均为 `Failed: DID NOT RAISE ValueError`。
  8. green（最终）：加入 K 校验 → **`54 passed`**（39 既有 + 15 新增用例）。
- **未执行检查、原因及剩余问题：**
  - 未运行 `uv run pytest -q` 全套：按包内适配本步只要求指标测试；已知旧 qrels 哈希断言失败仍属既有问题，未在本轮验证或修复。
  - `pyproject.toml` 只配置了 pytest，没有 linter / 类型检查工具，因此没有可跑的静态检查步骤。
  - runner、逐 Query 汇总与正式评估数值仍不存在，属包外，未创建任何占位实现。
  - 剩余待办（交 Codex 与用户）：本包 Codex Spec / Standards 验收；旧版归档溯源问题；runner 与 K=1 / 3 / 4 的报告口径。
- **已教 / 待教内容：**
  - 已教（本轮交付）：`ndcg_at_k` 做什么 → 为什么需要（比只看首个命中的 RR、只看数量的 Recall / Precision 更关心前 K 条相关结果的位置）→ 怎样运行；依次讲清位置折扣 `1 / log2(rank + 1)`、DCG@K 用原排名位置、IDCG@K 用全部正例与 K、两者相除，并用样例 `ranked=["C001","C005","C003","C006"]`、`relevant={"C001","C003"}` 走完 K=1 / K=3 / K=4，说明二值 gain 下相关 Case 互换排名不影响得分、位置折扣不是阅读优先级权重。同时说明将来的 runner 分别调用各指标，目前尚不存在。
  - 待教（未开始）：逐 Query 指标汇总与均值口径（含无正例 Query 单列）、runner 与版本校验、M2 正式评估读数与错误分析。
  - 用户反馈：本轮尚未收到用户对 nDCG 的确认；讲解交付与用户理解分别报告，用户表示理解后才进入下一步。

## Codex Acceptance

已随 [M2 最终总审](m2-completion.md#2026-09-22-最终验收与交接) 验收，Verdict：**accepted（2026-09-22）**，不再单独等待审核。

- Spec / Standards：未发现 nDCG 缺陷；原基线差异与 54 个指标用例已纳入总审，验证及比较限制见 M2 完成包。
- 原教学回报保留，用户随后表示本步完成；代码验收不额外认定学习掌握程度。
- 后续计划以 Current Plan 为准，本包不再产生待办。
