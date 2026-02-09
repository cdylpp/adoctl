from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from jsonschema import Draft202012Validator
import yaml

from adoctl.config.contract_loader import EffectiveContractConfig, load_effective_contract
from adoctl.config.paths import outbox_dir
from adoctl.util.fs import atomic_write_text, ensure_dir
from adoctl.util.yaml_emit import render_yaml_with_header


TOP_LEVEL_CANONICAL_KEYS = {"title", "description", "acceptance_criteria"}
DEFAULT_SCHEMA_PATH = Path("schema") / "bundle.schema.json"


def _now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _normalize_path(value: str) -> str:
    normalized = value.strip().replace("/", "\\")
    normalized = normalized.lstrip("\\")
    normalized = re.sub(r"\\+", r"\\", normalized)
    return normalized


def _normalize_string_set(values: Sequence[str]) -> Set[str]:
    return {_normalize_path(v) for v in values if isinstance(v, str) and v.strip()}


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _as_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def _add_issue(
    issues: List[Dict[str, str]],
    stage: str,
    code: str,
    path: str,
    message: str,
    suggestion: str,
) -> None:
    issues.append(
        {
            "stage": stage,
            "code": code,
            "path": path,
            "message": message,
            "suggestion": suggestion,
        }
    )


def _json_pointer(path_parts: Sequence[Any]) -> str:
    if not path_parts:
        return "$"
    cleaned: List[str] = []
    for part in path_parts:
        cleaned.append(str(part))
    return "$." + ".".join(cleaned)


def _load_json_schema(schema_path: Path) -> Dict[str, Any]:
    if not schema_path.exists():
        raise FileNotFoundError(f"Bundle schema file not found: {schema_path}")
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Bundle schema must decode to an object: {schema_path}")
    return payload


def _load_path_list(path_file: Path, key: str) -> Tuple[Optional[Set[str]], Optional[str]]:
    if not path_file.exists():
        return None, f"Missing generated metadata file: {path_file}"
    with path_file.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    if not isinstance(payload, dict):
        return None, f"Invalid YAML object in generated metadata file: {path_file}"
    values = payload.get(key)
    if not isinstance(values, list):
        return None, f"Expected key '{key}' to be a list in generated metadata file: {path_file}"
    return _normalize_string_set(values), None


