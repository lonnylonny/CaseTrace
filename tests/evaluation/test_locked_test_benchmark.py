"""Locked Test 评估接缝：版本/split 显式配对、合成快照校验与报告一致性。

全部输入来自 tests/conftest.py 的独立合成夹具；本文件不读写真实 Locked Test 数据，
也不生成真实排名或成绩。
"""

import json

import pytest

from casetrace.evaluation import runner
from casetrace.evaluation.benchmark import PROJECT_ROOT, load_benchmark
from casetrace.evaluation.runner import run_evaluation
from casetrace.retrieval.base import SearchHit

DEV_QRELS_RELATIVE = "data/evaluation/dev-v2/qrels.json"


class StubRetriever:
    """替身检索器：只提供公共契约行为，用来验证报告接线，不调用真实模型。"""

    def __init__(self, documents):
        self.case_ids = sorted(documents)

    def search(self, query, *, top_k):
        return [
            SearchHit(case_id, 1.0 / rank)
            for rank, case_id in enumerate(self.case_ids, start=1)
        ][:top_k]

    def describe(self):
        return {"method": "stub", "model": "stub-model", "model_revision": "stub-rev"}


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _resave_corpus(layout, corpus, qrels=None):
    """改写语料后同步刷新 qrels 记录的哈希，避免把哈希错误当成目标错误。"""
    layout.write_corpus(corpus)
    layout.write_qrels(qrels)
    return layout


def _run(layout, monkeypatch, *, method="bm25"):
    monkeypatch.setitem(runner.RETRIEVER_FACTORIES, method, StubRetriever)
    return run_evaluation(layout.qrels_path, base_dir=layout.root, method=method)


def test_locked_test_benchmark_is_accepted(locked_test_layout):
    benchmark = load_benchmark(locked_test_layout.qrels_path, base_dir=locked_test_layout.root)

    assert benchmark.qrels_version == "locked-test-qrels-v1"
    assert benchmark.split == "locked_test"
    assert benchmark.confirmed_on == "2026-10-08"
    assert benchmark.case_ids == ["SC001", "SC002"]
    assert benchmark.relevant_case_ids("LQ001") == {"SC001"}
    assert benchmark.latest_detection.isoformat() == "2026-06-04"
    assert benchmark.availability_snapshot == {
        "snapshot_id": "locked-test-v1-2026-08-31",
        "complete_available_on": "2026-08-31",
        "basis": "测试夹具：人为合成快照约定，不代表真实结案时间。",
    }


def test_locked_test_report_carries_its_own_snapshot(locked_test_layout, monkeypatch):
    report = _run(locked_test_layout, monkeypatch)

    recorded = report["benchmark"]
    assert recorded["split"] == "locked_test"
    assert recorded["qrels_version"] == "locked-test-qrels-v1"
    assert recorded["availability_snapshot"]["snapshot_id"] == "locked-test-v1-2026-08-31"
    assert recorded["availability_snapshot"]["complete_available_on"] == "2026-08-31"
    assert recorded["history_snapshot"] == runner.LOCKED_TEST_HISTORY_SNAPSHOT
    assert report["summary"]["query_count"] == 1


def test_development_report_keeps_its_original_snapshot_wording(monkeypatch):
    """新数据不得让旧 Development 报告改口：仍用原约定文字，且不带新快照字段。"""
    monkeypatch.setitem(runner.RETRIEVER_FACTORIES, "stub", StubRetriever)
    report = run_evaluation(PROJECT_ROOT / DEV_QRELS_RELATIVE, method="stub")

    recorded = report["benchmark"]
    assert recorded["split"] == "development"
    assert "availability_snapshot" not in recorded
    assert recorded["history_snapshot"] == runner.HISTORY_SNAPSHOT


def test_without_a_positive_case_the_exclusion_policy_is_unchanged(
    locked_test_layout, monkeypatch,
):
    qrels = _read(locked_test_layout.qrels_path)
    for row in qrels["judgments"]:
        row["relevance"] = 0
    locked_test_layout.write_qrels(qrels)

    report = _run(locked_test_layout, monkeypatch)

    assert report["summary"]["no_relevant_query_ids"] == ["LQ001"]
    assert report["summary"]["metrics"]["recall@4"]["value"] is None
    assert report["summary"]["metrics"]["ndcg@4"]["value"] is None
    assert report["summary"]["metrics"]["mrr@4"]["value"] is None
    # Precision 按既有口径为 0.0 并参与均值，不因新 split 改变。
    assert report["summary"]["metrics"]["precision@4"]["value"] == 0.0


