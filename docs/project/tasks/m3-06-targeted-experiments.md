# M3-06 — 有限针对性实验

创建：2026-09-22。状态：已建包，待 [M3-05](m3-05-rerank.md) 验收后激活；尚未实施。

## Codex Plan

**执行入口：** 先读 [Current Plan](../current-plan.md) 确认活动包，再按 [AGENTS 的 M3 工作流](../../../AGENTS.md#m3-delivery-workflow--user-confirmed-override) 执行。下列要求是本包边界，不是替 Cline 预排的子交付；由 Cline 在 Report 中安排最多 5 个子交付，每次只推进当前一步。

**目标与范围：** 根据前五包的实际证据检验少量有价值的假设。保留原定按证据触发的性质：没有明确问题时，交付“不开展检索调整的依据”，不为完成编号强行优化。

**任务来源与阅读：** [Current Plan](../current-plan.md) 的相关性、阅读优先级与 M3-06 边界；[M3-05](m3-05-rerank.md) 及其引用的四类结果，按需回看 [M2 错误分析](../../../results/dev-v2-bm25-error-analysis.md)。

**输入 → 输出：** 同一 benchmark 的错误及配置 → 有限实验对照和取舍依据，或证据充分的“不开展调整”记录。

**必须实现的行为：**

- 开始先写问题、观察证据、假设、拟改变因素及运行次数上限；优先最小可解释的对照，不遍历大参数网格。每次改变一个因素，保留未改配置作为对照。
- 可检验已计划的字段权重、泛词/背景话术、否定表达问题；阅读优先级单独分析，不转为分级 qrels，不削弱“同产品本身即 Relevant”等确认规则。
- 本包使用 M3-03 已确认数据；不为调参调整标签或扩充数据。需要超出该边界时报告范围变化，不自行扩大。
- 比较逐 Query 改善与退步及耗时，不只看均值。二值指标不能区分 Relevant 内部顺序时，明确记为阅读判断，不虚构数值提升。
- 无可验证假设时仍记录所检查的证据和不调整理由，并完成下面的小型用户代码；该分支不需要新增运行时检索功能。

**用户亲手部分（预留）：** 建议用户在本包的小型结果分析脚本中完成“同一指标逐 Query 的 after − before”函数，供本包证据表使用并在 M3-07 复用。输入为两份已核对版本的逐 Query 指标映射，输出逐 Query 差值；Query 集合不一致应报错，任一值为 None 时明确标为不可比较。Cline 仅给接口与提示，用户完成后用手算输入检查。无调整分支用两份相同配置的实际结果说明没有变化，不制造新实验。

**测试边界与命令：** 用户函数用独立常数验证升降、相等、缺失 Query 和 None；运行 `uv run pytest -q <本包实际测试路径>`。若修改检索逻辑，追加相关检索/runner 测试和固定 benchmark 对照运行；若不改检索，读取既有证据即可，不为测试数量重复整套模型实验。将真实文件名和命令填入 Report。

**验收与教学停止点：** 实验或不开展理由可核查，有明确停止依据，用户代码可用，无隐含标签/指标变更；允许全部调整被放弃。讲清假设、控制变量与退步分析，停在本包，不自行进行最终选型。

**使用 skills：** Cline 按需读取 [implement](../../../.agents/skills/implement/SKILL.md)、[teach](../../../.agents/skills/teach/SKILL.md)，纯逻辑与回归测试采用 [tdd](../../../.agents/skills/tdd/SKILL.md)；均按 AGENTS 项目适配。Codex 回交时用 [code-review](../../../.agents/skills/code-review/SKILL.md) 分开审阅 Spec / Standards，默认单 agent。

## Handoff Baseline

尚未激活。前包 accepted 后由 Codex 记录当时 HEAD、tracked/untracked 改动、相关快照与实际依赖，再交接实施；准备期状态不作为实施基线。

## Cline Report

未开始。激活后按 [AGENTS 的 M3 工作流](../../../AGENTS.md#m3-delivery-workflow--user-confirmed-override)记录最多 5 个子交付、用户代码、实际验证、教学与未结项。

## Codex Acceptance

Spec / Standards 均未审阅，无验证结论，Verdict 待验收。仅 accepted 后进入 [M3-07](m3-07-selection.md)。
