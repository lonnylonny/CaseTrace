"""只测试 Dataset 内实体关系；不使用主数据或 Locked Test。"""

import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import date

from casetrace.data.dataset_model import Case, CaseDetail, CaseGroup, EvidenceCheckpoint, Membership
from casetrace.data.validators import build_unique_index, validate_relations


def make_dataset():
    cases, details, evidences = [], [], []
    for number in [1, 2]:
        case_id = f"C{number}"
        cases.append(Case(case_id, "异常", "NDF", "加强监控", None, abnormal_processes=["P004"]))
        details.append(CaseDetail(
            detail_id=f"D{number}", case_id=case_id, product_id="P1",
            customer_lot=f"CL{number}", production_lot=f"PL{number}",
            production_time=date(2026, 9, 1), detection_stage="OQC",
            detection_time=date(2026, 9, 2), abnormal_types=["001"],
            affected_qty=1, disposition="全部报废",
        ))
        evidences.append(EvidenceCheckpoint(f"E{number}", case_id, "QC", None, "检查结果", "uncertain"))
    return dict(
        cases=cases, details=details, evidences=evidences,
        groups=[CaseGroup("G1", ["project"], "项目调查", None)],
        memberships=[Membership("G1", "C1", "项目成员"), Membership("G1", "C2", "项目成员")],
        product_customers={"P1": "CUS1"}, product_routes={"P1": "LF_WB"},
        failure_mode_routes={"001": {"LF_WB"}},
        processes={"P004": "Wire Bond"}, route_processes={"LF_WB": {"P004"}},
    )


class TestUniqueIndex(unittest.TestCase):
    def test_duplicate_id_keeps_first_record_and_reports_both_positions(self):
        first = make_dataset()["cases"][0]
        second = replace(first, abnormal_description="另一条记录")
        index, errors = build_unique_index([first, second], id_field="case_id", object_name="Case")
        self.assertIs(index["C1"], first)
        self.assertEqual(len(index), 1)
        self.assertEqual(len(errors), 1)
        self.assertIn("Case[1]", errors[0])
        self.assertIn("Case[0]", errors[0])


