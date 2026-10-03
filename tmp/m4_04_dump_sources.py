"""M4-04 审阅辅助：打印 dev-v3 各 Case 的原文摘要，供逐条核对回答的事实支持。

只读；不修改语料、qrels 或任何产物。
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
payload = json.loads((ROOT / "data/dev/demo-v3.json").read_text(encoding="utf-8"))

DETAIL_KEYS = ("detail_id", "product_id", "production_lot", "customer_lot",
               "detection_stage", "abnormal_types", "affected_qty", "disposition")

for case in payload["cases"]:
    case_id = case["case_id"]
    print(f"=== {case_id} ===")
    print("  desc      :", case["abnormal_description"])
    print("  root_cause:", case["root_cause"])
    print("  action    :", case["corrective_action"])
    print("  others    :", case["investigation_others"])
    print("  processes :", case["abnormal_processes"])
    for detail in payload["details"]:
        if detail["case_id"] == case_id:
            print("  detail    :", {key: detail[key] for key in DETAIL_KEYS})
    for evidence in payload["evidences"]:
        if evidence["case_id"] == case_id:
            print(f"  ev {evidence['checkpoint_id']} [{evidence['relevance']}]: {evidence['result']}")
    print("  source    :", payload["sources"][case_id])
