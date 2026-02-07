import tempfile
import unittest
from pathlib import Path

import yaml

from adoctl.config.wiki_policy_bootstrap import bootstrap_field_policy_from_docs


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestWikiPolicyBootstrap(unittest.TestCase):
    def test_bootstrap_extracts_required_optional_and_ignores_nested(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "docs"
            out_path = root / "field_policy.yaml"

            _write_text(
                docs_dir / "Blockers.md",
                "\n".join(
                    [
                        "# Blocker",
                        "## Metadata",
                        "**Work Item Type**: `Blocker`",
                        "### Required",
                        "- **Description**: explain issue",
                        "- **Links**: include links",
                        "    - **Parent Link:** context",
                        "    - **Successor Link:** dependency",
                    ]
                ),
            )
            _write_text(
                docs_dir / "Risks.md",
                "\n".join(
                    [
                        "# Risks",
                        "- Work Item Type: `Risk`",
                        "**Required**",
                        "- **Title**: risk title",
                        "- **Owner**: risk owner",
                        "### Optional",
                        "- **Likelihood**: optional",
                    ]
                ),
            )
            _write_text(docs_dir / "Critical-Business-Decisions.md", "# CBD\n### Required\n- **Title**")
            _write_text(docs_dir / "Features.md", "# Feature\n### Required\n- **Title**\n- **Description**")
            _write_text(docs_dir / "Iterations.md", "# Iterations")
            _write_text(docs_dir / "Key-Results.md", "# KR\n### Required\n- **Title**")
            _write_text(docs_dir / "Linking.md", "# Linking")
            _write_text(docs_dir / "User-Stories.md", "# Story\n### Required\n- **Title**")
            _write_text(docs_dir / "Work-Items.md", "# Work Items")

            # Existing canonical policy keys should be preserved.
            out_path.write_text(
                yaml.safe_dump(
                    {
                        "schema_version": "1.0",
                        "allowed_fields": {"Feature": [], "UserStory": []},
                        "required_fields": {"Feature": ["priority"], "UserStory": []},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            result = bootstrap_field_policy_from_docs(docs_dir=str(docs_dir), out_path=str(out_path))
            self.assertEqual(result["source_count"], 9)

            payload = yaml.safe_load(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["required_fields"]["Feature"], ["priority"])
            self.assertEqual(payload["wiki_required_metadata"]["Blocker"], ["Description", "Links"])
            self.assertNotIn("Parent Link:", payload["wiki_required_metadata"]["Blocker"])
            self.assertEqual(payload["wiki_required_metadata"]["Risk"], ["Title", "Owner"])
            self.assertEqual(payload["wiki_optional_metadata"]["Risk"], ["Likelihood"])


if __name__ == "__main__":
    unittest.main()
