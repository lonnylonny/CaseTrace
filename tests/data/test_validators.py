import unittest
from dataclasses import replace
from datetime import date, datetime

from casetrace.data.dataset_model import CaseDetail
from casetrace.data.validators import check_required_text, validate_detail_fields


class TestRequiredText(unittest.TestCase):
    def test_accepts_text_with_content(self):
        for value in ["PL001", " PL001 "]:
            with self.subTest(value=value):
                errors = check_required_text(
                    value,
                    field="production_lot",
                    location="CaseDetail[D001]",
                    rule="CR-06",
                )
                self.assertEqual(errors, [])

    def test_rejects_blank_and_non_string_values(self):
        for value in [None, "", "   ", "\n\t", 123, True, []]:
            with self.subTest(value=value):
                errors = check_required_text(
                    value,
                    field="production_lot",
                    location="CaseDetail[D001]",
                    rule="CR-06",
                )
                self.assertEqual(
                    errors,
                    ["CR-06 | CaseDetail[D001] | production_lot | 必须是非空字符串"],
                )


class TestDetailFields(unittest.TestCase):
    def setUp(self):
        self.detail = CaseDetail(
            detail_id="D001",
            case_id="C001",
            product_id="P001",
            customer_lot="CL001",
            production_lot="PL001",
            production_time=date(2026, 9, 1),
            detection_stage="OQC",
            detection_time=date(2026, 9, 2),
            abnormal_types=["001"],
            affected_qty=100,
            disposition="全部报废",
        )

    def test_accepts_required_text_with_content(self):
        errors = validate_detail_fields(self.detail, location="CaseDetail[D001]")
        self.assertEqual(errors, [])

    def test_checks_every_required_text_field(self):
        for field in (
            "detail_id", "case_id", "product_id", "customer_lot",
            "production_lot", "detection_stage", "disposition",
        ):
            with self.subTest(field=field):
                detail = replace(self.detail, **{field: "   "})
                errors = validate_detail_fields(detail, location="CaseDetail[0]")
                self.assertEqual(len(errors), 1)
                self.assertIn(f" | CaseDetail[0] | {field} | ", errors[0])

    def test_collects_multiple_errors_with_rule_and_location(self):
        detail = replace(self.detail, customer_lot="   ", disposition=None)
        errors = validate_detail_fields(detail, location="CaseDetail[D001]")
        self.assertEqual(
            errors,
            [
                "CR-07 | CaseDetail[D001] | customer_lot | 必须是非空字符串",
                "CR-27 | CaseDetail[D001] | disposition | 必须是非空字符串",
            ],
        )

    def test_preserves_input_whitespace(self):
        detail = replace(self.detail, production_lot=" PL001 ")
        errors = validate_detail_fields(detail, location="CaseDetail[D001]")
        self.assertEqual(errors, [])
        self.assertEqual(detail.production_lot, " PL001 ")

    def test_accepts_positive_integer_quantity_without_generation_limit(self):
        for value in [1, 5000, 5001]:
            with self.subTest(value=value):
                detail = replace(self.detail, affected_qty=value)
                errors = validate_detail_fields(detail, location="CaseDetail[D001]")
                self.assertEqual(errors, [])

    def test_rejects_invalid_quantity(self):
        for value in [0, -1, True, False, 1.0, 1.5, "100", None, []]:
            with self.subTest(value=value):
                detail = replace(self.detail, affected_qty=value)
                errors = validate_detail_fields(detail, location="CaseDetail[D001]")
                self.assertEqual(
                    errors,
                    ["CR-23 | CaseDetail[D001] | affected_qty | 必须是正整数"],
                )

    def test_collects_text_and_quantity_errors_together(self):
        detail = replace(self.detail, customer_lot="", affected_qty=0)
        errors = validate_detail_fields(detail, location="CaseDetail[D001]")
        self.assertEqual(
            errors,
            [
                "CR-07 | CaseDetail[D001] | customer_lot | 必须是非空字符串",
                "CR-23 | CaseDetail[D001] | affected_qty | 必须是正整数",
            ],
        )

    def test_accepts_same_day_and_later_detection(self):
        for value in [date(2026, 9, 1), date(2026, 9, 2), date(2027, 9, 1)]:
            with self.subTest(value=value):
                detail = replace(self.detail, detection_time=value)
                errors = validate_detail_fields(detail, location="CaseDetail[D001]")
                self.assertEqual(errors, [])

    def test_rejects_detection_before_production(self):
        detail = replace(self.detail, detection_time=date(2026, 8, 31))
        errors = validate_detail_fields(detail, location="CaseDetail[D001]")
        self.assertEqual(
            errors,
            ["CR-21 | CaseDetail[D001] | detection_time | 不能早于 production_time"],
        )

    def test_rejects_invalid_date_types_without_comparing_them(self):
        for field, rule in [("production_time", "CR-19"), ("detection_time", "CR-20")]:
            for value in [None, "2026-09-01", "", 123, True, [], datetime(2026, 9, 1)]:
                with self.subTest(field=field, value=value):
                    detail = replace(self.detail, **{field: value})
                    errors = validate_detail_fields(detail, location="CaseDetail[D001]")
                    self.assertEqual(
                        errors,
                        [f"{rule} | CaseDetail[D001] | {field} | 必须是 date 日期"],
                    )

    def test_reports_both_invalid_dates(self):
        detail = replace(self.detail, production_time=None, detection_time=None)
        errors = validate_detail_fields(detail, location="CaseDetail[D001]")
        self.assertEqual(
            errors,
            [
                "CR-19 | CaseDetail[D001] | production_time | 必须是 date 日期",
                "CR-20 | CaseDetail[D001] | detection_time | 必须是 date 日期",
            ],
        )

    def test_checks_date_order_even_when_text_is_invalid(self):
        detail = replace(self.detail, customer_lot="", detection_time=date(2026, 8, 31))
        errors = validate_detail_fields(detail, location="CaseDetail[D001]")
        self.assertEqual(
            errors,
            [
                "CR-07 | CaseDetail[D001] | customer_lot | 必须是非空字符串",
                "CR-21 | CaseDetail[D001] | detection_time | 不能早于 production_time",
            ],
        )

    def test_accepts_all_detection_stages(self):
        for value in ["IQC", "In-process", "OQC", "Customer", "Other"]:
            with self.subTest(value=value):
                detail = replace(self.detail, detection_stage=value)
                self.assertEqual(
                    validate_detail_fields(detail, location="CaseDetail[D001]"), [],
                )

    def test_rejects_unknown_or_non_exact_detection_stage(self):
        for value in ["Production", "oqc", " OQC ", "In-Process"]:
            with self.subTest(value=value):
                detail = replace(self.detail, detection_stage=value)
                errors = validate_detail_fields(detail, location="CaseDetail[D001]")
                self.assertEqual(
                    errors,
                    [
                        "结构 §2 | CaseDetail[D001] | detection_stage | "
                        "必须是以下值之一：IQC / In-process / OQC / Customer / Other"
                    ],
                )
                self.assertEqual(detail.detection_stage, value)

    def test_reports_only_text_error_for_invalid_stage_type_or_blank(self):
        for value in [None, "", "   ", 123, True, [], {}]:
            with self.subTest(value=value):
                detail = replace(self.detail, detection_stage=value)
                errors = validate_detail_fields(detail, location="CaseDetail[D001]")
                self.assertEqual(
                    errors,
                    ["结构 §2 | CaseDetail[D001] | detection_stage | 必须是非空字符串"],
                )

    def test_checks_stage_even_when_quantity_is_invalid(self):
        detail = replace(self.detail, affected_qty=0, detection_stage="unknown")
        errors = validate_detail_fields(detail, location="CaseDetail[D001]")
        self.assertEqual(len(errors), 2)
        self.assertTrue(any(" | affected_qty | " in error for error in errors))
        self.assertTrue(any(" | detection_stage | 必须是以下值之一：" in error for error in errors))
