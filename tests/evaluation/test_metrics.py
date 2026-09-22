"""用手算样例和边界情况验证检索指标。"""

import pytest

from casetrace.evaluation.metrics import (
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)


@pytest.mark.parametrize(("k", "expected"), [(1, 0.25), (3, 0.5), (4, 0.75)])
def test_recall_matches_hand_calculation(k, expected):
    # 教学排名，不是实际 BM25 结果。四个正例中，C004 位于第 5 名。
    ranked = ["C001", "C005", "C003", "C002", "C004", "C006"]
    relevant = {"C001", "C002", "C003", "C004"}

    assert recall_at_k(ranked, relevant, k) == pytest.approx(expected)


def test_empty_results_with_positives_have_zero_recall():
    assert recall_at_k([], {"C001"}, 4) == 0.0


def test_fewer_than_k_results_still_use_all_positives_as_denominator():
    assert recall_at_k(["C001"], {"C001", "C002"}, 4) == 0.5


def test_no_relevant_hits_have_zero_recall():
    assert recall_at_k(["C005", "C006"], {"C001"}, 4) == 0.0


@pytest.mark.parametrize("ranked", [[], ["C005"]])
def test_no_positives_have_undefined_recall(ranked):
    assert recall_at_k(ranked, set(), 4) is None


@pytest.mark.parametrize("k", [0, -1, True, 1.5])
def test_k_must_be_a_positive_integer(k):
    with pytest.raises(ValueError):
        recall_at_k(["C001"], {"C001"}, k)


@pytest.mark.parametrize(("k", "expected"), [(1, 1.0), (3, 2 / 3), (4, 0.75)])
def test_precision_matches_hand_calculation(k, expected):
    ranked = ["C001", "C005", "C003", "C002", "C004", "C006"]
    relevant = {"C001", "C002", "C003", "C004"}

    assert precision_at_k(ranked, relevant, k) == pytest.approx(expected)


def test_fewer_than_k_results_still_use_k_as_precision_denominator():
    # 唯一的正例已找回：Recall=1，但四个位置只提供了一条相关结果。
    assert precision_at_k(["C001"], {"C001"}, 4) == 0.25


def test_empty_results_have_zero_precision():
    assert precision_at_k([], {"C001"}, 4) == 0.0


def test_no_relevant_hits_have_zero_precision():
    assert precision_at_k(["C005", "C006"], {"C001"}, 4) == 0.0


@pytest.mark.parametrize("ranked", [[], ["C005"]])
def test_no_positives_have_zero_precision(ranked):
    assert precision_at_k(ranked, set(), 4) == 0.0


@pytest.mark.parametrize("k", [0, -1, True, 1.5])
def test_precision_k_must_be_a_positive_integer(k):
    with pytest.raises(ValueError):
        precision_at_k(["C001"], {"C001"}, k)


@pytest.mark.parametrize(("ranked", "expected"), [
    (["C005"], 1.0),
    (["C001", "C005"], 0.5),
    (["C001", "C002", "C005"], 1 / 3),
    (["C001", "C002", "C003", "C005"], 0.25),
])
def test_reciprocal_rank_matches_hand_calculation(ranked, expected):
    assert reciprocal_rank_at_k(ranked, {"C005"}, 4) == pytest.approx(expected)


def test_reciprocal_rank_does_not_count_a_relevant_result_after_k():
    ranked = ["C001", "C002", "C003", "C004", "C005"]
    assert reciprocal_rank_at_k(ranked, {"C005"}, 4) == 0.0


def test_reciprocal_rank_uses_only_the_first_relevant_result():
    ranked = ["C005", "C003", "C002", "C001"]
    relevant = {"C001", "C002", "C003", "C004"}
    assert reciprocal_rank_at_k(ranked, relevant, 4) == 0.5


@pytest.mark.parametrize("ranked", [[], ["C001", "C002"]])
def test_reciprocal_rank_without_relevant_hits_is_zero(ranked):
    assert reciprocal_rank_at_k(ranked, {"C005"}, 4) == 0.0


def test_reciprocal_rank_respects_the_supplied_cutoff():
    assert reciprocal_rank_at_k(["C001", "C005"], {"C005"}, 1) == 0.0


@pytest.mark.parametrize("ranked", [[], ["C001"]])
def test_reciprocal_rank_without_positives_is_undefined(ranked):
    assert reciprocal_rank_at_k(ranked, set(), 4) is None


@pytest.mark.parametrize("k", [0, -1, True, 1.5])
def test_reciprocal_rank_k_must_be_a_positive_integer(k):
    with pytest.raises(ValueError):
        reciprocal_rank_at_k(["C005"], {"C005"}, k)


def test_ndcg_at_1_matches_hand_calculation():
    # 教学排名，不是实际 BM25 结果：第 1 名就是相关 Case。
    ranked = ["C001", "C005", "C003", "C006"]
    relevant = {"C001", "C003"}

    assert ndcg_at_k(ranked, relevant, 1) == pytest.approx(1.0)


@pytest.mark.parametrize("k", [3, 4])
def test_ndcg_matches_hand_calculation(k):
    # DCG = 1/log2(2) + 1/log2(4) = 1.5，第二个正例在第 3 名；
    # IDCG = 1/log2(2) + 1/log2(3)。K=4 的第 4 名不相关，不改变 DCG。
    ranked = ["C001", "C005", "C003", "C006"]
    relevant = {"C001", "C003"}

    assert ndcg_at_k(ranked, relevant, k) == pytest.approx(0.9197207891481876)


def test_ndcg_ideal_ranking_scores_one():
    ranked = ["C001", "C003", "C005", "C006"]
    relevant = {"C001", "C003"}

    assert ndcg_at_k(ranked, relevant, 4) == pytest.approx(1.0)


def test_ndcg_is_unchanged_when_relevant_cases_swap_ranks():
    # 两个正例仍占第 1、3 名；二值 nDCG 不区分相关 Case 之间的阅读优先级。
    swapped = ["C003", "C005", "C001", "C006"]
    relevant = {"C001", "C003"}

    assert ndcg_at_k(swapped, relevant, 3) == pytest.approx(0.9197207891481876)


def test_ndcg_denominator_does_not_shrink_with_fewer_results():
    # 只返回一个正例时 DCG = 1，但 IDCG 仍按两个正例与 K 计算。
    assert ndcg_at_k(["C001"], {"C001", "C003"}, 4) == pytest.approx(0.6131471927654584)


@pytest.mark.parametrize("ranked", [[], ["C005", "C006", "C001"]])
def test_ndcg_without_hits_in_top_k_is_zero(ranked):
    # 空返回，以及唯一正例只出现在第 3 名（K=2 之外），都记 0.0。
    assert ndcg_at_k(ranked, {"C001"}, 2) == 0.0


@pytest.mark.parametrize("ranked", [[], ["C005"]])
def test_ndcg_without_positives_is_undefined(ranked):
    assert ndcg_at_k(ranked, set(), 4) is None


@pytest.mark.parametrize("k", [0, -1, True, 1.5])
def test_ndcg_k_must_be_a_positive_integer(k):
    with pytest.raises(ValueError):
        ndcg_at_k(["C001"], {"C001"}, k)


def test_ndcg_validates_k_before_the_no_positives_case():
    with pytest.raises(ValueError):
        ndcg_at_k([], set(), 0)
