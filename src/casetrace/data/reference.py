"""读取当前演示需要的主数据子集；完整 BOM／工序导入校验留待实际需要时补齐。"""

from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook


@dataclass
class ReferenceData:
    products: dict[str, dict[str, str]]
    failure_modes: dict[str, dict[str, str]]
    product_customers: dict[str, str]

    def validator_maps(self) -> dict:
        """从同一份主数据构造现有 Validator 的三个输入映射。"""
        return {
            "product_customers": self.product_customers,
            "product_routes": {key: row["package_route"] for key, row in self.products.items()},
            "failure_mode_routes": {
                key: {route.strip() for route in row["applicable_package"].split(";")}
                for key, row in self.failure_modes.items()
            },
        }


def _read_table(workbook, name: str, key: str, columns: tuple[str, ...]) -> dict:
    """建字典前拒绝重复 ID；不把数字 ID 转成字符串来掩盖前导零丢失。"""
    if name not in workbook.sheetnames:
        raise ValueError(f"主数据缺少 Sheet：{name}")
    rows = workbook[name].iter_rows(values_only=True)
    headers = next(rows, ())
    if any(headers.count(column) != 1 for column in columns):
        raise ValueError(f"{name} 缺少必需列或列名重复：{columns}")
    positions = {column: headers.index(column) for column in columns}
    records = {}
    for number, values in enumerate(rows, start=2):
        if all(value is None for value in values):
            continue
        row = {column: values[position] for column, position in positions.items()}
        if any(not isinstance(value, str) or not value.strip() for value in row.values()):
            raise ValueError(f"{name} 第 {number} 行：必需字段须为非空文本，ID 须保留前导零")
        if row[key] in records:
            raise ValueError(f"{name} 第 {number} 行：{key}={row[key]} 重复")
        records[row[key]] = row
    if not records:
        raise ValueError(f"主数据表 {name} 不能为空")
    return records


def load_reference(path: Path) -> ReferenceData:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        products = _read_table(workbook, "products", "product_id",
                               ("product_id", "product_name", "package_route"))
        modes = _read_table(workbook, "failure_modes", "failure_mode_id",
                           ("failure_mode_id", "failure_mode", "applicable_package",
                            "possible_root_causes", "corrective_actions"))
        assignments = _read_table(workbook, "customer_product_map", "product_id",
                                 ("product_id", "customer_id"))
        customers = _read_table(workbook, "customers", "customer_id", ("customer_id",))
        routes = _read_table(workbook, "package_routes", "package_route", ("package_route",))
    finally:
        workbook.close()

    product_customers = {key: row["customer_id"] for key, row in assignments.items()}
    if products.keys() != product_customers.keys() or set(product_customers.values()) != set(customers):
        raise ValueError("客户归属必须覆盖全部产品及客户，且引用有效")
    reference = ReferenceData(products, modes, product_customers)
    maps = reference.validator_maps()
    used_routes = set(maps["product_routes"].values())
    for applicable in maps["failure_mode_routes"].values():
        used_routes.update(applicable)
    if not used_routes <= routes.keys():
        raise ValueError("产品或 Failure Mode 引用了未知路线")
    return reference