@pytest.mark.parametrize(("mutation", "pattern"), [
    ("missing_snapshot", r"Dataset \| availability_snapshot \| Locked Test 必须提供可用性快照对象"),
    ("unregistered_snapshot_id", r"availability_snapshot\.snapshot_id \| 期望已登记"),
    ("bad_complete_date", r"availability_snapshot\.complete_available_on \| 必须是 YYYY-MM-DD"),
    ("empty_basis", r"availability_snapshot\.basis \| 必须写明这是人为合成快照约定"),
    ("detection_after_available_on", r"CaseDetail\[SD002\] \| detection_time .* 晚于完整可用日"),
    ("known_at_before_available_on", r"Query\[LQ001\] \| known_at .* 必须晚于完整可用日"),
])
def test_locked_test_snapshot_must_be_well_formed(locked_test_layout, mutation, pattern):
    corpus = _read(locked_test_layout.corpus_path)
    if mutation == "missing_snapshot":
        del corpus["availability_snapshot"]
    elif mutation == "unregistered_snapshot_id":
        corpus["availability_snapshot"]["snapshot_id"] = "locked-test-v2-2099-12-31"
    elif mutation == "bad_complete_date":
        corpus["availability_snapshot"]["complete_available_on"] = "2026/08/31"
    elif mutation == "empty_basis":
        corpus["availability_snapshot"]["basis"] = "   "
    elif mutation == "detection_after_available_on":
        corpus["details"][1]["detection_time"] = "2026-09-05"
    else:
        corpus["queries"][0]["known_at"] = "2026-08-31"
    _resave_corpus(locked_test_layout, corpus)

    with pytest.raises(ValueError, match=pattern):
        load_benchmark(locked_test_layout.qrels_path, base_dir=locked_test_layout.root)


@pytest.mark.parametrize(("field", "value", "pattern"), [
    ("split", "development",
     r"qrels \| split \| qrels_version 'locked-test-qrels-v1' 要求 locked_test"),
    ("qrels_version", "locked-test-qrels-v99", r"qrels \| qrels_version \| 期望 "),
    ("review_status", "draft_pending_human_review",
     r"review_status \| 正式评估要求 human_confirmed"),
    ("sources", None, r"qrels \| sources \| 必须是对象"),
])
def test_locked_test_qrels_guards_still_apply(locked_test_layout, field, value, pattern):
    qrels = _read(locked_test_layout.qrels_path)
    qrels[field] = value
    locked_test_layout.write_qrels(qrels)

    with pytest.raises(ValueError, match=pattern):
        load_benchmark(locked_test_layout.qrels_path, base_dir=locked_test_layout.root)


def test_locked_test_corpus_split_must_match_qrels_version(locked_test_layout):
    corpus = _read(locked_test_layout.corpus_path)
    corpus["split"] = "development"
    _resave_corpus(locked_test_layout, corpus)

    with pytest.raises(
        ValueError,
        match=r"Dataset \| split \| qrels_version 'locked-test-qrels-v1' 要求 locked_test",
    ):
        load_benchmark(locked_test_layout.qrels_path, base_dir=locked_test_layout.root)


def test_locked_test_changed_corpus_hash_is_rejected(locked_test_layout):
    corpus = _read(locked_test_layout.corpus_path)
    corpus["cases"][0]["abnormal_description"] = "改写后的描述"
    locked_test_layout.write_corpus(corpus)  # 故意不刷新 qrels 记录的哈希

    with pytest.raises(ValueError, match=r"sources\.dataset \| .* SHA-256 不一致"):
        load_benchmark(locked_test_layout.qrels_path, base_dir=locked_test_layout.root)


def test_locked_test_requires_complete_integer_pairs(locked_test_layout):
    """缺配对、重复配对与 null 标签都必须被拒绝，不能降级为不相关。"""
    qrels = _read(locked_test_layout.qrels_path)
    qrels["judgments"] = qrels["judgments"][:1]
    locked_test_layout.write_qrels(qrels)
    with pytest.raises(ValueError, match=r"缺少 1 个配对：\(LQ001, SC002\)"):
        load_benchmark(locked_test_layout.qrels_path, base_dir=locked_test_layout.root)

    qrels = _read(locked_test_layout.qrels_path)
    qrels["judgments"].append(dict(qrels["judgments"][0]))
    locked_test_layout.write_qrels(qrels)
    with pytest.raises(ValueError, match=r"CR-03 \| qrels \| \(LQ001, SC001\) \| 配对重复"):
        load_benchmark(locked_test_layout.qrels_path, base_dir=locked_test_layout.root)

    qrels = _read(locked_test_layout.qrels_path)
    qrels["judgments"][0]["relevance"] = None
    locked_test_layout.write_qrels(qrels)
    with pytest.raises(ValueError, match=r"relevance \| 必须是整数 0 或 1"):
        load_benchmark(locked_test_layout.qrels_path, base_dir=locked_test_layout.root)


def test_labels_and_generation_metadata_stay_out_of_retrieval_text(locked_test_layout):
    from casetrace.demo import build_documents

    benchmark = load_benchmark(locked_test_layout.qrels_path, base_dir=locked_test_layout.root)
    documents = "\n".join(build_documents(benchmark.records, benchmark.reference).values())

    # 历史 Case 文本照常可检索。
    assert "焊线脱落" in documents and "表面污染" in documents
    # Query、标注理由与生成/快照元数据都不进入检索文本。
    for leaked in ("原因尚未确认", "同异常", "不同异常", "availability_snapshot",
                   "synthetic-locked-fixture", "locked-test-v1-2026-08-31"):
        assert leaked not in documents
