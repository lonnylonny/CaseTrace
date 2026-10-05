"""SD1：Schema 初始化入口的纯函数检查。

集成检查（真实 PostgreSQL）在文件下半部分，需要 CASETRACE_TEST_DATABASE_URL。
"""

from __future__ import annotations

from datetime import date

import psycopg
import pytest

from casetrace.storage.connection import resolve_database_url
from casetrace.storage.schema import (
    AUXILIARY_TABLES,
    DEFAULT_SCHEMA,
    FROZEN_TABLES,
    SCHEMA_VERSION,
    schema_version,
    check_schema_name,
    initialize_schema,
    list_tables,
)


@pytest.mark.parametrize("name", ["casetrace", "casetrace_test", "_x", "a", "a" * 63])
def test_check_schema_name_accepts_valid_names(name):
    assert check_schema_name(name) == name


@pytest.mark.parametrize(
    "name",
    ["", "Casetrace", "1abc", "a-b", "a b", "a;DROP SCHEMA public", "a" * 64, None, 5],
)
def test_check_schema_name_rejects_invalid_names(name):
    with pytest.raises(ValueError):
        check_schema_name(name)


def test_default_schema_name_is_valid():
    assert check_schema_name(DEFAULT_SCHEMA) == DEFAULT_SCHEMA


SEED_MAIN_DATA = """
INSERT INTO package_routes (package_route, carrier, die_interconnect, external_terminal, description)
    VALUES ('LF_WB', 'leadframe', 'wire_bond', 'leadframe_terminal', '路线背景');
INSERT INTO product_families (product_family_id, product_family) VALUES ('PF_001', 'Power Management');
INSERT INTO customers (customer_id, customer_name) VALUES ('CUS_001', 'SYN_AX');
INSERT INTO products (product_id, product_name, product_family_id, package_route, product_function, customer_id)
    VALUES ('PROD_001', 'SYN_PWR_A', 'PF_001', 'LF_WB', 'Power regulation', 'CUS_001');
INSERT INTO processes (process_id, process, process_category, description)
    VALUES ('P004', 'Wire Bond', 'core', '打线');
INSERT INTO package_process_map (package_route, process_id, sequence_no, relation_type, process_scope, notes)
    VALUES ('LF_WB', 'P004', 40, 'core', 'package_manufacturing', NULL);
INSERT INTO failure_modes (failure_mode_id, failure_mode, applicable_process, possible_root_causes, corrective_actions)
    VALUES ('00010', 'wire bond lift', ARRAY['Wire Bond'], '污染', '改善清洁');
INSERT INTO failure_mode_routes (failure_mode_id, package_route) VALUES ('00010', 'LF_WB');
INSERT INTO cases (case_id, abnormal_description, root_cause, corrective_action)
    VALUES ('C001', '焊线脱落', '结案确认：污染', '加强清洁');
INSERT INTO case_abnormal_processes (case_id, process_id) VALUES ('C001', 'P004');
"""

