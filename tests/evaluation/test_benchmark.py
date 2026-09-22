"""校验评估输入的读取与拒绝行为；只扰动临时副本，不改动仓库中已确认的数据。"""

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from casetrace.evaluation.benchmark import PROJECT_ROOT, load_benchmark

DATASET_RELATIVE = "data/dev/demo.json"
REFERENCE_RELATIVE = "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"
QRELS_RELATIVE = "data/evaluation/dev-v2/qrels.json"
INPUT_FILES = (DATASET_RELATIVE, REFERENCE_RELATIVE, QRELS_RELATIVE)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture
def benchmark_inputs(tmp_path):
    """按原字节复制已确认数据到临时项目目录，供本文件扰动。"""
    root = tmp_path / "project"
    for relative in INPUT_FILES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / relative, target)
    return root


def _dataset(root: Path) -> dict:
    return json.loads((root / DATASET_RELATIVE).read_text(encoding="utf-8"))


def _qrels(root: Path) -> dict:
    return json.loads((root / QRELS_RELATIVE).read_text(encoding="utf-8"))


def _save_qrels(root: Path, qrels: dict) -> None:
    _write(root / QRELS_RELATIVE, qrels)


def _save_dataset(root: Path, qrels: dict, dataset: dict) -> None:
    """写入改动后的语料，并同步记录新哈希，模拟“换了数据版本”。"""
    _write(root / DATASET_RELATIVE, dataset)
    qrels["sources"]["dataset"]["sha256"] = _sha256(root / DATASET_RELATIVE)
    _save_qrels(root, qrels)


def _load(root: Path):
    return load_benchmark(root / QRELS_RELATIVE, base_dir=root)


def test_confirmed_dev_v2_benchmark_is_accepted():
    benchmark = load_benchmark(PROJECT_ROOT / QRELS_RELATIVE)

    assert benchmark.base_dir == PROJECT_ROOT
    assert benchmark.qrels_version == "dev-qrels-v2"
    assert benchmark.split == "development"
    assert benchmark.confirmed_on == "2026-09-19"
    assert benchmark.qrels_sha256 == _sha256(PROJECT_ROOT / QRELS_RELATIVE)
    assert benchmark.dataset.recorded_path == DATASET_RELATIVE
    assert benchmark.dataset.path == PROJECT_ROOT / DATASET_RELATIVE
    assert benchmark.reference_file.recorded_path == REFERENCE_RELATIVE
    assert benchmark.case_ids == [f"C00{number}" for number in range(1, 7)]
    assert [query.query_id for query in benchmark.queries] == ["Q001", "Q002", "Q003"]
    assert {query.known_at.isoformat() for query in benchmark.queries} == {"2026-09-15"}
    assert sum(len(labels) for labels in benchmark.judgments.values()) == 18
    assert [len(benchmark.relevant_case_ids(query_id))
            for query_id in ("Q001", "Q002", "Q003")] == [4, 1, 1]
    assert benchmark.relevant_case_ids("Q001") == {"C001", "C002", "C003", "C004"}
    # 快照约定：语料在所有 Query 时点前已完整可用，且不声称实现了通用时间过滤。
    assert benchmark.latest_detection <= min(query.known_at for query in benchmark.queries)
    # 标签确认与源 Case 的审阅状态分开记录，源 Case 仍是 draft 不阻止评估。
    assert benchmark.dataset_review_status == "draft_pending_human_review"


def test_relative_source_paths_resolve_against_base_dir(benchmark_inputs):
    root = benchmark_inputs

    benchmark = _load(root)

    assert benchmark.base_dir == root
    assert benchmark.dataset.path == root / DATASET_RELATIVE
    assert benchmark.reference_file.path == root / REFERENCE_RELATIVE
    assert benchmark.dataset.sha256 == _sha256(root / DATASET_RELATIVE)


def test_successful_load_does_not_modify_inputs(benchmark_inputs):
    root = benchmark_inputs
    before = {relative: _sha256(root / relative) for relative in INPUT_FILES}

    _load(root)

    assert {relative: _sha256(root / relative) for relative in INPUT_FILES} == before


def test_source_hash_mismatch_reports_file_expected_and_actual(benchmark_inputs):
    root = benchmark_inputs
    dataset_path = root / DATASET_RELATIVE
    recorded = _qrels(root)["sources"]["dataset"]["sha256"]
    dataset_path.write_bytes(dataset_path.read_bytes() + b"\n")
    actual = _sha256(dataset_path)

    with pytest.raises(ValueError) as error:
        _load(root)

    message = str(error.value)
    assert str(dataset_path) in message
    assert recorded in message and actual in message
    assert "不能直接刷新哈希" in message
    # 失败后源文件与记录都保持原样，不自动刷新哈希。
    assert _sha256(dataset_path) == actual
    assert _qrels(root)["sources"]["dataset"]["sha256"] == recorded


