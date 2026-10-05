"""SD2：单快照原子导入的成功、重复 no-op、冲突拒绝与失败回滚。

需要真实 PostgreSQL（CASETRACE_TEST_DATABASE_URL）；每个用例独占一个 schema。
源文件是已记录的 dev-v3 快照，测试不修改它们。
"""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import threading

import psycopg
import pytest
from psycopg import sql

from casetrace.answer.context import DEV_V3_SNAPSHOT
from casetrace.storage import snapshot as snapshot_module
from casetrace.storage.connection import resolve_database_url
from casetrace.storage.content import CONTENT_DIGEST_VERSION, IMPORT_ORDER
from casetrace.storage.schema import initialize_schema
from casetrace.storage.snapshot import import_snapshot

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "data/dev/demo-v3.json"
REFERENCE = PROJECT_ROOT / (
    "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"
)

# dev-v3 已记录快照的观察结果：主数据来自 Excel，实体来自 demo-v3.json。
EXPECTED_COUNTS = {
    "customers": 5, "product_families": 7, "package_routes": 3, "products": 18,
    "processes": 15, "package_process_map": 36, "failure_modes": 37,
    "failure_mode_routes": 74, "cases": 9, "case_abnormal_processes": 9,
    "case_details": 9, "detail_failure_modes": 9, "evidence_checkpoints": 9,
    "case_groups": 1, "case_group_memberships": 3,
}


def table_counts(connection, schema: str) -> dict[str, int]:
    return {
        table: connection.execute(
            sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(schema, table))
        ).fetchone()[0]
        for table in IMPORT_ORDER
    }


def import_into(connection, schema: str):
    return import_snapshot(
        connection, DATASET, REFERENCE, snapshot=DEV_V3_SNAPSHOT, schema=schema,
    )


@pytest.fixture
def imported(storage_connection, scratch_schema):
    """初始化并完成一次真实导入；返回连接、schema 名与导入结果。"""

    initialize_schema(storage_connection, schema=scratch_schema)
    result = import_into(storage_connection, scratch_schema)
    return storage_connection, scratch_schema, result


def test_import_requires_initialized_schema(storage_connection, scratch_schema):
    with pytest.raises(ValueError) as error:
        import_into(storage_connection, scratch_schema)
    assert "init" in str(error.value)


def test_import_stores_full_snapshot_and_reports_counts(imported):
    connection, schema, result = imported

    assert result.status == "imported"
    assert result.snapshot_id == DEV_V3_SNAPSHOT.snapshot_id
    assert result.counts == EXPECTED_COUNTS
    assert table_counts(connection, schema) == EXPECTED_COUNTS

    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    for key, table in (("cases", "cases"), ("details", "case_details"),
                       ("evidences", "evidence_checkpoints"), ("groups", "case_groups"),
                       ("memberships", "case_group_memberships")):
        assert result.counts[table] == len(payload[key]), key

    row = connection.execute(
        sql.SQL(
            "SELECT snapshot_id, known_at, dataset_sha256, reference_sha256, split, "
            "review_status, digest_version, payload, ordering FROM {}"
        ).format(sql.Identifier(schema, "snapshot_metadata"))
    ).fetchone()
    snapshot_id, known_at, dataset_sha256, reference_sha256, split, review_status, digest_version, extra, ordering = row
    assert snapshot_id == DEV_V3_SNAPSHOT.snapshot_id
    assert known_at == DEV_V3_SNAPSHOT.known_at
    assert dataset_sha256 == DEV_V3_SNAPSHOT.dataset_sha256
    assert reference_sha256 == DEV_V3_SNAPSHOT.reference_sha256
    assert split == payload["split"] and review_status == payload["review_status"]
    assert digest_version == CONTENT_DIGEST_VERSION
    # 非实体 payload 原样保留；实体仍与 Case 分离，qrels 不进入数据库。
    assert extra["sources"]["C001"]["failure_mode_id"] == "00010"
    assert extra["queries"] == payload["queries"]
    assert extra["case_families"] == payload["case_families"]
    assert set(extra) & {"cases", "details", "evidences", "groups", "memberships"} == set()
    # 源列表顺序可恢复。
    assert ordering["cases"] == [case["case_id"] for case in payload["cases"]]
    assert ordering["detail_failure_modes"] == {
        detail["detail_id"]: detail["abnormal_types"] for detail in payload["details"]
    }


