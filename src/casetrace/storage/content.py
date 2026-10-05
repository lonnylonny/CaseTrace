"""快照的规范化内容、表/列映射与带版本的内容摘要。

用途：导入前算一次摘要写进 ``snapshot_metadata.content_digest``，读回时用同一套
规范化规则重算并核对，防止「只存旧文件哈希、掩盖数据库内容变化」。

摘要输入是**规范化内容**：

- 日期统一转 ISO 文本，字典键排序，列表保留语义顺序；
- 实体列表（Case/Detail/Evidence/Group/Membership）保留源文件顺序；
- 主数据表按自然键排序后入摘要——现有消费方都按 key 查表，行顺序无语义；
- 不含摘要自身、摘要算法版本、导入时间、文件路径与数据库连接信息。

本模块只处理数据结构，不连接数据库、不读文件。
"""

from __future__ import annotations

import hashlib
import json
from datetime import date

CONTENT_DIGEST_VERSION = "content-digest-v2"

# v1 → v2：`ordering` 增补 `failure_mode_routes` 的源顺序，用于把
# `failure_modes.applicable_package` 这个 Excel 冗余字符串按原顺序重建；
# 摘要输入形状变了就必须升版本，旧库会被显式拒绝而不是静默沿用。
#
# `ordering` 的键（与实体/关系表同名，读回时据此恢复顺序）：
#   cases / case_details / evidence_checkpoints / case_groups：键列表
#   case_group_memberships：[[group_id, case_id], ...]
#   case_abnormal_processes / detail_failure_modes / failure_mode_routes：
#     {父键: [子键, ...]}

# 五类实体对应的 payload 键（源文件里的名字）。
ENTITY_PAYLOAD_KEYS = ("cases", "details", "evidences", "groups", "memberships")

# 实体表：列表顺序来自源文件，靠 snapshot_metadata.ordering 恢复。
ENTITY_TABLES = (
    "cases", "case_abnormal_processes", "case_details", "detail_failure_modes",
    "evidence_checkpoints", "case_groups", "case_group_memberships",
)

# 主数据表：来自 Excel，摘要内按自然键排序。
REFERENCE_TABLES = (
    "customers", "product_families", "package_routes", "products",
    "processes", "package_process_map", "failure_modes", "failure_mode_routes",
)

# 写入顺序：先主数据，再 Case 及其关系，最后快照元数据（满足外键依赖）。
IMPORT_ORDER = (
    "customers", "product_families", "package_routes", "products",
    "processes", "package_process_map", "failure_modes", "failure_mode_routes",
    "cases", "case_abnormal_processes", "case_details", "detail_failure_modes",
    "evidence_checkpoints", "case_groups", "case_group_memberships",
)

# 每张表的读写列，与 sql/schema.sql 对应。
INSERT_COLUMNS = {
    "customers": ("customer_id", "customer_name"),
    "product_families": ("product_family_id", "product_family"),
    "package_routes": ("package_route", "carrier", "die_interconnect", "external_terminal", "description"),
    "products": ("product_id", "product_name", "product_family_id", "package_route",
                 "product_function", "customer_id"),
    "processes": ("process_id", "process", "process_category", "description"),
    "package_process_map": ("package_route", "process_id", "sequence_no",
                            "relation_type", "process_scope", "notes"),
    "failure_modes": ("failure_mode_id", "failure_mode", "applicable_process", "possible_root_causes",
                      "failure_effects", "detection_methods", "screening_methods",
                      "corrective_actions", "notes"),
    "failure_mode_routes": ("failure_mode_id", "package_route"),
    "cases": ("case_id", "abnormal_description", "root_cause", "corrective_action",
              "investigation_others"),
    "case_abnormal_processes": ("case_id", "process_id"),
    "case_details": ("detail_id", "case_id", "product_id", "customer_lot", "production_lot",
                     "production_time", "detection_stage", "detection_time", "affected_qty",
                     "disposition"),
    "detail_failure_modes": ("detail_id", "failure_mode_id"),
    "evidence_checkpoints": ("checkpoint_id", "case_id", "checkpoint_type", "custom_name",
                             "result", "relevance"),
    "case_groups": ("group_id", "group_type", "description", "other_type_description"),
    "case_group_memberships": ("group_id", "case_id", "association_reason"),
}


def normalize(value):
    """把内容转成确定性可比较的形式：date → ISO，dict/list 递归，拒绝未知类型。"""

    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"无法纳入内容摘要的值：{type(value).__name__}")


def canonical_json(content: dict) -> str:
    """规范化 JSON 文本：`sort_keys` 让字典键稳定，列表顺序按传入顺序保留。"""

    return json.dumps(normalize(content), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_digest(content: dict) -> str:
    """对规范化内容取 SHA-256；同一内容在任何机器上得到同一摘要。"""

    return hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


def build_content(
    *, snapshot_fields: dict, reference: dict, entities: dict,
    payload: dict, ordering: dict,
) -> dict:
    """装配完整内容；固定表映射同时用于导入和读回。"""
    return {
        "snapshot": snapshot_fields,
        "reference": {table: reference[table] for table in REFERENCE_TABLES},
        "entities": {table: entities[table] for table in ENTITY_TABLES},
        "payload": payload,
        "ordering": ordering,
    }