def test_absent_source_file_is_reported(benchmark_inputs):
    root = benchmark_inputs
    qrels = _qrels(root)
    qrels["sources"]["dataset"]["path"] = "data/dev/missing.json"
    _save_qrels(root, qrels)

    with pytest.raises(ValueError, match=r"sources\.dataset \| 文件不存在"):
        _load(root)


@pytest.mark.parametrize(("field", "value"), [
    ("qrels_version", "dev-qrels-v1"),
    ("split", "locked_test"),
])
def test_qrels_version_and_split_must_match(benchmark_inputs, field, value):
    root = benchmark_inputs
    qrels = _qrels(root)
    qrels[field] = value
    _save_qrels(root, qrels)

    with pytest.raises(ValueError, match=rf"qrels \| {field} \| 期望 "):
        _load(root)


@pytest.mark.parametrize("status", ["draft_pending_human_review", "agent_confirmed", None])
def test_unconfirmed_qrels_are_rejected(benchmark_inputs, status):
    root = benchmark_inputs
    qrels = _qrels(root)
    qrels["review_status"] = status
    _save_qrels(root, qrels)

    with pytest.raises(ValueError, match=r"review_status \| 正式评估要求 human_confirmed"):
        _load(root)


def test_dataset_split_must_be_development(benchmark_inputs):
    root = benchmark_inputs
    dataset = _dataset(root)
    dataset["split"] = "locked_test"
    _save_dataset(root, _qrels(root), dataset)

    with pytest.raises(ValueError, match=r"Dataset \| split \| 期望 development"):
        _load(root)


@pytest.mark.parametrize(("mutation", "pattern"), [
    ("duplicate_query_id", r"CR-03 \| Dataset \| queries\[1\] \| query_id 'Q001' 重复"),
    ("missing_known_at", r"Dataset \| Query\[Q001\] \| known_at"),
    ("empty_text", r"Dataset \| Query\[Q001\] \| text"),
])
def test_invalid_query_records_are_rejected(benchmark_inputs, mutation, pattern):
    root = benchmark_inputs
    dataset = _dataset(root)
    if mutation == "duplicate_query_id":
        dataset["queries"][1]["query_id"] = "Q001"
    elif mutation == "missing_known_at":
        del dataset["queries"][0]["known_at"]
    else:
        dataset["queries"][0]["text"] = "   "
    _save_dataset(root, _qrels(root), dataset)

    with pytest.raises(ValueError, match=pattern):
        _load(root)


def test_corpus_after_the_query_timepoint_is_rejected(benchmark_inputs):
    root = benchmark_inputs
    dataset = _dataset(root)
    dataset["details"][0]["detection_time"] = "2026-09-16"
    _save_dataset(root, _qrels(root), dataset)

    with pytest.raises(ValueError) as error:
        _load(root)

    message = str(error.value)
    assert "时点一致性" in message and "2026-09-16" in message
    assert "不实现通用时间过滤" in message


@pytest.mark.parametrize(("field", "value"), [("query_id", "Q004"), ("case_id", "C007")])
def test_judgment_with_unknown_id_is_rejected(benchmark_inputs, field, value):
    root = benchmark_inputs
    qrels = _qrels(root)
    qrels["judgments"][0][field] = value
    _save_qrels(root, qrels)

    with pytest.raises(ValueError, match=rf"judgments\[0\] \| {field} '{value}' \| 不在本次语料的范围内"):
        _load(root)


def test_duplicate_judgment_pair_is_rejected(benchmark_inputs):
    root = benchmark_inputs
    qrels = _qrels(root)
    qrels["judgments"].append(dict(qrels["judgments"][0]))
    _save_qrels(root, qrels)

    with pytest.raises(ValueError, match=r"CR-03 \| qrels \| \(Q001, C001\) \| 配对重复"):
        _load(root)


@pytest.mark.parametrize("relevance", [2, -1, "1", "Ambiguous", None, True, 1.0])
def test_labels_must_be_integer_zero_or_one(benchmark_inputs, relevance):
    root = benchmark_inputs
    qrels = _qrels(root)
    qrels["judgments"][0]["relevance"] = relevance
    _save_qrels(root, qrels)

    with pytest.raises(ValueError, match=r"\(Q001, C001\) \| relevance \| 必须是整数 0 或 1"):
        _load(root)


def test_removed_label_is_reported_as_a_missing_pair(benchmark_inputs):
    root = benchmark_inputs
    qrels = _qrels(root)
    qrels["judgments"] = [row for row in qrels["judgments"]
                          if (row["query_id"], row["case_id"]) != ("Q002", "C004")]
    _save_qrels(root, qrels)

    with pytest.raises(ValueError, match=r"缺少 1 个配对：\(Q002, C004\)"):
        _load(root)


def test_judgment_without_rationale_is_rejected(benchmark_inputs):
    root = benchmark_inputs
    qrels = _qrels(root)
    qrels["judgments"][3]["rationale"] = ""
    _save_qrels(root, qrels)

    with pytest.raises(ValueError, match=r"\(Q001, C004\) \| rationale"):
        _load(root)
