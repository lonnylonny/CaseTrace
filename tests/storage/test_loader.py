"""SD3：完整读回、顺序恢复与内容身份核对。

需要真实 PostgreSQL（CASETRACE_TEST_DATABASE_URL）；每个用例独占一个 schema。
"""

from __future__ import annotations

from datetime import date
from dataclasses import replace
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from psycopg import sql

from casetrace.answer.context import DEV_V3_SNAPSHOT
from casetrace.demo import build_documents, load_validated_dataset
from casetrace.storage.__main__ import main
from casetrace.storage.content import CONTENT_DIGEST_VERSION, IMPORT_ORDER
from casetrace.storage import load_snapshot, verify_snapshot
from casetrace.storage.schema import initialize_schema
from casetrace.storage.snapshot import import_snapshot

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "data/dev/demo-v3.json"
REFERENCE = PROJECT_ROOT / (
    "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"
)


@lru_cache(maxsize=1)
def file_objects():
    """文件侧的五类实体、payload 与主数据；只读，用于与库内读回对比。"""

    return load_validated_dataset(DATASET, REFERENCE)


@pytest.fixture
def imported(storage_connection, scratch_schema):
    """真实导入 dev-v3 快照；返回连接、schema 名与导入结果。"""

    initialize_schema(storage_connection, schema=scratch_schema)
    result = import_snapshot(
        storage_connection, DATASET, REFERENCE, snapshot=DEV_V3_SNAPSHOT, schema=scratch_schema,
    )
    return storage_connection, scratch_schema, result


def _set_ordering_jsonb(connection, schema, path: str, value) -> None:
    connection.execute(
        sql.SQL("UPDATE {} SET ordering = jsonb_set(ordering, %s, %s::jsonb)").format(
            sql.Identifier(schema, "snapshot_metadata")),
        (path, json.dumps(value, ensure_ascii=False)),
    )


def test_load_snapshot_round_trips_everything(imported):
    connection, schema, result = imported
    file_records, file_payload, file_reference = file_objects()

    loaded = load_snapshot(connection, schema=schema)

    # 五类实体逐字段等价：dataclass 相等同时覆盖列表顺序与两个无序集合的顺序。
    assert loaded.records == file_records
    assert loaded.payload == file_payload
    assert loaded.reference == file_reference
    assert loaded.snapshot.content_digest == result.content_digest
    assert loaded.snapshot.digest_version == CONTENT_DIGEST_VERSION
    assert loaded.snapshot.snapshot_id == DEV_V3_SNAPSHOT.snapshot_id
    assert loaded.snapshot.known_at == DEV_V3_SNAPSHOT.known_at
    assert loaded.snapshot.dataset_sha256 == DEV_V3_SNAPSHOT.dataset_sha256
    assert loaded.snapshot.reference_sha256 == DEV_V3_SNAPSHOT.reference_sha256
    assert loaded.counts == result.counts
    assert set(loaded.counts) == set(IMPORT_ORDER)
    # 检索文档逐 Case 逐字相同（读回路径不改变文档拼接）。
    assert build_documents(loaded.records, loaded.reference) == build_documents(
        file_records, file_reference
    )


def test_load_snapshot_keeps_source_order_not_id_sort(storage_connection, scratch_schema, tmp_path):
    """实体与关系列表顺序不等于 ID 排序时，读回仍按源顺序还原。"""

    connection, schema = storage_connection, scratch_schema
    initialize_schema(connection, schema=schema)
    payload = {
        "split": "development",
        "review_status": "draft_pending_human_review",
        "cases": [
            {"case_id": "C902", "abnormal_description": "在线拉力测试焊点剥离",
             "root_cause": "结案确认：die pad或lead/substrate bond finger污染/氧化。",
             "corrective_action": "加强wafer pad和载体bond finger来料/清洁管控。",
             "investigation_others": None, "abnormal_processes": ["P007", "P004"]},
            {"case_id": "C901", "abnormal_description": "焊线脱落",
             "root_cause": "结案确认：die pad或lead/substrate bond finger污染/氧化。",
             "corrective_action": "加强wafer pad和载体bond finger来料/清洁管控。",
             "investigation_others": None, "abnormal_processes": ["P004"]},
        ],
        "details": [
            {"detail_id": "D902", "case_id": "C902", "product_id": "PROD_001",
             "customer_lot": "SYN_CL_902", "production_lot": "SYN_PL_902",
             "production_time": "2026-06-01", "detection_stage": "OQC",
             "detection_time": "2026-06-05", "abnormal_types": ["00010", "00001"],
             "affected_qty": 40, "disposition": "纳入处置范围的产品隔离。"},
            {"detail_id": "D901", "case_id": "C901", "product_id": "PROD_001",
             "customer_lot": "SYN_CL_902", "production_lot": "SYN_PL_902",
             "production_time": "2026-06-01", "detection_stage": "In-process",
             "detection_time": "2026-06-03", "abnormal_types": ["00001", "00010"],
             "affected_qty": 30, "disposition": "纳入处置范围的产品隔离。"},
        ],
        "evidences": [
            {"checkpoint_id": "E902", "case_id": "C902", "checkpoint_type": "QC",
             "custom_name": None, "result": "观察到焊点剥离", "relevance": "related"},
            {"checkpoint_id": "E901", "case_id": "C901", "checkpoint_type": "QC",
             "custom_name": None, "result": "观察到焊点剥离", "relevance": "related"},
        ],
        "groups": [], "memberships": [],
        "sources": {
            "C902": {"sheet": "failure_modes", "failure_mode_id": "00010",
                     "root_cause": "die pad或lead/substrate bond finger污染/氧化",
                     "corrective_action": "加强wafer pad和载体bond finger来料/清洁管控",
                     "closure_status": "confirmed"},
            "C901": {"sheet": "failure_modes", "failure_mode_id": "00010",
                     "root_cause": "die pad或lead/substrate bond finger污染/氧化",
                     "corrective_action": "加强wafer pad和载体bond finger来料/清洁管控",
                     "closure_status": "confirmed"},
        },
        "queries": [{"query_id": "Q901", "known_at": "2026-09-15", "text": "焊线脱落"}],
    }
    dataset = tmp_path / "ordered.json"
    dataset.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    snapshot = SimpleNamespace(
        snapshot_id="synthetic-order", known_at=date(2026, 9, 15),
        dataset_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),
        reference_sha256=DEV_V3_SNAPSHOT.reference_sha256,
        basis="测试样例：列表顺序不等于 ID 排序",
    )
    import_snapshot(connection, dataset, REFERENCE, snapshot=snapshot, schema=schema)

    loaded = load_snapshot(connection, schema=schema)
    file_records, _, _ = load_validated_dataset(dataset, REFERENCE)

    assert [case.case_id for case in loaded.records["cases"]] == ["C902", "C901"]
    assert [item.detail_id for item in loaded.records["details"]] == ["D902", "D901"]
    assert [item.checkpoint_id for item in loaded.records["evidences"]] == ["E902", "E901"]
    assert loaded.records["cases"][0].abnormal_processes == ["P007", "P004"]
    assert loaded.records["details"][0].abnormal_types == ["00010", "00001"]
    assert loaded.records == file_records
    assert build_documents(loaded.records, loaded.reference) == build_documents(
        file_records, loaded.reference
    )


