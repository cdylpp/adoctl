import tempfile
import unittest
from pathlib import Path

import yaml

from adoctl.config.context import CLIContext, load_cli_context, load_local_project_defaults, save_cli_context


class TestCLIContext(unittest.TestCase):
    def test_load_missing_context_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "context.yaml"
            context = load_cli_context(path=path)
            self.assertEqual(context, CLIContext())

    def test_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "context.yaml"
            expected = CLIContext(
                org_url="https://dev.azure.com/MyOrg",
                project="BlackLagoon",
                team="DataScience",
                current_iteration="BlackLagoon\\CY26\\Q2\\03",
                owner_display_name="Alex Data",
            )
            save_cli_context(expected, path=path)
            loaded = load_cli_context(path=path)
            self.assertEqual(loaded, expected)

    def test_load_ignores_invalid_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "context.yaml"
            with path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(["not", "a", "mapping"], f)
            self.assertEqual(load_cli_context(path=path), CLIContext())

    def test_load_applies_project_defaults_when_context_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "context.yaml"
            defaults_path = Path(tmpdir) / "project_defaults.yaml"
            with defaults_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(
                    {
                        "schema_version": "1.0",
                        "project": "Black Lagoon",
                        "project_id": "a91ee819-8d82-4e7a-a81c-3f7ed357ab17",
                        "ssl_verify": False,
                        "ca_bundle_path": "/tmp/org-ca.pem",
                    },
                    f,
                    sort_keys=False,
                )

            context = load_cli_context(path=path)
            defaults = load_local_project_defaults(path=defaults_path)
            self.assertEqual(context.project, "Black Lagoon")
            self.assertEqual(defaults.project, "Black Lagoon")
            self.assertEqual(defaults.project_id, "a91ee819-8d82-4e7a-a81c-3f7ed357ab17")
            self.assertFalse(defaults.ssl_verify)
            self.assertEqual(defaults.ca_bundle_path, "/tmp/org-ca.pem")


if __name__ == "__main__":
    unittest.main()
