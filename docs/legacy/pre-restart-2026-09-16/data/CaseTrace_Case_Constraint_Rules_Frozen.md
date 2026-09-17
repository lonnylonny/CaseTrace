> 历史归档（2026-09-16）：本文件不是当前要求、状态或 Agent 指令；后续任务以 [Current Plan](../../../project/current-plan.md) 为准。原文中的“当前”“已完成”“冻结”等仅对应历史时点。

# CaseTrace Case Constraint Rules — Frozen

适用于 V1 已结案 Case。字段、枚举、数据库映射及用于复发判断的 B07 实际生产信息见《CaseTrace_Data_Structure_V2_No_Scenario.md》；合成范围见《CaseTrace_Case_Generation_Rules_V1.md》。不设置 Scenario。

保留 CR-01～CR-47 编号及原类型：Hard 为硬约束，Hard semantic 包含语义判断，Hard boundary 定义允许范围，Soft 仅提示复核。

| ID | 类型 | 规则 |
|---|---|---|
| CR-01 | Hard | Case 至少包含一个 CaseDetail。 |
| CR-02 | Hard | 每个 CaseDetail 恰属一个 Case。 |
| CR-03 | Hard | Case、CaseDetail、EvidenceCheckpoint、CaseGroup 的 ID 各自在对象类型内唯一；所有引用有效。Membership 的组合身份见 CR-40。 |
| CR-04 | Hard | Product 唯一确定 Customer；通过 Detail→Product 推导出的 Case 客户必须唯一。同一 Case 可多 Product，但须同客户；跨客户关系用 CaseGroup 表达。 |
| CR-05 | Hard | 每个 Detail 必须引用有效 product_id。 |
| CR-06 | Hard | production_lot 必填。 |
| CR-07 | Hard | customer_lot 必填，厂内发现也不例外。 |
| CR-08 | Hard | Dataset 内，同一 production_lot 的 product_id 固定。 |
| CR-09 | Hard | V1 内，同一 production_lot 的 customer_lot 固定。 |
| CR-10 | Hard | 同一 production_lot 的 production_time 固定。 |
| CR-11 | Hard | 同一 Case 内，production_lot、detection_stage、detection_time、abnormal_types 集合均相同的 Detail 不得重复；异常集合无序、内部不重复。 |
| CR-12 | Hard | abnormal_description 非空。 |
| CR-13 | Hard semantic | abnormal_description 不得直接违背 Detail 中的明确事实。 |
| CR-14 | Hard | abnormal_types 至少包含一个异常。 |
| CR-15 | Hard | abnormal_types 直接引用现有 failure_modes，不另建异常分类。 |
| CR-16 | Hard | 所选异常须适用于 Product 的封装路线。 |
| CR-17 | Hard boundary | 一个 Detail 可包含多个 Failure Mode。 |
| CR-18 | Hard boundary | applicable_process 仅为知识属性，不参与 Case 合法性校验，也不要求 Case 指定或匹配唯一发生工序。 |
| CR-19 | Hard | production_time 必填，含义固定为投批时间。 |
| CR-20 | Hard | detection_time 必填，统一表示异常发现/反馈时间。 |
| CR-21 | Hard | detection_time ≥ production_time。 |
| CR-22 | Hard boundary | 同批不同发现/反馈事件可有不同 detection_time。 |
| CR-23 | Hard | affected_qty 为正整数。 |
| CR-24 | Hard | affected_qty 必填，单位固定为 ea（颗），不另存单位字段。 |
| CR-25 | Hard | 每条 Detail 只记录一个 affected_qty，使用固定的颗数口径。 |
| CR-26 | Hard semantic | affected_qty 是该 Detail 纳入处置范围的数量，不是仅指确认不良的颗数。 |
| CR-27 | Hard | disposition 是非空的最终处置文本，可组合多种处置。 |
| CR-28 | Hard | root_cause 必须有明确结案结论；允许 NDF / 未确认原因，不得空白。 |
| CR-29 | Hard | corrective_action 必须有具体措施；包括 NDF 在内，均不使用“无需改善”分支。候选来源限制由 GR-09 检查。 |
| CR-30 | Hard | 每个 Case 至少有一个 EvidenceCheckpoint。 |
| CR-31 | Hard | Evidence 必须属于有效 Case，不直接归属某个 Detail。 |
| CR-32 | Hard | Evidence 的 checkpoint_type、result、relevance 必填；类型限于结构文档列出的十个值。 |
| CR-33 | Hard | relevance 仅为 related / not_related / uncertain。 |
| CR-34 | Hard | checkpoint_type=Other 时，custom_name 必须写明具体调查名称；未归入已有类型的方法用此方式记录，不扩展枚举。 |
| CR-35 | Hard | Confirmed Root Cause 至少由一个 related Evidence 支持。 |
| CR-36 | Hard semantic | related Evidence 的结果不得直接反驳其所支持的 Root Cause。 |
| CR-37 | Soft | QC、AOI、Production、OCAP、前后批、Monitoring 等调查仅在适用时预期出现；缺少适用项提示复核，不直接判非法。 |
| CR-38 | Hard | CaseGroup 至少包含两个不同 Case。 |
| CR-39 | Hard | Membership 引用的 Case 和 Group 必须存在。 |
| CR-40 | Hard | Membership 以 (group_id, case_id) 唯一标识，同一组合不得重复。 |
| CR-41 | Hard | 每条 Membership 的 association_reason 非空。 |
| CR-42 | Hard | group_type 为非空多选列表，每个值仅为 repeat_case / project / customer_request / management_request / other。 |
| CR-43 | Hard | group_type 包含 other 时，other_type_description 非空并解释分组类型；description 描述这组 Case，不能代替该字段。 |
| CR-44 | Hard semantic | repeat_case 必须有明确确认的异常复发关系，通常表现为重复或高度相关的发生原因、Root Cause 或失效机制。设备、材料批号、wafer lot、参数调整等 Evidence 可作为判断依据，但任一字段相同都不能自动建组。 |
| CR-45 | Hard boundary | repeat_case 可跨 Customer、Product。 |
| CR-46 | Hard boundary | same_root_cause、same_customer_product、common_failure_event 不作为 group_type 或新增子类型；相关信息写入 description 或 association_reason。 |
| CR-47 | Hard boundary | project、customer_request、management_request 允许管理目的分组，这些类型本身除通用 Group 结构规则外，不追加技术关联条件；同时选择 repeat_case 时仍须满足 CR-44。 |

本文件不规定候选原因/措施来源、采样权重或频率、记录数上限、固定的发现阶段时间间隔；生成限制由 GR 规定。无 lot_total_qty 字段，不建立与其比较的约束。Group 始终显式建立，不根据字段相似度自动推导。Dataset Composition、Ground Truth 和 SQL 实现不属于本文件。
