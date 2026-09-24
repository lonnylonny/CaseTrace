"""验证评估运行器的排名覆盖、防泄漏、逐 Query 指标口径、跨 Query 汇总与耗时记录；只读真实数据。"""

import dataclasses
import hashlib
import json
import math
from pathlib import Path

import pytest

from casetrace.demo import build_documents
from casetrace.evaluation.benchmark import PROJECT_ROOT, load_benchmark
from casetrace.evaluation.runner import (
    DEFAULT_METHOD,
    METRIC_KS,
    MRR_KEY,
    NO_RELEVANT_REASON,
    RECIPROCAL_RANK_K,
    REPRODUCIBILITY_SOURCE_FILES,
    RESULT_SCHEMA_VERSION,
    RETRIEVER_FACTORIES,
    RR_KEY,
    SCORE_KEYS,
    SUMMARY_METRIC_KEYS,
    ExcludedQuery,
    aggregate,
    build_retriever,
    evaluate_query,
    rank_query,
    run_evaluation,
    write_report,
)
from casetrace.retrieval.base import SearchHit

QRELS_RELATIVE = "data/evaluation/dev-v2/qrels.json"


@pytest.fixture(scope="module")
def benchmark():
    """已确认的 dev-v2 输入，只读使用，不修改仓库数据。"""
    return load_benchmark(PROJECT_ROOT / QRELS_RELATIVE)


def _query(benchmark, query_id):
    return next(query for query in benchmark.queries if query.query_id == query_id)


def _hits(*case_ids):
    return [SearchHit(case_id, 1.0, ["stub"]) for case_id in case_ids]


def _without_run_metadata(report):
    """剔除不参与确定性比较的运行元数据：记录生成时间与机器相关的耗时。"""
    report.pop("generated_at")
    report.pop("timing")
    return report


class StubRetriever:
    """按给定顺序返回固定排名，用于在不受 BM25 分数影响时验证运行器口径。"""

    def __init__(self, hits):
        self._hits = list(hits)
        self.requested_top_k = None

    def search(self, query, *, top_k):
        self.requested_top_k = top_k
        return self._hits[:top_k]

    def describe(self):
        return {"method": "stub", "implementation": "tests.StubRetriever",
                "note": "固定排名替身，不读任何文本"}


def test_ranking_requests_the_whole_corpus(benchmark):
    retriever = StubRetriever(_hits("C001", "C003"))
    ranked = rank_query(benchmark, retriever, _query(benchmark, "Q001"))

    assert retriever.requested_top_k == len(benchmark.case_ids) == 6
    assert [(item.rank, item.case_id) for item in ranked] == [(1, "C001"), (2, "C003")]


@pytest.mark.parametrize(("hits", "message"), [
    (_hits("C001", "C999"), "语料之外"),
    (_hits("C001", "C001"), "重复"),
])
def test_invalid_return_ids_are_rejected(benchmark, hits, message):
    with pytest.raises(ValueError, match=message):
        rank_query(benchmark, StubRetriever(hits), _query(benchmark, "Q001"))


def test_retriever_corpus_must_match_validated_cases(benchmark, monkeypatch):
    monkeypatch.setattr(
        "casetrace.evaluation.runner.build_documents",
        lambda records, reference: {"C001": "only one case"},
    )
    with pytest.raises(ValueError, match="不一致"):
        build_retriever(benchmark)


def test_contract_retriever_needs_only_search_and_describe(benchmark):
    # 评估器只依赖公共契约：能按 Query 返回 SearchHit 并声明自己的元数据。
    retriever = StubRetriever(_hits("C001", "C005"))

    evaluation = evaluate_query(benchmark, retriever, _query(benchmark, "Q001"))

    assert retriever.describe()["method"] == "stub"
    assert [item.case_id for item in evaluation.ranked] == ["C001", "C005"]
    # Q001 有 4 个已确认正例，第 1 名命中其中的 C001；口径与 M2 相同，替身不改变计分。
    assert evaluation.scores["recall@1"] == 0.25


