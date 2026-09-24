"""Embedding 检索的替身测试：不加载模型、不联网、不使用真实向量。

两类用例：
- 绿色：编码调用顺序、Query 前缀、向量校验、报告元数据（本步已实现）；
- 红色（M3-02 SD2 交给用户实现）：rank_by_similarity 及其排序行为，
  手算样例写在这里，函数体留空。
"""

from collections.abc import Sequence

import json

import numpy as np
import pytest

from casetrace.retrieval import embedding as embedding_module
from casetrace.retrieval.embedding import (
    QUERY_INSTRUCTION,
    EmbeddingRetriever,
    rank_by_similarity,
)

DOCUMENTS = {"C1": "甲文档", "C2": "乙文档", "C3": "丙文档"}


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """所有用例都不写仓库默认缓存目录；需要缓存行为时用 tmp_path 显式传入。"""
    monkeypatch.setattr(embedding_module, "DEFAULT_CACHE_DIR", tmp_path / "default-cache")


class FakeEncoder:
    """替身编码器：按文本查表返回向量，并记录收到的每一次调用。"""

    def __init__(self, vectors: dict[str, list[float]], dimension: int = 3):
        self.vectors = vectors
        self.dimension = dimension
        self.calls: list[list[str]] = []

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        self.calls.append(list(texts))
        return np.asarray([self.vectors[text] for text in texts], dtype="float32")


class FixedFake:
    """固定返回同一矩阵的替身：用于制造数量 / 维度 / 数值异常。"""

    def __init__(self, matrix: object, dimension: int = 3):
        self.matrix = np.asarray(matrix, dtype="float32")
        self.dimension = dimension
        self.calls = 0

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        self.calls += 1
        return self.matrix


class ZeroQueryFake:
    """第一次返回正常文档矩阵，之后返回零向量，用于 Query 零向量分支。"""

    dimension = 3

    def __init__(self):
        self.calls = 0

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        self.calls += 1
        if self.calls == 1:
            return np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]],
                              dtype="float32")
        return np.zeros((1, self.dimension), dtype="float32")


def make_encoder() -> FakeEncoder:
    """甲与丙文档向量相同，因此它们对同一条 Query 同分，可检验同分规则。"""
    return FakeEncoder({
        "甲文档": [1.0, 0.0, 0.0],
        "乙文档": [0.0, 1.0, 0.0],
        "丙文档": [1.0, 0.0, 0.0],
        QUERY_INSTRUCTION + "甲": [1.0, 0.0, 0.0],
    })


def test_documents_are_encoded_once_in_sorted_case_order():
    encoder = make_encoder()

    EmbeddingRetriever(DOCUMENTS, encoder=encoder)

    assert encoder.calls == [["甲文档", "乙文档", "丙文档"]]


def test_empty_or_blank_corpus_is_rejected():
    for documents in [{}, {"C1": "  "}, {"C1": "甲文档", "C2": ""}]:
        with pytest.raises(ValueError):
            EmbeddingRetriever(documents, encoder=make_encoder())


def test_vector_count_mismatch_is_rejected():
    encoder = FixedFake(np.zeros((1, 3), dtype="float32"))

    with pytest.raises(ValueError) as error:
        EmbeddingRetriever(DOCUMENTS, encoder=encoder)

    assert "形状不符" in str(error.value) and "(3, 3)" in str(error.value)


def test_vector_dimension_mismatch_is_rejected():
    encoder = FixedFake(np.zeros((3, 4), dtype="float32"), dimension=3)

    with pytest.raises(ValueError) as error:
        EmbeddingRetriever(DOCUMENTS, encoder=encoder)

    assert "形状不符" in str(error.value)


def test_non_finite_vectors_are_rejected():
    encoder = FixedFake(np.asarray([[np.nan, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]]))

    with pytest.raises(ValueError) as error:
        EmbeddingRetriever(DOCUMENTS, encoder=encoder)

    assert "非有限值" in str(error.value)


def test_zero_document_vector_is_rejected():
    encoder = FixedFake(np.asarray([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]]))

    with pytest.raises(ValueError) as error:
        EmbeddingRetriever(DOCUMENTS, encoder=encoder)

    assert "零向量" in str(error.value) and "C1" in str(error.value)


def test_documents_are_l2_normalized_before_scoring():
    # 丙文档与甲文档方向相同但长度不同；归一化后两者必须得到同一个分数。
    encoder = FakeEncoder({
        "甲文档": [1.0, 0.0, 0.0],
        "乙文档": [0.0, 1.0, 0.0],
        "丙文档": [5.0, 0.0, 0.0],
    })
    retriever = EmbeddingRetriever(DOCUMENTS, encoder=encoder)

    norms = np.linalg.norm(retriever.document_vectors, axis=1)

    assert np.allclose(norms, 1.0)


