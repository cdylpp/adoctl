from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

import requests

from adoctl.ado_client.auth import basic_auth_header_from_pat
from adoctl.ado_client.models import ADOConfig


def _is_expand_fields_conflict(status_code: int, body: str, params: Dict[str, str]) -> bool:
    if status_code != 400:
        return False
    if "fields" not in params or "$expand" not in params:
        return False
    normalized = body.lower()
    if "conflictingparametersexception" in normalized:
        return True
    return "expand parameter" in normalized and "fields parameter" in normalized


def ado_get(cfg: ADOConfig, url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    headers: Dict[str, str] = {"Accept": "application/json"}
    headers.update(basic_auth_header_from_pat(cfg.pat))

    request_params = dict(params or {})
    request_params.setdefault("api-version", cfg.api_version)

    resp = requests.get(url, headers=headers, params=request_params, timeout=30)
    if _is_expand_fields_conflict(resp.status_code, resp.text or "", request_params):
        retry_params = dict(request_params)
        retry_params.pop("$expand", None)
        resp = requests.get(url, headers=headers, params=retry_params, timeout=30)
    if resp.status_code >= 400:
        body = (resp.text or "")[:500]
        raise RuntimeError(f"ADO GET failed ({resp.status_code}) for {url}: {body}")
    return resp.json()


def ado_post_json_patch(
    cfg: ADOConfig,
    url: str,
    patch_document: Sequence[Dict[str, Any]],
    params: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    headers: Dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json-patch+json",
    }
    headers.update(basic_auth_header_from_pat(cfg.pat))

    request_params = dict(params or {})
    request_params.setdefault("api-version", cfg.api_version)

    resp = requests.post(url, headers=headers, params=request_params, json=list(patch_document), timeout=30)
    if resp.status_code >= 400:
        body = (resp.text or "")[:500]
        raise RuntimeError(f"ADO POST failed ({resp.status_code}) for {url}: {body}")
    return resp.json()


def ado_post_json(
    cfg: ADOConfig,
    url: str,
    payload: Dict[str, Any],
    params: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    headers: Dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    headers.update(basic_auth_header_from_pat(cfg.pat))

    request_params = dict(params or {})
    request_params.setdefault("api-version", cfg.api_version)

    resp = requests.post(url, headers=headers, params=request_params, json=dict(payload), timeout=30)
    if resp.status_code >= 400:
        body = (resp.text or "")[:500]
        raise RuntimeError(f"ADO POST failed ({resp.status_code}) for {url}: {body}")
    return resp.json()


def ado_patch_json_patch(
    cfg: ADOConfig,
    url: str,
    patch_document: Sequence[Dict[str, Any]],
    params: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    headers: Dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json-patch+json",
    }
    headers.update(basic_auth_header_from_pat(cfg.pat))

    request_params = dict(params or {})
    request_params.setdefault("api-version", cfg.api_version)

    resp = requests.patch(url, headers=headers, params=request_params, json=list(patch_document), timeout=30)
    if resp.status_code >= 400:
        body = (resp.text or "")[:500]
        raise RuntimeError(f"ADO PATCH failed ({resp.status_code}) for {url}: {body}")
    return resp.json()