def test_ranked_case_keeps_missing_terms_as_none(benchmark):
    retriever = StubRetriever([SearchHit("C001", 0.5)])

    ranked = rank_query(benchmark, retriever, _query(benchmark, "Q001"))

    assert ranked[0].matched_terms is None


def test_single_query_scores_match_hand_calculation(benchmark):
    # 教学排名，不是实际 BM25 结果；Q001 的已确认正例是 C001–C004。
    retriever = StubRetriever(_hits("C003", "C001", "C006", "C002", "C004", "C005"))

    result = evaluate_query(benchmark, retriever, _query(benchmark, "Q001"))

    assert result.relevant_case_ids == ["C001", "C002", "C003", "C004"]
    assert [item.case_id for item in result.ranked] == [
        "C003", "C001", "C006", "C002", "C004", "C005",
    ]
    # 前 4 名命中 3 个正例，首个相关结果在第 1 名；
    # nDCG@3 的理想序列为 3 个正例，nDCG@4 的理想序列为 4 个正例。
    assert result.scores == {
        "recall@1": 0.25,
        "recall@3": 0.5,
        "recall@4": 0.75,
        "precision@1": 1.0,
        "precision@3": pytest.approx(2 / 3),
        "precision@4": 0.75,
        "ndcg@1": 1.0,
        "ndcg@3": pytest.approx(
            (1 + 1 / math.log2(3)) / (1 + 1 / math.log2(3) + 1 / math.log2(4))
        ),
        "ndcg@4": pytest.approx(
            (1 + 1 / math.log2(3) + 1 / math.log2(5))
            / (1 + 1 / math.log2(3) + 1 / math.log2(4) + 1 / math.log2(5))
        ),
        "rr@4": 1.0,
    }


@pytest.mark.parametrize("ranked_case_ids", [(), ("C001", "C002")])
def test_query_without_positives_keeps_undefined_metrics(benchmark, ranked_case_ids):
    """合成输入：把 Q001 的标签全部置 0，不改动仓库中的 qrels。"""
    judgments = {query_id: dict(labels) for query_id, labels in benchmark.judgments.items()}
    judgments["Q001"] = dict.fromkeys(benchmark.case_ids, 0)
    synthetic = dataclasses.replace(benchmark, judgments=judgments)

    result = evaluate_query(
        synthetic, StubRetriever(_hits(*ranked_case_ids)), _query(benchmark, "Q001")
    )

    assert result.relevant_case_ids == []
    assert result.scores["recall@4"] is None
    assert result.scores["ndcg@4"] is None
    assert result.scores["rr@4"] is None
    assert result.scores["precision@4"] == 0.0


def test_label_changes_do_not_change_retrieval(benchmark):
    relabeled = dataclasses.replace(
        benchmark,
        judgments={
            query_id: dict.fromkeys(labels, 0)
            for query_id, labels in benchmark.judgments.items()
        },
    )
    query = _query(benchmark, "Q001")

    assert rank_query(relabeled, build_retriever(relabeled), query) == rank_query(
        benchmark, build_retriever(benchmark), query
    )


def test_runner_indexes_history_only(benchmark):
    records = dict(benchmark.records)
    records["queries"] = [{"text": "FUTURE_CAUSE_LEAK"}]
    records["sources"] = {"C001": "ANNOTATION_LEAK"}
    records["judgments"] = [{"rationale": "QRELS_LEAK"}]
    patched = dataclasses.replace(benchmark, records=records)
    query = _query(benchmark, "Q001")

    documents = build_documents(patched.records, patched.reference)
    assert all("LEAK" not in text for text in documents.values())
    assert rank_query(patched, build_retriever(patched), query) == rank_query(
        benchmark, build_retriever(benchmark), query
    )


