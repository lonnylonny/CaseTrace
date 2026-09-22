# CaseTrace Case Generation Rules V1

> Data Foundation v1：2026-09-16 已确认完成并冻结。以下规则继续有效；不为补齐自动化生成或校验能力阻塞检索评估，见 [Current Plan](../project/current-plan.md#3-data-foundation-v1-冻结)。

生成结果须通过 CR-01～CR-51，并满足本表；字段枚举及 BOM 定义见《CaseTrace_Data_Structure_V2_No_Scenario.md》。2026-09-19 异常站点修订已获用户确认。

| ID | 生成规则 |
|---|---|
| GR-01 | 每 Case 1～3 个 Detail；默认单 Product，少量多 Product（CR-04）。沿用固定客户归属和 BOM，不随 Case 重新分配。 |
| GR-02 | 从现有 failure_modes 选择并满足路线适用性。按 Detail 统计，约 90% 单异常、10% 双异常。 |
| GR-03 | 双异常须能与现有原因、证据、措施形成一致逻辑，否则重选；不建 compatibility 表。原因、措施及材料/料号不得违背路线或固定 BOM。BOM 外工艺耗材仍可作已有知识候选，但不得冒充固定配置。 |
| GR-04 | 默认每 Detail 使用新 production_lot；整个 Dataset 仅有 1～2 个复用批号，各至少出现两次；固定属性沿用 CR-08～CR-10。 |
| GR-05 | 按日期随机生成发现/反馈时间，满足 CR-19～CR-22；通常距投批半年内，少量超过半年，不建立发现阶段时间模型。 |
| GR-06 | 每生产批上限 5,000 ea；每 Detail 的 affected_qty 为 1～5,000 的整数，单位仅 ea，不作 wafer 换算、不新增 lot_total_qty。同批事件可覆盖相同实物，数量不能相加作为去重受影响量。 |
| GR-07 | 生成必要 Evidence 子集，每 Case 至少一个。类型及 Other 用法按结构文档；detection_methods 仅作候选，不强制采用或覆盖全部常见调查。与 Case 逻辑相关的实际设备、参数调整写入 Production result，材料料号/批号、wafer lot 写入 Material result。 |
| GR-08 | Confirmed Root Cause 仅来自现有 failure_modes.possible_root_causes，可改写，不新增原因概念。允许 NDF，但同样须满足 GR-09；无合理已有措施可结案时不生成该 Case。 |
| GR-09 | 每 Case 必须有具体措施，仅来自现有 failure_modes.corrective_actions；允许改写、组合，不新增措施概念，不使用“无需改善/措施”分支。 |
| GR-10 | Python 先确定 Customer/Product、Detail、lot、time、Failure Mode、quantity、Case.abnormal_processes 及其调查依据、Evidence 类型与 relevance、原因/措施候选，以及实际 equipment_id、material_id/material_lot、wafer_lot、参数调整等 Evidence 事实；异常工序按 CR-48～50 选择，不从 applicable_process 整体复制。LLM 仅生成或改写 abnormal_description、Evidence.result、root_cause、corrective_action、disposition。分别检查 CR、GR，并审查事实、候选概念及原因—证据—措施逻辑；候选来源在生成过程中保留供核查，不为来源追踪增加 Case 永久字段。 |

## GR-10 的异常描述生成提示词

2026-09-17 用户确认的文本生成约束。生成或改写 Case 时使用以下提示词，通过生成和人工审阅执行，不新增 Validator 检查。

```text
将每条 Case 的 abnormal_description 写成可独立阅读的异常记录。
仅根据本 Case 提供的事实，描述发现阶段、异常表现、位置和必要的观测条件；缺少的信息不要补造。
已确认异常工序由输入的 abnormal_processes 决定；不得把发现阶段或候选工序改写成已确认站点，叙述须与调查依据一致。
不要使用依赖其他样例才能理解的“另一产品”“同一生产批”“与前例相同”等相对描述，也不要写入检索相关性、排名或样例设计意图。
产品和批号关系以 CaseDetail 的具体字段为依据，不通过异常描述暗示跨 Case 关系。
本 Case 确实涉及多个产品或批号且需要区分时，使用输入中已有的明确标识。
生成后单独阅读每条 abnormal_description，确认无需查看其他 Case 就能理解。
```

此约束针对异常描述中的跨样例叙述，不删除 Detail 的真实关系，也不禁止 Evidence 中有明确事实依据的批次对照。
