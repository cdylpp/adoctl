from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from adoctl.config.contract_loader import EffectiveContractConfig, load_effective_contract
from adoctl.config.paths import generated_config_dir, policy_config_dir
from adoctl.util.fs import atomic_write_text, ensure_dir


SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def _add_finding(
    findings: List[Dict[str, str]],
    severity: str,
    code: str,
    path: str,
    message: str,
    suggestion: str,
) -> None:
    findings.append(
        {
            "severity": severity,
            "code": code,
            "path": path,
            "message": message,
            "suggestion": suggestion,
        }
    )


def _policy_types_by_source(config: EffectiveContractConfig) -> Dict[str, Set[str]]:
    sources: Dict[str, Set[str]] = {}
    source_maps = {
        "field_policy.allowed_fields": config.field_policy.allowed_fields,
        "field_policy.required_fields": config.field_policy.required_fields,
        "field_policy.description_required_sections": config.field_policy.description_required_sections,
        "field_policy.description_optional_sections": config.field_policy.description_optional_sections,
    }
    for source_name, type_map in source_maps.items():
        for canonical_type in type_map.keys():
            sources.setdefault(canonical_type, set()).add(source_name)
    for canonical_type in config.standards.work_item_standards.keys():
        sources.setdefault(canonical_type, set()).add("standards.work_item_standards")
    return sources


