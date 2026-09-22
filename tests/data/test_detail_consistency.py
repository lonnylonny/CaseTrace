"""批号固定属性与事件身份是两种不同的跨记录约束。"""

import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import date

from casetrace.data.dataset_model import Case, CaseDetail, EvidenceCheckpoint
from casetrace.data.validators import check_detail_consistency, validate_relations


class TestDetailConsistency(unittest.TestCase):
    def setUp(self):
        self.first = CaseDetail(
            detail_id="D1", case_id="C1", product_id="P1", customer_lot="CL1",
            production_lot="PL1", production_time=date(2026, 9, 1),
            detection_stage="OQC", detection_time=date(2026, 9, 2),
            abnormal_types=["001", "002"], affected_qty=4000, disposition="全部报废",
        )
        self.second = replace(self.first, detail_id="D2", detection_time=date(2026, 9, 3))

    def test_same_lot_can_have_different_events_and_overlapping_quantities(self):
        self.assertEqual(check_detail_consistency([self.first, self.second]), [])

    def test_different_lots_can_have_different_fixed_attributes(self):
        second = replace(self.second, production_lot="PL2", product_id="P2",
                         customer_lot="CL2", production_time=date(2026, 8, 1))
        self.assertEqual(check_detail_consistency([self.first, second]), [])

    def test_same_lot_fixed_attributes_must_match_even_across_cases(self):
        for field, value, rule in [
            ("product_id", "P2", "CR-08"),
            ("customer_lot", "CL2", "CR-09"),
            ("production_time", date(2026, 8, 1), "CR-10"),
        ]:
            with self.subTest(field=field):
                second = replace(self.second, case_id="C2", **{field: value})
                errors = check_detail_consistency([self.first, second])
                self.assertEqual(len(errors), 1)
                self.assertTrue(errors[0].startswith(f"{rule} | CaseDetail[D2] | {field} |"))
                self.assertIn("PL1", errors[0])
                self.assertIn("CaseDetail[D1]", errors[0])

    def test_reports_all_conflicting_fixed_attributes(self):
        second = replace(self.second, product_id="P2", customer_lot="CL2",
                         production_time=date(2026, 8, 1))
        errors = check_detail_consistency([self.first, second])
        self.assertEqual([error.split(" | ")[0] for error in errors], ["CR-08", "CR-09", "CR-10"])

    def test_first_lot_record_is_not_overwritten_after_conflict(self):
        conflicting = replace(self.second, product_id="P2")
        third = replace(self.first, detail_id="D3", detection_time=date(2026, 9, 4))
        errors = check_detail_consistency([self.first, conflicting, third])
        self.assertEqual(len(errors), 1)
        self.assertIn("CaseDetail[D2]", errors[0])

    def test_event_identity_ignores_detail_id_quantity_and_disposition(self):
        duplicate = replace(self.first, detail_id="D2", affected_qty=1, disposition="筛选后放行")
        errors = check_detail_consistency([self.first, duplicate])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("CR-11 | CaseDetail[D2] |"))
        self.assertIn("CaseDetail[D1]", errors[0])

    def test_abnormal_order_does_not_create_new_event(self):
        duplicate = replace(self.first, detail_id="D2", abnormal_types=["002", "001"])
        errors = check_detail_consistency([self.first, duplicate])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("CR-11 |"))

    def test_each_event_key_component_can_distinguish_records(self):
        for field, value in [
            ("case_id", "C2"), ("production_lot", "PL2"),
            ("detection_stage", "Customer"), ("detection_time", date(2026, 9, 3)),
            ("abnormal_types", ["001"]),
        ]:
            with self.subTest(field=field):
                second = replace(self.first, detail_id="D2", **{field: value})
                self.assertEqual(check_detail_consistency([self.first, second]), [])

    def test_repeated_event_reports_first_detail_for_each_duplicate(self):
        records = [self.first, replace(self.first, detail_id="D2"), replace(self.first, detail_id="D3")]
        errors = check_detail_consistency(records)
        self.assertEqual(len(errors), 2)
        self.assertTrue(all("与 CaseDetail[D1]" in error for error in errors))

    def test_check_does_not_mutate_input(self):
        records = [self.first, replace(self.first, detail_id="D2", abnormal_types=["002", "001"])]
        before = deepcopy(records)
        check_detail_consistency(records)
        self.assertEqual(records, before)

    def dataset(self, second):
        return dict(
            cases=[Case("C1", "异常", "NDF", "加强监控", None, abnormal_processes=["P004"])],
            details=[self.first, second],
            evidences=[EvidenceCheckpoint("E1", "C1", "QC", None, "检查结果", "uncertain")],
            groups=[], memberships=[],
            product_customers={"P1": "CUS1"}, product_routes={"P1": "LF_WB"},
            failure_mode_routes={"001": {"LF_WB"}, "002": {"LF_WB"}},
            processes={"P004": "Wire Bond"}, route_processes={"LF_WB": {"P004"}},
        )

    def test_relations_entry_runs_consistency_checks(self):
        self.assertEqual(validate_relations(**self.dataset(self.second)), [])
        for second, rule in [
            (replace(self.second, customer_lot="CL2"), "CR-09"),
            (replace(self.first, detail_id="D2"), "CR-11"),
        ]:
            errors = validate_relations(**self.dataset(second))
            self.assertEqual(len(errors), 2)
            self.assertTrue(errors[0].startswith(f"{rule} |"))
            self.assertIn("主数据关联检查未执行", errors[1])

    def test_invalid_abnormal_elements_stop_before_event_key_construction(self):
        errors = validate_relations(**self.dataset(replace(self.second, abnormal_types=[[]])))
        self.assertEqual(len(errors), 2)
        self.assertIn("abnormal_types[0]", errors[0])
        self.assertIn("未执行", errors[1])

    def test_reference_error_does_not_hide_independent_lot_conflict(self):
        second = replace(self.second, case_id="missing", product_id="P2")
        errors = validate_relations(**self.dataset(second))
        self.assertTrue(any(error.startswith("CR-02 |") for error in errors))
        self.assertTrue(any(error.startswith("CR-08 |") for error in errors))
