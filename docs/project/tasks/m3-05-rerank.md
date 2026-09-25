# M3-05 — Rerank

创建：2026-09-22。状态：已建包，待 [M3-04](m3-04-hybrid.md) 验收后激活；尚未实施。

## Codex Plan

**执行入口：** 先读 [Current Plan](../current-plan.md) 确认活动包，再按 [AGENTS 的 M3 工作流](../../../AGENTS.md#m3-delivery-workflow--user-confirmed-override) 执行。下列要求是本包边界，不是替 Cline 预排的子交付；由 Cline 在 Report 中安排最多 5 个子交付，每次只推进当前一步。

**目标与范围：** 完成一种真实重排模型的接入和评估，比较同一候选集合重排前后效果与成本。

**任务来源与阅读：** [Current Plan](../current-plan.md) 第 4、5 节、[M3-04](m3-04-hybrid.md) 候选配置与结果；按需读已验收检索接口、公共 runner 和模型依赖。选重排模型时查其官方文档，记录版本与实际运行条件。

**输入 → 输出：** 一个固定候选生成方法、候选 Case 的原文和 Query → 候选内的新排名、重排分数与来源、端到端评估和分阶段耗时。

**必须实现的行为：**

- 依据已验收结果固定一个候选生成方法、候选数和一个重排模型；明确重排为流水线组件。候选数通常覆盖主评估 K，但以实际可用候选为准；记录是否覆盖全部语料。
- 将 Query 与各候选文本配对评分；文本截断、批量处理、模型版本和评分方向明确记录，ID 与得分逐一对应。
- 输出只能包含输入候选，保持唯一和稳定的同分规则。空候选不调用模型；模型失败、数量不匹配或非有限分数必须报告，不静默回退或生成成功报告。
- 保存候选原名次、重排后名次与原始分数；相同候选下比较排序效果，再报告端到端指标。候选之外的正例遗漏不能归因于重排。
- 记录候选检索、重排和整条查询的耗时；不给分数附加未经校准的概率含义。性能与质量均无收益时也保留结果。

**实现边界：** 必要模型依赖、重排模块、流水线配置与结果记录；不实现 Grounded Answer 或 LLM 调查流程。

**用户亲手部分（预留）：** 建议用户编写重排 ID 映射的回归测试：用可控模型分数使候选次序改变，检查输出 ID 与预期分数对应且没有候选外条目。Cline 给公共调用接口、替身注入位置和预期行为，不提供测试体；完成后检查该测试能发现“排序了分数但未同步 ID”的错误。

**测试边界与命令：** 替身测试覆盖映射、空输入、异常返回和候选边界；另以真实模型运行固定候选及 benchmark。运行本包检索测试及 `uv run pytest -q tests/evaluation tests/test_cli_evaluate.py tests/test_demo.py`。记录真实模型 smoke check 和流水线评估命令，不以替身测试代替模型实验。

**验收与教学停止点：** 真实模型已运行，候选前后对比公平，成本和错误可解释，用户测试已检查；不要求最终采用。讲清召回与重排职责、为什么重排救不回候选外记录；本包结束回交验收。

**使用 skills：** Cline 按需读取 [implement](../../../.agents/skills/implement/SKILL.md)、[teach](../../../.agents/skills/teach/SKILL.md)，纯逻辑与回归测试采用 [tdd](../../../.agents/skills/tdd/SKILL.md)；均按 AGENTS 项目适配。Codex 回交时用 [code-review](../../../.agents/skills/code-review/SKILL.md) 分开审阅 Spec / Standards，默认单 agent。

## Handoff Baseline

尚未激活。前包 accepted 后由 Codex 记录当时 HEAD、tracked/untracked 改动、相关快照与实际依赖，再交接实施；准备期状态不作为实施基线。

## Cline Report

未开始。激活后按 [AGENTS 的 M3 工作流](../../../AGENTS.md#m3-delivery-workflow--user-confirmed-override)记录最多 5 个子交付、用户代码、实际验证、教学与未结项。

## Codex Acceptance

Spec / Standards 均未审阅，无验证结论，Verdict 待验收。仅 accepted 后进入 [M3-06](m3-06-targeted-experiments.md)。
