# define case structure

from dataclasses import dataclass
from datetime import date


@dataclass
class CaseDetail:

    detail_id : str
    case_id : str

    product_id : str

    customer_lot : str
    production_lot : str
    production_time : date

    detection_stage : str
    detection_time  : date

    abnormal_types : list[str]

    affected_qty : int
    affected_unit : str

    disposition : str


@dataclass
class EvidenceCheckpoint:

    checkpoint_id : str
    case_id : str

    checkpoint_type : str
    custom_name : str | None

    result : str
    relevance : str


@dataclass
class Case:

    case_id : str

    abnormal_description : str

    root_cause : str
    corrective_action  : str

    investigation_others : str | None

    detail_ids : list[str]
    evidence_checkpoint_ids : list[str]


@dataclass
class CaseGroup:

    group_id  : str
    group_type : list[str]

    description : str

    other_type_description : str | None
# 和case属于n：n关系，通过membership进行关联

@dataclass
class Membership:

    group_id : str
    case_id : str

    association_reason : str

@dataclass
class CaseBundle:
    case : Case
    groups : list[CaseGroup]
    memberships: list[Membership]
    details: list[CaseDetail]
    evidences: list[EvidenceCheckpoint]
