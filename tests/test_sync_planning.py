import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from adoctl.ado_client.models import ADOConfig
from adoctl.sync.ado_sync import sync_ado_to_yaml


def _path_tree(project: str) -> dict:
    return {
        "path": f"\\{project}",
        "children": [
            {
                "path": f"\\{project}\\DataScience",
                "children": [{"path": f"\\{project}\\DataScience\\Sprint 01", "children": []}],
            },
            {"path": f"\\{project}\\AppDev", "children": []},
        ],
    }


class TestPlanningSync(unittest.TestCase):
    def test_sync_planning_outputs_team_paths_and_objective_kr_semantics(self) -> None:
        project_name = "Black Lagoon"

        def fake_get(_: ADOConfig, url: str, params=None):  # noqa: ANN001
            normalized = url.lower()
            if normalized.endswith("/_apis/projects/project-123/teams"):
                return {
                    "value": [
                        {"id": "t1", "name": "DataScience"},
                        {"id": "t2", "name": "AppDev"},
                    ]
                }
            if normalized.endswith("/_apis/projects/project-123/teams/t1/members"):
                return {
                    "value": [
                        {
                            "identity": {
                                "displayName": "Alex Data",
                                "uniqueName": "alex.data@example.org",
                                "mailAddress": "alex.data@example.org",
                            }
                        }
                    ]
                }
            if normalized.endswith("/_apis/projects/project-123/teams/t2/members"):
                return {
                    "value": [
                        {
                            "identity": {
                                "displayName": "Bailey App",
                                "uniqueName": "bailey.app@example.org",
                                "mailAddress": "bailey.app@example.org",
                            }
                        }
                    ]
                }
            if "/classificationnodes/areas" in normalized:
                return _path_tree(project_name)
            if "/classificationnodes/iterations" in normalized:
                return _path_tree(project_name)
            if normalized.endswith("/datascience/_apis/work/teamsettings/iterations"):
                return {"value": [{"path": f"{project_name}\\DataScience"}]}
            if normalized.endswith("/datascience/_apis/work/teamsettings/teamfieldvalues"):
                return {"value": [{"value": f"{project_name}\\DataScience"}]}
            if normalized.endswith("/appdev/_apis/work/teamsettings/iterations"):
                return {"value": [{"path": f"{project_name}\\AppDev"}]}
            if normalized.endswith("/appdev/_apis/work/teamsettings/teamfieldvalues"):
                return {"value": [{"value": f"{project_name}\\AppDev"}]}
            if normalized.endswith("/_apis/wit/workitems/100"):
                self.assertIsInstance(params, dict)
                self.assertNotIn("$expand", params)
                self.assertIn("System.WorkItemType", str(params.get("fields")))
                return {
                    "id": 100,
                    "fields": {
                        "System.WorkItemType": "Objective",
                        "System.Title": "Improve onboarding",
                        "System.State": "New",
                        "System.AreaPath": project_name,
                        "System.IterationPath": project_name,
                    },
                }
            if normalized.endswith("/_apis/wit/workitems/101"):
                self.assertIsInstance(params, dict)
                self.assertNotIn("$expand", params)
                self.assertIn("System.WorkItemType", str(params.get("fields")))
                return {
                    "id": 101,
                    "fields": {
                        "System.WorkItemType": "Key Result",
                        "System.Title": "Reduce time to value",
                        "System.State": "New",
                        "System.AreaPath": project_name,
                        "System.IterationPath": project_name,
                        "System.Parent": 100,
                    },
                }
            raise AssertionError(f"Unexpected GET URL in test: {url}")

        def fake_post(_: ADOConfig, url: str, payload, params=None):  # noqa: ANN001
            if not url.lower().endswith("/_apis/wit/wiql"):
                raise AssertionError(f"Unexpected POST URL in test: {url}")
            query = payload.get("query", "")
            self.assertIn("Objective", query)
            self.assertIn("Key Result", query)
            return {"workItems": [{"id": 100}, {"id": 101}]}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "generated"
            cfg = ADOConfig(
                org_url="https://dev.azure.com/example-org",
                project=project_name,
                project_id="project-123",
                pat="test-pat",
                api_version="6.0",
            )
            with patch("adoctl.sync.ado_sync.ado_get", side_effect=fake_get), patch(
                "adoctl.sync.ado_sync.ado_post_json", side_effect=fake_post
            ):
                sync_ado_to_yaml(
                    cfg=cfg,
                    out_dir=str(output_dir),
                    sections=["paths", "teams", "planning"],
                )

            planning_path = output_dir / "planning_context.yaml"
            raw_dump_path = output_dir / "planning_sync_dump.json"
            self.assertTrue(planning_path.exists())
            self.assertTrue(raw_dump_path.exists())
            self.assertTrue((output_dir / "teams.yaml").exists())
            self.assertTrue((output_dir / "paths_area.yaml").exists())
            self.assertTrue((output_dir / "paths_iteration.yaml").exists())

            planning = yaml.safe_load(planning_path.read_text(encoding="utf-8"))
            self.assertEqual(planning["project"], project_name)
            self.assertEqual(planning["core_team"], project_name)
            self.assertEqual(planning["project_backlog_defaults"]["area_path"], project_name)
            self.assertEqual(planning["project_backlog_defaults"]["iteration_path"], project_name)
            self.assertEqual(planning["owner_identity_mode"], "display_name")
            self.assertEqual(len(planning["project_assignable_identities"]), 2)
            self.assertEqual(len(planning["teams"]), 2)
            data_science = next(item for item in planning["teams"] if item["name"] == "DataScience")
            self.assertEqual(data_science["default_area_path"], f"{project_name}\\DataScience")
            self.assertIn(f"{project_name}\\DataScience", data_science["allowed_area_paths"])
            self.assertIn(f"{project_name}\\DataScience", data_science["allowed_iteration_paths"])
            self.assertEqual(len(data_science["assignable_identities"]), 1)
            self.assertEqual(len(planning["objectives"]), 1)
            self.assertEqual(len(planning["key_results"]), 1)
            self.assertEqual(planning["key_results"][0]["parent_objective_id"], 100)

            raw_dump = json.loads(raw_dump_path.read_text(encoding="utf-8"))
            self.assertEqual(raw_dump["project"], project_name)
            self.assertIn("objective_kr_wiql_payload", raw_dump)
            self.assertIn("team_settings_payloads", raw_dump)

    def test_sync_paths_strips_area_and_iteration_container_segments(self) -> None:
        project_name = "Black Lagoon"

        area_tree = {
            "path": f"\\{project_name}\\Area",
            "children": [
                {
                    "path": f"\\{project_name}\\Area\\DSA",
                    "children": [{"path": f"\\{project_name}\\Area\\DSA\\Analytics", "children": []}],
                }
            ],
        }
        iteration_tree = {
            "path": f"\\{project_name}\\Iteration",
            "children": [
                {
                    "path": f"\\{project_name}\\Iteration\\DSA",
                    "children": [{"path": f"\\{project_name}\\Iteration\\DSA\\FY26-Q2-03", "children": []}],
                }
            ],
        }

        def fake_get(_: ADOConfig, url: str, params=None):  # noqa: ANN001
            normalized = url.lower()
            if "/classificationnodes/areas" in normalized:
                return area_tree
            if "/classificationnodes/iterations" in normalized:
                return iteration_tree
            raise AssertionError(f"Unexpected GET URL in test: {url}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "generated"
            cfg = ADOConfig(
                org_url="https://dev.azure.com/example-org",
                project=project_name,
                project_id="project-123",
                pat="test-pat",
                api_version="6.0",
            )
            with patch("adoctl.sync.ado_sync.ado_get", side_effect=fake_get):
                sync_ado_to_yaml(
                    cfg=cfg,
                    out_dir=str(output_dir),
                    sections=["paths"],
                )

            area_paths = yaml.safe_load((output_dir / "paths_area.yaml").read_text(encoding="utf-8"))["area_paths"]
            iteration_paths = yaml.safe_load((output_dir / "paths_iteration.yaml").read_text(encoding="utf-8"))[
                "iteration_paths"
            ]
            self.assertIn(f"{project_name}\\DSA", area_paths)
            self.assertIn(f"{project_name}\\DSA\\Analytics", area_paths)
            self.assertIn(f"{project_name}\\DSA\\FY26-Q2-03", iteration_paths)
            self.assertTrue(all(f"{project_name}\\Area\\" not in path for path in area_paths))
            self.assertTrue(all(f"{project_name}\\Iteration\\" not in path for path in iteration_paths))

    def test_sync_planning_applies_team_default_overrides(self) -> None:
        project_name = "Black Lagoon"

        def fake_get(_: ADOConfig, url: str, params=None):  # noqa: ANN001
            normalized = url.lower()
            if normalized.endswith("/_apis/projects/project-123/teams"):
                return {"value": [{"id": "t1", "name": "Data Science and Analytics"}]}
            if "/classificationnodes/areas" in normalized:
                return {
                    "path": f"\\{project_name}\\Area",
                    "children": [{"path": f"\\{project_name}\\Area\\Data Science and Analytics", "children": []}],
                }
            if "/classificationnodes/iterations" in normalized:
                return {
                    "path": f"\\{project_name}\\Iteration",
                    "children": [{"path": f"\\{project_name}\\Iteration\\DSA", "children": []}],
                }
            if normalized.endswith("/data%20science%20and%20analytics/_apis/work/teamsettings/iterations"):
                return {"value": [{"path": f"{project_name}\\DSA"}]}
            if normalized.endswith("/data%20science%20and%20analytics/_apis/work/teamsettings/teamfieldvalues"):
                return {"defaultValue": f"{project_name}\\Data Science and Analytics", "value": []}
            if normalized.endswith("/_apis/projects/project-123/teams/t1/members"):
                return {"value": []}
            if normalized.endswith("/_apis/wit/wiql"):
                raise AssertionError("WIQL should not be called via GET")
            raise AssertionError(f"Unexpected GET URL in test: {url}")

        def fake_post(_: ADOConfig, url: str, payload, params=None):  # noqa: ANN001
            if not url.lower().endswith("/_apis/wit/wiql"):
                raise AssertionError(f"Unexpected POST URL in test: {url}")
            return {"workItems": []}

        overrides = {
            "data science and analytics": {
                "iteration_default": f"{project_name}\\DSA",
                "area_default": f"{project_name}\\Data Science and Analytics",
                "iteration_prefixes": [f"{project_name}\\DSA"],
                "area_prefixes": [f"{project_name}\\Data Science and Analytics"],
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "generated"
            cfg = ADOConfig(
                org_url="https://dev.azure.com/example-org",
                project=project_name,
                project_id="project-123",
                pat="test-pat",
                api_version="6.0",
            )
            with patch("adoctl.sync.ado_sync.ado_get", side_effect=fake_get), patch(
                "adoctl.sync.ado_sync.ado_post_json", side_effect=fake_post
            ), patch("adoctl.sync.ado_sync._load_team_defaults_policy", return_value=overrides):
                sync_ado_to_yaml(
                    cfg=cfg,
                    out_dir=str(output_dir),
                    sections=["paths", "teams", "planning"],
                )

            planning = yaml.safe_load((output_dir / "planning_context.yaml").read_text(encoding="utf-8"))
            team = planning["teams"][0]
            self.assertEqual(team["default_iteration_path"], f"{project_name}\\DSA")
            self.assertEqual(team["default_area_path"], f"{project_name}\\Data Science and Analytics")

    def test_sync_planning_scopes_key_results_by_configured_team_area_path(self) -> None:
        project_name = "Black Lagoon"

        def fake_get(_: ADOConfig, url: str, params=None):  # noqa: ANN001
            normalized = url.lower()
            if normalized.endswith("/_apis/projects/project-123/teams"):
                return {"value": [{"id": "t1", "name": "DataScience"}, {"id": "t2", "name": "AppDev"}]}
            if normalized.endswith("/_apis/projects/project-123/teams/t1/members"):
                return {"value": []}
            if normalized.endswith("/_apis/projects/project-123/teams/t2/members"):
                return {"value": []}
            if "/classificationnodes/areas" in normalized:
                return {
                    "path": f"\\{project_name}",
                    "children": [
                        {"path": f"\\{project_name}\\DataScience", "children": []},
                        {"path": f"\\{project_name}\\AppDev", "children": []},
                    ],
                }
            if "/classificationnodes/iterations" in normalized:
                return {
                    "path": f"\\{project_name}",
                    "children": [
                        {"path": f"\\{project_name}\\DataScience", "children": []},
                        {"path": f"\\{project_name}\\AppDev", "children": []},
                    ],
                }
            if normalized.endswith("/datascience/_apis/work/teamsettings/iterations"):
                return {"value": [{"path": f"{project_name}\\DataScience"}]}
            if normalized.endswith("/datascience/_apis/work/teamsettings/teamfieldvalues"):
                return {"value": [{"value": f"{project_name}\\DataScience"}]}
            if normalized.endswith("/appdev/_apis/work/teamsettings/iterations"):
                return {"value": [{"path": f"{project_name}\\AppDev"}]}
            if normalized.endswith("/appdev/_apis/work/teamsettings/teamfieldvalues"):
                return {"value": [{"value": f"{project_name}\\AppDev"}]}
            if normalized.endswith("/_apis/wit/workitems/100"):
                return {
                    "id": 100,
                    "fields": {
                        "System.WorkItemType": "Objective",
                        "System.Title": "Improve mission outcomes",
                        "System.State": "New",
                        "System.AreaPath": project_name,
                        "System.IterationPath": project_name,
                    },
                }
            if normalized.endswith("/_apis/wit/workitems/101"):
                return {
                    "id": 101,
                    "fields": {
                        "System.WorkItemType": "Key Result",
                        "System.Title": "DataScience KR",
                        "System.State": "New",
                        "System.AreaPath": f"{project_name}\\DataScience",
                        "System.IterationPath": f"{project_name}\\DataScience",
                        "System.Parent": 100,
                    },
                }
            if normalized.endswith("/_apis/wit/workitems/102"):
                return {
                    "id": 102,
                    "fields": {
                        "System.WorkItemType": "Key Result",
                        "System.Title": "AppDev KR",
                        "System.State": "New",
                        "System.AreaPath": f"{project_name}\\AppDev",
                        "System.IterationPath": f"{project_name}\\AppDev",
                        "System.Parent": 100,
                    },
                }
            raise AssertionError(f"Unexpected GET URL in test: {url}")

        def fake_post(_: ADOConfig, url: str, payload, params=None):  # noqa: ANN001
            if not url.lower().endswith("/_apis/wit/wiql"):
                raise AssertionError(f"Unexpected POST URL in test: {url}")
            return {"workItems": [{"id": 100}, {"id": 101}, {"id": 102}]}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "generated"
            cfg = ADOConfig(
                org_url="https://dev.azure.com/example-org",
                project=project_name,
                project_id="project-123",
                pat="test-pat",
                api_version="6.0",
            )
            with patch("adoctl.sync.ado_sync.ado_get", side_effect=fake_get), patch(
                "adoctl.sync.ado_sync.ado_post_json", side_effect=fake_post
            ):
                sync_ado_to_yaml(
                    cfg=cfg,
                    out_dir=str(output_dir),
                    sections=["paths", "teams", "planning"],
                    planning_team="DataScience",
                )

            planning = yaml.safe_load((output_dir / "planning_context.yaml").read_text(encoding="utf-8"))
            self.assertEqual(planning["configured_team_scope"], "DataScience")
            self.assertEqual(len(planning["key_results"]), 1)
            self.assertEqual(planning["key_results"][0]["id"], 101)
            self.assertEqual(planning["key_results"][0]["area_path"], f"{project_name}\\DataScience")
            self.assertEqual(len(planning["objectives"]), 1)


if __name__ == "__main__":
    unittest.main()
