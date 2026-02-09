import unittest
from unittest.mock import patch

from adoctl.ado_client.http import ado_get
from adoctl.ado_client.models import ADOConfig


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict:
        return self._payload


class TestADOHttp(unittest.TestCase):
    def test_ado_get_retries_without_expand_on_conflict(self) -> None:
        cfg = ADOConfig(org_url="https://dev.azure.com/example", pat="pat", api_version="6.0")
        conflict_text = "The expand parameter can not be used with the fields parameter."
        responses = [
            _FakeResponse(status_code=400, payload={}, text=conflict_text),
            _FakeResponse(status_code=200, payload={"id": 123}, text=""),
        ]

        with patch("adoctl.ado_client.http.requests.get", side_effect=responses) as mock_get:
            result = ado_get(
                cfg,
                "https://dev.azure.com/example/Black%20Lagoon/_apis/wit/workitems/123",
                params={"fields": "System.Id,System.Title", "$expand": "relations"},
            )

        self.assertEqual(result["id"], 123)
        self.assertEqual(mock_get.call_count, 2)
        first_params = mock_get.call_args_list[0].kwargs["params"]
        second_params = mock_get.call_args_list[1].kwargs["params"]
        self.assertIn("$expand", first_params)
        self.assertNotIn("$expand", second_params)
        self.assertIn("fields", second_params)
        self.assertEqual(second_params.get("api-version"), "6.0")

    def test_ado_get_does_not_retry_non_conflict_error(self) -> None:
        cfg = ADOConfig(org_url="https://dev.azure.com/example", pat="pat", api_version="6.0")
        error_response = _FakeResponse(status_code=400, payload={}, text="Some other error")

        with patch("adoctl.ado_client.http.requests.get", return_value=error_response) as mock_get:
            with self.assertRaises(RuntimeError):
                ado_get(
                    cfg,
                    "https://dev.azure.com/example/Black%20Lagoon/_apis/wit/workitems/123",
                    params={"fields": "System.Id,System.Title", "$expand": "relations"},
                )

        self.assertEqual(mock_get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
