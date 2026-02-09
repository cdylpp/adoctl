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
            if normalized.endswith("/_apis/teams"):
                return {
                    "value": [
                        {"id": "t1", "name": "DataScience"},
                        {"id": "t2", "name": "AppDev"},
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
            if normalized.endswith("/_apis/wit/workitems"):
                return {
                    "value": [
                        {
                            "id": 100,
                            "fields": {
                                "System.WorkItemType": "Objective",
                                "System.Title": "Improve onboarding",
                                "System.State": "New",
                                "System.AreaPath": project_name,
                                "System.IterationPath": project_name,
                            },
                        },
                        {
                            "id": 101,
                            "fields": {
                                "System.WorkItemType": "Key Result",
                                "System.Title": "Reduce time to value",
                                "System.State": "New",
                                "System.AreaPath": project_name,
                                "System.IterationPath": project_name,
                                "System.Parent": 100,
                            },
                        },
                    ]
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
            self.assertEqual(len(planning["teams"]), 2)
            data_science = next(item for item in planning["teams"] if item["name"] == "DataScience")
            self.assertEqual(data_science["default_area_path"], f"{project_name}\\DataScience")
            self.assertIn(f"{project_name}\\DataScience", data_science["allowed_area_paths"])
            self.assertIn(f"{project_name}\\DataScience", data_science["allowed_iteration_paths"])
            self.assertEqual(len(planning["objectives"]), 1)
            self.assertEqual(len(planning["key_results"]), 1)
            self.assertEqual(planning["key_results"][0]["parent_objective_id"], 100)

            raw_dump = json.loads(raw_dump_path.read_text(encoding="utf-8"))
            self.assertEqual(raw_dump["project"], project_name)
            self.assertIn("objective_kr_wiql_payload", raw_dump)
            self.assertIn("team_settings_payloads", raw_dump)


if __name__ == "__main__":
    unittest.main()
