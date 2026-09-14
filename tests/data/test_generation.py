"""GR 生成限制的确定性检查；使用人工小样例，不依赖主数据文件或 Locked Test。"""

import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import date

from casetrace.data.dataset_model import Case, CaseDetail, EvidenceCheckpoint
from casetrace.data.validators import (
    check_case_detail_count,
    check_detail_generation_limits,
    check_production_lot_reuse,
    validate_generation,
    validate_relations,
)


def make_detail(
    detail_id, *, case_id="C1", production_lot="PL1", stage="OQC",
    detection_day=2, abnormal_types=("001",), qty=100,
):
    """构造字段合法的 Detail；改 detection_day/stage 可以让同一批号成为不同事件。"""
    return CaseDetail(
        detail_id=detail_id, case_id=case_id, product_id="P1", customer_lot="CL1",
        production_lot=production_lot, production_time=date(2026, 9, 1),
        detection_stage=stage, detection_time=date(2026, 9, detection_day),
        abnormal_types=list(abnormal_types), affected_qty=qty, disposition="全部报废",
    )


def make_case(case_id):
    return Case(case_id, "异常", "NDF", "加强监控", None)


class TestCaseDetailCount(unittest.TestCase):
    def test_accepts_one_to_three_details(self):
        for count in range(1, 4):
            with self.subTest(count=count):
                details = [make_detail(f"D{index}") for index in range(count)]
                case = make_case("C1")
                self.assertEqual(check_case_detail_count([case], details), [])

    def test_rejects_more_than_three_details(self):
        details = [make_detail(f"D{index}") for index in range(4)]
        case = make_case("C1")
        errors = check_case_detail_count([case], details)
        self.assertEqual(
            errors,
            ["GR-01 | Case[C1] | details | 每 Case 最多 3 个 Detail，当前 4 个"],
        )

    def test_reports_every_case_over_the_limit(self):
        cases = [make_case("C1"), make_case("C2")]
        details = [make_detail(f"D{index}") for index in range(4)]
        details.extend(make_detail(f"E{index}", case_id="C2") for index in range(4))
        errors = check_case_detail_count(cases, details)
        self.assertEqual(len(errors), 2)
        self.assertTrue(all(error.startswith("GR-01 |") for error in errors))

    def test_zero_details_is_left_to_cr01(self):
        cases = [make_case("C1"), make_case("C2")]
        errors = check_case_detail_count(cases, [make_detail("D1")])
        self.assertEqual(errors, [])

    def test_dangling_case_id_is_left_to_cr_reference_checks(self):
        cases = [make_case("C1")]
        details = [make_detail("D1"), make_detail("D2", case_id="missing")]
        self.assertEqual(check_case_detail_count(cases, details), [])

    def test_input_is_not_modified(self):
        cases = [make_case("C1")]
        details = [make_detail("D1")]
        before = deepcopy((cases, details))
        check_case_detail_count(cases, details)
        self.assertEqual((cases, details), before)


class TestDetailGenerationLimits(unittest.TestCase):
    def test_quantity_upper_bound(self):
        for qty in [1, 4999, 5000]:
            with self.subTest(qty=qty):
                self.assertEqual(check_detail_generation_limits([make_detail("D1", qty=qty)]), [])
        self.assertEqual(
            check_detail_generation_limits([make_detail("D1", qty=5001)]),
            ["GR-06 | CaseDetail[D1] | affected_qty | 每 Detail 上限 5000 ea，当前 5001"],
        )

    def test_abnormal_count_upper_bound(self):
        for types in [("001",), ("001", "002")]:
            with self.subTest(types=types):
                self.assertEqual(
                    check_detail_generation_limits([make_detail("D1", abnormal_types=types)]), [],
                )
        self.assertEqual(
            check_detail_generation_limits([make_detail("D1", abnormal_types=("001", "002", "003"))]),
            ["GR-02 | CaseDetail[D1] | abnormal_types | 生成只采样单异常或双异常，当前 3 个"],
        )

    def test_quantities_in_one_lot_are_not_summed(self):
        details = [
            make_detail("D1", stage="IQC", detection_day=2, qty=5000),
            make_detail("D2", stage="In-process", detection_day=3, qty=5000),
            make_detail("D3", stage="OQC", detection_day=4, qty=5000),
            make_detail("D4", stage="Customer", detection_day=5, qty=5000),
        ]
        self.assertEqual(check_detail_generation_limits(details), [])

    def test_reports_each_offending_detail(self):
        details = [make_detail("D1", qty=6000), make_detail("D2", qty=9000)]
        errors = check_detail_generation_limits(details)
        self.assertEqual([error.split(" | ")[0] for error in errors], ["GR-06", "GR-06"])

    def test_input_is_not_modified(self):
        details = [make_detail("D1", qty=6000, abnormal_types=("002", "001"))]
        before = deepcopy(details)
        check_detail_generation_limits(details)
        self.assertEqual(details, before)


