from __future__ import annotations

from typing import Optional
from urllib.parse import quote, unquote, urlsplit, urlunsplit


def encode_path_segment(value: str) -> str:
    """
    Percent-encode a single URL path segment.

    - Encodes spaces, slashes, unicode, etc.
    - Avoids double-encoding if the input already contains %XX sequences.
    """
    return quote(unquote(value), safe="")


def join_url(base_url: str, *segments: Optional[str]) -> str:
    """
    Joins base_url with additional path segments, encoding each segment safely.

    Example:
        join_url("https://dev.azure.com/MyOrg", "Black Lagoon", "_apis", "teams")
        -> "https://dev.azure.com/MyOrg/Black%20Lagoon/_apis/teams"
    """
    split = urlsplit(base_url)
    base_path = split.path.rstrip("/")

    cleaned = []
    for seg in segments:
        if seg is None:
            continue
        seg = str(seg).strip("/")
        if not seg:
            continue
        cleaned.append(encode_path_segment(seg))

    path = base_path
    if cleaned:
        path = f"{base_path}/{'/'.join(cleaned)}"

    return urlunsplit((split.scheme, split.netloc, path, split.query, split.fragment))

