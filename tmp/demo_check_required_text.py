"""演示：只用 check_required_text 这一个已实现的函数。

临时脚本，不属于项目代码，不修改任何项目文件。
运行：cd /home/lonny/Projects/casetrace && .venv/bin/python /tmp/demo_check_required_text.py
"""

from datetime import date

from casetrace.data.dataset_model import CaseDetail
from casetrace.data.validators import check_required_text

# =============================================================================
# 1. 最小形态：直接把值给尺子
# =============================================================================
errors: list[str] = []
errors.extend(check_required_text("A123", field="customer_lot", location="CaseDetail D001", rule="CR-07"))
errors.extend(check_required_text("   ", field="production_lot", location="CaseDetail D001", rule="CR-06"))
print("1 最小形态:", errors)

# =============================================================================
# 2. 真实形态：值从 dataclass 字段取，location 由调用方渲染
# =============================================================================
detail = CaseDetail(
    detail_id="D001",
    case_id="C001",
    product_id="P001",
    customer_lot="A123",          # 合法
    production_lot="",            # 空串  -> CR-06
    production_time=date(2025, 3, 1),
    detection_stage="OQC",
    detection_time=date(2025, 3, 5),
    abnormal_types=["FM-012"],
    affected_qty=120,
    disposition=None,             # None -> CR-27
)

location = f"CaseDetail {detail.detail_id}"

errors = []
errors.extend(check_required_text(detail.customer_lot, field="customer_lot", location=location, rule="CR-07"))
errors.extend(check_required_text(detail.production_lot, field="production_lot", location=location, rule="CR-06"))
errors.extend(check_required_text(detail.disposition, field="disposition", location=location, rule="CR-27"))

print("2 真实形态:")
for line in errors:
    print("   ", line)

# =============================================================================
# 3. 无有效 ID 时，location 退化成列表下标（渲染责任在调用方）
# =============================================================================
unknown = CaseDetail(
    detail_id="",                 # 没有有效 ID
    case_id="C002",
    product_id="P001",
    customer_lot="   ",           # 纯空白 -> CR-07
    production_lot="PL-2025-002",
    production_time=date(2025, 1, 1),
    detection_stage="IQC",
    detection_time=date(2025, 1, 2),
    abnormal_types=["FM-001"],
    affected_qty=1,
    disposition="hold",
)

index = 0
location = (
    f"CaseDetail {unknown.detail_id}"
    if isinstance(unknown.detail_id, str) and unknown.detail_id.strip()
    else f"CaseDetail[{index}]"
)
print("3 无有效 ID :", check_required_text(unknown.customer_lot, field="customer_lot", location=location, rule="CR-07"))
