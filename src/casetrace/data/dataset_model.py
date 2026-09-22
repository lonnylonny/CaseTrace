"""V1 已结案 Case 的内存记录，字段以 docs/data 的冻结结构为准。

Dataclass 只承载数据，类型注解不会执行校验；构造后交给 validators 检查。
ID 均使用字符串，保留 Failure Mode ID 的前导零。
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class CaseDetail:
    """一个 Case 中某生产批的一次发现／反馈事件；同批可有多次事件。"""

    detail_id: str
    case_id: str
    product_id: str  # 客户从 Product 推导，Case 不重复保存客户或产品。
    customer_lot: str
    production_lot: str
    production_time: date  # 投批日期。
    detection_stage: str  # 发现阶段，不是发生工序；枚举见 constants.py。
    detection_time: date  # 发现／反馈日期，不得早于投批日期。
    abnormal_types: list[str]  # Failure Mode ID 的无序集合，至少一个、内部不重复。
    affected_qty: int  # 纳入处置范围的颗数（ea），不是仅确认不良的数量。
    disposition: str  # 最终处置文本，可组合多种处置。


@dataclass
class EvidenceCheckpoint:
    """Case 级调查项，不直接归属 Detail；实际生产事实写入 result（结构 §6）。"""

    checkpoint_id: str
    case_id: str
    checkpoint_type: str
    custom_name: str | None  # Other 类型时必须填写具体调查名称。
    result: str
    relevance: str  # related 标签本身不能证明结果支持 Root Cause。


@dataclass
class Case:
    """一次完整调查的结案记录。

    Detail／Evidence 仅通过各自的 case_id 关联；这里不重复保存子记录 ID 列表。
    最少子记录数量必须在完整 Dataset 上检查，不能由单个 Case 对象保证。
    """

    case_id: str
    abnormal_description: str
    root_cause: str  # 允许 NDF，但必须有明确结案结论。
    corrective_action: str  # 包括 NDF 在内，均须有具体措施。
    investigation_others: str | None
    abnormal_processes: list[str]  # 已确认异常工序的 process_id；非空、无序、内部不重复。


@dataclass
class CaseGroup:
    """显式建立的 Case 分组；通过 Membership 关联至少两个不同 Case。"""

    group_id: str
    group_type: list[str]  # 多选；同站点检查全组交集，repeat_case 仍需复发语义审查。
    description: str
    other_type_description: str | None  # 包含 other 时必填，description 不能替代。


@dataclass
class Membership:
    """Case 入组关系，以 (group_id, case_id) 唯一标识，不另设 membership_id。"""

    group_id: str
    case_id: str
    association_reason: str