def _validate_schema_stage(bundle_payload: Dict[str, Any], schema_payload: Dict[str, Any]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    validator = Draft202012Validator(schema_payload)
    for error in sorted(validator.iter_errors(bundle_payload), key=lambda err: list(err.path)):
        _add_issue(
            issues=issues,
            stage="schema",
            code="SCHEMA_VIOLATION",
            path=_json_pointer(list(error.absolute_path)),
            message=error.message,
            suggestion="Fix bundle JSON to satisfy schema/bundle.schema.json.",
        )
    return issues


def _collect_local_id_map(work_items: Sequence[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], Set[str], List[str]]:
    by_local_id: Dict[str, Dict[str, Any]] = {}
    duplicates: Set[str] = set()
    ordered: List[str] = []
    for item in work_items:
        local_id = _as_string(item.get("local_id"))
        if not local_id:
            continue
        ordered.append(local_id)
        if local_id in by_local_id:
            duplicates.add(local_id)
            continue
        by_local_id[local_id] = item
    return by_local_id, duplicates, ordered


def _required_key_satisfied(
    field_key: str,
    work_item: Dict[str, Any],
    context: Dict[str, Any],
) -> bool:
    if field_key in TOP_LEVEL_CANONICAL_KEYS:
        return _is_non_empty(work_item.get(field_key))

    fields = work_item.get("fields")
    if isinstance(fields, dict) and _is_non_empty(fields.get(field_key)):
        return True

    if field_key == "area_path":
        return _is_non_empty(context.get("default_area_path"))
    if field_key == "iteration_path":
        return _is_non_empty(context.get("default_iteration_path"))
    return False


def _policy_stage(
    bundle_payload: Dict[str, Any],
    config: EffectiveContractConfig,
) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    work_items_raw = bundle_payload.get("work_items", [])
    context = bundle_payload.get("context", {})
    if not isinstance(work_items_raw, list):
        return issues
    work_items = [item for item in work_items_raw if isinstance(item, dict)]

    by_local_id, duplicates, _ = _collect_local_id_map(work_items)
    for duplicate_id in sorted(duplicates):
        _add_issue(
            issues=issues,
            stage="policy",
            code="DUPLICATE_LOCAL_ID",
            path="$.work_items.local_id",
            message=f"Duplicate local_id '{duplicate_id}' found in bundle.",
            suggestion="Ensure each work item local_id is unique within the bundle.",
        )

    effective_required = config.effective_required_fields_by_type()
    forbid_same_type = set(config.link_policy.forbid_double_nesting)
    required_tags = set(config.standards.required_tags)
    context_tags = set()
    if isinstance(context, dict):
        context_tags_raw = context.get("tags")
        if isinstance(context_tags_raw, list):
            context_tags = {str(tag).strip() for tag in context_tags_raw if isinstance(tag, str) and tag.strip()}

    for index, item in enumerate(work_items):
        item_path = f"$.work_items.{index}"
        local_id = _as_string(item.get("local_id")) or f"<index:{index}>"
        canonical_type = _as_string(item.get("type"))
        relations = item.get("relations")
        parent_local_id: Optional[str] = None
        if isinstance(relations, dict):
            parent_local_id = _as_string(relations.get("parent_local_id"))

        if required_tags:
            item_tags = set()
            tags_raw = item.get("tags")
            if isinstance(tags_raw, list):
                item_tags = {str(tag).strip() for tag in tags_raw if isinstance(tag, str) and tag.strip()}
            missing_tags = sorted(required_tags - (item_tags | context_tags))
            if missing_tags:
                _add_issue(
                    issues=issues,
                    stage="policy",
                    code="MISSING_REQUIRED_TAGS",
                    path=f"{item_path}.tags",
                    message=f"Work item '{local_id}' is missing required tags: {missing_tags}.",
                    suggestion="Add required tags in bundle context.tags or item tags (if schema supports tags).",
                )

        if canonical_type:
            required_fields = effective_required.get(canonical_type, set())
            for field_key in sorted(required_fields):
                if not _required_key_satisfied(field_key, item, context if isinstance(context, dict) else {}):
                    _add_issue(
                        issues=issues,
                        stage="policy",
                        code="MISSING_REQUIRED_FIELD",
                        path=f"{item_path}.fields.{field_key}",
                        message=(
                            f"Work item '{local_id}' ({canonical_type}) is missing required canonical field "
                            f"'{field_key}'."
                        ),
                        suggestion="Populate required field in work_item.fields or applicable top-level canonical key.",
                    )

            fields = item.get("fields", {})
            if isinstance(fields, dict):
                allowed_fields = set(config.field_policy.allowed_fields.get(canonical_type, ()))
                if allowed_fields:
                    for field_key in sorted(fields.keys()):
                        if field_key not in allowed_fields:
                            _add_issue(
                                issues=issues,
                                stage="policy",
                                code="FIELD_NOT_ALLOWED_BY_POLICY",
                                path=f"{item_path}.fields.{field_key}",
                                message=(
                                    f"Work item '{local_id}' ({canonical_type}) uses canonical field '{field_key}' "
                                    "which is not allowed by field_policy."
                                ),
                                suggestion="Remove field or add it to field_policy.allowed_fields for this type.",
                            )

        if not parent_local_id:
            continue
        parent_item = by_local_id.get(parent_local_id)
        if parent_item is not None:
            parent_type = _as_string(parent_item.get("type"))
            if canonical_type and parent_type and canonical_type == parent_type and canonical_type in forbid_same_type:
                _add_issue(
                    issues=issues,
                    stage="policy",
                    code="DOUBLE_NESTING_FORBIDDEN",
                    path=f"{item_path}.relations.parent_local_id",
                    message=(
                        f"Work item '{local_id}' has parent '{parent_local_id}' with the same type "
                        f"'{canonical_type}', which is forbidden by link policy."
                    ),
                    suggestion="Re-parent item under an allowed parent type.",
                )

        # Depth/cycle checks over local links only.
        depth = 1
        cursor_parent = parent_local_id
        seen: Set[str] = {local_id}
        while cursor_parent and cursor_parent in by_local_id:
            if cursor_parent in seen:
                _add_issue(
                    issues=issues,
                    stage="policy",
                    code="HIERARCHY_CYCLE",
                    path=f"{item_path}.relations.parent_local_id",
                    message=f"Cycle detected in local parent chain at '{cursor_parent}'.",
                    suggestion="Break local parent cycle; hierarchy must be acyclic.",
                )
                break
            seen.add(cursor_parent)
            depth += 1
            if depth > config.link_policy.max_depth:
                _add_issue(
                    issues=issues,
                    stage="policy",
                    code="MAX_DEPTH_EXCEEDED",
                    path=f"{item_path}.relations.parent_local_id",
                    message=(
                        f"Local hierarchy depth for '{local_id}' exceeds max_depth={config.link_policy.max_depth}."
                    ),
                    suggestion="Flatten decomposition to satisfy max_depth.",
                )
                break
            parent_rel = by_local_id[cursor_parent].get("relations")
            if isinstance(parent_rel, dict):
                cursor_parent = _as_string(parent_rel.get("parent_local_id"))
            else:
                cursor_parent = None

    return issues


def _metadata_stage(
    bundle_payload: Dict[str, Any],
    config: EffectiveContractConfig,
    area_paths: Optional[Set[str]],
    iteration_paths: Optional[Set[str]],
    area_paths_error: Optional[str],
    iteration_paths_error: Optional[str],
) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    work_items_raw = bundle_payload.get("work_items", [])
    context = bundle_payload.get("context", {})
    if not isinstance(work_items_raw, list):
        return issues
    work_items = [item for item in work_items_raw if isinstance(item, dict)]

    if area_paths_error:
        _add_issue(
            issues=issues,
            stage="metadata",
            code="AREA_PATHS_METADATA_MISSING",
            path="config/generated/paths_area.yaml",
            message=area_paths_error,
            suggestion="Run `adoctl sync --paths` to generate area paths metadata.",
        )
    if iteration_paths_error:
        _add_issue(
            issues=issues,
            stage="metadata",
            code="ITERATION_PATHS_METADATA_MISSING",
            path="config/generated/paths_iteration.yaml",
            message=iteration_paths_error,
            suggestion="Run `adoctl sync --paths` to generate iteration paths metadata.",
        )

    for index, item in enumerate(work_items):
        item_path = f"$.work_items.{index}"
        local_id = _as_string(item.get("local_id")) or f"<index:{index}>"
        canonical_type = _as_string(item.get("type"))
        if not canonical_type:
            continue

        ado_wit = config.wit_map.canonical_to_ado.get(canonical_type)
        if not ado_wit:
            _add_issue(
                issues=issues,
                stage="metadata",
                code="UNKNOWN_CANONICAL_TYPE",
                path=f"{item_path}.type",
                message=f"Canonical type '{canonical_type}' has no wit_map entry.",
                suggestion="Add canonical type mapping in config/policy/wit_map.yaml.",
            )
            continue

        wit_contract = config.generated_wit_contract.work_item_types.get(ado_wit)
        if wit_contract is None:
            _add_issue(
                issues=issues,
                stage="metadata",
                code="WIT_NOT_IN_GENERATED_METADATA",
                path=f"{item_path}.type",
                message=f"ADO work item type '{ado_wit}' is missing in config/generated/wit_contract.yaml.",
                suggestion="Regenerate WIT metadata with `adoctl sync --wit-only` or bootstrap.",
            )
            continue

        fields = item.get("fields", {})
        if isinstance(fields, dict):
            for field_key in sorted(fields.keys()):
                mapping = config.field_map.canonical_to_ado.get(field_key)
                if mapping is None:
                    _add_issue(
                        issues=issues,
                        stage="metadata",
                        code="UNKNOWN_CANONICAL_FIELD_KEY",
                        path=f"{item_path}.fields.{field_key}",
                        message=f"Canonical field key '{field_key}' has no field_map entry.",
                        suggestion="Add field to config/policy/field_map.yaml or remove it from bundle fields.",
                    )
                    continue
                if mapping.applies_to and canonical_type not in mapping.applies_to:
                    _add_issue(
                        issues=issues,
                        stage="metadata",
                        code="FIELD_NOT_APPLICABLE_TO_TYPE",
                        path=f"{item_path}.fields.{field_key}",
                        message=(
                            f"Canonical field '{field_key}' is not applicable to type '{canonical_type}' per field_map."
                        ),
                        suggestion="Adjust field_map applies_to or remove field from bundle fields.",
                    )
                    continue
                if mapping.reference_name not in wit_contract.field_reference_names:
                    _add_issue(
                        issues=issues,
                        stage="metadata",
                        code="ADO_FIELD_UNAVAILABLE_FOR_WIT",
                        path=f"{item_path}.fields.{field_key}",
                        message=(
                            f"ADO field '{mapping.reference_name}' (for '{field_key}') is not available on WIT '{ado_wit}'."
                        ),
                        suggestion="Update mapping or remove field for this WIT.",
                    )

        resolved_area: Optional[str] = None
        resolved_iteration: Optional[str] = None
        if isinstance(fields, dict):
            resolved_area = _as_string(fields.get("area_path"))
            resolved_iteration = _as_string(fields.get("iteration_path"))
        if not resolved_area and isinstance(context, dict):
            resolved_area = _as_string(context.get("default_area_path"))
        if not resolved_iteration and isinstance(context, dict):
            resolved_iteration = _as_string(context.get("default_iteration_path"))

        if not resolved_area:
            _add_issue(
                issues=issues,
                stage="metadata",
                code="UNRESOLVED_AREA_PATH",
                path=f"{item_path}.fields.area_path",
                message=(
                    f"Work item '{local_id}' has no area_path and no context.default_area_path fallback."
                ),
                suggestion="Set work_item.fields.area_path or context.default_area_path.",
            )
        elif area_paths is not None and _normalize_path(resolved_area) not in area_paths:
            _add_issue(
                issues=issues,
                stage="metadata",
                code="UNKNOWN_AREA_PATH",
                path=f"{item_path}.fields.area_path",
                message=f"Resolved area path '{resolved_area}' is not present in generated area paths.",
                suggestion="Use a known path from config/generated/paths_area.yaml.",
            )

        if not resolved_iteration:
            _add_issue(
                issues=issues,
                stage="metadata",
                code="UNRESOLVED_ITERATION_PATH",
                path=f"{item_path}.fields.iteration_path",
                message=(
                    f"Work item '{local_id}' has no iteration_path and no context.default_iteration_path fallback."
                ),
                suggestion="Set work_item.fields.iteration_path or context.default_iteration_path.",
            )
        elif iteration_paths is not None and _normalize_path(resolved_iteration) not in iteration_paths:
            _add_issue(
                issues=issues,
                stage="metadata",
                code="UNKNOWN_ITERATION_PATH",
                path=f"{item_path}.fields.iteration_path",
                message=f"Resolved iteration path '{resolved_iteration}' is not present in generated iteration paths.",
                suggestion="Use a known path from config/generated/paths_iteration.yaml.",
            )

    return issues


def _build_report(
    bundle_path: Path,
    bundle_payload: Optional[Dict[str, Any]],
    schema_issues: List[Dict[str, str]],
    policy_issues: List[Dict[str, str]],
    metadata_issues: List[Dict[str, str]],
) -> Dict[str, Any]:
    issues = schema_issues + policy_issues + metadata_issues
    report = {
        "schema_version": "1.0",
        "validated_at_utc": _now_utc(),
        "bundle": {
            "source_path": str(bundle_path),
            "bundle_id": bundle_payload.get("bundle_id") if isinstance(bundle_payload, dict) else None,
        },
        "stages": {
            "schema": {
                "status": "passed" if not schema_issues else "failed",
                "issue_count": len(schema_issues),
            },
            "policy": {
                "status": "skipped" if schema_issues else ("passed" if not policy_issues else "failed"),
                "issue_count": len(policy_issues),
            },
            "metadata": {
                "status": "skipped"
                if (schema_issues or policy_issues)
                else ("passed" if not metadata_issues else "failed"),
                "issue_count": len(metadata_issues),
            },
        },
        "summary": {
            "error_count": len(issues),
            "result": "passed" if not issues else "failed",
        },
        "issues": issues,
    }
    return report


def _validate_single_bundle(
    bundle_path: Path,
    config: EffectiveContractConfig,
    schema_payload: Dict[str, Any],
    area_paths: Optional[Set[str]],
    iteration_paths: Optional[Set[str]],
    area_paths_error: Optional[str],
    iteration_paths_error: Optional[str],
) -> Dict[str, Any]:
    schema_issues: List[Dict[str, str]] = []
    policy_issues: List[Dict[str, str]] = []
    metadata_issues: List[Dict[str, str]] = []
    bundle_payload: Optional[Dict[str, Any]] = None

    try:
        raw_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        if not isinstance(raw_payload, dict):
            raise ValueError("Bundle JSON must decode to an object.")
        bundle_payload = raw_payload
    except Exception as exc:  # noqa: BLE001 - structured report required for all failures
        _add_issue(
            issues=schema_issues,
            stage="schema",
            code="BUNDLE_JSON_DECODE_ERROR",
            path="$",
            message=f"Failed to parse bundle JSON: {exc}",
            suggestion="Provide a valid JSON object file.",
        )
        return _build_report(bundle_path, {}, schema_issues, policy_issues, metadata_issues)

    schema_issues = _validate_schema_stage(bundle_payload=bundle_payload, schema_payload=schema_payload)
    if not schema_issues:
        policy_issues = _policy_stage(bundle_payload=bundle_payload, config=config)
    if not schema_issues and not policy_issues:
        metadata_issues = _metadata_stage(
            bundle_payload=bundle_payload,
            config=config,
            area_paths=area_paths,
            iteration_paths=iteration_paths,
            area_paths_error=area_paths_error,
            iteration_paths_error=iteration_paths_error,
        )
    return _build_report(bundle_path, bundle_payload, schema_issues, policy_issues, metadata_issues)


def _unique_file_path(directory: Path, filename: str) -> Path:
    ensure_dir(directory)
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        numbered = directory / f"{stem}.{index}{suffix}"
        if not numbered.exists():
            return numbered
        index += 1


def _is_under_directory(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _write_failure_report(report_payload: Dict[str, Any], report_path: Path) -> None:
    atomic_write_text(
        report_path,
        render_yaml_with_header(
            report_payload,
            [
                "MACHINE-GENERATED FILE. DO NOT EDIT BY HAND.",
                "Generated by `adoctl outbox validate`.",
                "Fix reported issues and re-run validation.",
            ],
        ),
    )


def validate_outbox(
    bundle: Optional[str],
    validate_all: bool,
    policy_dir: Optional[Path] = None,
    generated_dir: Optional[Path] = None,
    schema_path: Optional[Path] = None,
    outbox_root: Optional[Path] = None,
) -> Dict[str, Any]:
    if validate_all and bundle:
        raise ValueError("Pass either a bundle path or --all, not both.")
    if not validate_all and not bundle:
        raise ValueError("Provide a bundle path or pass --all.")

    resolved_outbox = outbox_root or outbox_dir()
    ready_dir = resolved_outbox / "ready"
    validated_dir = resolved_outbox / "validated"
    failed_dir = resolved_outbox / "failed"

    ensure_dir(ready_dir)
    ensure_dir(validated_dir)
    ensure_dir(failed_dir)

    if validate_all:
        bundle_paths = sorted([path for path in ready_dir.glob("*.json") if path.is_file()], key=lambda p: p.name)
    else:
        bundle_path = Path(bundle).resolve() if bundle else None
        if bundle_path is None or not bundle_path.exists() or not bundle_path.is_file():
            raise FileNotFoundError(f"Bundle file not found: {bundle}")
        bundle_paths = [bundle_path]

    schema_payload = _load_json_schema(schema_path or DEFAULT_SCHEMA_PATH)
    contract = load_effective_contract(policy_dir=policy_dir, generated_dir=generated_dir)

    generated_root = generated_dir if generated_dir is not None else Path("config") / "generated"
    area_paths, area_paths_error = _load_path_list(Path(generated_root) / "paths_area.yaml", "area_paths")
    iteration_paths, iteration_paths_error = _load_path_list(
        Path(generated_root) / "paths_iteration.yaml", "iteration_paths"
    )

    results: List[Dict[str, Any]] = []
    passed_count = 0
    failed_count = 0

    for bundle_path in bundle_paths:
        report = _validate_single_bundle(
            bundle_path=bundle_path,
            config=contract,
            schema_payload=schema_payload,
            area_paths=area_paths,
            iteration_paths=iteration_paths,
            area_paths_error=area_paths_error,
            iteration_paths_error=iteration_paths_error,
        )
        passed = report["summary"]["result"] == "passed"
        managed_by_outbox = _is_under_directory(bundle_path, ready_dir)

        moved_bundle_path: Optional[Path] = None
        report_path: Optional[Path] = None
        if passed:
            passed_count += 1
            if managed_by_outbox:
                destination = _unique_file_path(validated_dir, bundle_path.name)
                bundle_path.replace(destination)
                moved_bundle_path = destination
        else:
            failed_count += 1
            if managed_by_outbox:
                destination = _unique_file_path(failed_dir, bundle_path.name)
                bundle_path.replace(destination)
                moved_bundle_path = destination

            report_file_name = f"{bundle_path.stem}.report.yaml"
            report_path = _unique_file_path(failed_dir, report_file_name)
            _write_failure_report(report_payload=report, report_path=report_path)

        results.append(
            {
                "bundle_path": str(bundle_path),
                "result": report["summary"]["result"],
                "managed_by_outbox": managed_by_outbox,
                "moved_bundle_path": str(moved_bundle_path) if moved_bundle_path else None,
                "report_path": str(report_path) if report_path else None,
                "report": report,
            }
        )

    return {
        "validated_count": len(bundle_paths),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "results": results,
        "strict_ready": failed_count == 0,
    }
