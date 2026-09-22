"""异常站点通过公开的字段与 Dataset 校验入口验证。"""

from copy import deepcopy
from dataclasses import replace

import pytest
from openpyxl import load_workbook

from casetrace.data.dataset_model import Case, CaseGroup, Membership
from casetrace.data.reference import load_reference
from casetrace.data.validators import validate_case_fields, validate_relations
from casetrace.demo import load_demo


@pytest.mark.parametrize("processes", [None, [], "P004", [" "], [1], [[]], ["P004", "P004"]])
def test_case_requires_nonempty_distinct_process_ids(processes):
    case = Case("C1", "异常", "NDF", "加强监控", None, abnormal_processes=processes)
    errors = validate_case_fields(case, location="Case[C1]")
    assert len(errors) == 1
    assert errors[0].startswith("CR-48 | Case[C1] | abnormal_processes")


@pytest.mark.parametrize("processes", [["P004"], ["P007", "P004"]])
def test_ndf_case_can_have_one_or_multiple_confirmed_processes(processes):
    case = Case("C1", "异常", "NDF", "加强监控", None, abnormal_processes=processes)
    assert validate_case_fields(case, location="Case[C1]") == []


def test_case_has_no_default_for_unknown_processes():
    with pytest.raises(TypeError, match="abnormal_processes"):
        Case("C1", "异常", "NDF", "加强监控", None)


@pytest.fixture
def dataset(demo_path, reference_path):
    records, _ = load_demo(demo_path)
    return dict(**records, **load_reference(reference_path).validator_maps())


def test_case_uses_union_of_all_product_routes_without_mutating_input(dataset):
    dataset["cases"] = [replace(dataset["cases"][0], abnormal_processes=["P004", "P005"])]
    dataset["details"][1] = replace(
        dataset["details"][1], case_id="C1", product_id="P2", production_lot="PL2",
    )
    dataset["evidences"] = dataset["evidences"][:1]
    dataset["product_customers"]["P2"] = "CUS1"
    dataset["product_routes"]["P2"] = "SUBSTRATE_FC"
    dataset["failure_mode_routes"]["00001"].add("SUBSTRATE_FC")
    dataset["processes"]["P005"] = "Flip Chip Attach"
    dataset["route_processes"]["SUBSTRATE_FC"] = {"P005"}
    before = deepcopy(dataset)
    assert validate_relations(**dataset) == []
    assert dataset == before


def test_same_process_group_needs_global_intersection_not_pairwise_overlap(dataset):
    dataset["cases"] = [
        replace(dataset["cases"][0], abnormal_processes=["P004", "P007"]),
        replace(dataset["cases"][1], abnormal_processes=["P004", "P013"]),
        replace(dataset["cases"][0], case_id="C3", abnormal_processes=["P007", "P013"]),
    ]
    dataset["details"].append(replace(dataset["details"][0], detail_id="D3", case_id="C3"))
    dataset["evidences"].append(replace(dataset["evidences"][0], checkpoint_id="E3", case_id="C3"))
    dataset["groups"] = [CaseGroup("G1", ["same_abnormal_process", "project"], "共同站点调查", None)]
    dataset["memberships"] = [Membership("G1", key, "异常站点关联") for key in ("C1", "C2", "C3")]
    errors = validate_relations(**dataset)
    assert len(errors) == 1
    assert errors[0].startswith("CR-51 | CaseGroup[G1]")
    dataset["cases"][2].abnormal_processes.append("P004")
    assert validate_relations(**dataset) == []


@pytest.mark.parametrize("process_id,message", [("missing", "不存在"), ("P005", "工序并集")])
def test_unknown_or_out_of_route_process_is_rejected(dataset, process_id, message):
    dataset["processes"]["P005"] = "Flip Chip Attach"
    dataset["cases"][0].abnormal_processes = [process_id]
    errors = validate_relations(**dataset)
    assert len(errors) == 1
    assert errors[0].startswith("CR-49 | Case[C1] | abnormal_processes[0]")
    assert message in errors[0]


@pytest.mark.parametrize("field,value", [
    ("processes", None), ("processes", {}), ("processes", {"P004": " "}),
    ("processes", {1: "Wire Bond"}), ("route_processes", []), ("route_processes", {}),
    ("route_processes", {"LF_WB": []}), ("route_processes", {"LF_WB": set()}),
    ("route_processes", {"LF_WB": {1}}), ("route_processes", {"LF_WB": {"missing"}}),
    ("route_processes", {"OTHER": {"P004"}}),
])
def test_invalid_process_maps_explicitly_stop_dependent_checks(dataset, field, value):
    dataset[field] = value
    errors = validate_relations(**dataset)
    assert any(error.startswith("主数据 |") for error in errors)
    assert "未执行" in errors[-1]
    assert not any(error.startswith(("CR-49 |", "CR-51 |")) for error in errors)


@pytest.mark.parametrize("types,shared", [
    (["same_abnormal_process"], True), (["same_abnormal_process", "project"], False),
    (["project"], False), (["same_abnormal_process", "repeat_case"], True),
])
def test_group_types_apply_their_own_deterministic_requirements(dataset, types, shared):
    dataset["groups"] = [CaseGroup("G1", types, "调查分组", None)]
    dataset["memberships"] = [Membership("G1", key, "入组理由") for key in ("C1", "C2")]
    if not shared:
        dataset["cases"][1].abnormal_processes = ["P007"]
    errors = validate_relations(**dataset)
    if "same_abnormal_process" in types and not shared:
        assert len(errors) == 1
        assert errors[0].startswith("CR-51 |")
    else:
        # repeat_case 的复发关系仍由语义审查负责，确定性通过不证明语义成立。
        assert errors == []


def test_same_process_group_can_span_customers_and_products(dataset):
    dataset["product_customers"]["P2"] = "CUS2"
    dataset["product_routes"]["P2"] = "LF_WB"
    dataset["details"][1] = replace(dataset["details"][1], product_id="P2", production_lot="PL2")
    dataset["groups"] = [CaseGroup("G1", ["same_abnormal_process"], "跨客户站点调查", None)]
    dataset["memberships"] = [Membership("G1", key, "涉及 Wire Bond") for key in ("C1", "C2")]
    assert validate_relations(**dataset) == []


def test_invalid_case_process_does_not_become_a_shared_group_process(dataset):
    for case in dataset["cases"]:
        case.abnormal_processes = ["missing"]
    dataset["groups"] = [CaseGroup("G1", ["same_abnormal_process"], "站点调查", None)]
    dataset["memberships"] = [Membership("G1", key, "共同站点") for key in ("C1", "C2")]
    errors = validate_relations(**dataset)
    assert sum(error.startswith("CR-49 |") for error in errors) == 2
    assert "同站点分组检查未执行" in errors[-1]


def test_invalid_process_element_stops_before_set_operations(dataset):
    dataset["cases"][0].abnormal_processes = [[]]
    errors = validate_relations(**dataset)
    assert errors[0].startswith("CR-48 |")
    assert "字段检查未通过" in errors[-1]


def test_failure_mode_candidate_processes_do_not_constrain_case(dataset, reference_path):
    workbook = load_workbook(reference_path)
    workbook["failure_modes"]["F1"] = "applicable_process"
    workbook["failure_modes"]["F2"] = "Wire Bond"
    workbook.save(reference_path)
    workbook.close()
    dataset.update(load_reference(reference_path).validator_maps())
    dataset["cases"][0].abnormal_processes = ["P013"]
    assert validate_relations(**dataset) == []
    assert dataset["cases"][0].abnormal_processes == ["P013"]
