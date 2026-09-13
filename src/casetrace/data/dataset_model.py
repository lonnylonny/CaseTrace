# define case structure

from dataclasses import dataclass
from datetime import date


@dataclass
class CaseDetail:

    detail_id : str
    #非空且唯一
    case_id : str
    #非空，必须是case表中存在的case_id，只能是一个
    product_id : str
    #非空，引用一个有效 Product；不同 Detail 可以引用同一 Product
    customer_lot : str
    #非空
    production_lot : str
    #非空
    production_time : date
    #非空，必须是日期
    detection_stage : str
    #非空，枚举见数据结构文档 §2；不引用生产工序表
    detection_time  : date
    #必须是 date，且不早于 production_time（CR-21）
    abnormal_types : list[str]
    #非空，元素引用 failure_modes，内部不重复；允许多异常
    affected_qty : int
    #处置范围数量，单位固定 ea（颗）；正整数（CR-23），生成上限见 GR-06
    disposition : str
    #非空

@dataclass
class EvidenceCheckpoint:

    checkpoint_id : str
    #非空且唯一
    case_id : str
    #非空，必须是case表中存在的case_id，只能是一个
    checkpoint_type : str
    #非空，使用数据结构文档 §3 的固定枚举
    custom_name : str | None
    #checkpoint_type 为 Other 时必须是非空文本（CR-34）
    result : str
    #非空
    relevance : str
    #非空

@dataclass
class Case:

    case_id : str
    #非空且唯一
    abnormal_description : str
    #非空
    root_cause : str
    #非空
    corrective_action  : str
    #非空
    investigation_others : str | None
    #可为空
    detail_ids : list[str]
    #非空，必须是case_detail表中存在的detail_id，可多选
    evidence_checkpoint_ids : list[str]
    #非空，必须是evidence_checkpoint表中存在的checkpoint_id，可多选

@dataclass
class CaseGroup:

    group_id  : str
    #非空且唯一
    group_type : list[str]
    #非空多选列表，允许值见 CR-42
    description : str
    #非空
    other_type_description : str | None
    #group_type 包含 other 时必须是非空文本（CR-43）
    #和case属于n：n关系，通过membership进行关联

@dataclass
class Membership:

    #用于构建关系表，用于多对多关系

    group_id : str
    #非空，必须是case_group表中存在的group_id，只能是一个
    case_id : str
    #非空，必须是case表中存在的case_id，只能是一个
    association_reason : str
    #非空

@dataclass
class CaseBundle:

#用于将case、case_group、membership、case_detail、evidence_checkpoint等表进行组合，形成一个完整的case结构

    case : Case
    groups : list[CaseGroup]
    memberships: list[Membership]
    details: list[CaseDetail]
    evidences: list[EvidenceCheckpoint]
