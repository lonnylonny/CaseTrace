import json
from pathlib import Path
import sys

import pytest

from casetrace import main
from casetrace.demo import build_documents, load_demo, run_demo
from casetrace.data.reference import load_reference


@pytest.mark.parametrize("query_index", [0, 1, 2])
def test_real_demo_cli_returns_stable_traceable_results(query_index, monkeypatch, capsys):
    """检查实际开发数据和 CLI 默认路径；不将当前排名当成 Ground Truth。"""
    project_root = Path(__file__).resolve().parents[1]
    payload = json.loads((project_root / "data/dev/demo.json").read_text(encoding="utf-8"))
    query = payload["queries"][query_index]["text"]
    args = ["casetrace", "demo", "--json"]
    if query_index != 0:
        args.extend(["--query", query])
    monkeypatch.chdir(project_root)
    monkeypatch.setattr(sys, "argv", args)

    main()
    result = json.loads(capsys.readouterr().out)
    main()
    assert json.loads(capsys.readouterr().out) == result
    assert result["query"] == query
    assert result["case_count"] == len(payload["cases"])
    assert result["review_status"] == "development_draft_pending_human_review"
    assert result["results"]
    assert len({hit["case_id"] for hit in result["results"]}) == len(result["results"])

    cases = {case["case_id"]: case for case in payload["cases"]}
    for hit in result["results"]:
        case = cases[hit["case_id"]]
        assert hit["abnormal_description"] == case["abnormal_description"]
        assert hit["root_cause"] == case["root_cause"]
        assert hit["evidences"] == [
            {"checkpoint_id": item["checkpoint_id"], "result": item["result"]}
            for item in payload["evidences"] if item["case_id"] == hit["case_id"]
        ]
        assert hit["evidences"]


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