def test_repeat_import_is_explicit_no_op(imported):
    connection, schema, first = imported
    before = table_counts(connection, schema)

    second = import_into(connection, schema)

    assert second.status == "no_op"
    assert second.content_digest == first.content_digest
    assert second.counts == before
    assert table_counts(connection, schema) == before
    stored = connection.execute(
        sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(schema, "snapshot_metadata"))
    ).fetchone()
    assert stored == (1,)


def test_import_rejects_missing_or_changed_source_file(storage_connection, scratch_schema, tmp_path):
    connection, schema = storage_connection, scratch_schema
    initialize_schema(connection, schema=schema)

    with pytest.raises(ValueError) as missing:
        import_snapshot(connection, tmp_path / "不存在.json", REFERENCE,
                        snapshot=DEV_V3_SNAPSHOT, schema=schema)
    assert "源文件不存在" in str(missing.value)

    changed = tmp_path / "demo-v3.json"
    changed.write_bytes(DATASET.read_bytes() + b"\n")
    with pytest.raises(ValueError) as wrong:
        import_snapshot(connection, changed, REFERENCE,
                        snapshot=DEV_V3_SNAPSHOT, schema=schema)
    assert "语料文件与已记录快照不一致" in str(wrong.value)

    other_reference = tmp_path / "reference.xlsx"
    other_reference.write_bytes(REFERENCE.read_bytes() + b"0")
    with pytest.raises(ValueError) as wrong_reference:
        import_snapshot(connection, DATASET, other_reference,
                        snapshot=DEV_V3_SNAPSHOT, schema=schema)
    assert "主数据文件与已记录快照不一致" in str(wrong_reference.value)

    assert sum(table_counts(connection, schema).values()) == 0


def test_import_refuses_unregistered_business_data(storage_connection, scratch_schema):
    connection, schema = storage_connection, scratch_schema
    initialize_schema(connection, schema=schema)
    connection.execute(
        sql.SQL("INSERT INTO {} (customer_id, customer_name) VALUES (%s, %s)").format(
            sql.Identifier(schema, "customers")),
        ("CUS_X", "手工客户"),
    )

    with pytest.raises(ValueError) as error:
        import_into(connection, schema)
    assert "已有业务数据" in str(error.value)

    counts = table_counts(connection, schema)
    assert counts["customers"] == 1
    assert sum(counts.values()) == 1


@pytest.mark.parametrize("damage", ["missing_row", "extra_row", "version_conflict", "changed_field"])
def test_import_refuses_conflicting_database_and_keeps_it(imported, damage):
    connection, schema, _ = imported
    payload = json.loads(DATASET.read_text(encoding="utf-8"))

    if damage == "missing_row":
        connection.execute(
            sql.SQL("DELETE FROM {} WHERE checkpoint_id = %s").format(
                sql.Identifier(schema, "evidence_checkpoints")),
            (payload["evidences"][0]["checkpoint_id"],),
        )
    elif damage == "extra_row":
        connection.execute(
            sql.SQL(
                "INSERT INTO {} (case_id, abnormal_description, root_cause, corrective_action) "
                "VALUES (%s, %s, %s, %s)"
            ).format(sql.Identifier(schema, "cases")),
            ("C999", "手工新增", "原因", "措施"),
        )
    elif damage == "version_conflict":
        connection.execute(
            sql.SQL("UPDATE {} SET snapshot_id = %s").format(
                sql.Identifier(schema, "snapshot_metadata")),
            ("other-snapshot",),
        )
    else:
        connection.execute(
            sql.SQL("UPDATE {} SET root_cause = %s WHERE case_id = %s").format(
                sql.Identifier(schema, "cases")),
            ("被手工改写的原因", "C001"),
        )

    damaged = table_counts(connection, schema)
    with pytest.raises(ValueError) as error:
        import_into(connection, schema)
    assert "拒绝并保留原库" in str(error.value)
    # 原库保留：既不补回缺失行，也不重复写入，也不修复被改的版本。
    assert table_counts(connection, schema) == damaged
    if damage == "changed_field":
        assert connection.execute(
            sql.SQL("SELECT root_cause FROM {} WHERE case_id = 'C001'").format(
                sql.Identifier(schema, "cases")),
        ).fetchone() == ("被手工改写的原因",)


