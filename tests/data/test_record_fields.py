"""字段检查使用独立小样例，不依赖主数据或跨记录关系。"""

import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import date

from casetrace.data.dataset_model import Case, CaseDetail, CaseGroup, EvidenceCheckpoint, Membership
from casetrace.data.validators import (
    check_choice, check_text_list, validate_case_fields, validate_detail_fields,
    validate_evidence_fields, validate_group_fields, validate_membership_fields,
    validate_records,
)


class TestSharedChecks(unittest.TestCase):
    def test_choice_checks_type_blank_and_membership(self):
        for value in [None, [], {}, 1, "", " ", "oqc", " OQC ", "unknown"]:
            with self.subTest(value=value):
                errors = check_choice(value, allowed_values=("IQC", "OQC"),
                                      field="stage", location="record[0]", rule="test")
                self.assertEqual(len(errors), 1)
        self.assertEqual(check_choice("OQC", allowed_values=("IQC", "OQC"),
                                      field="stage", location="record[0]", rule="test"), [])

    def test_text_list_rejects_wrong_container_and_empty_list(self):
        for value in [None, "001", ("001",), {"001"}, {}, []]:
            with self.subTest(value=value):
                errors = check_text_list(value, field="ids", location="record[0]", rule="test")
                self.assertEqual(len(errors), 1)

    def test_text_list_reports_each_invalid_element_by_index(self):
        errors = check_text_list(["001", None, [], " "], field="ids", location="record[0]", rule="test")
        self.assertEqual(len(errors), 3)
        for index, error in zip([1, 2, 3], errors):
            self.assertIn(f"ids[{index}]", error)

    def test_text_list_does_not_invent_uniqueness_requirement(self):
        values = ["001", "001"]
        self.assertEqual(check_text_list(values, field="ids", location="record[0]", rule="test"), [])
        self.assertEqual(values, ["001", "001"])


