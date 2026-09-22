"""固定开发 benchmark 的迁移溯源，不计算或宣称检索质量。"""

import hashlib
from itertools import product
import json
from pathlib import Path


def test_v2_preserves_old_snapshot_queries_and_only_confirmed_label_correction():
    root = Path(__file__).resolve().parents[1]
    old_path = root / "data/evaluation/dev-v1/qrels.json"
    old = json.loads(old_path.read_bytes())
    snapshot = root / "data/evaluation/dev-v1/dataset.snapshot.json"
    previous_data = json.loads(snapshot.read_bytes())
    new = json.loads((root / "data/evaluation/dev-v2/qrels.json").read_bytes())
    current_data = json.loads((root / new["sources"]["dataset"]["path"]).read_bytes())

    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == old["sources"]["dataset"]["sha256"]
    assert hashlib.sha256(old_path.read_bytes()).hexdigest() == "c0175226433332e1ac592e0850248fe7bd4dbde9173d3c8f0773c2d1602a245e"
    assert new["previous_qrels"]["sha256"] == hashlib.sha256(old_path.read_bytes()).hexdigest()
    for source in new["sources"].values():
        assert hashlib.sha256((root / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    assert current_data["queries"] == previous_data["queries"]
    assert current_data["details"] == previous_data["details"]
    assert current_data["sources"]["C002"]["simulation_revision"]["evidence_ids"] == ["E002"]
    assert new["split"] == "development"
    assert len(new["judgments"]) == 18
    old_by_pair = {(row["query_id"], row["case_id"]): row for row in old["judgments"]}
    new_by_pair = {(row["query_id"], row["case_id"]): row for row in new["judgments"]}
    assert new_by_pair.keys() == old_by_pair.keys()
    changed = [pair for pair in old_by_pair if old_by_pair[pair] != new_by_pair[pair]]
    assert changed == [("Q001", "C002")]
    assert new_by_pair[("Q001", "C002")]["relevance"] == 1
    assert [sum(row["relevance"] for row in new["judgments"] if row["query_id"] == query)
            for query in ("Q001", "Q002", "Q003")] == [4, 1, 1]


def test_v2_confirmation_covers_complete_binary_labels_and_current_sources():
    root = Path(__file__).resolve().parents[1]
    qrels = json.loads((root / "data/evaluation/dev-v2/qrels.json").read_bytes())
    data = json.loads((root / qrels["sources"]["dataset"]["path"]).read_bytes())

    assert qrels["qrels_version"] == "dev-qrels-v2"
    assert qrels["review_status"] == "human_confirmed"
    assert qrels["confirmed_on"] == "2026-09-19"
    assert qrels["confirmation_scope"] == "dev_v2_data_version_and_all_18_binary_labels"
    assert qrels["split"] == data["split"] == "development"
    for source in qrels["sources"].values():
        assert hashlib.sha256((root / source["path"]).read_bytes()).hexdigest() == source["sha256"]

    case_ids = [case["case_id"] for case in data["cases"]]
    query_ids = [query["query_id"] for query in data["queries"]]
    pairs = [(row["query_id"], row["case_id"]) for row in qrels["judgments"]]
    assert len(case_ids) == len(set(case_ids)) == 6
    assert len(query_ids) == len(set(query_ids)) == 3
    assert len(pairs) == len(set(pairs)) == 18
    assert set(pairs) == set(product(query_ids, case_ids))
    assert all(type(row["relevance"]) is int and row["relevance"] in (0, 1)
               for row in qrels["judgments"])
    assert {query: {row["case_id"] for row in qrels["judgments"]
                    if row["query_id"] == query and row["relevance"] == 1}
            for query in query_ids} == {
        "Q001": {"C001", "C002", "C003", "C004"},
        "Q002": {"C005"},
        "Q003": {"C006"},
    }

    # qrels 的确认不能自动升级源 Case 的审阅状态。
    assert data["review_status"] == "draft_pending_human_review"
    assert all(source["review_status"] == "draft_pending_human_review"
               for source in data["sources"].values())