def test_real_dev_v2_evaluation_is_deterministic_and_within_corpus(benchmark):
    first = [evaluate_query(benchmark, build_retriever(benchmark), query)
             for query in benchmark.queries]
    second = [evaluate_query(benchmark, build_retriever(benchmark), query)
              for query in benchmark.queries]
    assert first == second

    expected_keys = {
        f"{name}@{k}" for name in ("recall", "precision", "ndcg") for k in METRIC_KS
    } | {f"rr@{RECIPROCAL_RANK_K}"}
    corpus = set(benchmark.case_ids)
    for result in first:
        ranked_case_ids = [item.case_id for item in result.ranked]
        assert ranked_case_ids and len(ranked_case_ids) == len(set(ranked_case_ids))
        assert set(ranked_case_ids) <= corpus
        assert [item.rank for item in result.ranked] == list(range(1, len(ranked_case_ids) + 1))
        assert result.relevant_case_ids
        assert set(result.scores) == expected_keys
        assert all(0.0 <= value <= 1.0 for value in result.scores.values())


class ScriptedRetriever:
    """按 Query 文本返回预设排名，用于给不同 Query 造出不同分数。"""

    def __init__(self, rankings):
        self._rankings = dict(rankings)

    def search(self, query, *, top_k):
        return _hits(*self._rankings[query])[:top_k]


# 教学排名，不是实际 BM25 结果：Q001 命中全部 4 个正例；Q002 只返回 3 条，
# 唯一正例 C005 在第 3 名；Q003 只返回 1 条，正例 C006 在第 1 名。
SCRIPTED_RANKINGS = {
    "Q001": ("C001", "C002", "C003", "C004", "C005", "C006"),
    "Q002": ("C001", "C002", "C005"),
    "Q003": ("C006",),
}


def _evaluate_scripted(benchmark, rankings):
    """按 Query 顺序逐条评估；rankings 用 Query ID 指定预设排名。"""
    retriever = ScriptedRetriever(
        {_query(benchmark, query_id).text: case_ids for query_id, case_ids in rankings.items()}
    )
    return [evaluate_query(benchmark, retriever, query) for query in benchmark.queries]


def _without_positives(benchmark, query_ids):
    """合成输入：把指定 Query 的标签全部置 0，不改动仓库中的 qrels。"""
    judgments = {query_id: dict(labels) for query_id, labels in benchmark.judgments.items()}
    for query_id in query_ids:
        judgments[query_id] = dict.fromkeys(benchmark.case_ids, 0)
    return dataclasses.replace(benchmark, judgments=judgments)


def _summary_values(summary):
    return {key: metric.value for key, metric in summary.metrics.items()}


def test_summary_averages_queries_with_equal_weight(benchmark):
    summary = aggregate(_evaluate_scripted(benchmark, SCRIPTED_RANKINGS))

    assert summary.query_count == 3
    assert summary.no_relevant_query_ids == []
    assert list(summary.metrics) == list(SUMMARY_METRIC_KEYS)
    # 每条 Query 的分数按 Q001 / Q002 / Q003 顺序等权平均，括号内即手算过程。
    assert _summary_values(summary) == {
        "recall@1": pytest.approx((0.25 + 0.0 + 1.0) / 3),
        "recall@3": pytest.approx((0.75 + 1.0 + 1.0) / 3),
        "recall@4": pytest.approx((1.0 + 1.0 + 1.0) / 3),
        "precision@1": pytest.approx((1.0 + 0.0 + 1.0) / 3),
        "precision@3": pytest.approx((1.0 + 1 / 3 + 1 / 3) / 3),
        "precision@4": pytest.approx((1.0 + 0.25 + 0.25) / 3),
        "ndcg@1": pytest.approx((1.0 + 0.0 + 1.0) / 3),
        "ndcg@3": pytest.approx((1.0 + 0.5 + 1.0) / 3),
        "ndcg@4": pytest.approx((1.0 + 0.5 + 1.0) / 3),
        "mrr@4": pytest.approx((1.0 + 1 / 3 + 1.0) / 3),
    }
    for metric in summary.metrics.values():
        assert metric.included_query_ids == ["Q001", "Q002", "Q003"]
        assert metric.excluded == []
    assert RR_KEY not in summary.metrics and MRR_KEY in summary.metrics


