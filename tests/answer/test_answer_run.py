"""M4-01 应用准备入口：固定 R3 配置、快照前提与运行元数据。"""

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from casetrace.answer.context import (
    DEFAULT_TOP_K,
    DEV_V3_SNAPSHOT,
    RETRIEVAL_METHOD,
    prepare_answer_run,
)
from casetrace.evaluation.benchmark import load_benchmark
from casetrace.evaluation.runner import build_retriever

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEV_V3_DATASET = PROJECT_ROOT / "data/dev/demo-v3.json"
REFERENCE_FILE = PROJECT_ROOT / "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"
SNAPSHOT_KNOWN_AT = date(2026, 9, 15)


def _run(answer_dataset, reference_path, make_snapshot, *, query, dataset_path=None,
         snapshot=None, **kwargs):
    """用自造语料跑准备入口；默认时点与快照都来自夹具。"""

    default_dataset, _ = answer_dataset
    dataset_path = default_dataset if dataset_path is None else dataset_path
    return prepare_answer_run(
        query, kwargs.pop("known_at", SNAPSHOT_KNOWN_AT),
        dataset_path=dataset_path, reference_path=reference_path,
        snapshot=make_snapshot(dataset_path) if snapshot is None else snapshot, **kwargs,
    )


def test_prepare_answer_run_uses_fixed_r3_configuration(
    answer_dataset, reference_path, make_snapshot, answer_query,
):
    run = _run(answer_dataset, reference_path, make_snapshot, query=answer_query)
    description = run.run_metadata["retrieval"]["description"]
    assert run.run_metadata["retrieval"]["requested_method"] == RETRIEVAL_METHOD
    assert run.run_metadata["retrieval"]["top_k"] == DEFAULT_TOP_K
    assert description["method"] == "bm25_filtered_query_terms"
    assert description["query_filter"]["drop_negation_clauses"] is True
    assert description["query_filter"]["drop_label_terms"] is True
    assert run.inputs.hits


def test_prepare_answer_run_keeps_query_text_and_ranking_order(
    answer_dataset, reference_path, make_snapshot, answer_query,
):
    run = _run(answer_dataset, reference_path, make_snapshot, query=answer_query)
    assert run.inputs.query == answer_query
    assert "已排除" in run.inputs.query and "DEV_PL_1" in run.inputs.query
    ranking = run.run_metadata["ranking"]
    assert [item["rank"] for item in ranking] == list(range(1, len(ranking) + 1))
    assert [item["case_id"] for item in ranking] == [hit.case_id for hit in run.inputs.hits]
    # R3 在计分时删掉的标识/标签词，不应作为命中词项出现。
    matched = {term for item in ranking for term in item["matched_terms"] or []}
    assert not matched & {"涉及", "产品", "客户", "dev_pl_1"}


def test_prepare_answer_run_records_snapshot_and_draft_status(
    answer_dataset, reference_path, make_snapshot, answer_query,
):
    dataset_path, _ = answer_dataset
    run = _run(answer_dataset, reference_path, make_snapshot, query=answer_query)
    snapshot = run.run_metadata["snapshot"]
    assert snapshot["snapshot_id"] == "test-snapshot"
    assert snapshot["dataset_sha256"] == hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    assert snapshot["reference_sha256"] == hashlib.sha256(reference_path.read_bytes()).hexdigest()
    assert run.run_metadata["corpus"]["review_status"] == "draft_pending_human_review"
    assert run.run_metadata["corpus"]["source_cases_are_draft"] is True
    assert "judgments" not in json.dumps(run.run_metadata, ensure_ascii=False)


def test_prepare_answer_run_rejects_known_at_outside_snapshot(
    answer_dataset, reference_path, make_snapshot, answer_query,
):
    with pytest.raises(ValueError, match="不被当前记录的可用性快照支持"):
        _run(answer_dataset, reference_path, make_snapshot, query=answer_query,
             known_at=date(2026, 9, 16))


def test_prepare_answer_run_rejects_corpus_without_recorded_hash(
    answer_dataset, reference_path, make_snapshot, answer_query,
):
    dataset_path, _ = answer_dataset
    with pytest.raises(ValueError, match="记录的语料不一致"):
        _run(answer_dataset, reference_path, make_snapshot, query=answer_query,
             snapshot=make_snapshot(dataset_path, dataset_sha256="0" * 64))


def test_prepare_answer_run_rejects_reference_without_recorded_hash(
    answer_dataset, reference_path, make_snapshot, answer_query,
):
    dataset_path, _ = answer_dataset
    with pytest.raises(ValueError, match="主数据.*记录的文件不一致"):
        _run(answer_dataset, reference_path, make_snapshot, query=answer_query,
             snapshot=make_snapshot(dataset_path, reference_sha256="0" * 64))


def test_prepare_answer_run_rejects_case_detected_after_snapshot(
    answer_dataset, reference_path, make_snapshot, answer_query, tmp_path,
):
    _, payload = answer_dataset
    payload["details"][0]["detection_time"] = date(2026, 9, 16).isoformat()
    late = tmp_path / "late.json"
    late.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="时点一致性"):
        _run(answer_dataset, reference_path, make_snapshot, query=answer_query,
             dataset_path=late, snapshot=make_snapshot(late))


def test_prepare_answer_run_does_not_accept_retrieval_method_override(
    answer_dataset, reference_path, make_snapshot, answer_query,
):
    with pytest.raises(TypeError, match="unexpected keyword argument 'method'"):
        _run(answer_dataset, reference_path, make_snapshot, query=answer_query,
             method="bm25")


@pytest.mark.parametrize("top_k", [0, -1, 2.5, True, "4"])
def test_prepare_answer_run_rejects_invalid_top_k(
    answer_dataset, reference_path, make_snapshot, answer_query, top_k,
):
    with pytest.raises(ValueError, match="top_k"):
        _run(answer_dataset, reference_path, make_snapshot, query=answer_query, top_k=top_k)


def _dev_v3_query(index=4):
    payload = json.loads(DEV_V3_DATASET.read_text(encoding="utf-8"))
    query = payload["queries"][index]
    return query["text"], date.fromisoformat(query["known_at"])


def test_qrels_free_entry_matches_benchmark_entry():
    """无 qrels 的准备入口必须给出与评估入口完全相同的排名与分数。"""

    query_text, known_at = _dev_v3_query()
    run = prepare_answer_run(
        query_text, known_at, dataset_path=DEV_V3_DATASET, reference_path=REFERENCE_FILE,
    )
    benchmark = load_benchmark(PROJECT_ROOT / "data/evaluation/dev-v3/qrels.json")
    expected = build_retriever(benchmark, method=RETRIEVAL_METHOD).search(query_text, top_k=4)
    assert [hit.case_id for hit in run.inputs.hits] == [hit.case_id for hit in expected]
    assert [hit.score for hit in run.inputs.hits] == [hit.score for hit in expected]
    assert run.run_metadata["snapshot"]["snapshot_id"] == DEV_V3_SNAPSHOT.snapshot_id
    assert run.run_metadata["corpus"]["case_count"] == len(benchmark.records["cases"])
    assert run.inputs.hits


def test_recorded_dev_v3_snapshot_keeps_query_text():
    query_text, known_at = _dev_v3_query()
    run = prepare_answer_run(
        query_text, known_at, dataset_path=DEV_V3_DATASET, reference_path=REFERENCE_FILE,
    )
    assert run.inputs.query == query_text
    assert "排除" in run.inputs.query
    assert run.run_metadata["ranking"][0]["rank"] == 1