def test_empty_query_returns_no_hits_without_encoding_the_query():
    encoder = make_encoder()
    retriever = EmbeddingRetriever(DOCUMENTS, encoder=encoder)

    assert retriever.search("   ") == []
    assert encoder.calls == [["甲文档", "乙文档", "丙文档"]]


def test_zero_query_vector_returns_no_hits():
    retriever = EmbeddingRetriever(DOCUMENTS, encoder=ZeroQueryFake())

    assert retriever.search("甲") == []


def test_invalid_top_k_is_rejected_before_ranking():
    retriever = EmbeddingRetriever(DOCUMENTS, encoder=make_encoder())

    for top_k in [0, -1, True, 1.5]:
        with pytest.raises(ValueError):
            retriever.search("甲", top_k=top_k)


def test_describe_reports_encoding_configuration_for_a_fake_encoder():
    retriever = EmbeddingRetriever(DOCUMENTS, encoder=make_encoder())

    described = retriever.describe()

    assert described["method"] == "embedding"
    assert described["implementation"].endswith("FakeEncoder")
    assert described["dimension"] == 3
    assert described["query_instruction"] == QUERY_INSTRUCTION
    assert described["document_instruction"] is None
    assert "余弦" in described["normalization"]
    assert described["max_seq_length"] is None  # 替身未提供该属性，如实记 None
    assert set(described["libraries"]) == {"numpy", "sentence-transformers", "transformers", "torch"}


def test_search_prefixes_the_query_and_returns_hits_without_matched_terms():
    encoder = make_encoder()
    retriever = EmbeddingRetriever(DOCUMENTS, encoder=encoder)

    hits = retriever.search("甲", top_k=2)

    # Query 加 instruction、文档不加；甲/丙 对同一条 Query 同分，同分按 Case ID 升序。
    assert encoder.calls[-1] == [QUERY_INSTRUCTION + "甲"]
    assert [hit.case_id for hit in hits] == ["C1", "C3"]
    assert all(hit.matched_terms is None for hit in hits)


def test_rank_orders_by_score_descending_and_slices_top_k():
    hits = rank_by_similarity(["C3", "C1", "C2"], [0.25, 0.75, 0.5], top_k=2)

    assert [(hit.case_id, hit.score) for hit in hits] == [("C1", 0.75), ("C2", 0.5)]


def test_rank_breaks_ties_by_case_id_independent_of_input_order():
    first = rank_by_similarity(["C2", "C1"], [0.5, 0.5], top_k=2)
    second = rank_by_similarity(["C1", "C2"], [0.5, 0.5], top_k=2)

    assert [hit.case_id for hit in first] == ["C1", "C2"]
    assert [hit.case_id for hit in second] == ["C1", "C2"]


def test_rank_returns_all_entries_when_top_k_exceeds_available():
    hits = rank_by_similarity(["C1", "C2"], [0.25, 0.75], top_k=5)

    assert [hit.case_id for hit in hits] == ["C2", "C1"]


def test_rank_rejects_mismatched_lengths_and_invalid_top_k():
    with pytest.raises(ValueError):
        rank_by_similarity(["C1", "C2"], [0.5], top_k=1)
    with pytest.raises(ValueError):
        rank_by_similarity([], [], top_k=1)
    for top_k in [0, -1, True, 1.5]:
        with pytest.raises(ValueError):
            rank_by_similarity(["C1"], [0.5], top_k=top_k)


def test_rank_does_not_modify_its_inputs():
    case_ids = ["C3", "C1", "C2"]
    scores = [0.25, 0.75, 0.5]

    rank_by_similarity(case_ids, scores, top_k=3)

    assert case_ids == ["C3", "C1", "C2"]
    assert scores == [0.25, 0.75, 0.5]


class ConfiguredFake(FakeEncoder):
    """带模型元数据的替身：用于验证缓存键绑定编码配置。"""

    def __init__(
        self, vectors, *, model_name="fake-model", revision="rev-1", device="cpu",
        batch_size=8, max_seq_length=512,
    ):
        super().__init__(vectors)
        self.model_name = model_name
        self.revision = revision
        self.device = device
        self.batch_size = batch_size
        self.max_seq_length = max_seq_length