def test_no_relevant_query_is_excluded_from_means_but_precision_counts_it(benchmark):
    synthetic = _without_positives(benchmark, ["Q001"])
    evaluations = _evaluate_scripted(synthetic, SCRIPTED_RANKINGS)

    summary = aggregate(evaluations)

    assert summary.no_relevant_query_ids == ["Q001"]
    # Recall / nDCG / MRR 排除无正例 Query：分母是 2，而不是 3。
    for key in ("recall@1", "recall@4", "ndcg@4", MRR_KEY):
        assert summary.metrics[key].included_query_ids == ["Q002", "Q003"]
        assert summary.metrics[key].excluded == [ExcludedQuery("Q001", NO_RELEVANT_REASON)]
    assert summary.metrics["recall@4"].value == pytest.approx((1.0 + 1.0) / 2)
    assert summary.metrics["ndcg@4"].value == pytest.approx((0.5 + 1.0) / 2)
    assert summary.metrics[MRR_KEY].value == pytest.approx((1 / 3 + 1.0) / 2)

    # Precision 按函数口径把无正例 Query 的 0.0 纳入均值，分母仍是 3。
    for key in ("precision@1", "precision@3", "precision@4"):
        assert summary.metrics[key].included_query_ids == ["Q001", "Q002", "Q003"]
        assert summary.metrics[key].excluded == []
    assert summary.metrics["precision@1"].value == pytest.approx((0.0 + 0.0 + 1.0) / 3)
    assert summary.metrics["precision@4"].value == pytest.approx((0.0 + 0.25 + 0.25) / 3)

    # 逐 Query 层不变：无正例时 Recall / nDCG / RR 为 None，Precision 为 0.0。
    assert evaluations[0].query_id == "Q001"
    assert evaluations[0].scores["recall@4"] is None
    assert evaluations[0].scores["ndcg@4"] is None
    assert evaluations[0].scores[RR_KEY] is None
    assert evaluations[0].scores["precision@4"] == 0.0


def test_metrics_without_participants_summarise_to_none(benchmark):
    synthetic = _without_positives(benchmark, ["Q001", "Q002", "Q003"])

    summary = aggregate(_evaluate_scripted(synthetic, SCRIPTED_RANKINGS))

    assert summary.no_relevant_query_ids == ["Q001", "Q002", "Q003"]
    for key in ("recall@1", "recall@3", "recall@4",
                "ndcg@1", "ndcg@3", "ndcg@4", MRR_KEY):
        metric = summary.metrics[key]
        assert metric.value is None          # 不除零，也不把「不适用」写成 0.0
        assert metric.included_query_ids == []
        assert [item.query_id for item in metric.excluded] == ["Q001", "Q002", "Q003"]
        assert {item.reason for item in metric.excluded} == {NO_RELEVANT_REASON}
    for key in ("precision@1", "precision@3", "precision@4"):
        assert summary.metrics[key].value == 0.0
        assert summary.metrics[key].included_query_ids == ["Q001", "Q002", "Q003"]


def test_empty_input_summarises_to_nulls():
    summary = aggregate([])

    assert summary.query_count == 0
    assert summary.no_relevant_query_ids == []
    assert list(summary.metrics) == list(SUMMARY_METRIC_KEYS)
    assert all(metric.value is None for metric in summary.metrics.values())
    assert all(metric.included_query_ids == [] for metric in summary.metrics.values())


def test_summary_rejects_duplicate_query_ids(benchmark):
    evaluations = _evaluate_scripted(benchmark, SCRIPTED_RANKINGS)

    with pytest.raises(ValueError, match="重复"):
        aggregate([evaluations[0], evaluations[0]])


