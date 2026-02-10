import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

import yaml

from adoctl.outbox.write import write_outbox


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
                    "applies_to": ["UserStory"],
                },
                "priority": {"reference_name": "Microsoft.VSTS.Common.Priority", "applies_to": ["Feature"]},
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
            "allowed_fields": {
                "Feature": ["title", "description", "priority"],
                "UserStory": ["title", "description", "acceptance_criteria", "story_points"],
            },
            "required_fields": {
                "Feature": ["title", "description"],
                "UserStory": ["title", "description", "acceptance_criteria", "story_points"],
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
            "work_item_standards": {},
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
                        {"reference_name": "Microsoft.VSTS.Common.Priority"},
                    ]
                },
                "User Story": {
                    "fields": [
                        {"reference_name": "System.Title"},
                        {"reference_name": "System.Description"},
                        {"reference_name": "Microsoft.VSTS.Common.AcceptanceCriteria"},
                        {"reference_name": "Microsoft.VSTS.Scheduling.StoryPoints"},
                    ]
                },
            },
        },
    )


def _bundle_payload(bundle_id: str = "bundle-1") -> dict:
    return {
        "schema_version": "1.0",
        "bundle_id": bundle_id,
        "source": {
            "agent_name": "test-agent",
            "prompt_id": "write-test",
            "generated_at": "2026-02-09T00:00:00Z",
        },
        "context": {},
        "work_items": [
            {
                "local_id": "F-001",
                "type": "Feature",
                "title": "Feature title",
                "description": "Feature description",
                "acceptance_criteria": [],
                "fields": {"priority": 2},
                "relations": {"parent_local_id": "9001"},
            },
            {
                "local_id": "US-001",
                "type": "UserStory",
                "title": "Story title",
                "description": "Story description",
                "acceptance_criteria": ["Given A, when B, then C."],
                "fields": {"story_points": 3},
                "relations": {"parent_local_id": "F-001"},
            },
        ],
    }