class TestProductionLotReuse(unittest.TestCase):
    def test_one_or_two_reused_lots_pass(self):
        for lots in [["PL1", "PL1", "PL2"], ["PL1", "PL1", "PL2", "PL2"]]:
            with self.subTest(lots=lots):
                details = [make_detail(f"D{index}", production_lot=lot)
                           for index, lot in enumerate(lots)]
                self.assertEqual(check_production_lot_reuse(details), [])

    def test_lot_appearing_three_times_is_still_one_reused_lot(self):
        lots = ["PL1", "PL1", "PL1", "PL2"]
        details = [make_detail(f"D{index}", production_lot=lot) for index, lot in enumerate(lots)]
        self.assertEqual(check_production_lot_reuse(details), [])

    def test_no_reused_lot_is_reported(self):
        details = [make_detail("D1"), make_detail("D2", production_lot="PL2")]
        self.assertEqual(
            check_production_lot_reuse(details),
            ["GR-04 | Dataset | production_lot | 复用批号（出现至少两次）应为 1～2 个，当前 0 个"],
        )

    def test_more_than_two_reused_lots_lists_the_ids(self):
        lots = ["PL1", "PL1", "PL2", "PL2", "PL3", "PL3"]
        details = [make_detail(f"D{index}", production_lot=lot) for index, lot in enumerate(lots)]
        errors = check_production_lot_reuse(details)
        self.assertEqual(len(errors), 1)
        self.assertIn("当前 3 个", errors[0])
        self.assertIn("PL1, PL2, PL3", errors[0])


class TestValidateGeneration(unittest.TestCase):
    def setUp(self):
        self.records = dict(
            cases=[make_case("C1")],
            details=[
                make_detail("D1", stage="OQC", detection_day=2),
                make_detail("D2", stage="Customer", detection_day=3),
            ],
            evidences=[EvidenceCheckpoint("E1", "C1", "QC", None, "检查结果", "uncertain")],
            groups=[], memberships=[],
        )
        self.reference = dict(
            product_customers={"P1": "CUS1"}, product_routes={"P1": "LF_WB"},
            failure_mode_routes={"001": {"LF_WB"}},
        )

    def generation_errors(self):
        return validate_generation(**self.records)

    def test_valid_generated_dataset_passes_without_mutation(self):
        before = deepcopy(self.records)
        self.assertEqual(self.generation_errors(), [])
        self.assertEqual(validate_relations(**self.records, **self.reference), [])
        self.assertEqual(self.records, before)

    def test_field_error_stops_before_gr_checks(self):
        self.records["details"][0] = replace(self.records["details"][0], affected_qty=None)
        errors = self.generation_errors()
        self.assertEqual(len(errors), 2)
        self.assertTrue(errors[0].startswith("CR-23 |"))
        self.assertEqual(errors[1], "依赖 | Dataset | generation | 字段检查未通过，GR 检查未执行")
        self.assertFalse(any(error.startswith("GR-") for error in errors))

    def test_quantity_above_generation_limit_fails_only_in_generation_entry(self):
        self.records["details"][0] = replace(self.records["details"][0], affected_qty=5001)
        self.assertEqual(validate_relations(**self.records, **self.reference), [])
        self.assertEqual(
            self.generation_errors(),
            ["GR-06 | CaseDetail[D1] | affected_qty | 每 Detail 上限 5000 ea，当前 5001"],
        )

    def test_more_than_three_details_fails_only_in_generation_entry(self):
        self.records["details"].append(make_detail("D3", production_lot="PL2", stage="IQC"))
        self.records["details"].append(
            make_detail("D4", production_lot="PL2", stage="In-process", detection_day=4))
        self.assertEqual(validate_relations(**self.records, **self.reference), [])
        self.assertEqual(
            self.generation_errors(),
            ["GR-01 | Case[C1] | details | 每 Case 最多 3 个 Detail，当前 4 个"],
        )

    def test_collects_independent_gr_errors(self):
        self.records["details"][0] = make_detail(
            "D1", stage="OQC", detection_day=2, abnormal_types=("001", "002", "003"))
        self.records["details"][1] = make_detail(
            "D2", stage="Customer", detection_day=3, qty=6000)
        self.records["details"].append(make_detail("D3", production_lot="PL2", stage="IQC"))
        self.records["details"].append(
            make_detail("D4", production_lot="PL2", stage="In-process", detection_day=4))
        errors = self.generation_errors()
        self.assertEqual([error.split(" | ")[0] for error in errors], ["GR-01", "GR-02", "GR-06"])

    def test_no_reused_lot_fails_in_generation_entry(self):
        self.records["details"][1] = replace(self.records["details"][1], production_lot="PL2")
        errors = self.generation_errors()
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("GR-04 | Dataset | production_lot |"))

    def test_relation_problems_are_left_to_the_relation_entry(self):
        self.records["details"][1] = replace(self.records["details"][1], case_id="missing")
        self.assertEqual(self.generation_errors(), [])
        errors = validate_relations(**self.records, **self.reference)
        self.assertTrue(any(error.startswith("CR-02 |") for error in errors))

    def test_reused_lot_still_must_satisfy_cr_fixed_attributes(self):
        """GR-04 不代替 CR-08～10：同一批号的固定属性冲突只在 CR 入口失败。"""
        self.records["details"][1] = replace(self.records["details"][1], customer_lot="CL2")
        self.assertEqual(self.generation_errors(), [])
        errors = validate_relations(**self.records, **self.reference)
        self.assertTrue(any(error.startswith("CR-09 |") for error in errors))
