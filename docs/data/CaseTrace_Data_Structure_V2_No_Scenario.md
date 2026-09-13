# CaseTrace 数据结构 V2（无 Scenario）

本文件定义字段、主数据关系及数据库映射；业务校验见 CR-01～CR-47，合成限制见 GR-01～GR-10。V1 仅包含已结案 Case。

## 1. Product 与主数据

Product 固定承载 Customer、Product Family、Package Route 和封装材料 BOM，Case 不重复存储。

| 关系 | 定义与存储 |
|---|---|
| Product → Customer | 每个 Product 恰属一个客户，每个客户至少一个产品。Excel 的 customer_product_map.product_id 唯一且覆盖全部产品；落库转为 products.customer_id 非空外键，不重复保存归属表 |
| Product → Product Family / Route | 分别引用一个产品族和一条路线；不能通过产品族推导路线 |
| Product → Material | product_material_map 仅存 (product_id, material_id)，组合唯一；类别从 materials 推导，每产品每类别一个固定料号 |
| Route → Process | package_process_map 表达路线工序关系；incoming、optional、auxiliary 不强制 sequence_no |

BOM 导入时检查材料引用、路线适用性、每类唯一及下列类别集合的完整性。

| Route | BOM 类别 |
|---|---|
| LF_WB | leadframe、die_attach_adhesive、bonding_wire、molding_compound |
| SUBSTRATE_WB | substrate、die_attach_adhesive、bonding_wire、molding_compound、solder_ball |
| SUBSTRATE_FC | substrate、underfill、molding_compound、solder_ball |

BOM 仅含现有封装构成料号，无单颗用量。助焊剂、胶带、清洗介质、气体、包装和防潮用品仍为 material_process_map 中的候选知识。当前未配置可选 SMT 元件，不生成已使用这些元件的事实；未提供的质量标准、车规属性和尺寸不补造或作为已知条件。

## 2. Case / CaseDetail

Case 是一次完整调查；Detail 是 Case × Production Lot × Detection Event。同批可有多次事件。Case 不存 product_id，客户通过 Case→Detail→Product 推导；同客户多产品见 CR-04。

下列 Case、CaseDetail 字段除标注可选或最少数量外均必填。实体沿用原 ID 主键，引用使用外键。

| Case 字段 | 定义 |
|---|---|
| case_id | 主键 |
| abnormal_description | 整体异常描述 |
| investigation_others | 补充调查文本，可选 |
| root_cause | 原因结论大文本，可多原因或 NDF；CR-28 |
| corrective_action | 具体措施大文本，可多措施；CR-29、GR-09 |

| CaseDetail 字段 | 定义 |
|---|---|
| detail_id | 主键 |
| case_id | 所属 Case |
| product_id | 对应 Product |
| customer_lot | 客户批号，厂内发现也必填 |
| production_lot | 内部生产批号 |
| production_time | 投批日期，date |
| detection_stage | IQC / In-process / OQC / Customer / Other |
| detection_time | 异常发现/反馈日期，date |
| abnormal_types[] | 现有 failure_mode_id 的无序集合，至少一个、内部不重复 |
| affected_qty | 整条 Detail 的处置范围数量，正整数，单位固定为 ea（颗），不另存单位字段；不按异常拆分，不仅指确认不良数量 |
| disposition | 最终处置文本，允许 hold、sort、rework、release 等组合 |

原因和措施不拆独立实体。abnormal_types 通过 Detail—FailureMode 关系表存储，(detail_id, failure_mode_id) 组合唯一；Detail 去重另按 CR-11 比较完整异常集合。

Case 至少一个 Detail、一个 Evidence。Lot 固定属性见 CR-08～CR-10；时间顺序见 CR-21；数量上限及同批事件数量重叠见 GR-06。不新增 ProductionLot 主表或 lot_total_qty。

## 3. EvidenceCheckpoint

一个 Evidence 是独立调查项，只挂 Case，不直接挂 Detail。

| 字段 | 定义 |
|---|---|
| checkpoint_id | 主键 |
| case_id | 所属 Case |
| checkpoint_type | QC / AOI / Production / OCAP / Previous/Next Lot / Monitoring / EDX / Reliability / Material / Other |
| custom_name | Other 的具体调查名称，Other 时必填 |
| result | 调查结果 |
| relevance | related / not_related / uncertain |

除 custom_name 条件必填外均必填。无法归入前九类的方法用 Other + custom_name；detection_methods 仅作候选，screening_methods 不自动转为调查项。原因与证据一致性见 CR-35～CR-37。

## 4. CaseGroup / Membership

Group 是显式建立、记录关联理由的 Case 集合，可用于技术复发或管理目的。Case 可属于零至多个 Group，每组至少两个不同 Case。

| CaseGroup 字段 | 定义 |
|---|---|
| group_id | 主键 |
| group_type | 多选列表（list[str]），至少选择 CR-42 中的一个类型 |
| description | 这组 Case 的整体说明 |
| other_type_description | Other 分组类型的解释；CR-43 |

| Membership 字段 | 定义 |
|---|---|
| group_id、case_id | 分别引用 Group、Case，组成主键；不增加 membership_id |
| association_reason | 该 Case 入组理由，非空 |

复发关系、跨客户/产品及管理分组边界见 CR-44～CR-47。

## 5. 数据库实现

| 事项 | 实现要求 |
|---|---|
| ID 与文本 | failure_mode_id 按文本保存前导零；必填文本拒绝 NULL、空串、纯空白 |
| Lot 一致性 | 写入/导入时跨记录校验固定属性；并发时保证检查与写入一致 |
| 父子数量 | Case、Detail、Evidence、Group、Membership 成组写入，在事务最终状态校验最少数量 |
| 工序引用 | package_process_map.process 落库时由 process_id 查询；applicable_process 仅作知识引用，不参与 Case 合法性门槛 |
| 校验分工 | CR、GR 分开检查；PK/FK、非空及 relevance 标签不能替代语义审查；生成顺序见 GR-10 |

## 6. Repeat Case 判断信息

实际设备、材料批号、晶圆批号和参数调整必须保留，用于判断 repeat_case。V1 使用现有 EvidenceCheckpoint，不新增字段或关系表：

| 事实 | 记录位置 | 内容 |
|---|---|---|
| 实际设备 | Production Evidence.result | 记录实际 equipment_id；该设备须存在并适用于所述工序 |
| 参数调整 | Production Evidence.result | 记录本次生产或改善中的具体参数调整 |
| material lot | Material Evidence.result | 同时记录 BOM material_id 与该料号的实际供货/制造批号 |
| wafer lot | Material Evidence.result | 记录晶圆来料批号；不自动等于 customer_lot 或 production_lot |

相关事实存在或被调查时写入对应 Evidence；不要求每个 Case 同时具有四项。ID 和批号由生成程序先确定，LLM 只组织 result 文本。它们用于支持复发判断，相同设备、材料批号或 wafer lot 本身不自动构成 repeat_case；分组仍须满足 CR-44。
