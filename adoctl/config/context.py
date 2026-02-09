from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from adoctl.config.paths import cli_context_path, local_project_defaults_path
from adoctl.util.fs import atomic_write_text, ensure_dir
from adoctl.util.yaml_emit import render_yaml_with_header


@dataclass(frozen=True)
class CLIContext:
    org_url: Optional[str] = None
    project: Optional[str] = None
    team: Optional[str] = None
    current_iteration: Optional[str] = None
    owner_display_name: Optional[str] = None


@dataclass(frozen=True)
class LocalProjectDefaults:
    project: Optional[str] = None
    project_id: Optional[str] = None


def _normalize_optional_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def load_local_project_defaults(path: Optional[Path] = None) -> LocalProjectDefaults:
    defaults_path = path or local_project_defaults_path()
    if not defaults_path.exists():
        return LocalProjectDefaults()

    with defaults_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        return LocalProjectDefaults()

    return LocalProjectDefaults(
        project=_normalize_optional_string(data.get("project")),
        project_id=_normalize_optional_string(data.get("project_id")),
    )


def load_cli_context(path: Optional[Path] = None) -> CLIContext:
    context_path = path or cli_context_path()
    defaults = load_local_project_defaults(path=context_path.parent / "project_defaults.yaml")
    if not context_path.exists():
        return CLIContext(project=defaults.project)

    with context_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        return CLIContext(project=defaults.project)

    return CLIContext(
        org_url=_normalize_optional_string(data.get("org_url")),
        project=_normalize_optional_string(data.get("project")) or defaults.project,
        team=_normalize_optional_string(data.get("team")),
        current_iteration=_normalize_optional_string(data.get("current_iteration")),
        owner_display_name=_normalize_optional_string(data.get("owner_display_name")),
    )


def save_cli_context(context: CLIContext, path: Optional[Path] = None) -> None:
    context_path = path or cli_context_path()
    ensure_dir(context_path.parent)
    payload: Dict[str, Any] = {
        "schema_version": "1.0",
        "org_url": context.org_url,
        "project": context.project,
        "team": context.team,
        "current_iteration": context.current_iteration,
        "owner_display_name": context.owner_display_name,
    }
    atomic_write_text(
        context_path,
        render_yaml_with_header(
            payload,
            [
                "LOCAL CLI CONTEXT. SAFE TO EDIT.",
                "This file stores operator defaults for convenience and may be overwritten by `adoctl context set` or `adoctl home`.",
            ],
        ),
    )