def _lint_loaded_contract(config: EffectiveContractConfig) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    wit_types = set(config.wit_map.canonical_to_ado.keys())
    field_map = config.field_map.canonical_to_ado
    export_types = set(config.agent_contract_export_types())

    # Export scope validity.
    for canonical_type in config.field_policy.export_work_item_types:
        if canonical_type not in wit_types:
            _add_finding(
                findings,
                severity="error",
                code="UNKNOWN_EXPORT_TYPE",
                path="field_policy.agent_contract_export.include_work_item_types",
                message=f"Export includes unknown canonical type '{canonical_type}'.",
                suggestion="Add the type to wit_map.canonical_to_ado or remove it from export scope.",
            )

    # Validate field map references against wit_map + generated metadata.
    for field_key in sorted(field_map.keys()):
        mapping = field_map[field_key]
        for canonical_type in mapping.applies_to:
            if canonical_type not in wit_types:
                _add_finding(
                    findings,
                    severity="error",
                    code="FIELD_MAP_UNKNOWN_TYPE",
                    path=f"field_map.canonical_to_ado.{field_key}.applies_to",
                    message=f"Field '{field_key}' applies to unknown canonical type '{canonical_type}'.",
                    suggestion="Fix applies_to or add canonical type to wit_map.canonical_to_ado.",
                )
                continue
            ado_wit = config.wit_map.canonical_to_ado[canonical_type]
            wit_contract = config.generated_wit_contract.work_item_types.get(ado_wit)
            if wit_contract is None:
                _add_finding(
                    findings,
                    severity="error",
                    code="WIT_MISSING_IN_GENERATED",
                    path=f"wit_map.canonical_to_ado.{canonical_type}",
                    message=f"ADO work item type '{ado_wit}' is missing in generated wit_contract.",
                    suggestion="Re-run sync/bootstrap to refresh config/generated/wit_contract.yaml.",
                )
                continue
            if mapping.reference_name not in wit_contract.field_reference_names:
                _add_finding(
                    findings,
                    severity="error",
                    code="FIELD_REF_MISSING_IN_WIT",
                    path=f"field_map.canonical_to_ado.{field_key}.reference_name",
                    message=(
                        f"Reference '{mapping.reference_name}' for canonical field '{field_key}' is absent in "
                        f"ADO WIT '{ado_wit}'."
                    ),
                    suggestion="Correct the mapping or regenerate wit metadata from ADO.",
                )

    # Validate field_policy typed fields against field_map.
    policy_sections: Dict[str, Dict[str, tuple[str, ...]]] = {
        "allowed_fields": config.field_policy.allowed_fields,
        "required_fields": config.field_policy.required_fields,
    }
    for section_name, typed_fields in policy_sections.items():
        for canonical_type in sorted(typed_fields.keys()):
            if canonical_type not in wit_types:
                _add_finding(
                    findings,
                    severity="error",
                    code="POLICY_UNKNOWN_TYPE",
                    path=f"field_policy.{section_name}.{canonical_type}",
                    message=f"field_policy {section_name} references unknown canonical type '{canonical_type}'.",
                    suggestion="Rename to a canonical type from wit_map or add the type to wit_map.",
                )
                continue
            for field_key in typed_fields[canonical_type]:
                mapping = field_map.get(field_key)
                if mapping is None:
                    _add_finding(
                        findings,
                        severity="error",
                        code="POLICY_UNKNOWN_FIELD_KEY",
                        path=f"field_policy.{section_name}.{canonical_type}",
                        message=f"field_policy {section_name} references unknown field key '{field_key}'.",
                        suggestion="Add field key to field_map.canonical_to_ado or remove it from field_policy.",
                    )
                    continue
                if mapping.applies_to and canonical_type not in mapping.applies_to:
                    _add_finding(
                        findings,
                        severity="error",
                        code="POLICY_FIELD_NOT_APPLICABLE",
                        path=f"field_policy.{section_name}.{canonical_type}",
                        message=(
                            f"field_policy {section_name} includes '{field_key}' for '{canonical_type}', "
                            "but field_map.applies_to does not include that type."
                        ),
                        suggestion="Align field_policy type usage with field_map.applies_to.",
                    )

    # Warn when required_fields contains keys outside allowed_fields (if allowed_fields is explicit).
    for canonical_type, required_field_keys in sorted(config.field_policy.required_fields.items(), key=lambda item: item[0]):
        allowed_field_keys = set(config.field_policy.allowed_fields.get(canonical_type, ()))
        if not allowed_field_keys:
            continue
        for field_key in required_field_keys:
            if field_key not in allowed_field_keys:
                _add_finding(
                    findings,
                    severity="warning",
                    code="REQUIRED_NOT_IN_ALLOWED",
                    path=f"field_policy.required_fields.{canonical_type}",
                    message=f"Required field '{field_key}' is missing from allowed_fields for '{canonical_type}'.",
                    suggestion="Add the field to allowed_fields or remove it from required_fields.",
                )

    # Validate section-type mappings for description section blocks.
    for section_name, typed_sections in {
        "description_required_sections": config.field_policy.description_required_sections,
        "description_optional_sections": config.field_policy.description_optional_sections,
    }.items():
        for canonical_type in sorted(typed_sections.keys()):
            if canonical_type not in wit_types:
                _add_finding(
                    findings,
                    severity="error",
                    code="POLICY_UNKNOWN_TYPE",
                    path=f"field_policy.{section_name}.{canonical_type}",
                    message=f"field_policy {section_name} references unknown canonical type '{canonical_type}'.",
                    suggestion="Rename to a canonical type from wit_map or add the type to wit_map.",
                )

    # Standards alignment checks for mapped fields.
    for canonical_type, standards in sorted(config.standards.work_item_standards.items(), key=lambda item: item[0]):
        if canonical_type not in wit_types:
            _add_finding(
                findings,
                severity="error",
                code="STANDARDS_UNKNOWN_TYPE",
                path=f"standards.work_item_standards.{canonical_type}",
                message=f"standards references unknown canonical type '{canonical_type}'.",
                suggestion="Rename to a canonical type from wit_map or add the type to wit_map.",
            )
            continue

        required_fields = set(config.field_policy.required_fields.get(canonical_type, ()))
        policy_fields = required_fields | set(config.field_policy.allowed_fields.get(canonical_type, ()))
        for standards_key, standards_value in sorted(standards.items(), key=lambda item: item[0]):
            mapping = field_map.get(standards_key)
            if standards_key in policy_fields and mapping is None:
                _add_finding(
                    findings,
                    severity="error",
                    code="STANDARDS_FIELD_UNMAPPED",
                    path=f"standards.work_item_standards.{canonical_type}.{standards_key}",
                    message=f"Standards field '{standards_key}' is used in policy but missing from field_map.",
                    suggestion="Add a canonical field mapping or remove the field from standards/policy.",
                )
                continue
            if mapping is None:
                continue
            if mapping.applies_to and canonical_type not in mapping.applies_to:
                _add_finding(
                    findings,
                    severity="error",
                    code="STANDARDS_FIELD_NOT_APPLICABLE",
                    path=f"standards.work_item_standards.{canonical_type}.{standards_key}",
                    message=(
                        f"Standards field '{standards_key}' is mapped but not applicable to canonical type "
                        f"'{canonical_type}' per field_map."
                    ),
                    suggestion="Align standards type usage with field_map.applies_to.",
                )
            if isinstance(standards_value, dict) and standards_value.get("required") is True:
                if standards_key not in required_fields:
                    _add_finding(
                        findings,
                        severity="error",
                        code="STANDARDS_REQUIRED_NOT_IN_POLICY",
                        path=f"standards.work_item_standards.{canonical_type}.{standards_key}.required",
                        message=(
                            f"Standards marks '{standards_key}' as required for '{canonical_type}', "
                            "but field_policy.required_fields does not."
                        ),
                        suggestion="Add the field to field_policy.required_fields or mark required=false in standards.",
                    )

    # Informational note for valid policy definitions excluded from export.
    for canonical_type, sources in sorted(_policy_types_by_source(config).items(), key=lambda item: item[0]):
        if canonical_type not in wit_types:
            continue
        if canonical_type in export_types:
            continue
        source_list = sorted(list(sources))
        _add_finding(
            findings,
            severity="info",
            code="TYPE_EXCLUDED_FROM_EXPORT",
            path=f"field_policy.agent_contract_export.include_work_item_types",
            message=(
                f"Canonical type '{canonical_type}' has policy/standards entries in {source_list} "
                "but is excluded from agent contract export."
            ),
            suggestion="Add this type to include_work_item_types if agents should receive this contract surface.",
        )

    findings.sort(key=lambda item: (SEVERITY_ORDER[item["severity"]], item["path"], item["code"], item["message"]))
    return findings