def test_summary_rejects_inconsistent_scores(benchmark):
    evaluation = _evaluate_scripted(benchmark, SCRIPTED_RANKINGS)[0]
    assert evaluation.relevant_case_ids
    none_but_positive = dataclasses.replace(
        evaluation, scores={**evaluation.scores, "recall@4": None}
    )
    missing_key = dataclasses.replace(
        evaluation,
        scores={key: value for key, value in evaluation.scores.items() if key != "ndcg@3"},
    )

    with pytest.raises(ValueError, match="指标口径不一致"):
        aggregate([none_but_positive])
    with pytest.raises(ValueError, match="分数键"):
        aggregate([missing_key])


def test_real_dev_v2_summary_matches_per_query_scores(benchmark):
    retriever = build_retriever(benchmark)
    evaluations = [evaluate_query(benchmark, retriever, query) for query in benchmark.queries]

    summary = aggregate(evaluations)

    assert summary.query_count == len(evaluations) == 3
    assert summary.no_relevant_query_ids == []
    assert list(summary.metrics) == list(SUMMARY_METRIC_KEYS)
    assert set(summary.metrics) == (set(SCORE_KEYS) - {RR_KEY}) | {MRR_KEY}
    for key, metric in summary.metrics.items():
        score_key = RR_KEY if key == MRR_KEY else key
        values = [evaluation.scores[score_key] for evaluation in evaluations]
        assert all(value is not None for value in values)
        assert metric.included_query_ids == [evaluation.query_id for evaluation in evaluations]
        assert metric.excluded == []
        assert metric.value == pytest.approx(sum(values) / len(values))
    assert aggregate(evaluations) == summary      # 同一输入重复汇总结果一致


def test_report_matches_pure_evaluation_and_records_inputs(benchmark):
    report = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE)

    assert report["schema_version"] == RESULT_SCHEMA_VERSION
    assert json.dumps(report, ensure_ascii=False)          # 可序列化，不依赖自定义编码
    assert report["generated_at"]

    recorded = report["benchmark"]
    assert recorded["qrels_path"] == QRELS_RELATIVE
    assert recorded["qrels_version"] == benchmark.qrels_version
    assert recorded["qrels_sha256"] == hashlib.sha256(
        (PROJECT_ROOT / QRELS_RELATIVE).read_bytes()
    ).hexdigest()
    assert recorded["split"] == "development"
    assert recorded["confirmed_on"] == benchmark.confirmed_on
    assert recorded["dataset"] == {
        "path": benchmark.dataset.recorded_path,
        "sha256": hashlib.sha256(benchmark.dataset.path.read_bytes()).hexdigest(),
    }
    assert recorded["reference"]["sha256"] == hashlib.sha256(
        benchmark.reference_file.path.read_bytes()
    ).hexdigest()
    assert recorded["dataset_review_status"] == benchmark.dataset_review_status
    assert recorded["latest_detection"] == benchmark.latest_detection.isoformat()
    assert recorded["history_snapshot"]

    retriever = build_retriever(benchmark)
    retrieval = report["retrieval"]
    assert retrieval["parameters"] == {
        "k1": retriever.index.k1, "b": retriever.index.b, "epsilon": retriever.index.epsilon,
    }
    assert retrieval["corpus_size"] == retrieval["requested_top_k"] == len(benchmark.case_ids)

    metrics = report["metrics"]
    assert metrics["ks"] == list(METRIC_KS)
    assert metrics["reciprocal_rank_k"] == RECIPROCAL_RANK_K
    assert metrics["summary_metric_keys"] == list(SUMMARY_METRIC_KEYS)
    assert set(metrics["definitions"]) == {
        "recall@k", "precision@k", "ndcg@k", RR_KEY, MRR_KEY,
    }
    assert metrics["no_relevant_policy"]

    evaluations = [evaluate_query(benchmark, retriever, query) for query in benchmark.queries]
    assert report["queries"] == [dataclasses.asdict(evaluation) for evaluation in evaluations]
    assert report["summary"] == dataclasses.asdict(aggregate(evaluations))


