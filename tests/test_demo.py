import json

import pytest

from casetrace.demo import build_documents, load_demo, run_demo
from casetrace.data.reference import load_reference


def test_demo_returns_traceable_sources_without_certifying_ground_truth(demo_path, reference_path):
    result = run_demo(demo_path, reference_path, query=None, top_k=1)
    assert result["case_count"] == 2
    assert result["review_status"] == "development_draft_pending_human_review"
    hit = result["results"][0]
    assert hit["case_id"] == "C1"
    assert hit["evidences"][0]["checkpoint_id"] == "E1"


def test_query_and_annotation_metadata_never_enter_documents(demo_path, reference_path):
    records, _ = load_demo(demo_path)
    records["queries"] = [{"text": "FUTURE_CAUSE_LEAK"}]
    records["sources"] = {"C1": "ANNOTATION_LEAK"}
    documents = build_documents(records, load_reference(reference_path))
    assert all("LEAK" not in text for text in documents.values())
    assert all("C1" not in text and "E1" not in text for text in documents.values())


@pytest.mark.parametrize("mutation,message", [
    ("invalid_quantity", "CR-23"),
    ("source_changed", "候选已不在主数据"),
    ("missing_details", "CR-01"),
    ("no_related_evidence", "CR-35"),
    ("wrong_mode_source", "未对应"),
])
def test_invalid_data_stops_before_retrieval(demo_path, reference_path, mutation, message):
    payload = json.loads(demo_path.read_text())
    if mutation == "invalid_quantity":
        payload["details"][0]["affected_qty"] = True
    elif mutation == "source_changed":
        payload["sources"]["C1"]["root_cause"] = "不在候选库的新原因"
    elif mutation == "missing_details":
        payload["details"] = []
    elif mutation == "no_related_evidence":
        payload["evidences"][0]["relevance"] = "uncertain"
    else:
        payload["sources"]["C1"]["failure_mode_id"] = "another-mode"
    demo_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        run_demo(demo_path, reference_path, query="焊线", top_k=3)