class TestRelations(unittest.TestCase):
    def setUp(self):
        self.dataset = make_dataset()

    def test_valid_dataset_passes_without_mutation(self):
        before = deepcopy(self.dataset)
        self.assertEqual(validate_relations(**self.dataset), [])
        self.assertEqual(self.dataset, before)

    def test_groups_are_optional(self):
        self.dataset.update(groups=[], memberships=[])
        self.assertEqual(validate_relations(**self.dataset), [])

    def test_case_can_belong_to_multiple_groups(self):
        self.dataset["groups"].append(CaseGroup("G2", ["customer_request"], "客户请求", None))
        self.dataset["memberships"].extend([
            Membership("G2", "C1", "客户请求"), Membership("G2", "C2", "客户请求"),
        ])
        self.assertEqual(validate_relations(**self.dataset), [])

    def test_entity_ids_are_unique_within_each_type(self):
        for collection in ["cases", "details", "evidences", "groups"]:
            with self.subTest(collection=collection):
                dataset = make_dataset()
                dataset[collection].append(replace(dataset[collection][0]))
                errors = validate_relations(**dataset)
                self.assertTrue(any(error.startswith("CR-03 |") for error in errors))
                self.assertIn("未执行", errors[-1])
                self.assertFalse(any(error.startswith("CR-38 |") for error in errors))

    def test_same_id_across_object_types_is_allowed(self):
        self.dataset["groups"][0] = replace(self.dataset["groups"][0], group_id="C1")
        self.dataset["memberships"] = [replace(item, group_id="C1") for item in self.dataset["memberships"]]
        self.assertEqual(validate_relations(**self.dataset), [])

    def test_invalid_fields_stop_relation_checks(self):
        self.dataset["details"][0] = replace(self.dataset["details"][0], detail_id=[])
        errors = validate_relations(**self.dataset)
        self.assertEqual(len(errors), 2)
        self.assertIn("detail_id", errors[0])
        self.assertIn("字段检查未通过", errors[1])
        self.assertIn("未执行", errors[1])

    def test_missing_case_for_children_is_reported(self):
        for collection, rule in [("details", "CR-02"), ("evidences", "CR-31")]:
            with self.subTest(collection=collection):
                dataset = make_dataset()
                dataset[collection][0] = replace(dataset[collection][0], case_id="missing")
                errors = validate_relations(**dataset)
                self.assertTrue(any(error.startswith(f"{rule} |") and "missing" in error for error in errors))

    def test_moving_child_checks_the_original_case_minimum(self):
        """归属只取子记录 case_id；其他 Case 的记录不能凑足本 Case 的最少数量。"""
        for collection, rule in [("details", "CR-01"), ("evidences", "CR-30")]:
            with self.subTest(collection=collection):
                dataset = make_dataset()
                dataset[collection][0] = replace(dataset[collection][0], case_id="C2")
                errors = validate_relations(**dataset)
                minimum_errors = [error for error in errors if error.startswith(f"{rule} |")]
                self.assertEqual(len(minimum_errors), 1)
                self.assertIn("Case[C1]", minimum_errors[0])

    def test_adding_child_requires_only_its_case_id(self):
        for collection, child in [
            ("details", replace(self.dataset["details"][0], detail_id="D3",
                                detection_time=date(2026, 9, 3))),
            ("evidences", replace(self.dataset["evidences"][0], checkpoint_id="E3")),
        ]:
            with self.subTest(collection=collection):
                dataset = make_dataset()
                dataset[collection].append(child)
                self.assertEqual(validate_relations(**dataset), [])

    def test_case_must_have_actual_detail_and_evidence(self):
        for collection, rule in [("details", "CR-01"), ("evidences", "CR-30")]:
            with self.subTest(collection=collection):
                dataset = make_dataset()
                dataset[collection] = []
                errors = validate_relations(**dataset)
                self.assertEqual(sum(error.startswith(f"{rule} |") for error in errors), 2)

    def test_child_record_order_does_not_matter(self):
        self.dataset["details"].append(replace(
            self.dataset["details"][0], detail_id="D3", detection_time=date(2026, 9, 3),
        ))
        self.dataset["details"].reverse()
        self.dataset["evidences"].reverse()
        self.assertEqual(validate_relations(**self.dataset), [])

    def test_membership_references_both_existing_case_and_group(self):
        self.dataset["memberships"].append(Membership("missing-group", "missing-case", "关联"))
        errors = validate_relations(**self.dataset)
        self.assertEqual(len(errors), 3)
        self.assertTrue(all(error.startswith("CR-39 |") for error in errors[:2]))
        self.assertIn("主数据关联检查未执行", errors[2])

    def test_duplicate_membership_is_rejected_even_with_different_reason(self):
        self.dataset["memberships"].append(replace(self.dataset["memberships"][0], association_reason="另一理由"))
        errors = validate_relations(**self.dataset)
        self.assertEqual(len(errors), 2)
        self.assertTrue(errors[0].startswith("CR-40 |"))
        self.assertIn("主数据关联检查未执行", errors[1])

    def test_group_requires_two_distinct_valid_members(self):
        for members in [[], [Membership("G1", "C1", "关联")],
                        [Membership("G1", "C1", "关联"), Membership("G1", "C1", "重复")],
                        [Membership("G1", "C1", "关联"), Membership("G1", "missing", "悬空引用")]]:
            with self.subTest(members=members):
                self.dataset["memberships"] = members
                errors = validate_relations(**self.dataset)
                self.assertTrue(any(error.startswith("CR-38 | CaseGroup[G1]") for error in errors))

    def test_reports_multiple_independent_relation_errors(self):
        self.dataset["memberships"] = [Membership("G1", "C1", "关联")]
        self.dataset["details"][0] = replace(self.dataset["details"][0], case_id="missing")
        errors = validate_relations(**self.dataset)
        self.assertTrue(any(error.startswith("CR-02 |") for error in errors))
        self.assertTrue(any(error.startswith("CR-38 |") for error in errors))
