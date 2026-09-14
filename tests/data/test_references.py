"""人工主数据映射用于验证规则；不依赖 Excel 读取。"""

import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import date

from casetrace.data.dataset_model import Case, CaseDetail, EvidenceCheckpoint, CaseGroup, Membership
from casetrace.data.validators import check_detail_references, validate_relations


class TestDetailReferences(unittest.TestCase):
    def setUp(self):
        self.first = CaseDetail(
            "D1", "C1", "P1", "CL1", "PL1", date(2026, 9, 1),
            "OQC", date(2026, 9, 2), ["00001"], 1, "全部报废",
        )
        self.second = replace(self.first, detail_id="D2", product_id="P2",
                              production_lot="PL2", customer_lot="CL2")
        self.reference = dict(
            product_customers={"P1": "CUS1", "P2": "CUS1", "P3": "CUS2"},
            product_routes={"P1": "LF_WB", "P2": "SUBSTRATE_FC", "P3": "LF_WB"},
            failure_mode_routes={"00001": {"LF_WB", "SUBSTRATE_FC"}, "00002": {"LF_WB"}},
        )

    def test_same_case_can_have_multiple_products_of_one_customer(self):
        self.assertEqual(check_detail_references([self.first, self.second], **self.reference), [])

    def test_case_cannot_mix_customers(self):
        second = replace(self.second, product_id="P3")
        errors = check_detail_references([self.first, second], **self.reference)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("CR-04 | Case[C1] |"))
        self.assertIn("CUS1", errors[0])
        self.assertIn("CUS2", errors[0])

    def test_different_cases_can_have_different_customers(self):
        second = replace(self.second, case_id="C2", product_id="P3")
        self.assertEqual(check_detail_references([self.first, second], **self.reference), [])

    def test_unknown_product_does_not_hide_unknown_failure_mode(self):
        detail = replace(self.first, product_id="missing", abnormal_types=["missing"])
        errors = check_detail_references([detail], **self.reference)
        self.assertEqual([e.split(" | ")[0] for e in errors], ["CR-05", "CR-15"])

    def test_failure_mode_id_keeps_leading_zeros(self):
        errors = check_detail_references([replace(self.first, abnormal_types=["1"])], **self.reference)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("CR-15 |"))

    def test_checks_route_for_every_selected_failure_mode(self):
        detail = replace(self.second, abnormal_types=["00001", "00002"])
        errors = check_detail_references([detail], **self.reference)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("CR-16 | CaseDetail[D2] | abnormal_types[1] |"))
        self.assertIn("00002", errors[0])
        self.assertIn("SUBSTRATE_FC", errors[0])

    def test_unknown_failure_mode_does_not_hide_other_route_error(self):
        detail = replace(self.second, abnormal_types=["missing", "00002"])
        errors = check_detail_references([detail], **self.reference)
        self.assertEqual([e.split(" | ")[0] for e in errors], ["CR-15", "CR-16"])

    def test_unknown_product_does_not_invent_route_mismatch(self):
        errors = check_detail_references([replace(self.first, product_id="missing")], **self.reference)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("CR-05 |"))

    def test_reference_maps_require_correct_container_and_value_shapes(self):
        for name, value in [
            ("product_customers", None), ("product_routes", []), ("failure_mode_routes", None),
            ("product_customers", {"P1": ["CUS1", "CUS2"]}),
            ("product_routes", {"P1": " "}),
            ("failure_mode_routes", {1: {"LF_WB"}}),
            ("failure_mode_routes", {"00001": "LF_WB"}),
            ("failure_mode_routes", {"00001": {1}}),
        ]:
            with self.subTest(name=name, value=value):
                reference = dict(self.reference, **{name: value})
                errors = check_detail_references([self.first], **reference)
                self.assertTrue(any(e.startswith("主数据 |") for e in errors))
                self.assertIn("未执行", errors[-1])

    def test_product_maps_must_cover_same_products(self):
        for field in ["product_customers", "product_routes"]:
            reference = deepcopy(self.reference)
            del reference[field]["P1"]
            errors = check_detail_references([self.first], **reference)
            self.assertTrue(any("P1" in e for e in errors))
            self.assertIn("未执行", errors[-1])

    def test_empty_maps_do_not_silently_pass_referenced_data(self):
        errors = check_detail_references([self.first], product_customers={}, product_routes={}, failure_mode_routes={})
        self.assertEqual([e.split(" | ")[0] for e in errors], ["CR-05", "CR-15"])

    def test_input_is_not_modified(self):
        details = [self.first, self.second]
        before = deepcopy((details, self.reference))
        check_detail_references(details, **self.reference)
        self.assertEqual((details, self.reference), before)

    def dataset(self):
        return dict(
            cases=[Case("C1", "异常", "NDF", "加强监控", None)],
            details=[self.first, self.second],
            evidences=[EvidenceCheckpoint("E1", "C1", "QC", None, "检查结果", "uncertain")],
            groups=[], memberships=[], **self.reference,
        )

    def test_relations_entry_runs_reference_checks(self):
        dataset = self.dataset()
        self.assertEqual(validate_relations(**dataset), [])
        dataset["details"][1] = replace(self.second, product_id="P3")
        errors = validate_relations(**dataset)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("CR-04 |"))

    def test_relation_failure_explicitly_skips_reference_checks(self):
        dataset = self.dataset()
        dataset["details"][1] = replace(self.second, case_id="missing")
        errors = validate_relations(**dataset)
        self.assertTrue(any(e.startswith("CR-02 |") for e in errors))
        self.assertIn("主数据关联检查未执行", errors[-1])

    def test_management_group_can_span_customers(self):
        dataset = self.dataset()
        dataset["cases"].append(Case("C2", "异常", "NDF", "加强监控", None))
        dataset["details"][1] = replace(self.second, case_id="C2", product_id="P3")
        dataset["evidences"].append(replace(dataset["evidences"][0], checkpoint_id="E2", case_id="C2"))
        dataset["groups"] = [CaseGroup("G1", ["project"], "管理项目", None)]
        dataset["memberships"] = [Membership("G1", "C1", "关联"), Membership("G1", "C2", "关联")]
        self.assertEqual(validate_relations(**dataset), [])
