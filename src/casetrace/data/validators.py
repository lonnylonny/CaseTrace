# define case structure constraints
# 实现清单：docs/data/CaseTrace_Validator_Implementation_Plan.md

from casetrace.data.dataset_model import CaseDetail, EvidenceCheckpoint, Case, CaseGroup, Membership
from datetime import date

# part1 字段和对象的内部检查

def check_required_text(
    value: object,
    *,
    field: str,
    location: str,
    rule: str,
) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return [
            f"{rule} | {location} | {field} | 必须是非空字符串"
        ]

    return []

'''
 传入值事例：errors = check_required_text(
    "abc",                       # 1 个位置值：待检查的值
    field="customer_lot",        # 3 个关键字值
    location="CaseDetail D001",
    rule="Rule CR-07",
)
'''

def validate_detail_fields(
    detail: CaseDetail,
    *,
    location: str,
) -> list[str]:
    """当前仅检查必填文本；空错误列表不代表全部 Detail 规则通过。"""
    errors: list[str] = []

    required_fields = {
        "detail_id": "结构 §2、§5",
        "case_id": "结构 §2、§5",
        "product_id": "CR-05",
        "customer_lot": "CR-07",
        "production_lot": "CR-06",
        "detection_stage": "结构 §2",
        "disposition": "CR-27",
    }

    for field, rule in required_fields.items():
        value = getattr(detail, field)

        errors.extend(
            check_required_text(
                value,
                field=field,
                location=location,
                rule=rule,
            )
        )

    return errors
