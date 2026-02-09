import json
import tempfile
import unittest
from pathlib import Path

import yaml

from adoctl.outbox.validate import validate_outbox


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _base_policy(policy_dir: Path) -> None:
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
                "description": {"reference_name": "System.Description", "applies_to": ["Feature", "UserStory"]},
                "acceptance_criteria": {
                    "reference_name": "Microsoft.VSTS.Common.AcceptanceCriteria",
                    "applies_to": ["Feature", "UserStory"],
                },
                "state": {"reference_name": "System.State", "applies_to": ["Feature", "UserStory"]},
                "priority": {"reference_name": "Microsoft.VSTS.Common.Priority", "applies_to": ["Feature"]},
                "story_points": {
                    "reference_name": "Microsoft.VSTS.Scheduling.StoryPoints",
                    "applies_to": ["UserStory"],
                },
                "area_path": {"reference_name": "System.AreaPath", "applies_to": ["Feature", "UserStory"]},
                "iteration_path": {
                    "reference_name": "System.IterationPath",
                    "applies_to": ["Feature", "UserStory"],
                },
            },
        },
    )
    _write_yaml(
        policy_dir / "field_policy.yaml",
        {
            "schema_version": "1.0",
            "agent_contract_export": {"include_work_item_types": ["Feature", "UserStory"]},
            "allowed_fields": {
                "Feature": ["state", "priority", "area_path", "iteration_path"],
                "UserStory": ["state", "story_points", "area_path", "iteration_path"],
            },
            "required_fields": {
                "Feature": ["title", "description", "state"],
                "UserStory": ["title", "description", "acceptance_criteria", "state", "story_points"],
            },
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
                "UserStory": {"title": {"rule": "Action-oriented title with clear scope."}}
            },
        },
    )


def _base_generated(generated_dir: Path) -> None:
    _write_yaml(
        generated_dir / "wit_contract.yaml",
        {
            "schema_version": "1.0",
            "work_item_types": {
                "Feature": {
                    "fields": [
                        {"reference_name": "System.Title"},
                        {"reference_name": "System.Description"},
                        {"reference_name": "Microsoft.VSTS.Common.AcceptanceCriteria"},
                        {"reference_name": "System.State"},
                        {"reference_name": "Microsoft.VSTS.Common.Priority"},
                        {"reference_name": "System.AreaPath"},
                        {"reference_name": "System.IterationPath"},
                    ]
                },
                "User Story": {
                    "fields": [
                        {"reference_name": "System.Title"},
                        {"reference_name": "System.Description"},
                        {"reference_name": "Microsoft.VSTS.Common.AcceptanceCriteria"},
                        {"reference_name": "System.State"},
                        {"reference_name": "Microsoft.VSTS.Scheduling.StoryPoints"},
                        {"reference_name": "System.AreaPath"},
                        {"reference_name": "System.IterationPath"},
                    ]
                },
            },
        },
    )
    _write_yaml(generated_dir / "paths_area.yaml", {"area_paths": ["Project\\Team"]})
    _write_yaml(generated_dir / "paths_iteration.yaml", {"iteration_paths": ["Project\\Sprint1"]})


def _valid_bundle_payload() -> dict:
    return {
        "schema_version": "1.0",
        "bundle_id": "bundle-valid",
        "source": {
            "agent_name": "test-agent",
            "prompt_id": "unit-test",
            "generated_at": "2026-02-07T00:00:00Z",
        },
        "context": {
            "default_area_path": "Project\\Team",
            "default_iteration_path": "Project\\Sprint1",
        },
        "work_items": [
            {
                "local_id": "F-001",
                "type": "Feature",
                "title": "Feature title",
                "description": "Feature description",
                "acceptance_criteria": ["Given something, when action, then result."],
                "fields": {"state": "New", "priority": 2},
                "relations": {"parent_local_id": "KR-001"},
            },
            {
                "local_id": "US-001",
                "type": "UserStory",
                "title": "As a user, I can do work, so that I get value.",
                "description": "Story description",
                "acceptance_criteria": ["Given state, when action, then outcome."],
                "fields": {"state": "New", "story_points": 3},
                "relations": {"parent_local_id": "F-001"},
            },
        ],
    }


class TestOutboxValidate(unittest.TestCase):
    def test_validate_all_routes_to_validated_and_failed_with_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            outbox_root = root / "outbox"
            ready_dir = outbox_root / "ready"

            _base_policy(policy_dir)
            _base_generated(generated_dir)

            _write_json(ready_dir / "good.json", _valid_bundle_payload())

            bad_schema_bundle = _valid_bundle_payload()
            del bad_schema_bundle["work_items"][0]["relations"]
            _write_json(ready_dir / "bad.json", bad_schema_bundle)

            result = validate_outbox(
                bundle=None,
                validate_all=True,
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                schema_path=Path("schema/bundle.schema.json"),
                outbox_root=outbox_root,
            )

            self.assertEqual(result["validated_count"], 2)
            self.assertEqual(result["passed_count"], 1)
            self.assertEqual(result["failed_count"], 1)
            self.assertFalse((ready_dir / "good.json").exists())
            self.assertFalse((ready_dir / "bad.json").exists())
            self.assertTrue((outbox_root / "validated" / "good.json").exists())
            self.assertTrue((outbox_root / "failed" / "bad.json").exists())

            failed_entry = next(entry for entry in result["results"] if entry["result"] == "failed")
            self.assertIsNotNone(failed_entry["report_path"])
            self.assertTrue(Path(failed_entry["report_path"]).exists())

    def test_policy_failure_duplicate_local_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            outbox_root = root / "outbox"
            ready_dir = outbox_root / "ready"

            _base_policy(policy_dir)
            _base_generated(generated_dir)

            bad_policy_bundle = _valid_bundle_payload()
            bad_policy_bundle["bundle_id"] = "bundle-policy-fail"
            bad_policy_bundle["work_items"][1]["local_id"] = "F-001"
            bundle_path = ready_dir / "dup.json"
            _write_json(bundle_path, bad_policy_bundle)

            result = validate_outbox(
                bundle=str(bundle_path),
                validate_all=False,
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                schema_path=Path("schema/bundle.schema.json"),
                outbox_root=outbox_root,
            )

            self.assertEqual(result["failed_count"], 1)
            failed_report = result["results"][0]["report"]
            issue_codes = [issue["code"] for issue in failed_report["issues"]]
            self.assertIn("DUPLICATE_LOCAL_ID", issue_codes)

    def test_metadata_failure_unknown_area_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            outbox_root = root / "outbox"
            ready_dir = outbox_root / "ready"

            _base_policy(policy_dir)
            _base_generated(generated_dir)

            bad_metadata_bundle = _valid_bundle_payload()
            bad_metadata_bundle["bundle_id"] = "bundle-metadata-fail"
            bad_metadata_bundle["context"]["default_area_path"] = "Project\\Unknown"
            bundle_path = ready_dir / "meta.json"
            _write_json(bundle_path, bad_metadata_bundle)

            result = validate_outbox(
                bundle=str(bundle_path),
                validate_all=False,
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                schema_path=Path("schema/bundle.schema.json"),
                outbox_root=outbox_root,
            )

            self.assertEqual(result["failed_count"], 1)
            failed_report = result["results"][0]["report"]
            issue_codes = [issue["code"] for issue in failed_report["issues"]]
            self.assertIn("UNKNOWN_AREA_PATH", issue_codes)


if __name__ == "__main__":
    unittest.main()
