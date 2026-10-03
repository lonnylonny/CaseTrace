"""验证结果对照工具的读取函数：键集合、重复 Query、非法值与只读性。

只验证“读进来的东西是否与报告一致、形状是否可对照”，不判断指标高低；
`per_query_deltas` 的测试由用户在 SD3 自行补充（见文件末尾）。
"""

import copy
import json
from pathlib import Path

import pytest

from casetrace.evaluation.compare import (
    PER_QUERY_METRIC_KEYS,
    check_comparable,
    load_per_query_scores,
    per_query_deltas,
)

from casetrace.evaluation.runner import SCORE_KEYS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
# 已验收的同基准正式结果，只读使用；它记录的是观测，不代表质量结论。
FORMAL_RESULT = PROJECT_ROOT / "results" / "dev-v3-bm25-m3-04-fixed.json"
# 同 benchmark 的另一方法结果：method、参数与耗时都不同，用于验证"不同模型允许比较"。
OTHER_RESULT = PROJECT_ROOT / "results" / "dev-v3-embedding-m3-04-fixed.json"
# 历史版本结果：与 dev-v3 不同 benchmark（qrels 与语料都不同），用于验证不可比时必须报错。
DEV_V2_RESULT = PROJECT_ROOT / "results" / "dev-v2-bm25-m3-01.json"
# 旧报告格式（evaluation-result-v1）的样例，用于验证 schema 变化必须拒绝比较。
V1_SCHEMA_RESULT = PROJECT_ROOT / "results" / "dev-v2-bm25.json"


def _scores(overrides=None, *, drop=(), extra=None):
    """一条 Query 的完整指标映射；默认值只用于说明形态，不代表任何真实读数。"""
    scores = {key: 0.5 for key in PER_QUERY_METRIC_KEYS}
    for key in drop:
        scores.pop(key)
    if overrides:
        scores.update(overrides)
    if extra:
        scores.update(extra)
    return scores


def _report(rows):
    """rows 为 query_id 字符串或 (query_id, scores) 对。"""
    queries = []
    for row in rows:
        query_id, scores = (row, _scores()) if isinstance(row, str) else row
        queries.append({"query_id": query_id, "scores": scores})
    return {"queries": queries}


def test_metric_keys_come_from_the_runner_not_a_second_copy():
    assert PER_QUERY_METRIC_KEYS == SCORE_KEYS
    assert len(PER_QUERY_METRIC_KEYS) == 10 and "rr@4" in PER_QUERY_METRIC_KEYS


def test_loads_every_query_with_the_full_metric_set():
    scores = _report(["Q001", "Q002"])

    loaded = load_per_query_scores(scores)

    assert set(loaded) == {"Q001", "Q002"}
    assert loaded == {"Q001": _scores(), "Q002": _scores()}


def test_none_stays_none_and_is_not_turned_into_zero():
    report = _report([("Q001", _scores({"recall@1": None}))])

    loaded = load_per_query_scores(report)

    assert loaded["Q001"]["recall@1"] is None
    assert loaded["Q001"]["recall@4"] == 0.5


def test_integer_values_are_read_as_float():
    report = _report([("Q001", _scores({"precision@1": 0}))])

    value = load_per_query_scores(report)["Q001"]["precision@1"]

    assert value == 0.0 and isinstance(value, float)


def test_duplicate_query_id_is_rejected():
    report = _report(["Q001", "Q001"])

    with pytest.raises(ValueError, match="重复：Q001"):
        load_per_query_scores(report)


@pytest.mark.parametrize(
    ("keyword", "scores"),
    [
        ("drop", _scores(drop=("ndcg@3",))),
        ("extra", _scores(extra={"ndcg@5": 0.5})),
    ],
)
def test_metric_key_set_must_match_the_runner_scope(keyword, scores):
    report = _report([("Q001", scores)])

    with pytest.raises(ValueError, match="键集合与 M2 口径不符"):
        load_per_query_scores(report)


@pytest.mark.parametrize("value", [True, False, "0.5", [0.5]])
def test_non_numeric_values_are_rejected(value):
    report = _report([("Q001", _scores({"recall@1": value}))])

    with pytest.raises(ValueError, match="必须是数值或 None"):
        load_per_query_scores(report)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_values_are_rejected(value):
    report = _report([("Q001", _scores({"recall@1": value}))])

    with pytest.raises(ValueError, match="必须是有限数值"):
        load_per_query_scores(report)


@pytest.mark.parametrize(
    "report",
    [
        {},
        {"queries": []},
        {"queries": {}},
        {"queries": ["Q001"]},
        {"queries": [{"query_id": "", "scores": _scores()}]},
        {"queries": [{"query_id": "Q001"}]},
        {"queries": [{"query_id": "Q001", "scores": []}]},
        [],
    ],
)
def test_malformed_reports_are_rejected(report):
    with pytest.raises(ValueError, match="结果报告"):
        load_per_query_scores(report)


def test_loading_does_not_modify_the_report():
    report = _report(["Q001", "Q002"])
    untouched = copy.deepcopy(report)

    loaded = load_per_query_scores(report)
    loaded["Q001"]["recall@1"] = 0.0

    assert report == untouched


def test_reads_a_formal_result_file_without_repackaging_it():
    report = json.loads(FORMAL_RESULT.read_text(encoding="utf-8"))

    loaded = load_per_query_scores(report)

    assert list(loaded) == [query["query_id"] for query in report["queries"]]
    for query in report["queries"]:
        assert loaded[query["query_id"]] == {
            key: float(value) if value is not None else None
            for key, value in query["scores"].items()
        }