@pytest.mark.parametrize("failure", ["relations", "generation", "sources"])
def test_invalid_dataset_is_rejected_without_writes(storage_connection, scratch_schema, tmp_path, failure):
    """身份合法但业务数据错误时，CR/GR/来源校验仍各自生效。"""
    connection, schema = storage_connection, scratch_schema
    initialize_schema(connection, schema=schema)
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    if failure == "relations":
        payload["details"][0]["affected_qty"] = 0
    elif failure == "generation":
        for detail in payload["details"]:
            detail["production_lot"] = f"UNIQUE_{detail['detail_id']}"
    else:
        payload["sources"]["C001"]["root_cause"] = "不存在的来源候选"
    dataset = tmp_path / "invalid.json"
    dataset.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    snapshot = SimpleNamespace(
        snapshot_id="invalid-test", known_at=DEV_V3_SNAPSHOT.known_at,
        dataset_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),
        reference_sha256=DEV_V3_SNAPSHOT.reference_sha256, basis="仅用于失败回滚测试",
    )
    with pytest.raises(ValueError):
        import_snapshot(connection, dataset, REFERENCE, snapshot=snapshot, schema=schema)
    assert sum(table_counts(connection, schema).values()) == 0
    assert connection.execute(
        sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(schema, "snapshot_metadata")),
    ).fetchone() == (0,)


def test_midway_failure_rolls_back_everything(storage_connection, scratch_schema, monkeypatch):
    """模拟写入中途的 SQL 失败：整个事务回滚，空库不留下任何已提交业务数据。

    Python 校验已覆盖数据库的基础约束，正常数据很难触发真实的中途 SQL 错误，
    因此这里注入一个 psycopg 错误，仍然走真实的 executemany 与事务路径。
    """

    connection, schema = storage_connection, scratch_schema
    initialize_schema(connection, schema=schema)
    original = snapshot_module._insert_rows

    def failing(conn, name, table, rows):
        if table == "case_details":
            raise psycopg.errors.ProgrammingError("模拟导入中途的 SQL 失败")
        return original(conn, name, table, rows)

    monkeypatch.setattr(snapshot_module, "_insert_rows", failing)

    with pytest.raises(psycopg.Error):
        import_into(connection, schema)

    assert sum(table_counts(connection, schema).values()) == 0
    stored = connection.execute(
        sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(schema, "snapshot_metadata"))
    ).fetchone()
    assert stored == (0,)


def test_concurrent_imports_are_serialized(storage_connection, scratch_schema):
    """两个连接同时导入：元数据表锁串行化，后到者返回 no_op。"""

    initialize_schema(storage_connection, schema=scratch_schema)
    url = resolve_database_url(test=True)
    statuses: list[str] = []
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            with psycopg.connect(url, connect_timeout=5) as connection:
                connection.autocommit = True
                statuses.append(import_into(connection, scratch_schema).status)
        except BaseException as error:  # noqa: BLE001 - 测试要如实报告线程内异常
            errors.append(error)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert errors == []
    assert sorted(statuses) == ["imported", "no_op"]
    assert table_counts(storage_connection, scratch_schema) == EXPECTED_COUNTS


