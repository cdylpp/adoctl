import json
import tempfile
import unittest
from pathlib import Path

import yaml

from adoctl.config.instruction_set_export import export_instruction_set


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)


class TestInstructionSetExport(unittest.TestCase):
    def test_export_instruction_set_runs_contract_export_and_builds_single_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            instruction_set_dir = root / "instruction_set"
            schema_path = root / "bundle.schema.json"
            instruction_set_dir.mkdir(parents=True, exist_ok=True)
            (instruction_set_dir / "01_required_inputs.md").write_text("# One\none content\n", encoding="utf-8")
            (instruction_set_dir / "02_contracts_and_rules.md").write_text("# Two\ntwo content\n", encoding="utf-8")
            (instruction_set_dir / "03_output_expectations.md").write_text("# Three\nthree content\n", encoding="utf-8")
            (instruction_set_dir / "04_generation_workflow.md").write_text("# Four\nfour content\n", encoding="utf-8")
            (instruction_set_dir / "05_efficiency_notes.md").write_text("# Five\nfive content\n", encoding="utf-8")

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
                    "teams": [{"name": "DataScience"}],
                    "objectives": [{"id": 1, "title": "Improve thing"}],
                    "key_results": [{"id": 2, "title": "KR thing", "parent_objective_id": 1}],
                    "orphan_key_results": [],
                },
            )
            schema_path.write_text(json.dumps({"type": "object"}, indent=2), encoding="utf-8")

            result = export_instruction_set(
                instruction_set_dir=str(instruction_set_dir),
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                schema_path=str(schema_path),
                run_contract_export=True,
            )

            self.assertIsNotNone(result["contract_export"])
            self.assertTrue((instruction_set_dir / "instruction_set.md").exists())

            exported_contract = yaml.safe_load((generated_dir / "agent_contract.yaml").read_text(encoding="utf-8"))
            self.assertTrue(exported_contract["planning"]["available"])
            self.assertEqual(exported_contract["planning"]["project"], "Black Lagoon")
            self.assertEqual(len(exported_contract["planning"]["objectives"]), 1)
            self.assertEqual(len(result["sections"]), 8)

            compiled = (instruction_set_dir / "instruction_set.md").read_text(encoding="utf-8")
            ordered_headers = [
                "## 01 Required Inputs",
                "## 02 Contracts And Rules",
                "## 03 Output Expectations",
                "## 04 Generation Workflow",
                "## 05 Efficiency Notes",
                "## 06 Agent Contract",
                "## 07 Bundle Schema",
                "## 08 Planning Context",
            ]
            positions = [compiled.find(header) for header in ordered_headers]
            self.assertTrue(all(pos >= 0 for pos in positions))
            self.assertEqual(positions, sorted(positions))
            self.assertIn("```yaml\n", compiled)
            self.assertIn("```json\n", compiled)
            self.assertGreaterEqual(compiled.count("```yaml\n"), 2)

    def test_export_instruction_set_requires_planning_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            generated_dir = root / "generated"
            instruction_set_dir = root / "instruction_set"
            schema_path = root / "bundle.schema.json"

            _write_yaml(generated_dir / "agent_contract.yaml", {"schema_version": "1.0"})
            schema_path.write_text(json.dumps({"type": "object"}, indent=2), encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                export_instruction_set(
                    instruction_set_dir=str(instruction_set_dir),
                    policy_dir=None,
                    generated_dir=generated_dir,
                    schema_path=str(schema_path),
                    run_contract_export=False,
                )


if __name__ == "__main__":
    unittest.main()