# --- 以下为 SD3 用户实现部分（Cline 不代写）：per_query_deltas 的测试从这里开始 ---
def test_query_before_and_after():
    before = {
        "Q001": {"recall@4": 0.5, "ndcg@4": 0.5},
        "Q002": {"recall@4": 1.0, "ndcg@4": 0.5},
    }
    after = {
        "Q001": {"recall@4": 1.0, "ndcg@4": 1.0},
        "Q002": {"recall@4": 1.0, "ndcg@4": 0.25},
    }

    assert per_query_deltas(before, after) == {
        "Q001": {"recall@4": 0.5, "ndcg@4": 0.5},
        "Q002": {"recall@4": 0.0, "ndcg@4": -0.25},
    }

def test_per_query_deltas_marks_none_as_not_comparable():
    before = {
        "Q001": {"recall@4": None, "ndcg@4": 0.5},    # ← before 侧有 None
        "Q002": {"recall@4": 1.0, "ndcg@4": 0.5},
    }
    after = {
        "Q001": {"recall@4": 0.5, "ndcg@4": 1.0},
        "Q002": {"recall@4": 1.0, "ndcg@4": None},    # ← after 侧有 None
    }

    assert per_query_deltas(before, after) == {
        "Q001": {"recall@4": None, "ndcg@4": 0.5},     # 这一格你自己手算
        "Q002": {"recall@4": 0.0, "ndcg@4": None},     # 这一格你自己手算
    }


@pytest.mark.parametrize(
    ("before_ids", "after_ids", "fragment"),
    [
        (("Q001", "Q002"), ("Q001",), "仅 before 有 ['Q002']"),
        (("Q001",), ("Q001", "Q002"), "仅 after 有 ['Q002']"),
        (("Q001", "Q003"), ("Q001", "Q004"), "仅 before 有 ['Q003']，仅 after 有 ['Q004']"),
    ],
)
def test_query_id_sets_must_match(before_ids, after_ids, fragment):
    """两份结果的 Query 集合不一致时报错，并分别指出两侧多出的 Query。"""
    before = {query_id: {"recall@4": 0.5} for query_id in before_ids}
    after = {query_id: {"recall@4": 0.5} for query_id in after_ids}

    with pytest.raises(ValueError, match="Query 集合不一致") as excinfo:
        per_query_deltas(before, after)

    assert fragment in str(excinfo.value)


@pytest.mark.parametrize(
    ("before_scores", "after_scores", "fragment"),
    [
        ({"recall@4": 0.5, "ndcg@4": 0.5}, {"recall@4": 0.5}, "仅 before 有 ['ndcg@4']"),
        ({"recall@4": 0.5}, {"recall@4": 0.5, "ndcg@4": 0.5}, "仅 after 有 ['ndcg@4']"),
    ],
)
def test_metric_key_sets_must_match_within_a_query(before_scores, after_scores, fragment):
    """同一 Query 两侧的指标键集合不一致时报错，并指出缺失或多出的键。"""
    before = {"Q001": before_scores}
    after = {"Q001": after_scores}

    with pytest.raises(ValueError, match="指标键不一致") as excinfo:
        per_query_deltas(before, after)

    message = str(excinfo.value)
    assert "Q001" in message
    assert fragment in message

# --- SD2：报告兼容性检查（check_comparable）：同基准不同模型允许比较；只读传入报告 ---

def test_check_comparable():
    left = json.loads(FORMAL_RESULT.read_text(encoding="utf-8"))
    right = json.loads(OTHER_RESULT.read_text(encoding="utf-8"))
    left_before = copy.deepcopy(left)
    right_before = copy.deepcopy(right)
    assert check_comparable(left, right) is None
    assert left == left_before
    assert right == right_before


def test_other_benchmark_is_rejected():
    """不同 benchmark（qrels 与语料都不同）不可比：必须报错并指出字段，不能静默放过。"""
    left = json.loads(FORMAL_RESULT.read_text(encoding="utf-8"))
    right = json.loads(DEV_V2_RESULT.read_text(encoding="utf-8"))

    with pytest.raises(ValueError) as excinfo:
        check_comparable(left, right)

    assert "benchmark.qrels_version" in str(excinfo.value)


def test_old_schema_is_rejected():
    """报告格式版本不同（evaluation-result-v1 与 v2）不可比：schema 变化必须拒绝比较。"""
    left = json.loads(FORMAL_RESULT.read_text(encoding="utf-8"))
    right = json.loads(V1_SCHEMA_RESULT.read_text(encoding="utf-8"))

    with pytest.raises(ValueError) as excinfo:
        check_comparable(left, right)

    assert "schema_version" in str(excinfo.value)


def test_metric_caliber_change_is_rejected():
    """指标口径不同不可比：只改动 metrics.ks 后，报错必须指出该字段。"""
    left = json.loads(FORMAL_RESULT.read_text(encoding="utf-8"))
    right = json.loads(FORMAL_RESULT.read_text(encoding="utf-8"))
    right["metrics"]["ks"] = [1, 3]

    with pytest.raises(ValueError) as excinfo:
        check_comparable(left, right)

    assert "metrics.ks" in str(excinfo.value)


def test_missing_field_is_rejected():
    """字段缺失不可比：报错要给出完整字段路径与缺失的一侧（这里是右侧）。"""
    left = json.loads(FORMAL_RESULT.read_text(encoding="utf-8"))
    right = json.loads(FORMAL_RESULT.read_text(encoding="utf-8"))
    del right["benchmark"]["qrels_sha256"]

    with pytest.raises(ValueError) as excinfo:
        check_comparable(left, right)

    message = str(excinfo.value)
    assert "benchmark.qrels_sha256" in message
    assert "右侧缺少该字段" in message
