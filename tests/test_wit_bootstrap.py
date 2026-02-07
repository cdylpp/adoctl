import json
import tempfile
import unittest
from pathlib import Path

import yaml

from adoctl.sync.wit_bootstrap import bootstrap_wit_contracts_from_extract


class TestWitBootstrap(unittest.TestCase):
    def test_bootstrap_from_double_encoded_extract_json(self) -> None:
        extract_payload = {
            "count": 2,
            "value": [
                {
                    "name": "Feature",
                    "referenceName": "Microsoft.VSTS.WorkItemTypes.Feature",
                    "description": "Feature item",
                    "isDisabled": False,
                    "states": [{"name": "New", "category": "Proposed", "color": "b2b2b2"}],
                    "fieldInstances": [
                        {
                            "name": "Title",
                            "referenceName": "System.Title",
                            "alwaysRequired": True,
                            "defaultValue": None,
                            "helpText": "Work item title",
                        }
                    ],
                },
                {
                    "name": "User Story",
                    "referenceName": "Microsoft.VSTS.WorkItemTypes.UserStory",
                    "description": "User Story item",
                    "isDisabled": False,
                    "states": [{"name": "New", "category": "Proposed", "color": "b2b2b2"}],
                    "fieldInstances": [
                        {
                            "name": "Title",
                            "referenceName": "System.Title",
                            "alwaysRequired": True,
                            "defaultValue": None,
                            "helpText": "Story title",
                        }
                    ],
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "data.json"
            input_path.write_text(json.dumps(json.dumps(extract_payload)), encoding="utf-8")

            output_dir = tmp_path / "generated"
            result = bootstrap_wit_contracts_from_extract(str(input_path), str(output_dir))

            self.assertEqual(result["work_item_type_count"], 2)
            self.assertTrue((output_dir / "wit_contract.yaml").exists())
            self.assertTrue((output_dir / "wit_contracts" / "feature.yaml").exists())
            self.assertTrue((output_dir / "wit_contracts" / "user_story.yaml").exists())

            aggregate = yaml.safe_load((output_dir / "wit_contract.yaml").read_text(encoding="utf-8"))
            self.assertIn("Feature", aggregate["work_item_types"])
            self.assertIn("User Story", aggregate["work_item_types"])
            self.assertEqual(
                aggregate["work_item_types"]["Feature"]["fields"][0]["reference_name"],
                "System.Title",
            )


if __name__ == "__main__":
    unittest.main()
