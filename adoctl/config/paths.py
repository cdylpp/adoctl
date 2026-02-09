from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path.cwd()


def generated_config_dir() -> Path:
    return repo_root() / "config" / "generated"


def policy_config_dir() -> Path:
    return repo_root() / "config" / "policy"


def outbox_dir() -> Path:
    return repo_root() / "outbox"


def local_config_dir() -> Path:
    return repo_root() / "config" / "local"


def cli_context_path() -> Path:
    return local_config_dir() / "context.yaml"


def local_project_defaults_path() -> Path:
    return local_config_dir() / "project_defaults.yaml"