def test_load_snapshot_detects_tampered_entity_field(imported):
    connection, schema, _ = imported
    connection.execute(
        sql.SQL("UPDATE {} SET root_cause = %s WHERE case_id = %s").format(
            sql.Identifier(schema, "cases")),
        ("被人为改写的原因", "C001"),
    )
    with pytest.raises(ValueError) as error:
        load_snapshot(connection, schema=schema)
    assert "内容摘要不一致" in str(error.value)


def test_load_snapshot_detects_tampered_source_metadata(imported):
    connection, schema, _ = imported
    connection.execute(
        sql.SQL("UPDATE {} SET payload = jsonb_set(payload, %s, %s::jsonb)").format(
            sql.Identifier(schema, "snapshot_metadata")),
        ("{sources,C001,failure_mode_id}", '"00001"'),
    )
    with pytest.raises(ValueError) as error:
        load_snapshot(connection, schema=schema)
    assert "内容摘要不一致" in str(error.value)


def test_load_snapshot_detects_tampered_ordering(imported):
    connection, schema, _ = imported
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    reversed_ids = [case["case_id"] for case in reversed(payload["cases"])]
    _set_ordering_jsonb(connection, schema, "{cases}", reversed_ids)

    with pytest.raises(ValueError) as error:
        load_snapshot(connection, schema=schema)
    assert "内容摘要不一致" in str(error.value)


def test_load_snapshot_requires_recorded_snapshot(storage_connection, scratch_schema):
    initialize_schema(storage_connection, schema=scratch_schema)
    with pytest.raises(ValueError) as error:
        load_snapshot(storage_connection, schema=scratch_schema)
    assert "没有已记录的快照" in str(error.value)


def test_load_snapshot_rejects_other_digest_version(imported):
    connection, schema, _ = imported
    connection.execute(
        sql.SQL("UPDATE {} SET digest_version = %s").format(
            sql.Identifier(schema, "snapshot_metadata")),
        ("content-digest-v99",),
    )
    with pytest.raises(ValueError) as error:
        load_snapshot(connection, schema=schema)
    assert "摘要版本" in str(error.value)


def test_verify_snapshot_reports_all_checks(imported):
    connection, schema, result = imported
    report = verify_snapshot(
        connection, dataset_path=DATASET, reference_path=REFERENCE,
        snapshot=DEV_V3_SNAPSHOT, schema=schema,
    )

    assert report.ok is True
    assert report.problems == []
    assert report.checks == {
        "file_identity": True, "snapshot_identity": True, "content": True,
    }
    assert report.content_digest == result.content_digest
    assert report.digest_version == CONTENT_DIGEST_VERSION
    assert report.counts == result.counts


def test_verify_rejects_different_availability_with_same_snapshot_id(imported):
    connection, schema, _ = imported
    requested = replace(DEV_V3_SNAPSHOT, known_at=date(2026, 9, 16))
    report = verify_snapshot(
        connection, dataset_path=DATASET, reference_path=REFERENCE,
        snapshot=requested, schema=schema,
    )
    assert report.ok is False
    assert report.checks["snapshot_identity"] is False


def test_verify_snapshot_detects_changed_source_file(imported, tmp_path):
    connection, schema, _ = imported
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    payload["details"][0]["affected_qty"] = 999
    changed = tmp_path / "demo-v3-changed.json"
    changed.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    report = verify_snapshot(
        connection, dataset_path=changed, reference_path=REFERENCE, schema=schema,
    )

    assert report.ok is False
    assert report.checks["file_identity"] is False
    assert "content" not in report.checks  # 身份不符时无需继续解析错误的文件。
    assert any("源文件哈希" in problem for problem in report.problems)


def test_verify_command_succeeds_on_recorded_snapshot(imported, capsys):
    _, schema, _ = imported
    exit_code = main(["verify", "--test", "--schema", schema])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "content-digest-v2" in output
    assert "通过  content" in output
    assert "数据库完整内容与源文件一致" in output
