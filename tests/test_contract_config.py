import tempfile
import unittest
from pathlib import Path

import yaml

from adoctl.config.contract_export import export_agent_contract
from adoctl.config.contract_loader import load_effective_contract


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)


class TestContractConfig(unittest.TestCase):
    def test_load_effective_contract_reads_work_item_standards(self) -> None:
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
                        "title": {
                            "reference_name": "System.Title",
                            "applies_to": ["Feature", "UserStory"],
                        }
                    },
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
                            "title": {"rule": "Clear action-oriented title."}
                        }
                    },
                },
            )
            _write_yaml(
                policy_dir / "field_policy.yaml",
                {
                    "schema_version": "1.0",
                    "agent_contract_export": {"include_work_item_types": ["Feature", "UserStory"]},
                    "allowed_fields": {},
                    "required_fields": {},
                    "description_required_sections": {},
                    "description_optional_sections": {},
                },
            )
            _write_yaml(
                generated_dir / "wit_contract.yaml",
                {
                    "schema_version": "1.0",
                    "work_item_types": {
                        "Feature": {"fields": [{"reference_name": "System.Title"}]},
                        "User Story": {"fields": [{"reference_name": "System.Title"}]},
                    },
                },
            )

            effective = load_effective_contract(policy_dir=policy_dir, generated_dir=generated_dir)
            self.assertEqual(
                effective.standards.work_item_standards["UserStory"]["title"]["rule"],
                "Clear action-oriented title.",
            )

    def test_load_effective_contract_and_validate_coverage(self) -> None:
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
                        "story_points": {
                            "reference_name": "Microsoft.VSTS.Scheduling.StoryPoints",
                            "applies_to": ["UserStory"],
                            "description": "Relative estimate",
                        }
                    },
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
                        "Feature": {"title": {"rule": "Concise"}},
                        "Risk": {"title": {"rule": "Has summary"}},
                    },
                },
            )
            _write_yaml(
                policy_dir / "field_policy.yaml",
                {
                    "schema_version": "1.0",
                    "agent_contract_export": {"include_work_item_types": ["Feature", "UserStory"]},
                    "allowed_fields": {},
                    "required_fields": {},
                    "description_required_sections": {},
                    "description_optional_sections": {},
                },
            )
            _write_yaml(
                generated_dir / "wit_contract.yaml",
                {
                    "schema_version": "1.0",
                    "work_item_types": {
                        "Feature": {
                            "fields": [
                                {"reference_name": "System.Title", "required": True},
                                {"reference_name": "Microsoft.VSTS.Common.Priority", "required": False},
                            ]
                        },
                        "User Story": {
                            "fields": [
                                {"reference_name": "System.Title", "required": True},
                                {"reference_name": "Microsoft.VSTS.Scheduling.StoryPoints", "required": False},
                            ]
                        },
                    },
                },
            )

            effective = load_effective_contract(policy_dir=policy_dir, generated_dir=generated_dir)
            self.assertEqual(effective.resolve_ado_wit("Feature"), "Feature")
            self.assertEqual(
                effective.resolve_ado_field("story_points", canonical_type="UserStory"),
                "Microsoft.VSTS.Scheduling.StoryPoints",
            )
            self.assertEqual(effective.validate_mapping_coverage(), [])

    def test_export_agent_contract_writes_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            out_path = root / "agent_contract.yaml"

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
                        "priority": {
                            "reference_name": "Microsoft.VSTS.Common.Priority",
                            "applies_to": ["Feature", "UserStory"],
                        }
                    },
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
                    "required_tags": ["KR-2"],
                    "work_item_standards": {
                        "Feature": {
                            "description": {
                                "template": "As a <persona>, I need <capability>, so that <outcome>.",
                            }
                        },
                        "UserStory": {
                            "acceptance_criteria": {
                                "format": "Given / When / Then",
                            }
                        },
                    },
                },
            )
            _write_yaml(
                policy_dir / "field_policy.yaml",
                {
                    "schema_version": "1.0",
                    "agent_contract_export": {"include_work_item_types": ["Feature", "UserStory"]},
                    "allowed_fields": {},
                    "required_fields": {},
                    "description_required_sections": {},
                    "description_optional_sections": {},
                },
            )
            _write_yaml(
                generated_dir / "wit_contract.yaml",
                {
                    "schema_version": "1.0",
                    "work_item_types": {
                        "Feature": {"fields": [{"reference_name": "Microsoft.VSTS.Common.Priority"}]},
                        "User Story": {"fields": [{"reference_name": "Microsoft.VSTS.Common.Priority"}]},
                    },
                },
            )

            result = export_agent_contract(
                out_path=str(out_path),
                policy_dir=policy_dir,
                generated_dir=generated_dir,
            )
            self.assertTrue(out_path.exists())
            snapshot = yaml.safe_load(out_path.read_text(encoding="utf-8"))
            self.assertEqual(result["strict_ready"], True)
            self.assertEqual(snapshot["mapping"]["wit_map"]["Feature"], "Feature")
            self.assertIn("priority", snapshot["mapping"]["field_map"])
            self.assertEqual(snapshot["validation"]["mapping_coverage_issues"], [])
            self.assertEqual(
                snapshot["field_policy"]["export_work_item_types"],
                ["Feature", "UserStory"],
            )
            self.assertEqual(snapshot["field_policy"]["owner_identity_format"], "display_name")
            self.assertIn("work_item_standards", snapshot["rules"]["standards"])
            self.assertIn("Feature", snapshot["rules"]["standards"]["work_item_standards"])
            self.assertIn("UserStory", snapshot["rules"]["standards"]["work_item_standards"])
            self.assertFalse(snapshot["planning"]["available"])

    def test_export_agent_contract_includes_planning_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            out_path = root / "agent_contract.yaml"

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
                        "title": {"reference_name": "System.Title", "applies_to": ["Feature", "UserStory"]},
                    },
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
                    "work_item_standards": {},
                },
            )
            _write_yaml(
                policy_dir / "field_policy.yaml",
                {
                    "schema_version": "1.0",
                    "agent_contract_export": {"include_work_item_types": ["Feature", "UserStory"]},
                    "allowed_fields": {},
                    "required_fields": {},
                    "description_required_sections": {},
                    "description_optional_sections": {},
                },
            )
            _write_yaml(
                generated_dir / "wit_contract.yaml",
                {
                    "schema_version": "1.0",
                    "work_item_types": {
                        "Feature": {"fields": [{"reference_name": "System.Title"}]},
                        "User Story": {"fields": [{"reference_name": "System.Title"}]},
                    },
                },
            )
            _write_yaml(
                generated_dir / "planning_context.yaml",
                {
                    "schema_version": "1.0",
                    "project": "Black Lagoon",
                    "core_team": "Black Lagoon",
                    "project_backlog_defaults": {"area_path": "Black Lagoon", "iteration_path": "Black Lagoon"},
                    "teams": [{"name": "DataScience", "default_area_path": "Black Lagoon\\DataScience"}],
                    "objectives": [{"id": 1, "title": "Obj 1"}],
                    "key_results": [{"id": 2, "title": "KR 1", "parent_objective_id": 1}],
                    "orphan_key_results": [],
                },
            )

            export_agent_contract(
                out_path=str(out_path),
                policy_dir=policy_dir,
                generated_dir=generated_dir,
            )
            snapshot = yaml.safe_load(out_path.read_text(encoding="utf-8"))
            self.assertTrue(snapshot["planning"]["available"])
            self.assertEqual(snapshot["planning"]["project"], "Black Lagoon")
            self.assertEqual(snapshot["planning"]["core_team"], "Black Lagoon")
            self.assertEqual(len(snapshot["planning"]["teams"]), 1)
            self.assertEqual(len(snapshot["planning"]["objectives"]), 1)
            self.assertEqual(len(snapshot["planning"]["key_results"]), 1)

    def test_export_syncs_field_policy_required_with_generated_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            out_path = root / "agent_contract.yaml"
            field_policy_path = policy_dir / "field_policy.yaml"

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
                        "priority": {
                            "reference_name": "Microsoft.VSTS.Common.Priority",
                            "applies_to": ["Feature"],
                        },
                        "story_points": {
                            "reference_name": "Microsoft.VSTS.Scheduling.StoryPoints",
                            "applies_to": ["UserStory"],
                        },
                    },
                },
            )
            _write_yaml(
                policy_dir / "field_policy.yaml",
                {
                    "schema_version": "1.0",
                    "agent_contract_export": {"include_work_item_types": ["Feature", "UserStory"]},
                    "allowed_fields": {},
                    "required_fields": {
                        "UserStory": ["story_points"]
                    },
                    "description_required_sections": {"UserStory": ["Acceptance Criteria"]},
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
                        "Feature": {"title": {"rule": "Concise"}},
                        "Risk": {"title": {"rule": "Has summary"}},
                    },
                },
            )
            _write_yaml(
                generated_dir / "wit_contract.yaml",
                {
                    "schema_version": "1.0",
                    "work_item_types": {
                        "Feature": {
                            "fields": [
                                {"reference_name": "Microsoft.VSTS.Common.Priority", "required": True},
                            ]
                        },
                        "User Story": {
                            "fields": [
                                {"reference_name": "Microsoft.VSTS.Scheduling.StoryPoints", "required": False},
                            ]
                        },
                    },
                },
            )

            result = export_agent_contract(
                out_path=str(out_path),
                policy_dir=policy_dir,
                generated_dir=generated_dir,
            )
            self.assertTrue(result["field_policy_updated"])

            updated_field_policy = yaml.safe_load(field_policy_path.read_text(encoding="utf-8"))
            self.assertIn("Feature", updated_field_policy["required_fields"])
            self.assertEqual(updated_field_policy["required_fields"]["Feature"], ["priority"])
            self.assertEqual(updated_field_policy["required_fields"]["UserStory"], ["story_points"])

            snapshot = yaml.safe_load(out_path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["field_policy"]["generated_required_fields"]["Feature"], ["priority"])
            self.assertEqual(snapshot["field_policy"]["effective_required_fields"]["Feature"], ["priority"])
            self.assertEqual(snapshot["field_policy"]["effective_required_fields"]["UserStory"], ["story_points"])
            self.assertEqual(
                snapshot["field_policy"]["description_required_sections"]["UserStory"],
                ["Acceptance Criteria"],
            )

    def test_export_filters_policy_types_with_feature_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            out_path = root / "agent_contract.yaml"

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
                        "priority": {
                            "reference_name": "Microsoft.VSTS.Common.Priority",
                            "applies_to": ["Feature", "UserStory"],
                        },
                        "risk_status": {
                            "reference_name": "Custom.RiskStatus",
                            "applies_to": ["Risk"],
                        },
                    },
                },
            )
            _write_yaml(
                policy_dir / "field_policy.yaml",
                {
                    "schema_version": "1.0",
                    "agent_contract_export": {"include_work_item_types": ["Feature", "UserStory"]},
                    "allowed_fields": {"Risk": ["risk_status"]},
                    "required_fields": {"Risk": ["risk_status"]},
                    "description_required_sections": {"Risk": ["Risk summary"]},
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
                        "Feature": {"title": {"rule": "Concise"}},
                        "Risk": {"title": {"rule": "Has summary"}},
                    },
                },
            )
            _write_yaml(
                generated_dir / "wit_contract.yaml",
                {
                    "schema_version": "1.0",
                    "work_item_types": {
                        "Feature": {"fields": [{"reference_name": "Microsoft.VSTS.Common.Priority"}]},
                        "User Story": {"fields": [{"reference_name": "Microsoft.VSTS.Common.Priority"}]},
                        "Risk": {"fields": [{"reference_name": "Custom.RiskStatus"}]},
                    },
                },
            )

            result = export_agent_contract(
                out_path=str(out_path),
                policy_dir=policy_dir,
                generated_dir=generated_dir,
            )
            self.assertTrue(out_path.exists())
            self.assertEqual(result["strict_ready"], True)
            snapshot = yaml.safe_load(out_path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["canonical"]["supported_types"], ["Feature", "UserStory"])
            self.assertEqual(snapshot["field_policy"]["required_fields"], {})
            self.assertEqual(
                sorted(snapshot["rules"]["standards"]["work_item_standards"].keys()),
                ["Feature"],
            )


if __name__ == "__main__":
    unittest.main()