def test_cache_is_written_on_miss_and_reused_on_hit(tmp_path):
    cache_dir = tmp_path / "cache"
    first_encoder = ConfiguredFake({"甲文档": [1.0, 0.0, 0.0], "乙文档": [0.0, 1.0, 0.0],
                                    "丙文档": [1.0, 0.0, 0.0]})
    first = EmbeddingRetriever(DOCUMENTS, encoder=first_encoder, cache_dir=cache_dir)
    files = sorted(path.name for path in cache_dir.iterdir())

    second_encoder = ConfiguredFake({"甲文档": [1.0, 0.0, 0.0], "乙文档": [0.0, 1.0, 0.0],
                                     "丙文档": [1.0, 0.0, 0.0]})
    second = EmbeddingRetriever(DOCUMENTS, encoder=second_encoder, cache_dir=cache_dir)

    assert first.cache_status == "miss"
    assert second.cache_status == "hit"
    assert first_encoder.calls == [["甲文档", "乙文档", "丙文档"]]
    assert second_encoder.calls == []  # 命中缓存后不再调用模型
    assert np.array_equal(first.document_vectors, second.document_vectors)
    assert files == [f"{first.cache_key}.json"]
    assert second.cache_read_seconds >= 0.0


def test_cache_file_records_key_config_and_case_ids(tmp_path):
    cache_dir = tmp_path / "cache"
    encoder = ConfiguredFake({"甲文档": [1.0, 0.0, 0.0], "乙文档": [0.0, 1.0, 0.0],
                              "丙文档": [1.0, 0.0, 0.0]})

    retriever = EmbeddingRetriever(DOCUMENTS, encoder=encoder, cache_dir=cache_dir)
    payload = json.loads(retriever.cache_path.read_text(encoding="utf-8"))

    assert payload["key"] == retriever.cache_key
    assert payload["case_ids"] == ["C1", "C2", "C3"]
    assert payload["dimension"] == 3
    assert payload["config"]["model"] == "fake-model"
    assert payload["config"]["model_revision"] == "rev-1"
    assert len(payload["vectors"]) == 3


def test_document_text_change_invalidates_cache(tmp_path):
    cache_dir = tmp_path / "cache"
    VECTORS = {"甲文档": [1.0, 0.0, 0.0], "乙文档": [0.0, 1.0, 0.0], "丙文档": [1.0, 0.0, 0.0]}
    first = EmbeddingRetriever(DOCUMENTS, encoder=ConfiguredFake(dict(VECTORS)), cache_dir=cache_dir)

    changed = dict(DOCUMENTS, C3="丙文档改")  # 文本变了，键必须跟着变
    second_encoder = ConfiguredFake(dict(VECTORS, **{"丙文档改": [1.0, 0.0, 0.0]}))
    second = EmbeddingRetriever(changed, encoder=second_encoder, cache_dir=cache_dir)

    assert second.cache_key != first.cache_key
    assert second.cache_status == "miss"
    assert second_encoder.calls == [["甲文档", "乙文档", "丙文档改"]]


def test_encoding_config_change_invalidates_cache(tmp_path):
    cache_dir = tmp_path / "cache"
    VECTORS = {"甲文档": [1.0, 0.0, 0.0], "乙文档": [0.0, 1.0, 0.0], "丙文档": [1.0, 0.0, 0.0]}
    first = EmbeddingRetriever(
        DOCUMENTS, encoder=ConfiguredFake(dict(VECTORS), revision="rev-1"), cache_dir=cache_dir,
    )

    second_encoder = ConfiguredFake(dict(VECTORS), revision="rev-2")
    second = EmbeddingRetriever(DOCUMENTS, encoder=second_encoder, cache_dir=cache_dir)

    assert second.cache_key != first.cache_key
    assert second.cache_status == "miss"
    assert second_encoder.calls == [["甲文档", "乙文档", "丙文档"]]


def test_case_id_set_change_invalidates_cache(tmp_path):
    cache_dir = tmp_path / "cache"
    VECTORS = {"甲文档": [1.0, 0.0, 0.0], "乙文档": [0.0, 1.0, 0.0], "丙文档": [1.0, 0.0, 0.0],
               "丁文档": [0.0, 0.0, 1.0]}
    first = EmbeddingRetriever(DOCUMENTS, encoder=ConfiguredFake(dict(VECTORS)), cache_dir=cache_dir)

    extended = dict(DOCUMENTS, C4="丁文档")
    second_encoder = ConfiguredFake(dict(VECTORS))
    second = EmbeddingRetriever(extended, encoder=second_encoder, cache_dir=cache_dir)

    assert second.cache_key != first.cache_key
    assert second.cache_status == "miss"
    assert second_encoder.calls == [["甲文档", "乙文档", "丙文档", "丁文档"]]


