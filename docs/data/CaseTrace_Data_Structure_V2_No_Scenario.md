# CaseTrace 数据结构 V2（无 Scenario）

> Data Foundation v1：2026-09-16 已确认完成并冻结。字段和关系继续有效；开发顺序与冻结边界见 [Current Plan](../project/current-plan.md#3-data-foundation-v1-冻结)。本文件中的 SQL 映射设计不表示数据库已实现，也不是检索评估的前置任务。

本文件定义字段、主数据关系及数据库映射；业务校验见 CR-01～CR-51，合成限制见 GR-01～GR-10。V1 仅包含已结案 Case。2026-09-19 用户确认补充异常站点及同站点分组，属于本次明确授权的数据基础修订。

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
| abnormal_processes[] | 已确认涉及异常的 process_id 无序集合，必填、至少一个、内部不重复；CR-48～50 |
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

abnormal_processes 通过 Case—Process 关系表存储，(case_id, process_id) 组合唯一。工序名称由 process_master 查询，不重复存入 Case。可选范围是 Case→Detail→Product 所有路线在 package_process_map 中的工序并集，包括 incoming、core、optional、auxiliary；不以 sequence_no 是否为空过滤。每项须属于至少一个涉及产品的路线，不表示每个产品都涉及该站点，也不建立逐 Detail 的工序归属。

异常站点与 detection_stage 分别表示调查确认涉及的工序和发现阶段，不能互相代填。原因允许 NDF，但至少一个异常站点须已确认；站点未知的记录暂不纳入正式 Case。路线允许 optional 工序不证明案例实际使用它，现有 SMT 生成边界继续有效。Failure Mode 的 applicable_process 仍只是候选知识，不用作匹配门槛或自动填充。

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

复发关系、跨客户/产品及管理分组边界见 CR-44～CR-47。same_abnormal_process 表示同站点异常关联：全组成员至少共享一个已确认异常工序（CR-51），可跨客户、产品，不要求相同异常表现或根因。各选中类型的条件同时适用；同站点不自动代表 repeat_case，不自动成为检索标签。

## 5. 数据库实现

| 事项 | 实现要求 |
|---|---|
| ID 与文本 | failure_mode_id 按文本保存前导零；必填文本拒绝 NULL、空串、纯空白 |
| Lot 一致性 | 写入/导入时跨记录校验固定属性；并发时保证检查与写入一致 |
| 父子数量 | Case、Detail、Evidence、Group、Membership 成组写入，在事务最终状态校验最少数量 |
| 工序引用 | package_process_map 以 (package_route, process_id) 唯一关联；工序名称由 process_id 查询。Case 异常工序按 CR-48～50 检查，applicable_process 仅作候选知识 |
| 校验分工 | CR、GR 分开检查；PK/FK、非空及 relevance 标签不能替代语义审查；生成顺序见 GR-10 |

### PostgreSQL Schema 范围（设计冻结，M5 实现）

PostgreSQL 是 V1 必做交付，在检索评估与 Grounded Answer 完成后按 [Current Plan](../project/current-plan.md) 的 M5 实现。届时落地能保存和取回完整历史 Case 的表。字段含义沿用本文件及 Excel，
不重新设计 Case 模型。其余主数据暂保留在 Excel，按实际使用需要接入。

| 表 | 主键与核心关系 | 保存内容 |
|---|---|---|
| customers | customer_id 主键 | 客户名称 |
| product_families | product_family_id 主键 | 产品族名称 |
| package_routes | package_route 主键 | 路线及其背景描述 |
| products | product_id 主键；customer_id、product_family_id、package_route 外键 | 产品名称、功能及固定归属；不再建 customer_product_map 表 |
| failure_modes | failure_mode_id 主键 | 异常名称及 Excel 中的原因、措施、检测方法等候选知识 |
| failure_mode_routes | (failure_mode_id, package_route) 组合主键，两列均为外键 | 将 applicable_package 拆成异常适用路线关系 |
| processes | process_id 主键 | process_master 的工序名称、类别及描述 |
| package_process_map | (package_route, process_id) 组合主键，两列均为外键 | 路线工序关系及顺序、类型、范围；名称通过 processes 查询 |
| cases | case_id 主键 | §2 的 Case 字段，abnormal_processes 通过下表保存 |
| case_abnormal_processes | (case_id, process_id) 组合主键，两列均为外键 | Case 调查确认涉及的一个或多个异常工序 |
| case_details | detail_id 主键；case_id、product_id 外键 | §2 的 Detail 字段，abnormal_types 通过下表保存 |
| detail_failure_modes | (detail_id, failure_mode_id) 组合主键，两列均为外键 | Detail 的一个或多个异常 |
| evidence_checkpoints | checkpoint_id 主键；case_id 外键 | §3 的 Evidence 字段，不直接关联 Detail |
| case_groups | group_id 主键 | §4 的 Group 字段；允许整表为空 |
| case_group_memberships | (group_id, case_id) 组合主键，两列均为外键 | association_reason；Case 不要求入组 |

类型与实现边界：

- ID、批号和叙述内容使用 text；日期使用 date；affected_qty 使用 integer；group_type 使用 text[] 保留多选。
- 枚举使用 text / text[] 配合简单 CHECK；必填字段使用 NOT NULL，并拒绝空白文本。
- 数据库先实现主键、外键、组合唯一性、正数量、日期先后和枚举等基础约束。跨记录检查复用已有 Python 能力，随导入事务执行；不为此次落库扩展完整 Validator 或复杂触发器体系。
- Case 至少一个异常工序、产品路线并集适配及同站点分组公共交集在事务最终状态复用 Python 校验；外键存在本身不能证明调查事实已确认。
- 为 case_details.case_id、case_details.product_id、evidence_checkpoints.case_id 和 case_group_memberships.case_id 建立普通索引，支持按 Case 取回内容及关联查询。
- 原因、措施保留在 cases 中；候选知识保留在 failure_modes 中；生成来源信息继续独立保留，不混入检索文本。
- 首次入库先导入主数据（含工序与路线工序映射），再在事务中写入 Case、异常工序关系、Detail、异常关系、Evidence 和可选 Group／Membership。读取时按 case_id 组装成现有对象，复用 build_documents() 和 BM25Retriever。
- BOM、设备按需后续落库；向量索引及 Ground Truth 存储在对应任务中按需处理，当前可使用文件，不以数据库 Schema 完成为前提。上述工序表仅是 M5 设计更新，本轮不建库。

## 6. Repeat Case 判断信息

实际设备、材料批号、晶圆批号和参数调整必须保留，用于判断 repeat_case。V1 使用现有 EvidenceCheckpoint，不新增字段或关系表：

| 事实 | 记录位置 | 内容 |
|---|---|---|
| 实际设备 | Production Evidence.result | 记录实际 equipment_id；该设备须存在并适用于所述工序 |
| 参数调整 | Production Evidence.result | 记录本次生产或改善中的具体参数调整 |
| material lot | Material Evidence.result | 同时记录 BOM material_id 与该料号的实际供货/制造批号 |
| wafer lot | Material Evidence.result | 记录晶圆来料批号；不自动等于 customer_lot 或 production_lot |

相关事实存在或被调查时写入对应 Evidence；不要求每个 Case 同时具有四项。ID 和批号由生成程序先确定，LLM 只组织 result 文本。它们用于支持复发判断，相同设备、材料批号或 wafer lot 本身不自动构成 repeat_case；分组仍须满足 CR-44。
