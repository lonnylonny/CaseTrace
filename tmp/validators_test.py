from dataclasses import replace
from datetime import date

from casetrace.data.dataset_model import CaseDetail
from casetrace.data.validators import validate_detail_fields


detail = CaseDetail(
    detail_id="D001",
    case_id="C001",
    product_id="P001",
    customer_lot="CL001",
    production_lot="PL001",
    production_time=date(2026, 9, 1),
    detection_stage="OQC",
    detection_time=date(2026, 9, 2),
    abnormal_types=["001"],
    affected_qty=100,
    disposition="全部报废",
)

# 1. 必填文本都有内容。
assert validate_detail_fields(
    detail,
    location="CaseDetail[D001]",
) == []

# 2. 两个字段同时不合法，应收集两条错误。
invalid_detail = replace(
    detail,
    customer_lot="   ",
    disposition=None,
)

errors = validate_detail_fields(
    invalid_detail,
    location="CaseDetail[D001]",
)

assert errors == [
    "CR-07 | CaseDetail[D001] | customer_lot | 必须是非空字符串",
    "CR-27 | CaseDetail[D001] | disposition | 必须是非空字符串",
]

# 3. ID 为空时，用调用方提供的位置定位。
errors = validate_detail_fields(
    replace(detail, detail_id=""),
    location="CaseDetail[0]",
)

assert errors == [
    "结构 §2、§5 | CaseDetail[0] | detail_id | 必须是非空字符串",
]

print("CaseDetail 必填文本检查通过")
