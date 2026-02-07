from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from adoctl.util.fs import atomic_write_text, ensure_dir
from adoctl.util.yaml_emit import render_yaml_with_header


_DOC_WIT_MAP = {
    "Blockers.md": "Blocker",
    "Critical-Business-Decisions.md": "Critical Business Decision",
    "Features.md": "Feature",
    "Iterations.md": "Iteration",
    "Key-Results.md": "Key Result",
    "Linking.md": "Linking",
    "Risks.md": "Risk",
    "User-Stories.md": "User Story",
    "Work-Items.md": "Work Items",
}


def _extract_section(markdown: str, heading: str) -> str:
    pattern = re.compile(rf"^###\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(markdown)
    if not match:
        return ""
    start = match.end()
    rest = markdown[start:]
    next_heading = re.search(r"^###\s+", rest, re.MULTILINE)
    if next_heading:
        return rest[: next_heading.start()]
    return rest


def _extract_labeled_block(markdown: str, label: str) -> str:
    markdown_heading = _extract_section(markdown, label)
    if markdown_heading:
        return markdown_heading

    label_pattern = re.compile(rf"^\*\*{re.escape(label)}\*\*\s*$", re.MULTILINE)
    match = label_pattern.search(markdown)
    if not match:
        return ""

    start = match.end()
    rest = markdown[start:]

    next_boundaries = [
        re.search(r"^###\s+", rest, re.MULTILINE),
        re.search(r"^\*\*[A-Za-z][^*]*\*\*\s*$", rest, re.MULTILINE),
    ]
    boundaries = [m.start() for m in next_boundaries if m]
    if boundaries:
        return rest[: min(boundaries)]
    return rest


def _extract_bold_field_names(section_text: str) -> List[str]:
    fields: List[str] = []
    for line in section_text.splitlines():
        if not line.startswith("-"):
            continue
        cleaned = line.rstrip()
        if not cleaned.startswith("-"):
            continue
        bold = re.search(r"\*\*([^*]+)\*\*", cleaned)
        if not bold:
            continue
        name = bold.group(1).strip()
        if name and name not in fields:
            fields.append(name)
    return fields


def _extract_work_item_type(markdown: str, fallback: str) -> str:
    match = re.search(r"Work Item Type:\s*`([^`]+)`", markdown)
    if match and match.group(1).strip():
        return match.group(1).strip()
    return fallback


def _load_existing_field_policy(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    if not isinstance(payload, dict):
        return {}
    return payload


def bootstrap_field_policy_from_docs(
    docs_dir: str = "docs",
    out_path: str = "config/policy/field_policy.yaml",
) -> Dict[str, object]:
    docs_path = Path(docs_dir)
    if not docs_path.exists() or not docs_path.is_dir():
        raise FileNotFoundError(f"Docs directory not found: {docs_dir}")

    output_path = Path(out_path)
    existing_payload = _load_existing_field_policy(output_path)
    existing_allowed = existing_payload.get("allowed_fields", {})
    existing_required = existing_payload.get("required_fields", {})
    if not isinstance(existing_allowed, dict):
        existing_allowed = {}
    if not isinstance(existing_required, dict):
        existing_required = {}

    wiki_required_metadata: Dict[str, List[str]] = {}
    wiki_optional_metadata: Dict[str, List[str]] = {}
    source_docs: List[str] = []

    for doc_name, fallback_wit in _DOC_WIT_MAP.items():
        path = docs_path / doc_name
        if not path.exists():
            continue
        source_docs.append(str(path))

        text = path.read_text(encoding="utf-8")
        wit_name = _extract_work_item_type(text, fallback=fallback_wit)

        required_text = _extract_labeled_block(text, "Required")
        optional_text = _extract_labeled_block(text, "Optional")

        required_fields = _extract_bold_field_names(required_text)
        optional_fields = _extract_bold_field_names(optional_text)

        if required_fields:
            wiki_required_metadata[wit_name] = required_fields
        if optional_fields:
            wiki_optional_metadata[wit_name] = optional_fields

    payload = dict(existing_payload)
    payload.update(
        {
        "schema_version": "1.0",
        "allowed_fields": dict(sorted(existing_allowed.items(), key=lambda item: item[0])),
        "required_fields": dict(sorted(existing_required.items(), key=lambda item: item[0])),
        "wiki_required_metadata": dict(sorted(wiki_required_metadata.items(), key=lambda item: item[0])),
        "wiki_optional_metadata": dict(sorted(wiki_optional_metadata.items(), key=lambda item: item[0])),
        "wiki_source_docs": sorted(source_docs),
        "notes": [
            "wiki_* sections are bootstrapped from docs and intended as one-time policy seed data.",
            "required_fields / allowed_fields remain the runtime canonical field policy for validation and export.",
        ],
        }
    )

    ensure_dir(output_path.parent)
    atomic_write_text(
        output_path,
        render_yaml_with_header(
            payload,
            [
                "USER-MANAGED POLICY FILE. SAFE TO EDIT.",
                "wiki_* sections are machine-bootstrapped snapshots from docs and can be re-generated.",
                "allowed_fields / required_fields remain the runtime canonical policy.",
            ],
        ),
    )

    return {
        "output_path": str(output_path),
        "source_count": len(source_docs),
        "work_item_count": len(wiki_required_metadata),
    }