class TestOutboxWrite(unittest.TestCase):
    def test_write_dry_run_outputs_resolved_plan_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            outbox_root = root / "outbox"
            audit_root = root / "audit"
            validated_bundle = outbox_root / "validated" / "bundle.json"

            _base_policy(policy_dir)
            _base_generated(generated_dir)
            _write_json(validated_bundle, _bundle_payload())

            result = write_outbox(
                bundle=None,
                write_all_validated=True,
                dry_run=True,
                org_url="https://dev.azure.com/example-org",
                project="ExampleProject",
                pat=None,
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                outbox_root=outbox_root,
                audit_root=audit_root,
            )

            self.assertEqual(result["processed_count"], 1)
            self.assertEqual(result["succeeded_count"], 1)
            self.assertEqual(result["failed_count"], 0)
            self.assertTrue(result["strict_ready"])
            self.assertTrue(validated_bundle.exists())
            self.assertFalse((outbox_root / "_written_work_items.yaml").exists())

            bundle_result = result["results"][0]
            self.assertEqual(bundle_result["result"], "passed")
            methods = [op["method"] for op in bundle_result["operations"]]
            self.assertEqual(methods, ["POST", "PATCH", "POST", "PATCH"])
            self.assertIn("/_apis/wit/workitems/%24Feature", bundle_result["operations"][0]["url"])
            self.assertEqual(
                bundle_result["operations"][1]["request_body"][0]["value"]["rel"],
                "System.LinkTypes.Hierarchy-Reverse",
            )
            self.assertIn("F-001", bundle_result["local_id_to_ado_id"])
            self.assertIn("US-001", bundle_result["local_id_to_ado_id"])

            audit_path = Path(result["audit_path"])
            self.assertTrue(audit_path.exists())
            audit_payload = yaml.safe_load(audit_path.read_text(encoding="utf-8"))
            self.assertEqual(audit_payload["summary"]["processed_count"], 1)
            self.assertEqual(audit_payload["summary"]["failed_count"], 0)

    def test_write_real_success_moves_bundle_to_archived(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            outbox_root = root / "outbox"
            audit_root = root / "audit"
            validated_bundle = outbox_root / "validated" / "bundle.json"

            _base_policy(policy_dir)
            _base_generated(generated_dir)
            _write_json(validated_bundle, _bundle_payload())

            create_ids = iter([7001, 7002])

            def fake_create(_: Any, __: str, ___: List[Dict[str, Any]]) -> Dict[str, Any]:
                return {"id": next(create_ids)}

            def fake_link(_: Any, __: str, ___: List[Dict[str, Any]]) -> Dict[str, Any]:
                return {"id": 9999}

            result = write_outbox(
                bundle=None,
                write_all_validated=True,
                dry_run=False,
                org_url="https://dev.azure.com/example-org",
                project="ExampleProject",
                pat="dummy",
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                outbox_root=outbox_root,
                audit_root=audit_root,
                create_request=fake_create,
                link_request=fake_link,
            )

            self.assertEqual(result["processed_count"], 1)
            self.assertEqual(result["succeeded_count"], 1)
            self.assertEqual(result["failed_count"], 0)
            self.assertTrue(result["strict_ready"])
            self.assertFalse(validated_bundle.exists())
            archived_files = list((outbox_root / "archived").glob("*.json"))
            self.assertEqual(len(archived_files), 1)
            registry_payload = yaml.safe_load((outbox_root / "_written_work_items.yaml").read_text(encoding="utf-8"))
            registry_index = registry_payload["ado_id_index"]
            self.assertEqual(registry_index[7001]["source_local_id"], "F-001")
            self.assertEqual(registry_index[7002]["source_local_id"], "US-001")

    def test_write_feature_acceptance_criteria_falls_back_to_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            outbox_root = root / "outbox"
            audit_root = root / "audit"
            validated_bundle = outbox_root / "validated" / "bundle.json"

            _base_policy(policy_dir)
            _base_generated(generated_dir)
            payload = _bundle_payload()
            payload["work_items"][0]["acceptance_criteria"] = [
                "Given feature scope, when behavior is complete, then value is delivered."
            ]
            _write_json(validated_bundle, payload)

            result = write_outbox(
                bundle=None,
                write_all_validated=True,
                dry_run=True,
                org_url="https://dev.azure.com/example-org",
                project="ExampleProject",
                pat=None,
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                outbox_root=outbox_root,
                audit_root=audit_root,
            )

            self.assertEqual(result["failed_count"], 0)
            feature_create_op = result["results"][0]["operations"][0]
            request_body = feature_create_op["request_body"]
            by_path = {entry["path"]: entry["value"] for entry in request_body}
            self.assertIn("/fields/System.Description", by_path)
            self.assertIn("Acceptance Criteria:", by_path["/fields/System.Description"])
            self.assertIn("Given feature scope", by_path["/fields/System.Description"])
            self.assertNotIn("/fields/Microsoft.VSTS.Common.AcceptanceCriteria", by_path)

    def test_write_description_markdown_is_transformed_to_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            outbox_root = root / "outbox"
            audit_root = root / "audit"
            validated_bundle = outbox_root / "validated" / "bundle.json"

            _base_policy(policy_dir)
            _base_generated(generated_dir)
            payload = _bundle_payload()
            payload["work_items"][0]["description"] = "# Feature Summary\n- First item\n- Second item"
            _write_json(validated_bundle, payload)

            result = write_outbox(
                bundle=None,
                write_all_validated=True,
                dry_run=True,
                org_url="https://dev.azure.com/example-org",
                project="ExampleProject",
                pat=None,
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                outbox_root=outbox_root,
                audit_root=audit_root,
            )

            self.assertEqual(result["failed_count"], 0)
            feature_create_op = result["results"][0]["operations"][0]
            by_path = {entry["path"]: entry["value"] for entry in feature_create_op["request_body"]}
            rendered_description = by_path["/fields/System.Description"]
            self.assertIn("<h1>Feature Summary</h1>", rendered_description)
            self.assertIn("<ul><li>First item</li><li>Second item</li></ul>", rendered_description)

    def test_write_invalid_owner_defaults_to_null_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            outbox_root = root / "outbox"
            audit_root = root / "audit"
            validated_bundle = outbox_root / "validated" / "bundle.json"

            _write_yaml(
                policy_dir / "wit_map.yaml",
                {
                    "schema_version": "1.0",
                    "canonical_to_ado": {"UserStory": "User Story"},
                },
            )
            _write_yaml(
                policy_dir / "field_map.yaml",
                {
                    "schema_version": "1.0",
                    "canonical_to_ado": {
                        "title": {"reference_name": "System.Title", "applies_to": ["UserStory"]},
                        "description": {"reference_name": "System.Description", "applies_to": ["UserStory"]},
                        "owner": {"reference_name": "System.AssignedTo", "applies_to": ["UserStory"]},
                    },
                },
            )
            _write_yaml(
                policy_dir / "field_policy.yaml",
                {
                    "schema_version": "1.0",
                    "agent_contract_export": {"include_work_item_types": ["UserStory"]},
                    "allowed_fields": {"UserStory": ["owner"]},
                    "required_fields": {"UserStory": ["title", "description"]},
                    "description_required_sections": {},
                    "description_optional_sections": {},
                    "owner_identity": {"format": "display_name"},
                },
            )
            _write_yaml(
                policy_dir / "link_policy.yaml",
                {
                    "schema_version": "1.0",
                    "allowed_link_types": ["parent-child"],
                    "max_depth": 2,
                    "forbid_double_nesting": ["UserStory"],
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
                generated_dir / "wit_contract.yaml",
                {
                    "schema_version": "1.0",
                    "work_item_types": {
                        "User Story": {
                            "fields": [
                                {"reference_name": "System.Title"},
                                {"reference_name": "System.Description"},
                                {"reference_name": "System.AssignedTo"},
                            ]
                        }
                    },
                },
            )
            _write_yaml(
                generated_dir / "planning_context.yaml",
                {
                    "schema_version": "1.0",
                    "project_assignable_identities": [],
                    "teams": [
                        {
                            "name": "DataScience",
                            "assignable_identities": [
                                {
                                    "display_name": "Alex Data",
                                    "unique_name": "alex.data@example.org",
                                }
                            ],
                        }
                    ],
                },
            )

            _write_json(
                validated_bundle,
                {
                    "schema_version": "1.0",
                    "bundle_id": "bundle-owner",
                    "source": {
                        "agent_name": "test-agent",
                        "prompt_id": "write-owner",
                        "generated_at": "2026-02-09T00:00:00Z",
                    },
                    "context": {"team": "DataScience"},
                    "work_items": [
                        {
                            "local_id": "US-001",
                            "type": "UserStory",
                            "title": "Story with owner",
                            "description": "Owner scenario",
                            "acceptance_criteria": [],
                            "fields": {"owner": "alex.data@example.org"},
                            "relations": {"parent_local_id": "9001"},
                        }
                    ],
                },
            )

            result = write_outbox(
                bundle=None,
                write_all_validated=True,
                dry_run=True,
                org_url="https://dev.azure.com/example-org",
                project="ExampleProject",
                pat=None,
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                outbox_root=outbox_root,
                audit_root=audit_root,
            )

            self.assertEqual(result["failed_count"], 0)
            create_operation = result["results"][0]["operations"][0]
            by_path = {entry["path"]: entry["value"] for entry in create_operation["request_body"]}
            self.assertNotIn("/fields/System.AssignedTo", by_path)
            self.assertTrue(create_operation["warnings"])
            self.assertIn("Assigned To will be null", create_operation["warnings"][0])

    def test_write_owner_override_sets_assigned_to(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            outbox_root = root / "outbox"
            audit_root = root / "audit"
            validated_bundle = outbox_root / "validated" / "bundle.json"

            _write_yaml(
                policy_dir / "wit_map.yaml",
                {
                    "schema_version": "1.0",
                    "canonical_to_ado": {"UserStory": "User Story"},
                },
            )
            _write_yaml(
                policy_dir / "field_map.yaml",
                {
                    "schema_version": "1.0",
                    "canonical_to_ado": {
                        "title": {"reference_name": "System.Title", "applies_to": ["UserStory"]},
                        "description": {"reference_name": "System.Description", "applies_to": ["UserStory"]},
                        "owner": {"reference_name": "System.AssignedTo", "applies_to": ["UserStory"]},
                    },
                },
            )
            _write_yaml(
                policy_dir / "field_policy.yaml",
                {
                    "schema_version": "1.0",
                    "agent_contract_export": {"include_work_item_types": ["UserStory"]},
                    "allowed_fields": {"UserStory": ["owner"]},
                    "required_fields": {"UserStory": ["title", "description"]},
                    "description_required_sections": {},
                    "description_optional_sections": {},
                    "owner_identity": {"format": "display_name"},
                },
            )
            _write_yaml(
                policy_dir / "link_policy.yaml",
                {
                    "schema_version": "1.0",
                    "allowed_link_types": ["parent-child"],
                    "max_depth": 2,
                    "forbid_double_nesting": ["UserStory"],
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
                generated_dir / "wit_contract.yaml",
                {
                    "schema_version": "1.0",
                    "work_item_types": {
                        "User Story": {
                            "fields": [
                                {"reference_name": "System.Title"},
                                {"reference_name": "System.Description"},
                                {"reference_name": "System.AssignedTo"},
                            ]
                        }
                    },
                },
            )
            _write_yaml(
                generated_dir / "planning_context.yaml",
                {
                    "schema_version": "1.0",
                    "project_assignable_identities": [],
                    "teams": [
                        {
                            "name": "DataScience",
                            "assignable_identities": [
                                {
                                    "display_name": "Alex Data",
                                    "unique_name": "alex.data@example.org",
                                }
                            ],
                        }
                    ],
                },
            )
            _write_json(
                validated_bundle,
                {
                    "schema_version": "1.0",
                    "bundle_id": "bundle-owner-override",
                    "source": {
                        "agent_name": "test-agent",
                        "prompt_id": "write-owner",
                        "generated_at": "2026-02-09T00:00:00Z",
                    },
                    "context": {"team": "DataScience"},
                    "work_items": [
                        {
                            "local_id": "US-001",
                            "type": "UserStory",
                            "title": "Story with override owner",
                            "description": "Owner scenario",
                            "acceptance_criteria": [],
                            "fields": {},
                            "relations": {"parent_local_id": "9001"},
                        }
                    ],
                },
            )

            result = write_outbox(
                bundle=None,
                write_all_validated=True,
                dry_run=True,
                org_url="https://dev.azure.com/example-org",
                project="ExampleProject",
                pat=None,
                owner_display_name="Alex Data",
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                outbox_root=outbox_root,
                audit_root=audit_root,
            )
            self.assertEqual(result["failed_count"], 0)
            create_operation = result["results"][0]["operations"][0]
            by_path = {entry["path"]: entry["value"] for entry in create_operation["request_body"]}
            self.assertEqual(by_path["/fields/System.AssignedTo"], "Alex Data")

    def test_write_real_stops_on_first_error_and_records_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            outbox_root = root / "outbox"
            audit_root = root / "audit"
            bundle_one = outbox_root / "validated" / "bundle_one.json"
            bundle_two = outbox_root / "validated" / "bundle_two.json"

            _base_policy(policy_dir)
            _base_generated(generated_dir)
            _write_json(bundle_one, _bundle_payload(bundle_id="bundle-one"))
            _write_json(bundle_two, _bundle_payload(bundle_id="bundle-two"))

            create_ids = iter([8001, 8002, 8003, 8004])

            def fake_create(_: Any, __: str, ___: List[Dict[str, Any]]) -> Dict[str, Any]:
                return {"id": next(create_ids)}

            def fake_link(_: Any, __: str, ___: List[Dict[str, Any]]) -> Dict[str, Any]:
                raise RuntimeError("simulated link failure")

            result = write_outbox(
                bundle=None,
                write_all_validated=True,
                dry_run=False,
                org_url="https://dev.azure.com/example-org",
                project="ExampleProject",
                pat="dummy",
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                outbox_root=outbox_root,
                audit_root=audit_root,
                create_request=fake_create,
                link_request=fake_link,
            )

            self.assertEqual(result["processed_count"], 1)
            self.assertEqual(result["succeeded_count"], 0)
            self.assertEqual(result["failed_count"], 1)
            self.assertFalse(result["strict_ready"])
            self.assertTrue(result["stopped_on_error"])
            self.assertTrue(bundle_one.exists())
            self.assertTrue(bundle_two.exists())

            bundle_result = result["results"][0]
            self.assertEqual(bundle_result["result"], "failed")
            self.assertIn("simulated link failure", bundle_result["error"])
            failed_ops = [op for op in bundle_result["operations"] if op.get("status") == "failed"]
            self.assertGreaterEqual(len(failed_ops), 1)

            audit_path = Path(result["audit_path"])
            self.assertTrue(audit_path.exists())
            audit_payload = yaml.safe_load(audit_path.read_text(encoding="utf-8"))
            self.assertEqual(audit_payload["summary"]["processed_count"], 1)
            self.assertEqual(audit_payload["summary"]["failed_count"], 1)
            self.assertTrue(audit_payload["summary"]["stopped_on_error"])
            registry_payload = yaml.safe_load((outbox_root / "_written_work_items.yaml").read_text(encoding="utf-8"))
            self.assertEqual(registry_payload["ado_id_index"][8001]["source_local_id"], "F-001")

    def test_write_uses_numeric_parent_reference_for_linking(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_dir = root / "policy"
            generated_dir = root / "generated"
            outbox_root = root / "outbox"
            audit_root = root / "audit"
            validated_bundle = outbox_root / "validated" / "bundle.json"

            _base_policy(policy_dir)
            _base_generated(generated_dir)
            payload = _bundle_payload()
            payload["work_items"] = [payload["work_items"][1]]
            payload["work_items"][0]["local_id"] = "US-NEW"
            payload["work_items"][0]["relations"]["parent_local_id"] = "9012"
            _write_json(validated_bundle, payload)

            captured_link_payloads: List[List[Dict[str, Any]]] = []

            def fake_create(_: Any, __: str, ___: List[Dict[str, Any]]) -> Dict[str, Any]:
                return {"id": 7100}

            def fake_link(_: Any, __: str, patch_doc: List[Dict[str, Any]]) -> Dict[str, Any]:
                captured_link_payloads.append(patch_doc)
                return {"id": 7100}

            result = write_outbox(
                bundle=None,
                write_all_validated=True,
                dry_run=False,
                org_url="https://dev.azure.com/example-org",
                project="ExampleProject",
                pat="dummy",
                policy_dir=policy_dir,
                generated_dir=generated_dir,
                outbox_root=outbox_root,
                audit_root=audit_root,
                create_request=fake_create,
                link_request=fake_link,
            )

            self.assertEqual(result["failed_count"], 0)
            self.assertEqual(len(captured_link_payloads), 1)
            link_target_url = captured_link_payloads[0][0]["value"]["url"]
            self.assertIn("/_apis/wit/workitems/9012", link_target_url)


if __name__ == "__main__":
    unittest.main()
