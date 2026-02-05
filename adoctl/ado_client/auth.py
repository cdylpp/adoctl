from __future__ import annotations

import base64
from typing import Dict


def basic_auth_header_from_pat(pat: str) -> Dict[str, str]:
    token = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}

