from openpyxl import load_workbook
import pytest

from casetrace.data.reference import load_reference


def test_reads_maps_and_preserves_leading_zeros(reference_path):
    reference = load_reference(reference_path)
    assert reference.product_customers == {"P1": "CUS1"}
    assert reference.validator_maps()["failure_mode_routes"] == {"00001": {"LF_WB"}}


@pytest.mark.parametrize("sheet,row,message", [
    ("customer_product_map", ("P1", "CUS1"), "重复"),
    ("products", ("P2", "另一个产品", "LF_WB"), "覆盖全部"),
    ("products", (2, "数字 ID", "LF_WB"), "非空文本"),
    ("failure_modes", ("00002", "unknown", "UNKNOWN", "原因", "措施"), "未知路线"),
])
def test_rejects_invalid_reference_rows(reference_path, sheet, row, message):
    workbook = load_workbook(reference_path)
    workbook[sheet].append(row)
    workbook.save(reference_path)
    workbook.close()
    with pytest.raises(ValueError, match=message):
        load_reference(reference_path)
