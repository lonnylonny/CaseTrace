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
    reference = load_reference(project_root / "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx")
    for hit in result["results"]:
        case = cases[hit["case_id"]]
        assert hit["abnormal_description"] == case["abnormal_description"]
        assert hit["root_cause"] == case["root_cause"]
        assert hit["abnormal_processes"] == sorted(case["abnormal_processes"])
        assert hit["abnormal_process_names"] == [reference.processes[key] for key in hit["abnormal_processes"]]
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


def test_documents_include_only_selected_processes_in_stable_order(demo_path, reference_path):
    records, _ = load_demo(demo_path)
    reference = load_reference(reference_path)
    records["cases"][0].abnormal_processes = ["P013", "P004"]
    records["groups"] = [{"description": "GROUP_REASON_LEAK"}]
    records["memberships"] = [{"association_reason": "MEMBERSHIP_LEAK"}]
    records["qrels"] = [{"rationale": "QRELS_LEAK"}]
    documents = build_documents(records, reference)
    assert documents["C1"].count("P004") == 1
    assert documents["C1"].count("Wire Bond") == 1
    assert "P013" in documents["C1"] and "Storage & Transportation" in documents["C1"]
    assert "P007" not in documents["C1"] and "Molding" not in documents["C1"]
    assert all("LEAK" not in text for text in documents.values())
    records["cases"][0].abnormal_processes.reverse()
    assert build_documents(records, reference) == documents
    assert records["cases"][0].abnormal_processes == ["P004", "P013"]


def test_process_query_returns_selected_ids_and_names(demo_path, reference_path):
    result = run_demo(demo_path, reference_path, query="P004", top_k=2)
    assert len(result["results"]) == 2
    for hit in result["results"]:
        assert hit["abnormal_processes"] == ["P004"]
        assert hit["abnormal_process_names"] == ["Wire Bond"]
    assert run_demo(demo_path, reference_path, query="P007", top_k=2)["results"] == []


def test_old_case_json_is_rejected_without_guessing_process(demo_path):
    payload = json.loads(demo_path.read_text())
    del payload["cases"][0]["abnormal_processes"]
    demo_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Case\\[C1\\].*abnormal_processes.*必填"):
        load_demo(demo_path)


def test_cli_displays_abnormal_process(demo_path, reference_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "casetrace", "demo", "--data", str(demo_path), "--reference", str(reference_path),
    ])
    main()
    assert "异常站点：Wire Bond (P004)" in capsys.readouterr().out


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
