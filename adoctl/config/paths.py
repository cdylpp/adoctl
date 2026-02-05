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