DETAIL_KEYS = (
    "detail_id", "case_id", "product_id", "customer_lot", "production_lot",
    "production_time", "detection_stage", "detection_time", "affected_qty", "disposition",
)
DETAIL_SQL = """
INSERT INTO case_details (detail_id, case_id, product_id, customer_lot, production_lot,
                          production_time, detection_stage, detection_time, affected_qty, disposition)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


@pytest.fixture
def initialized(storage_connection, scratch_schema):
    """初始化一个独占 schema，并铺好本次检查需要的最小主数据与一个 Case。"""

    initialize_schema(storage_connection, schema=scratch_schema)
    storage_connection.execute(SEED_MAIN_DATA)
    return storage_connection, scratch_schema


def _detail_values(**overrides):
    values = {
        "detail_id": "D001", "case_id": "C001", "product_id": "PROD_001",
        "customer_lot": "CL1", "production_lot": "PL1",
        "production_time": date(2026, 6, 1), "detection_stage": "OQC",
        "detection_time": date(2026, 6, 3), "affected_qty": 100, "disposition": "报废",
    }
    values.update(overrides)
    return values


def _insert_detail(connection, **overrides):
    values = _detail_values(**overrides)
    connection.execute(DETAIL_SQL, tuple(values[key] for key in DETAIL_KEYS))


def test_initialize_creates_frozen_tables_and_records_version(initialized):
    connection, schema = initialized
    assert list_tables(connection, schema=schema) == sorted((*FROZEN_TABLES, *AUXILIARY_TABLES))
    assert schema_version(connection, schema=schema) == SCHEMA_VERSION


def test_initialize_is_idempotent_and_preserves_data(initialized):
    connection, schema = initialized
    connection.execute(
        "INSERT INTO customers (customer_id, customer_name) VALUES (%s, %s)",
        ("CUS_KEEP", "保留客户"),
    )
    result = initialize_schema(connection, schema=schema)
    assert result["version"] == SCHEMA_VERSION
    assert list_tables(connection, schema=schema) == sorted((*FROZEN_TABLES, *AUXILIARY_TABLES))
    kept = connection.execute(
        "SELECT customer_name FROM customers WHERE customer_id = %s", ("CUS_KEEP",)
    ).fetchone()
    assert kept == ("保留客户",)
    version_rows = connection.execute("SELECT count(*) FROM schema_version").fetchone()
    assert version_rows == (1,)


def test_unknown_future_schema_version_is_rejected(initialized):
    connection, schema = initialized
    connection.execute(
        "INSERT INTO schema_version (version, description) VALUES ('999', '未来版本')"
    )
    with pytest.raises(RuntimeError) as error:
        initialize_schema(connection, schema=schema)
    assert "999" in str(error.value)


def test_required_indexes_exist(initialized):
    connection, schema = initialized
    names = {
        row[0]
        for row in connection.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = %s", (schema,)
        )
    }
    assert {
        "case_details_case_id_idx", "case_details_product_id_idx",
        "evidence_checkpoints_case_id_idx", "case_group_memberships_case_id_idx",
    } <= names


@pytest.mark.parametrize("key", ["CASETRACE_DATABASE_URL", "CASETRACE_TEST_DATABASE_URL"])
def test_resolve_database_url_reads_injected_env(key):
    env = {key: "postgresql://user:pw@127.0.0.1:5432/db"}
    assert resolve_database_url(test=key.endswith("_TEST_DATABASE_URL"), env=env) == (
        "postgresql://user:pw@127.0.0.1:5432/db"
    )


@pytest.mark.parametrize("value", [None, "", "   "])
def test_resolve_database_url_rejects_missing_value(value):
    env = {"CASETRACE_DATABASE_URL": value}
    with pytest.raises(RuntimeError) as error:
        resolve_database_url(env=env)
    assert "CASETRACE_DATABASE_URL" in str(error.value)


def test_blank_or_null_required_case_text_is_rejected(initialized):
    connection, _ = initialized
    statement = (
        "INSERT INTO cases (case_id, abnormal_description, root_cause, corrective_action) "
        "VALUES (%s, %s, %s, %s)"
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        connection.execute(statement, ("C900", "   ", "原因", "措施"))
    with pytest.raises(psycopg.errors.NotNullViolation):
        connection.execute(statement, ("C901", "描述", None, "措施"))


def test_detection_time_before_production_is_rejected(initialized):
    connection, _ = initialized
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert_detail(
            connection, detection_time=date(2026, 5, 31),
        )


def test_detection_time_equal_to_production_is_allowed(initialized):
    connection, _ = initialized
    _insert_detail(connection, detection_time=date(2026, 6, 1))
    stored = connection.execute(
        "SELECT production_time, detection_time FROM case_details WHERE detail_id = %s",
        ("D001",),
    ).fetchone()
    assert stored == (date(2026, 6, 1), date(2026, 6, 1))


@pytest.mark.parametrize("quantity", [0, -5])
def test_non_positive_affected_qty_is_rejected(initialized, quantity):
    connection, _ = initialized
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert_detail(connection, affected_qty=quantity)


@pytest.mark.parametrize("stage", ["FA", "iqc", "", "Other "])
def test_invalid_detection_stage_is_rejected(initialized, stage):
    connection, _ = initialized
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert_detail(connection, detection_stage=stage)


def test_unknown_references_are_rejected(initialized):
    connection, _ = initialized
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert_detail(connection, case_id="C404")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert_detail(connection, product_id="PROD_404")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        connection.execute(
            "INSERT INTO detail_failure_modes (detail_id, failure_mode_id) VALUES (%s, %s)",
            ("D404", "00010"),
        )


def test_duplicate_primary_key_and_duplicate_relation_are_rejected(initialized):
    connection, _ = initialized
    with pytest.raises(psycopg.errors.UniqueViolation):
        connection.execute(
            "INSERT INTO cases (case_id, abnormal_description, root_cause, corrective_action) "
            "VALUES (%s, %s, %s, %s)",
            ("C001", "重复主键", "原因", "措施"),
        )
    with pytest.raises(psycopg.errors.UniqueViolation):
        connection.execute(
            "INSERT INTO case_abnormal_processes (case_id, process_id) VALUES (%s, %s)",
            ("C001", "P004"),
        )


@pytest.mark.parametrize("relevance", ["RELATED", "maybe", ""])
def test_invalid_relevance_is_rejected(initialized, relevance):
    connection, _ = initialized
    with pytest.raises(psycopg.errors.CheckViolation):
        connection.execute(
            "INSERT INTO evidence_checkpoints "
            "(checkpoint_id, case_id, checkpoint_type, custom_name, result, relevance) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            ("E900", "C001", "QC", None, "结果", relevance),
        )


def test_other_checkpoint_requires_custom_name(initialized):
    connection, _ = initialized
    statement = (
        "INSERT INTO evidence_checkpoints "
        "(checkpoint_id, case_id, checkpoint_type, custom_name, result, relevance) "
        "VALUES (%s, %s, %s, %s, %s, %s)"
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        connection.execute(statement, ("E901", "C001", "Other", None, "结果", "related"))
    with pytest.raises(psycopg.errors.CheckViolation):
        connection.execute(statement, ("E902", "C001", "Other", "  ", "结果", "related"))
    connection.execute(statement, ("E903", "C001", "Other", "自定检查", "结果", "related"))


def test_group_type_and_other_description_constraints(initialized):
    connection, _ = initialized
    statement = (
        "INSERT INTO case_groups (group_id, group_type, description, other_type_description) "
        "VALUES (%s, %s, %s, %s)"
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        connection.execute(statement, ("G900", ["unknown_type"], "说明", None))
    with pytest.raises(psycopg.errors.CheckViolation):
        connection.execute(statement, ("G901", [], "说明", None))
    with pytest.raises(psycopg.errors.CheckViolation):
        connection.execute(statement, ("G902", ["other"], "说明", None))
    connection.execute(statement, ("G903", ["repeat_case"], "说明", None))
    connection.execute(statement, ("G904", ["other"], "说明", "客户指定的专项分组"))


def test_text_identity_roundtrip_preserves_leading_zeros_and_arrays(initialized):
    connection, _ = initialized
    mode = connection.execute(
        "SELECT failure_mode_id, applicable_process FROM failure_modes "
        "WHERE failure_mode_id = %s",
        ("00010",),
    ).fetchone()
    assert mode == ("00010", ["Wire Bond"])
    connection.execute(
        "INSERT INTO failure_modes (failure_mode_id, failure_mode) VALUES (%s, %s)",
        ("0002", "die crack"),
    )
    stored = connection.execute(
        "SELECT failure_mode_id FROM failure_modes WHERE failure_mode_id = %s", ("0002",)
    ).fetchone()
    assert stored == ("0002",)


def test_initialize_accepts_existing_m5_01_version_markers(initialized):
    """兼容简化前已有的 001/002 标记，保留已有客户数据。"""
    connection, schema = initialized
    connection.execute("INSERT INTO schema_version (version, description) VALUES ('001', '旧建表标记')")
    initialize_schema(connection, schema=schema)
    assert schema_version(connection, schema=schema) == SCHEMA_VERSION
    assert connection.execute("SELECT customer_name FROM customers WHERE customer_id = 'CUS_001'").fetchone() == ("SYN_AX",)


def test_products_require_known_customer(initialized):
    connection, _ = initialized
    statement = (
        "INSERT INTO products "
        "(product_id, product_name, product_family_id, package_route, customer_id) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    with pytest.raises(psycopg.errors.NotNullViolation):
        connection.execute(statement, ("PROD_X", "X", "PF_001", "LF_WB", None))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        connection.execute(statement, ("PROD_Y", "Y", "PF_001", "LF_WB", "CUS_404"))
