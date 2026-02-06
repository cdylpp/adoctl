import tempfile
import unittest
from pathlib import Path

import yaml

from adoctl.config.context import CLIContext, load_cli_context, save_cli_context


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


if __name__ == "__main__":
    unittest.main()