class TestRecordFields(unittest.TestCase):
    def setUp(self):
        self.detail = CaseDetail("D1", "C1", "P1", "CL1", "PL1", date(2026, 9, 1),
                                 "OQC", date(2026, 9, 2), ["001"], 1, "全部报废")
        self.case = Case("C1", "异常描述", "NDF", "加强监控", None)
        self.evidence = EvidenceCheckpoint("E1", "C1", "QC", None, "检查结果", "uncertain")
        self.group = CaseGroup("G1", ["project"], "项目调查", None)
        self.membership = Membership("G1", "C1", "属于该项目")

    def test_all_five_valid_objects_pass_field_checks(self):
        for record, validator in self.object_checks():
            with self.subTest(record=type(record).__name__):
                self.assertEqual(validator(record, location="record[0]"), [])

    def object_checks(self):
        return [(self.detail, validate_detail_fields), (self.case, validate_case_fields),
                (self.evidence, validate_evidence_fields), (self.group, validate_group_fields),
                (self.membership, validate_membership_fields)]

    def test_abnormal_list_structure_and_duplicates(self):
        for value in [[], None, "001", [None], [[]], ["001", "001"]]:
            with self.subTest(value=value):
                errors = validate_detail_fields(replace(self.detail, abnormal_types=value), location="D1")
                self.assertEqual(len(errors), 1)
        errors = validate_detail_fields(replace(self.detail, abnormal_types=["002", "001"]), location="D1")
        self.assertEqual(errors, [])

    def test_required_text_fields_on_other_objects(self):
        checks = [
            (self.case, validate_case_fields, ["case_id", "abnormal_description", "root_cause", "corrective_action"]),
            (self.evidence, validate_evidence_fields, ["checkpoint_id", "case_id", "result"]),
            (self.group, validate_group_fields, ["group_id", "description"]),
            (self.membership, validate_membership_fields, ["group_id", "case_id", "association_reason"]),
        ]
        for record, validator, fields in checks:
            for field in fields:
                with self.subTest(record=type(record).__name__, field=field):
                    self.assertEqual(len(validator(replace(record, **{field: " "}), location="row[0]")), 1)

    def test_evidence_enums_and_other_name(self):
        types = ["QC", "AOI", "Production", "OCAP", "Previous/Next Lot", "Monitoring",
                 "EDX", "Reliability", "Material", "Other"]
        for checkpoint_type in types:
            with self.subTest(checkpoint_type=checkpoint_type):
                evidence = replace(self.evidence, checkpoint_type=checkpoint_type, custom_name="专项检查")
                self.assertEqual(validate_evidence_fields(evidence, location="E1"), [])
        for relevance in ["related", "not_related", "uncertain"]:
            self.assertEqual(validate_evidence_fields(replace(self.evidence, relevance=relevance), location="E1"), [])
        for field in ["checkpoint_type", "relevance"]:
            for value in [None, [], "", "unknown"]:
                with self.subTest(field=field, value=value):
                    self.assertEqual(len(validate_evidence_fields(replace(self.evidence, **{field: value}), location="E1")), 1)
        for value in [None, "", " ", 123]:
            with self.subTest(custom_name=value):
                errors = validate_evidence_fields(replace(self.evidence, checkpoint_type="Other", custom_name=value), location="E1")
                self.assertEqual(len(errors), 1)
                self.assertTrue(errors[0].startswith("CR-34 |"))

    def test_group_multiselect_and_conditional_description(self):
        self.assertEqual(validate_group_fields(replace(self.group, group_type=["repeat_case", "project"]), location="G1"), [])
        self.assertEqual(validate_group_fields(replace(self.group, group_type=["other", "project"], other_type_description="专项分类"), location="G1"), [])
        for value in [None, "", " ", []]:
            errors = validate_group_fields(replace(self.group, group_type=["project", "other"], other_type_description=value), location="G1")
            self.assertEqual(len(errors), 1)
            self.assertTrue(errors[0].startswith("CR-43 |"))
        for value in [[], None, "project", [None], [[]], ["same_root_cause"]]:
            with self.subTest(group_type=value):
                self.assertEqual(len(validate_group_fields(replace(self.group, group_type=value), location="G1")), 1)
        for value in [["customer_request"], ["management_request"], ["project", "project"]]:
            self.assertEqual(validate_group_fields(replace(self.group, group_type=value), location="G1"), [])

    def test_optional_text_allows_none_or_string_only(self):
        for record, validator, field in [
            (self.case, validate_case_fields, "investigation_others"),
            (self.evidence, validate_evidence_fields, "custom_name"),
            (self.group, validate_group_fields, "other_type_description"),
        ]:
            for value in [None, "", " ", "补充说明"]:
                self.assertEqual(validator(replace(record, **{field: value}), location="row[0]"), [])
            for value in [1, [], False]:
                self.assertEqual(len(validator(replace(record, **{field: value}), location="row[0]")), 1)

    def dataset(self):
        return dict(cases=[self.case], details=[self.detail], evidences=[self.evidence],
                    groups=[self.group], memberships=[self.membership])

    def test_records_checks_fields_without_enforcing_group_size_or_references(self):
        records = self.dataset()
        before = deepcopy(records)
        self.assertEqual(validate_records(**records), [])
        self.assertEqual(records, before)
        records["details"] = [replace(self.detail, product_id="not-in-reference")]
        self.assertEqual(validate_records(**records), [])

    def test_records_collects_errors_and_uses_index_for_missing_id(self):
        records = self.dataset()
        records["cases"] = [replace(self.case, case_id=None)]
        records["details"] = [replace(self.detail, affected_qty=0)]
        errors = validate_records(**records)
        self.assertEqual(len(errors), 2)
        self.assertIn("Case[0]", errors[0])
        self.assertIn("CaseDetail[D1]", errors[1])

    def test_records_rejects_wrong_containers_and_wrong_record_types(self):
        records = self.dataset()
        records["cases"] = None
        records["details"] = [None, self.evidence]
        errors = validate_records(**records)
        self.assertEqual(len(errors), 3)
        self.assertIn("cases", errors[0])
        self.assertIn("CaseDetail[0]", errors[1])
        self.assertIn("CaseDetail[1]", errors[2])
