from __future__ import annotations

from typing import Any, Iterable

import yaml


def render_yaml_with_header(
    payload: Any,
    header_lines: Iterable[str],
) -> str:
    lines = [line.strip() for line in header_lines if line and line.strip()]
    header = "".join(f"# {line}\n" for line in lines)
    body = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    if not header:
        return body
    return f"{header}\n{body}"

