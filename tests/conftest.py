"""演示集成测试使用最小人工主数据，不依赖真实 Excel 或 Locked Test。"""

from datetime import date
import json

from openpyxl import Workbook
import pytest


@pytest.fixture
def reference_path(tmp_path):
    tables = {
        "products": [("product_id", "product_name", "package_route"), ("P1", "演示产品", "LF_WB")],
        "failure_modes": [
            ("failure_mode_id", "failure_mode", "applicable_package", "possible_root_causes", "corrective_actions"),
            ("00001", "wire lift", "LF_WB", "表面污染; 参数异常", "改善清洁; 优化参数"),
        ],
        "customer_product_map": [("product_id", "customer_id"), ("P1", "CUS1")],
        "customers": [("customer_id",), ("CUS1",)],
        "package_routes": [("package_route",), ("LF_WB",)],
        "process_master": [
            ("process_id", "process"), ("P004", "Wire Bond"), ("P007", "Molding"),
            ("P013", "Storage & Transportation"),
        ],
        "package_process_map": [
            ("package_route", "process_id", "process"),
            ("LF_WB", "P004", "Wire Bond"), ("LF_WB", "P007", "Molding"),
            ("LF_WB", "P013", "Storage & Transportation"),
        ],
    }
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in tables.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
    path = tmp_path / "reference.xlsx"
    workbook.save(path)
    workbook.close()
    return path


@pytest.fixture
def demo_path(tmp_path):
    payload = dict(cases=[], details=[], evidences=[], groups=[], memberships=[], sources={},
                   queries=[{"text": "焊线脱落"}])
    for number in [1, 2]:
        case_id = f"C{number}"
        payload["cases"].append(dict(
            case_id=case_id, abnormal_description="焊线脱落", root_cause="表面污染",
            corrective_action="改善清洁", investigation_others=None,
            abnormal_processes=["P004"],
        ))
        payload["details"].append(dict(
            detail_id=f"D{number}", case_id=case_id, product_id="P1", customer_lot="CL1",
            production_lot="PL1", production_time=date(2026, 6, 1).isoformat(),
            detection_stage="OQC", detection_time=date(2026, 6, number + 1).isoformat(),
            abnormal_types=["00001"], affected_qty=100, disposition="报废",
        ))
        payload["evidences"].append(dict(
            checkpoint_id=f"E{number}", case_id=case_id, checkpoint_type="QC", custom_name=None,
            result="观察到表面污染", relevance="related",
        ))
        payload["sources"][case_id] = dict(
            failure_mode_id="00001", root_cause="表面污染", corrective_action="改善清洁",
            closure_status="confirmed",
        )
    path = tmp_path / "demo.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path