def _build_report(
    findings: List[Dict[str, str]],
    policy_dir: Path,
    generated_dir: Path,
) -> Dict[str, Any]:
    error_count = sum(1 for finding in findings if finding["severity"] == "error")
    warning_count = sum(1 for finding in findings if finding["severity"] == "warning")
    info_count = sum(1 for finding in findings if finding["severity"] == "info")
    return {
        "schema_version": "1.0",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": {
            "policy_dir": str(policy_dir),
            "generated_dir": str(generated_dir),
        },
        "summary": {
            "errors": error_count,
            "warnings": warning_count,
            "info": info_count,
        },
        "findings": findings,
        "strict_ready": error_count == 0,
    }


def lint_contract(
    policy_dir: Optional[Path] = None,
    generated_dir: Optional[Path] = None,
    out_path: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_policy_dir = policy_dir or policy_config_dir()
    resolved_generated_dir = generated_dir or generated_config_dir()

    try:
        contract = load_effective_contract(policy_dir=resolved_policy_dir, generated_dir=resolved_generated_dir)
        findings = _lint_loaded_contract(contract)
    except Exception as exc:
        findings = [
            {
                "severity": "error",
                "code": "CONFIG_LOAD_ERROR",
                "path": "config",
                "message": str(exc),
                "suggestion": "Fix config structure/content and rerun contract lint.",
            }
        ]

    report = _build_report(findings=findings, policy_dir=resolved_policy_dir, generated_dir=resolved_generated_dir)
    if out_path:
        destination = Path(out_path)
        ensure_dir(destination.parent)
        atomic_write_text(destination, yaml.safe_dump(report, sort_keys=False, allow_unicode=True))
        report["output_path"] = str(destination)
    return report