def test_corrupt_cache_is_not_used_and_is_rebuilt(tmp_path):
    cache_dir = tmp_path / "cache"
    VECTORS = {"甲文档": [1.0, 0.0, 0.0], "乙文档": [0.0, 1.0, 0.0], "丙文档": [1.0, 0.0, 0.0]}
    reference = EmbeddingRetriever(DOCUMENTS, encoder=ConfiguredFake(dict(VECTORS)),
                                   cache_dir=tmp_path / "other-cache")
    cache_dir.mkdir()
    (cache_dir / f"{reference.cache_key}.json").write_text("{ 不是合法 JSON", encoding="utf-8")

    encoder = ConfiguredFake(dict(VECTORS))
    retriever = EmbeddingRetriever(DOCUMENTS, encoder=encoder, cache_dir=cache_dir)

    assert retriever.cache_status == "corrupt"
    assert "无法解析" in retriever.cache_reason
    assert encoder.calls == [["甲文档", "乙文档", "丙文档"]]  # 坏缓存不采信，重新编码
    assert np.array_equal(retriever.document_vectors, reference.document_vectors)
    json.loads(retriever.cache_path.read_text(encoding="utf-8"))  # 已用有效内容重写


def test_cache_config_records_dependency_versions_and_dtypes(tmp_path):
    # Codex Spec finding：缓存键/报告必须真的绑定依赖版本与 dtype，而不只是写在文档里。
    cache_dir = tmp_path / "cache"
    encoder = ConfiguredFake({"甲文档": [1.0, 0.0, 0.0], "乙文档": [0.0, 1.0, 0.0],
                              "丙文档": [1.0, 0.0, 0.0]})

    retriever = EmbeddingRetriever(DOCUMENTS, encoder=encoder, cache_dir=cache_dir)
    config = json.loads(retriever.cache_path.read_text(encoding="utf-8"))["config"]

    assert config["model_output_dtype"] == embedding_module.MODEL_OUTPUT_DTYPE
    assert config["working_dtype"] == embedding_module.WORKING_DTYPE
    assert set(config["libraries"]) == set(embedding_module.ENCODER_PACKAGES)


def test_dependency_version_change_invalidates_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    VECTORS = {"甲文档": [1.0, 0.0, 0.0], "乙文档": [0.0, 1.0, 0.0], "丙文档": [1.0, 0.0, 0.0]}
    first = EmbeddingRetriever(DOCUMENTS, encoder=ConfiguredFake(dict(VECTORS)),
                               cache_dir=cache_dir)

    # 依赖升级后，旧版本算出的向量不能再被当作等价结果。
    monkeypatch.setattr(
        embedding_module, "_package_versions",
        lambda: dict.fromkeys(embedding_module.ENCODER_PACKAGES, "upgraded"),
    )
    second_encoder = ConfiguredFake(dict(VECTORS))
    second = EmbeddingRetriever(DOCUMENTS, encoder=second_encoder, cache_dir=cache_dir)

    assert second.cache_key != first.cache_key
    assert second.cache_status == "miss"
    assert second_encoder.calls == [["甲文档", "乙文档", "丙文档"]]


@pytest.mark.parametrize("invalid_vectors", [
    [{"not": "a vector"}, {"not": "a vector"}, {"not": "a vector"}],
    "not-a-matrix",
    None,
])
def test_valid_json_with_invalid_vector_payload_is_corrupt(tmp_path, invalid_vectors):
    """合法 JSON + 非法 vectors 内容必须判 corrupt 并重建，不能抛 TypeError 终止评估。"""
    cache_dir = tmp_path / "cache"
    VECTORS = {"甲文档": [1.0, 0.0, 0.0], "乙文档": [0.0, 1.0, 0.0], "丙文档": [1.0, 0.0, 0.0]}
    reference = EmbeddingRetriever(DOCUMENTS, encoder=ConfiguredFake(dict(VECTORS)),
                                   cache_dir=tmp_path / "other-cache")
    cache_dir.mkdir()
    payload = json.loads(reference.cache_path.read_text(encoding="utf-8"))
    payload["vectors"] = invalid_vectors
    (cache_dir / f"{reference.cache_key}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    encoder = ConfiguredFake(dict(VECTORS))
    retriever = EmbeddingRetriever(DOCUMENTS, encoder=encoder, cache_dir=cache_dir)

    assert retriever.cache_status == "corrupt"
    assert "缓存向量不可用" in retriever.cache_reason
    assert encoder.calls == [["甲文档", "乙文档", "丙文档"]]
    assert np.array_equal(retriever.document_vectors, reference.document_vectors)
    json.loads(retriever.cache_path.read_text(encoding="utf-8"))  # 已用有效内容重写


def test_cache_can_be_disabled(tmp_path):
    cache_dir = tmp_path / "cache"
    encoder = ConfiguredFake({"甲文档": [1.0, 0.0, 0.0], "乙文档": [0.0, 1.0, 0.0],
                              "丙文档": [1.0, 0.0, 0.0]})

    retriever = EmbeddingRetriever(DOCUMENTS, encoder=encoder, cache_dir=cache_dir,
                                   use_cache=False)

    assert retriever.cache_status == "disabled"
    assert not cache_dir.exists()
    assert encoder.calls == [["甲文档", "乙文档", "丙文档"]]


