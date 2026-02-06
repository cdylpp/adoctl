from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ADOConfig:
    org_url: str
    pat: str
    project: Optional[str] = None
    api_version: str = "6.0"