def test_report_reproducibility_section_is_verifiable():
    reproducibility = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE)["reproducibility"]

    assert reproducibility["python"]
    assert all(reproducibility["packages"].values())
    assert set(reproducibility["source_files"]) == set(REPRODUCIBILITY_SOURCE_FILES)
    for name, digest in reproducibility["source_files"].items():
        assert digest == hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()

    if reproducibility["git_head"] is None:
        assert any("无法读取 git 状态" in note for note in reproducibility["notes"])
    else:
        assert len(reproducibility["git_head"]) == 40
        assert isinstance(reproducibility["git_dirty"], bool)
        assert reproducibility["git_status_paths"] == sorted(
            set(reproducibility["git_status_paths"])
        )
    assert any("generated_at" in note for note in reproducibility["notes"])


def test_run_evaluation_is_deterministic_apart_from_run_metadata():
    first = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE)
    second = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE)

    assert first["generated_at"] and first["timing"]
    assert _without_run_metadata(first) == _without_run_metadata(second)


def test_explicit_default_method_matches_the_implicit_default():
    default = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE)
    explicit = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE, method=DEFAULT_METHOD)

    assert _without_run_metadata(default) == _without_run_metadata(explicit)


def test_report_timing_records_boundaries_and_stays_out_of_scores():
    report = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE)

    timing = report["timing"]
    assert timing["unit"] == "seconds" and timing["clock"] == "time.perf_counter"
    assert timing["index_build_seconds"] >= 0
    assert [item["query_id"] for item in timing["per_query"]] == [
        query["query_id"] for query in report["queries"]
    ]
    assert all(item["seconds"] >= 0 for item in timing["per_query"])
    assert timing["queries_total_seconds"] == pytest.approx(
        sum(item["seconds"] for item in timing["per_query"])
    )
    assert timing["total_seconds"] >= timing["index_build_seconds"]
    assert len(timing["boundaries"]) == 3 and all(timing["boundaries"])
    assert "不参与确定性比较" in timing["comparison_note"]
    for document in (report["metrics"], report["queries"], report["summary"]):
        serialized = json.dumps(document, ensure_ascii=False)
        assert "timing" not in serialized and "seconds" not in serialized


def test_unknown_method_is_rejected_before_anything_is_built(benchmark):
    # hybrid 尚未实现：真正的未知方法必须在建索引之前报错，且列出当前可用方法。
    with pytest.raises(ValueError) as error:
        build_retriever(benchmark, method="hybrid")

    message = str(error.value)
    assert "未实现的检索方法" in message and "hybrid" in message
    assert DEFAULT_METHOD in message            # 报错必须说明当前可用的方法

    with pytest.raises(ValueError, match="未实现的检索方法"):
        run_evaluation(PROJECT_ROOT / QRELS_RELATIVE, method="hybrid")


def test_second_method_without_terms_can_be_registered(benchmark, monkeypatch):
    """用替身证明入口可接入第二种返回，不需要先写 Embedding。"""

    class RankingOnlyRetriever:
        """不读文本、没有词项信息，只按 Case ID 顺序排名的替身方法。"""

        def __init__(self, documents):
            self.case_ids = sorted(documents)

        def search(self, query, *, top_k):
            return [
                SearchHit(case_id, 1.0 / rank)
                for rank, case_id in enumerate(self.case_ids[:top_k], start=1)
            ]

        def describe(self):
            return {
                "method": "ranking_only_toy",
                "implementation": "tests.evaluation.test_runner.RankingOnlyRetriever",
                "note": "替身方法：只验证入口可替换，不代表任何真实检索效果",
            }

    monkeypatch.setitem(RETRIEVER_FACTORIES, "ranking_only_toy", RankingOnlyRetriever)

    report = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE, method="ranking_only_toy")

    retrieval = report["retrieval"]
    # 报告记录的是实际执行的那个方法，不是写死的常量。
    assert retrieval["method"] == "ranking_only_toy"
    assert "parameters" not in retrieval and "tokenizer" not in retrieval
    assert retrieval["corpus_size"] == retrieval["requested_top_k"] == len(benchmark.case_ids)

    first = report["queries"][0]
    assert [item["case_id"] for item in first["ranked"]] == sorted(benchmark.case_ids)
    assert all(item["matched_terms"] is None for item in first["ranked"])
    assert report["summary"]["query_count"] == len(benchmark.queries)

    # 替身只在本次测试内注册；默认入口仍然运行 BM25。
    assert run_evaluation(PROJECT_ROOT / QRELS_RELATIVE)["retrieval"]["method"] == "bm25_okapi"


