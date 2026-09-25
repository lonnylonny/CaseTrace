# Data Foundation v1 — 保留的设计与主数据决定

字段、实体关系与 M5 数据库设计统一在[数据结构](CaseTrace_Data_Structure_V2_No_Scenario.md)，业务规则在 [CR](CaseTrace_Case_Constraint_Rules_Frozen.md) / [GR](CaseTrace_Case_Generation_Rules_V1.md)，已实现及未覆盖范围在 [Validator 说明](CaseTrace_Validator_Implementation_Plan.md)。历史审计与修订过程通过 Git 查阅。

主数据文件为 `data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx`。客户归属与 BOM 曾按固定种子 **20260908** 分配并持久保存；Case 生成沿用现有归属和固定 BOM，不重新分配。未使用的候选知识仍保留，不能据其存在推定某个 Case 使用了对应工序或材料。

实际设备、材料批号、晶圆批号和参数调整（原决定 B07）使用现有 Evidence.result 保存，支持人工复发判断；具体落位见结构 §6。数据库映射为已确认设计，M5 尚未实施；既有规格审查不等于数据库运行或全部文本语义已验收。
