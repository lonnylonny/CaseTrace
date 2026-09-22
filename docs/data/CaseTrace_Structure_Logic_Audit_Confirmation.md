# CaseTrace 审计确认记录

> 本文件保留数据设计的历史确认记录；“尚未实现”等状态仅对应当时审计时点，不代表当前进度。Data Foundation v1 已于 2026-09-16 确认完成并冻结；当前状态见 [Current Plan](../project/current-plan.md)，校验覆盖见 [Validator 说明](CaseTrace_Validator_Implementation_Plan.md)。

## 已确认决定

| 编号 | 决定与落实 |
|---|---|
| A01 | product_id 放在 CaseDetail，Case 经 Detail 引用 Product |
| A02 | customer_lot 必填，厂内发现不例外 |
| A03 | Group 允许管理目的；仅 repeat_case 要求复发关系；采用 CR-42 的五个类型 |
| A04 | Product 唯一确定 Customer；获准在原有客户候选中分配，全部客户和产品均被覆盖 |
| B01 | 已补固定 BOM：每产品每类别一个料号，类别范围及耗材边界见结构文档 §1 |
| B02 | 仅 ea（颗）；正整数，每生产批上限 5,000 ea，Detail 生成范围 1～5,000；取消 wafer 换算 |
| B03 | V1 每 Case 均使用具体候选措施，不设“无需改善”分支；NDF 保留但不免除措施要求 |
| B04 | 固定十种 Evidence 类型，Other + custom_name 兜底 |
| B05 | CR、GR 与文本语义分别检查；已写入规格，尚未实现 Validator |
| B06 | other_type_description 解释 Other 类型，不能由 description 替代 |
| B07 | 确认保留实际设备、材料批号、晶圆批号和参数调整，用于判断 repeat_case；V1 写入 Production / Material Evidence.result，不新增字段，见结构文档 §6 |
| T01～T06 | 数据库实现方向已确认，见结构文档；尚未执行建库 |

## 主数据记录

文件：`封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx`。客户归属及 BOM 使用固定种子 20260908 分配后已存为主数据，不随 Case 生成重选。

| 内容 | 权威位置与结果 |
|---|---|
| 客户归属 | customer_product_map：18 条唯一归属；5 个客户均有产品，18 个产品均有客户 |
| 产品背景 | products：产品族、路线；materials：材料类别；不在本记录复制主数据 |
| 固定 BOM | product_material_map：77 条关系，覆盖 18 个产品；每产品每类唯一且路线适配 |
| 总规模 | 12 张 Sheet、498 条有效记录；保留原主数据及未使用的候选知识 |

## 本轮 IT 复审与精简

主键候选、普通及组合引用、客户覆盖、BOM 类别完整性与唯一性、路线工序引用和顺序检查通过；未发现新的规格硬冲突。

B07 已按现有 Evidence 结构落位；这些信息支持人工确认 repeat_case，不根据相同设备或批号自动建组。“少量”“通常半年内”等仍是原生成口径，尚未定为可复现执行参数，本轮不补设数值。当前 BOM 未配置 SMT 元件，相关异常知识仍保留，不代表必须生成其 Case。

四份 Markdown 已删减重复理由、反例、关系说明和主数据抄录，保留 CR-01～CR-47、GR-01～GR-10 及原字段和边界，并同步本轮 B07 决定；Excel 数据未修改。此次验证覆盖主数据及规格，不代表数据库、Validator 或实际生成 Case 已通过运行测试。

## 2026-09-19 异常站点修订

用户确认在冻结基础上增加 Case.abnormal_processes 必填多选，按涉及产品路线工序并集限制选项；站点未知的记录暂不纳入正式 Case，原因 NDF 仍可保留。新增 same_abnormal_process 分组类型，全组须共享至少一个异常站点，可跨客户和产品，不要求同异常表现或根因。

此决定更新 A03 的“五个类型”范围；原确认记录保留为历史。现行字段与 SQL 设计见结构文档，约束见修订后的 CR-18、42、47 和新增 CR-48～51，生成安排见 GR-10，不在本记录复制完整规则。

主数据复核：process_master 有 15 条有效工序，package_process_map 有 36 条有效路线工序关系；空行不计数。未发现重复工序 ID、重复路线工序组合或工序引用/名称不一致，Excel 原文件未修改。数据库仍未实施；代码覆盖以 Validator 说明及 Current Plan 为准。