def test_registry_ships_only_real_methods():
    # 注册表只登记真实实现：替身方法只能通过 monkeypatch 注入；新增方法必须显式登记。
    assert set(RETRIEVER_FACTORIES) == {"bm25", "embedding"}


def test_embedding_method_report_records_cache_and_run_details(tmp_path, monkeypatch):
    """用替身编码器驱动真实 EmbeddingRetriever，验证报告接入：不加载模型、不联网。"""
    import numpy as np

    from casetrace.retrieval.embedding import EmbeddingRetriever

    class StubEncoder:
        """固定 4 维的单位向量替身：只验证接线，不代表任何真实语义。"""

        dimension = 4

        def encode(self, texts):
            return np.eye(4, dtype="float32")[np.arange(len(texts)) % 4]

    monkeypatch.setitem(
        RETRIEVER_FACTORIES, "embedding",
        lambda documents: EmbeddingRetriever(
            documents, encoder=StubEncoder(), cache_dir=tmp_path / "cache",
        ),
    )

    report = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE, method="embedding")

    retrieval = report["retrieval"]
    assert retrieval["method"] == "embedding"
    assert retrieval["dimension"] == 4
    assert retrieval["cache"]["enabled"] is True
    assert {"key", "file", "directory", "note"} <= set(retrieval["cache"])

    details = report["timing"]["method_details"]
    assert details["cache"]["status"] in {"miss", "hit"}
    assert details["timing"]["document_encode_seconds"] >= 0.0
    assert len(details["timing"]["per_query_encode_seconds"]) == len(report["queries"])

    # 运行观测值与方法配置分离：可比较的面板里不得出现秒数。
    for document in (report["metrics"], report["queries"], report["summary"], retrieval):
        serialized = json.dumps(document, ensure_ascii=False)
        assert "seconds" not in serialized


def test_report_fingerprints_cli_and_data_dependencies():
    # 独立列出本次曾遗漏的执行依赖，不从生产清单推导期望值。
    # 否则生产清单和报告一起漏项时，测试仍会通过。
    source_files = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE)["reproducibility"]["source_files"]
    required = {
        "src/casetrace/__init__.py",
        "src/casetrace/data/constants.py",
        "src/casetrace/data/dataset_model.py",
        "src/casetrace/data/reference.py",
        "src/casetrace/data/validators.py",
        "src/casetrace/retrieval/base.py",
    }

    assert required <= source_files.keys()
    for name in required:
        assert source_files[name] == hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()


def test_write_report_writes_complete_json_and_no_temporary_file(tmp_path):
    report = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE)
    target = tmp_path / "results" / "dev-v2-bm25.json"

    written = write_report(report, target)

    assert written == target
    assert json.loads(target.read_text(encoding="utf-8")) == report
    assert [path.name for path in target.parent.iterdir()] == [target.name]


def test_write_report_failure_leaves_no_partial_report(tmp_path):
    report = run_evaluation(PROJECT_ROOT / QRELS_RELATIVE)
    existing = tmp_path / "existing.json"
    existing.write_text("不要被覆盖", encoding="utf-8")

    with pytest.raises(OSError):
        write_report(report, tmp_path)          # 目标是目录，替换一定失败

    assert existing.read_text(encoding="utf-8") == "不要被覆盖"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["existing.json"]