def test_import_accepts_legal_snapshot_without_groups(storage_connection, scratch_schema, tmp_path):
    """没有 CaseGroup 的合法样例同样能导入：groups/memberships 为空表。"""

    connection, schema = storage_connection, scratch_schema
    initialize_schema(connection, schema=schema)
    payload = {
        "split": "development",
        "review_status": "draft_pending_human_review",
        "cases": [{
            "case_id": "C901", "abnormal_description": "焊线脱落",
            "root_cause": "结案确认：die pad或lead/substrate bond finger污染/氧化。",
            "corrective_action": "加强wafer pad和载体bond finger来料/清洁管控。",
            "investigation_others": None, "abnormal_processes": ["P004"],
        }, {
            "case_id": "C902", "abnormal_description": "在线拉力测试焊点剥离",
            "root_cause": "结案确认：die pad或lead/substrate bond finger污染/氧化。",
            "corrective_action": "加强wafer pad和载体bond finger来料/清洁管控。",
            "investigation_others": None, "abnormal_processes": ["P004"],
        }],
        # GR-04 要求存在 1～2 个复用批号：两条 Detail 共用同一生产批（属性一致）。
        "details": [{
            "detail_id": "D901", "case_id": "C901", "product_id": "PROD_001",
            "customer_lot": "SYN_CL_901", "production_lot": "SYN_PL_901",
            "production_time": "2026-06-01", "detection_stage": "OQC",
            "detection_time": "2026-06-03", "abnormal_types": ["00010"],
            "affected_qty": 30, "disposition": "纳入处置范围的产品隔离。",
        }, {
            "detail_id": "D902", "case_id": "C902", "product_id": "PROD_001",
            "customer_lot": "SYN_CL_901", "production_lot": "SYN_PL_901",
            "production_time": "2026-06-01", "detection_stage": "In-process",
            "detection_time": "2026-06-05", "abnormal_types": ["00010"],
            "affected_qty": 40, "disposition": "纳入处置范围的产品隔离。",
        }],
        "evidences": [{
            "checkpoint_id": "E901", "case_id": "C901", "checkpoint_type": "QC",
            "custom_name": None, "result": "观察到焊点剥离", "relevance": "related",
        }, {
            "checkpoint_id": "E902", "case_id": "C902", "checkpoint_type": "QC",
            "custom_name": None, "result": "观察到焊点剥离", "relevance": "related",
        }],
        "groups": [], "memberships": [],
        "sources": {
            "C901": {
                "sheet": "failure_modes", "failure_mode_id": "00010",
                "root_cause": "die pad或lead/substrate bond finger污染/氧化",
                "corrective_action": "加强wafer pad和载体bond finger来料/清洁管控",
                "closure_status": "confirmed",
            },
            "C902": {
                "sheet": "failure_modes", "failure_mode_id": "00010",
                "root_cause": "die pad或lead/substrate bond finger污染/氧化",
                "corrective_action": "加强wafer pad和载体bond finger来料/清洁管控",
                "closure_status": "confirmed",
            },
        },
        "queries": [{"query_id": "Q901", "known_at": "2026-09-15", "text": "焊线脱落"}],
    }
    dataset = tmp_path / "nogroup.json"
    dataset.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    snapshot = SimpleNamespace(
        snapshot_id="synthetic-nogroup",
        known_at=date(2026, 9, 15),
        dataset_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),
        reference_sha256=DEV_V3_SNAPSHOT.reference_sha256,
        basis="测试样例：合法但无 CaseGroup",
    )
    result = import_snapshot(connection, dataset, REFERENCE, snapshot=snapshot, schema=schema)

    assert result.status == "imported"
    assert result.counts["cases"] == 2
    assert result.counts["case_groups"] == 0
    assert result.counts["case_group_memberships"] == 0
    assert table_counts(connection, schema)["case_details"] == 2

