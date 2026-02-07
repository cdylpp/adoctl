import tempfile
import unittest
from pathlib import Path

import yaml

from adoctl.config.contract_lint import lint_contract


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)


class TestContractLint(unittest.TestCase):
    def test_lint_reports_info_for_excluded_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"

            _write_yaml(
                policy_dir / "wit_map.yaml",
                {
                    "schema_version": "1.0",
                    "canonical_to_ado": {
                        "Feature": "Feature",
                        "UserStory": "User Story",
                        "Risk": "Risk",
                    },
                },
            )
            _write_yaml(
                policy_dir / "field_map.yaml",
                {
                    "schema_version": "1.0",
                    "canonical_to_ado": {
                        "title": {
                            "reference_name": "System.Title",
                            "applies_to": ["Feature", "UserStory", "Risk"],
                        }
                    },
                },
            )
            _write_yaml(
                policy_dir / "field_policy.yaml",
                {
                    "schema_version": "1.0",
                    "agent_contract_export": {"include_work_item_types": ["Feature", "UserStory"]},
                    "allowed_fields": {"Risk": ["title"]},
                    "required_fields": {"Risk": ["title"]},
                    "description_required_sections": {"Risk": ["Summary"]},
                    "description_optional_sections": {},
                },
            )
            _write_yaml(
                policy_dir / "link_policy.yaml",
                {
                    "schema_version": "1.0",
                    "allowed_link_types": ["parent-child"],
                    "max_depth": 2,
                    "forbid_double_nesting": ["Feature", "UserStory"],
                },
            )
            _write_yaml(
                policy_dir / "standards.yaml",
                {
                    "schema_version": "1.0",
                    "required_tags": [],
                    "work_item_standards": {
                        "UserStory": {"title": {"rule": "Action oriented"}},
                        "Risk": {"title": {"rule": "Summary present"}},
                    },
                },
            )
            _write_yaml(
                generated_dir / "wit_contract.yaml",
                {
                    "schema_version": "1.0",
                    "work_item_types": {
                        "Feature": {"fields": [{"reference_name": "System.Title"}]},
                        "User Story": {"fields": [{"reference_name": "System.Title"}]},
                        "Risk": {"fields": [{"reference_name": "System.Title"}]},
                    },
                },
            )

            report = lint_contract(policy_dir=policy_dir, generated_dir=generated_dir)
            self.assertTrue(report["strict_ready"])
            self.assertEqual(report["summary"]["errors"], 0)
            self.assertGreaterEqual(report["summary"]["info"], 1)
            info_codes = [finding["code"] for finding in report["findings"] if finding["severity"] == "info"]
            self.assertIn("TYPE_EXCLUDED_FROM_EXPORT", info_codes)

    def test_lint_errors_when_standards_required_missing_from_field_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"

            _write_yaml(
                policy_dir / "wit_map.yaml",
                {
                    "schema_version": "1.0",
                    "canonical_to_ado": {"Feature": "Feature", "UserStory": "User Story"},
                },
            )
            _write_yaml(
                policy_dir / "field_map.yaml",
                {
                    "schema_version": "1.0",
                    "canonical_to_ado": {
                        "acceptance_criteria": {
                            "reference_name": "Microsoft.VSTS.Common.AcceptanceCriteria",
                            "applies_to": ["UserStory"],
                        },
                        "title": {
                            "reference_name": "System.Title",
                            "applies_to": ["UserStory", "Feature"],
                        },
                    },
                },
            )
            _write_yaml(
                policy_dir / "field_policy.yaml",
                {
                    "schema_version": "1.0",
                    "agent_contract_export": {"include_work_item_types": ["Feature", "UserStory"]},
                    "allowed_fields": {"UserStory": ["acceptance_criteria", "title"]},
                    "required_fields": {"UserStory": ["title"]},
                    "description_required_sections": {},
                    "description_optional_sections": {},
                },
            )
            _write_yaml(
                policy_dir / "link_policy.yaml",
                {
                    "schema_version": "1.0",
                    "allowed_link_types": ["parent-child"],
                    "max_depth": 2,
                    "forbid_double_nesting": ["Feature", "UserStory"],
                },
            )
            _write_yaml(
                policy_dir / "standards.yaml",
                {
                    "schema_version": "1.0",
                    "required_tags": [],
                    "work_item_standards": {
                        "UserStory": {
                            "title": {"rule": "Action oriented"},
                            "acceptance_criteria": {"required": True},
                        }
                    },
                },
            )
            _write_yaml(
                generated_dir / "wit_contract.yaml",
                {
                    "schema_version": "1.0",
                    "work_item_types": {
                        "Feature": {"fields": [{"reference_name": "System.Title"}]},
                        "User Story": {
                            "fields": [
                                {"reference_name": "System.Title"},
                                {"reference_name": "Microsoft.VSTS.Common.AcceptanceCriteria"},
                            ]
                        },
                    },
                },
            )

            report = lint_contract(policy_dir=policy_dir, generated_dir=generated_dir)
            self.assertFalse(report["strict_ready"])
            error_codes = [finding["code"] for finding in report["findings"] if finding["severity"] == "error"]
            self.assertIn("STANDARDS_REQUIRED_NOT_IN_POLICY", error_codes)

    def test_lint_errors_for_unknown_export_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"

            _write_yaml(
                policy_dir / "wit_map.yaml",
                {
                    "schema_version": "1.0",
                    "canonical_to_ado": {"Feature": "Feature"},
                },
            )
            _write_yaml(
                policy_dir / "field_map.yaml",
                {
                    "schema_version": "1.0",
                    "canonical_to_ado": {
                        "title": {
                            "reference_name": "System.Title",
                            "applies_to": ["Feature"],
                        }
                    },
                },
            )
            _write_yaml(
                policy_dir / "field_policy.yaml",
                {
                    "schema_version": "1.0",
                    "agent_contract_export": {"include_work_item_types": ["Feature", "UserStory"]},
                    "allowed_fields": {"Feature": ["title"]},
                    "required_fields": {"Feature": ["title"]},
                    "description_required_sections": {},
                    "description_optional_sections": {},
                },
            )
            _write_yaml(
                policy_dir / "link_policy.yaml",
                {
                    "schema_version": "1.0",
                    "allowed_link_types": ["parent-child"],
                    "max_depth": 2,
                    "forbid_double_nesting": ["Feature", "UserStory"],
                },
            )
            _write_yaml(
                policy_dir / "standards.yaml",
                {
                    "schema_version": "1.0",
                    "required_tags": [],
                    "work_item_standards": {
                        "UserStory": {"title": {"rule": "Action oriented"}}
                    },
                },
            )
            _write_yaml(
                generated_dir / "wit_contract.yaml",
                {
                    "schema_version": "1.0",
                    "work_item_types": {
                        "Feature": {"fields": [{"reference_name": "System.Title"}]},
                    },
                },
            )

            report = lint_contract(policy_dir=policy_dir, generated_dir=generated_dir)
            self.assertFalse(report["strict_ready"])
            error_codes = [finding["code"] for finding in report["findings"] if finding["severity"] == "error"]
            self.assertIn("UNKNOWN_EXPORT_TYPE", error_codes)


if __name__ == "__main__":
    unittest.main()

