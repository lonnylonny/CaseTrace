# M3-04 — Hybrid

创建：2026-09-22。状态：已建包，待 [M3-03](m3-03-expand-mock-datasets.md) 验收后激活；尚未实施。

## Codex Plan

**执行入口：** 先读 [Current Plan](../current-plan.md) 确认活动包，再按 [AGENTS 的 M3 工作流](../../../AGENTS.md#m3-delivery-workflow--user-confirmed-override) 执行。下列要求是本包边界，不是替 Cline 预排的子交付；由 Cline 在 Report 中安排最多 5 个子交付，每次只推进当前一步。

**目标与范围：** 在已确认的新 benchmark 上融合 BM25 与 Embedding，逐 Query 比较两个单方法和融合方法。

**任务来源与阅读：** [Current Plan](../current-plan.md) 第 4、5 节；[M3-03](m3-03-expand-mock-datasets.md) 已发布的数据版本、[M3-01](m3-01-evaluation-entry.md) 和 [M3-02](m3-02-embedding.md) 的已验收接口。

**输入 → 输出：** 同一 Query 的两路候选排名 → 去重后的融合排名、各路名次与融合配置、同版本三方法结果。

**必须实现的行为：**

- 首轮采用按排名的 RRF，不直接相加 BM25 与向量原始分数。RRF 常数、两路候选数与最终返回数在运行前固定并记录；常数与指标 K、候选数分别命名。
- 每一路同一 Case 只计一次，不在某路出现的 Case 不虚构该路名次；候选按 Case ID 合并，排序及同分规则确定。无候选时返回空；一路无候选时另一路仍可贡献。
- 结果可追溯到各路名次、融合得分及原 Case。指标仍由公共评估器计算；不接收 qrels 作为融合输入。
- 保存三方法的同版本结果，检查正例被推进或挤出前 K 的具体原因，观察精确 ID 与语义信号的取舍。候选范围变化须记录，不能归因为融合公式的单独效果。

**实现边界：** 小型融合逻辑、方法接入、必要报告字段及测试，不引入权重搜索平台。

**用户亲手部分（预留）：** 建议用户完成纯融合计分函数：输入两路 Case ID 排名和 RRF 常数，输出 Case ID → 融合分数；由 Cline 给参数契约、RRF 概念和必要提示，用户完成计分部分后再检查。Cline 负责周边检索接入，避免先在别处写出同一函数答案。

**测试边界与命令：** 独立手算小排名验证重叠、单路出现、空路、同分与无重复输出；验证 qrels 变化不改变候选/融合。运行本包检索测试及 `uv run pytest -q tests/evaluation tests/test_cli_evaluate.py tests/test_demo.py`，执行新 benchmark 的三方法对比，Report 记录真实命令。

**验收与教学停止点：** 融合可追溯、计分正确、同基准比较完成、用户函数经检查；允许无收益。讲清名次融合与分数相加的区别、候选数量如何影响最终结果；停在 Hybrid，不提前实现重排。

**使用 skills：** Cline 按需读取 [implement](../../../.agents/skills/implement/SKILL.md)、[teach](../../../.agents/skills/teach/SKILL.md)，纯逻辑与回归测试采用 [tdd](../../../.agents/skills/tdd/SKILL.md)；均按 AGENTS 项目适配。Codex 回交时用 [code-review](../../../.agents/skills/code-review/SKILL.md) 分开审阅 Spec / Standards，默认单 agent。

## Handoff Baseline

尚未激活。前包 accepted 后由 Codex 记录当时 HEAD、tracked/untracked 改动、相关快照与实际依赖，再交接实施；准备期状态不作为实施基线。

## Cline Report

未开始。激活后按 [AGENTS 的 M3 工作流](../../../AGENTS.md#m3-delivery-workflow--user-confirmed-override)记录最多 5 个子交付、用户代码、实际验证、教学与未结项。

## Codex Acceptance

Spec / Standards 均未审阅，无验证结论，Verdict 待验收。仅 accepted 后进入 [M3-05](m3-05-rerank.md)。
