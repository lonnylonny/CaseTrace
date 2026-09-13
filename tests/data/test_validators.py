import unittest
from dataclasses import replace
from datetime import date

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


class TestDetailRequiredText(unittest.TestCase):
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
