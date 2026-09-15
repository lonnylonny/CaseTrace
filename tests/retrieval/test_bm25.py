import pytest

from casetrace.retrieval.bm25 import BM25Retriever, tokenize


def test_tokenize_mixed_text_preserves_ids_and_normalizes_case():
    assert tokenize("焊线脱落 PROD_001 Wire-Bond！") == [
        "焊线", "线脱", "脱落", "prod_001", "wire-bond",
    ]


def test_ranks_term_matches_and_returns_source_ids():
    retriever = BM25Retriever({
        "C1": "wire lift pad contamination",
        "C2": "molding void vacuum",
        "C3": "lead corrosion",
        "C4": "bga ball missing",
    })
    hits = retriever.search("WIRE lift", top_k=2)
    assert [hit.case_id for hit in hits] == ["C1"]
    assert hits[0].matched_terms == ["lift", "wire"]
    assert hits[0].score > 0


def test_chinese_query_matches_inside_longer_sentence():
    retriever = BM25Retriever({"C1": "发现焊线脱落", "C2": "塑封空洞", "C3": "引脚腐蚀"})
    assert retriever.search("脱落")[0].case_id == "C1"


def test_empty_and_unknown_queries_return_no_matches():
    retriever = BM25Retriever({"C1": "wire lift"})
    for query in ["", "！？", "banana"]:
        assert retriever.search(query) == []


def test_common_terms_are_not_mistaken_for_no_match():
    # 小语料中 Okapi 的 IDF 可能非正；是否命中要看词项交集，不按 score > 0 判断。
    retriever = BM25Retriever({"C2": "wire", "C1": "wire"})
    assert [hit.case_id for hit in retriever.search("wire", top_k=1)] == ["C1"]


def test_empty_documents_and_invalid_top_k_are_rejected():
    for documents in [{}, {"C1": "！？"}, {"C1": "wire", "C2": ""}]:
        with pytest.raises(ValueError):
            BM25Retriever(documents)
    retriever = BM25Retriever({"C1": "wire"})
    for top_k in [0, -1, True, 1.5]:
        with pytest.raises(ValueError):
            retriever.search("wire", top_k=top_k)
