from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from adoctl.ado_client.auth import basic_auth_header_from_pat
from adoctl.ado_client.models import ADOConfig


def ado_get(cfg: ADOConfig, url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    headers: Dict[str, str] = {"Accept": "application/json"}
    headers.update(basic_auth_header_from_pat(cfg.pat))

    request_params = dict(params or {})
    request_params.setdefault("api-version", cfg.api_version)

    resp = requests.get(url, headers=headers, params=request_params, timeout=30)
    if resp.status_code >= 400:
        body = (resp.text or "")[:500]
        raise RuntimeError(f"ADO GET failed ({resp.status_code}) for {url}: {body}")
    return resp.json()

