import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from adoctl.cli.home import apply_home_menu_choice, load_generated_teams, render_home_screen
from adoctl.config.context import CLIContext


class TestHomeScreen(unittest.TestCase):
    def test_render_home_screen_shows_context(self) -> None:
        context = CLIContext(
            org_url="https://dev.azure.com/MyOrg",
            project="BlackLagoon",
            team="DataScience",
            current_iteration="BlackLagoon\\CY26\\Q2\\03",
        )
        screen = render_home_screen(context)
        self.assertIn("ADOCTL HOME", screen)
        self.assertIn("ORG URL", screen)
        self.assertIn("PROJECT", screen)
        self.assertIn("TEAM", screen)
        self.assertIn("CURRENT ITERATION", screen)
        self.assertIn("DataScience", screen)

    def test_load_generated_teams_for_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "teams.yaml"
            with path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(
                    {
                        "project": "BlackLagoon",
                        "teams": [
                            {"name": "DataScience"},
                            {"name": "DataEngineering"},
                            {"name": "DataScience"},
                        ],
                    },
                    f,
                )
            teams = load_generated_teams(project="BlackLagoon", teams_path=path)
            self.assertEqual(teams, ["DataEngineering", "DataScience"])

    def test_load_generated_teams_project_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "teams.yaml"
            with path.open("w", encoding="utf-8") as f:
                yaml.safe_dump({"project": "OtherProject", "teams": [{"name": "TeamA"}]}, f)
            teams = load_generated_teams(project="BlackLagoon", teams_path=path)
            self.assertEqual(teams, [])

    def test_menu_choice_select_team_from_list(self) -> None:
        context = CLIContext(project="BlackLagoon")
        with patch("adoctl.cli.home.load_generated_teams", return_value=["TeamA", "TeamB"]):
            with patch("builtins.input", return_value="2"):
                updated, should_exit = apply_home_menu_choice(context, "3")
        self.assertFalse(should_exit)
        self.assertEqual(updated.team, "TeamB")


if __name__ == "__main__":
    unittest.main()
