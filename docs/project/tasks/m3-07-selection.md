# M3-07 — 汇总选型与验收

创建：2026-09-22。状态：已建包，待 [M3-06](m3-06-targeted-experiments.md) 验收后激活；尚未实施。

## Codex Plan

**执行入口：** 先读 [Current Plan](../current-plan.md) 确认活动包，再按 [AGENTS 的 M3 工作流](../../../AGENTS.md#m3-delivery-workflow--user-confirmed-override) 执行。下列要求是本包边界，不是替 Cline 预排的子交付；由 Cline 在 Report 中安排最多 5 个子交付，每次只推进当前一步。

**目标与范围：** 汇总 M3 四类方法与有限调整，固定交给 M4 的检索方案，完成 M3 收尾。数据和模型能力有限时保留结论边界，不要求某个复杂组合胜出。

**任务来源与阅读：** [Current Plan](../current-plan.md) 的 M3 完成标准、前六包的验收与结果路径；复现信息沿用已交付报告，不另建实验管理系统。

**输入 → 输出：** 已验收的同版本四类方法配置、结果、错误和耗时 → 对比报告、选定配置、复现命令、M4 检索交接说明及本包最终验收。

**必须实现的行为：**

- 对比前核对 Corpus / Query / qrels 哈希、指标定义与 K；不同方法允许源码和模型不同，不能以模型或源码哈希相同作为同 benchmark 的要求。不同数据或指标版本的结果拒绝放进同一质量对比表。
- 覆盖 BM25、Embedding、Hybrid、候选方法 + Rerank 四类实际运行结果，列出逐 Query 与汇总指标、代表性退步、冷启动/缓存及硬件/API 条件下的耗时和复杂度。注明候选数量和模型版本。
- 根据证据固定方案；效果持平时解释成本与维护复杂度的取舍。Rerank 未采用仍保留已完成实验记录；Development 选型不冒充 Locked Test 或生产泛化验证。
- 按最终配置完成必要复跑与复现核对，数据/指标版本有变化时四类方法统一重跑；明确模型数值误差与允许变化的时间字段。保存源码及依赖信息，复现命令实际可执行，保留此前正式结果。
- M4 交接包含 Query 输入、Case ID/排名/分数、取回历史原文与 Evidence 来源的调用路径、已知限制；复用已有字段，不提前实现回答生成、数据库或 Web。

**用户亲手部分（预留）：** 建议用户实现结果对比前的兼容性检查函数，输入两份结果报告，比较 benchmark 身份与指标口径，不兼容则指出字段并报错；模型差异应允许。Cline 提供报告字段说明和函数接口，用户完成后检查；将函数用于本包真实结果汇总，避免只做脱离项目的练习。

**测试边界与命令：** 独立样例覆盖同基准不同模型允许比较、语料/qrels/指标变化拒绝比较；运行本包比较逻辑测试和 `uv run pytest -q`，如仍有旧 dev-v1 归档失败须单列，不能宣称全绿。记录最终四类方法的实际评估命令、复现结果与 `uv run casetrace demo` 结果；耗时/模型调用等未跑项如实说明。

**验收与教学停止点：** 四方法同基准对比完整、选型理由及局限明确、用户代码已检查、复现和来源可核对。Cline 完成回报后停下；Codex 检查前六包验收及本包证据，决定 M3 是否完成并更新 Current Plan。下一阶段为另行规划 M4，不在本包实施。

**使用 skills：** Cline 按需读取 [implement](../../../.agents/skills/implement/SKILL.md)、[teach](../../../.agents/skills/teach/SKILL.md)，纯逻辑与回归测试采用 [tdd](../../../.agents/skills/tdd/SKILL.md)；均按 AGENTS 项目适配。Codex 回交时用 [code-review](../../../.agents/skills/code-review/SKILL.md) 分开审阅 Spec / Standards，默认单 agent。

## Handoff Baseline

尚未激活。前包 accepted 后由 Codex 记录当时 HEAD、tracked/untracked 改动、相关快照与实际依赖，再交接实施；准备期状态不作为实施基线。

## Cline Report

未开始。激活后按 [AGENTS 的 M3 工作流](../../../AGENTS.md#m3-delivery-workflow--user-confirmed-override)记录最多 5 个子交付、用户代码、实际验证、教学与未结项。

## Codex Acceptance

Spec / Standards 均未审阅，无验证结论，Verdict 待验收。仅 accepted 后进入 由 Codex 另行规划 M4。
