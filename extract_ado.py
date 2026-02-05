import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import requests
import yaml


@dataclass
class ADOConfig:
    org_url: str              # e.g., "https://dev.azure.com/MyOrg"
    project: Optional[str]    # some endpoints are org-level; others project-level
    pat: str                  # personal access token
    api_version: str = "6.0"


def _auth_header(pat: str) -> Dict[str, str]:
    # ADO uses Basic auth with PAT as the password and blank username.
    token = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def _get(cfg: ADOConfig, url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    headers = {"Accept": "application/json"}
    headers.update(_auth_header(cfg.pat))

    params = dict(params or {})
    params.setdefault("api-version", cfg.api_version)

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"ADO GET failed ({resp.status_code}) for {url}: {resp.text[:500]}")
    return resp.json()


def _encode_path_segment(value: str) -> str:
    return quote(unquote(value), safe="")


def _join_url(base_url: str, *segments: Optional[str]) -> str:
    split = urlsplit(base_url)
    base_path = split.path.rstrip("/")

    cleaned = []
    for seg in segments:
        if seg is None:
            continue
        seg = str(seg).strip("/")
        if not seg:
            continue
        cleaned.append(_encode_path_segment(seg))

    path = base_path
    if cleaned:
        path = f"{base_path}/{'/'.join(cleaned)}"

    return urlunsplit((split.scheme, split.netloc, path, split.query, split.fragment))


def sync_ado_to_yaml(
    cfg: ADOConfig,
    out_dir: str,
    wit_names: Optional[List[str]] = None,
) -> None:
    """
    Writes generated config YAML files into out_dir:
      - projects.yaml
      - paths_area.yaml
      - paths_iteration.yaml
      - wit_contract.yaml

    wit_names: list like ["Feature", "User Story"] based on your process template.
    """
    wit_names = wit_names or ["Feature", "User Story"]
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # --- Projects (org-level)
    projects_url = _join_url(cfg.org_url, "_apis", "projects")
    projects = _get(cfg, projects_url).get("value", [])

    # --- Classification nodes (project-level): Areas and Iterations
    if not cfg.project:
        raise ValueError("cfg.project is required to sync area/iteration paths.")

    areas_url = _join_url(cfg.org_url, cfg.project, "_apis", "wit", "classificationnodes", "areas")
    iters_url = _join_url(cfg.org_url, cfg.project, "_apis", "wit", "classificationnodes", "iterations")

    # depth controls how many child levels come back
    areas_tree = _get(cfg, areas_url, params={"$depth": "100"})
    iters_tree = _get(cfg, iters_url, params={"$depth": "100"})

    def flatten_paths(node: Dict[str, Any]) -> List[str]:
        paths: List[str] = []

        def walk(n: Dict[str, Any]) -> None:
            path = n.get("path")
            if isinstance(path, str) and path:
                paths.append(path.lstrip("\\"))
            for child in (n.get("children") or []):
                if isinstance(child, dict):
                    walk(child)

        walk(node)
        return sorted(set(paths))

    area_paths = flatten_paths(areas_tree)
    iteration_paths = flatten_paths(iters_tree)

    # --- Work item type fields (project-level)
    # Endpoint: /_apis/wit/workitemtypes/{type}/fields
    wit_contract: Dict[str, Any] = {"schema_version": "1.0", "work_item_types": {}}

    for wit in wit_names:
        fields_url = _join_url(
            cfg.org_url,
            cfg.project,
            "_apis",
            "wit",
            "workitemtypes",
            wit,
            "fields",
        )
        fields_json = _get(cfg, fields_url)
        fields = fields_json.get("value", [])

        # Keep only stable, useful metadata
        wit_contract["work_item_types"][wit] = {
            "fields": [
                {
                    "name": f.get("name"),
                    "reference_name": f.get("referenceName"),
                    "type": f.get("type"),
                    "read_only": f.get("readOnly", False),
                }
                for f in fields
            ]
        }

    # --- Write YAML files
    def dump_yaml(obj: Any, filename: str) -> None:
        path = out_path / filename
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)

    dump_yaml({"projects": projects}, "projects.yaml")
    dump_yaml({"area_paths": area_paths}, "paths_area.yaml")
    dump_yaml({"iteration_paths": iteration_paths}, "paths_iteration.yaml")
    dump_yaml(wit_contract, "wit_contract.yaml")
