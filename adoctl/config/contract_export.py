from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Dict, Optional

from adoctl.config.contract_loader import (
    EffectiveContractConfig,
    FieldMapConfig,
    FieldMapping,
    FieldPolicyConfig,
    load_effective_contract,
    save_field_policy,
)
from adoctl.config.paths import policy_config_dir
from adoctl.util.fs import atomic_write_text, ensure_dir
from adoctl.util.yaml_emit import render_yaml_with_header


def _sorted_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sorted_nested(value[key]) for key in sorted(value.keys())}
    if isinstance(value, list):
        return [_sorted_nested(item) for item in value]
    return value


def _field_mapping_to_payload(mapping: FieldMapping) -> Dict[str, Any]:
    return {
        "canonical_key": mapping.canonical_key,
        "reference_name": mapping.reference_name,
        "applies_to": list(mapping.applies_to),
        "description": mapping.description,
    }


def _canonical_field_map(field_map: FieldMapConfig) -> Dict[str, str]:
    return {
        key: field_map.canonical_to_ado[key].reference_name
        for key in sorted(field_map.canonical_to_ado.keys())
    }


def _sync_field_policy_required_fields(config: EffectiveContractConfig, field_policy_path: Path) -> bool:
    generated_required = config.generated_required_fields_by_type()
    export_types = set(config.agent_contract_export_types())

    merged_required: Dict[str, tuple[str, ...]] = {}
    changed = False

    all_types = set(config.field_policy.required_fields.keys()) | set(generated_required.keys())
    for canonical_type in sorted(all_types):
        if canonical_type not in export_types:
            merged_required[canonical_type] = tuple(sorted(set(config.field_policy.required_fields.get(canonical_type, ()))))
            continue
        policy_required = set(config.field_policy.required_fields.get(canonical_type, ()))
        generated_required_set = set(generated_required.get(canonical_type, set()))
        merged = policy_required | generated_required_set

        if generated_required_set - policy_required:
            changed = True
        merged_required[canonical_type] = tuple(sorted(merged))

    if not changed:
        return False

    updated_policy = FieldPolicyConfig(
        allowed_fields=config.field_policy.allowed_fields,
        required_fields=merged_required,
        export_work_item_types=config.field_policy.export_work_item_types,
        description_required_sections=config.field_policy.description_required_sections,
        description_optional_sections=config.field_policy.description_optional_sections,
    )
    save_field_policy(updated_policy, path=field_policy_path)
    return True


def build_agent_contract_snapshot(config: EffectiveContractConfig) -> Dict[str, Any]:
    coverage_issues = config.validate_mapping_coverage()

    export_types = set(config.agent_contract_export_types())
    canonical_types_sorted = sorted([t for t in config.wit_map.canonical_to_ado.keys() if t in export_types])
    canonical_fields_sorted = sorted(config.field_map.canonical_to_ado.keys())

    field_mappings = [
        _field_mapping_to_payload(config.field_map.canonical_to_ado[key]) for key in canonical_fields_sorted
    ]

    ado_capabilities: Dict[str, Dict[str, Any]] = {}
    for canonical_type in canonical_types_sorted:
        ado_wit = config.resolve_ado_wit(canonical_type)
        wit_data = config.generated_wit_contract.work_item_types.get(ado_wit)
        ado_capabilities[canonical_type] = {
            "ado_work_item_type": ado_wit,
            "available_fields": sorted(list(wit_data.field_reference_names)) if wit_data else [],
            "required_fields": sorted(list(wit_data.required_field_reference_names)) if wit_data else [],
        }

    return {
        "schema_version": "1.0",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "canonical": {
            "supported_types": canonical_types_sorted,
            "field_mappings": field_mappings,
        },
        "rules": {
            "link_policy": {
                "allowed_link_types": list(config.link_policy.allowed_link_types),
                "max_depth": config.link_policy.max_depth,
                "forbid_double_nesting": list(config.link_policy.forbid_double_nesting),
            },
            "standards": {
                "required_tags": list(config.standards.required_tags),
                "work_item_standards": {
                    canonical_type: _sorted_nested(standard)
                    for canonical_type, standard in sorted(config.standards.work_item_standards.items(), key=lambda item: item[0])
                    if canonical_type in export_types
                },
            },
        },
        "mapping": {
            "wit_map": dict(sorted(config.wit_map.canonical_to_ado.items(), key=lambda item: item[0])),
            "field_map": _canonical_field_map(config.field_map),
        },
        "ado_capabilities": ado_capabilities,
        "field_policy": {
            "allowed_fields": {
                canonical_type: sorted(list(field_keys))
                for canonical_type, field_keys in sorted(config.field_policy.allowed_fields.items(), key=lambda item: item[0])
                if canonical_type in export_types
            },
            "required_fields": {
                canonical_type: sorted(list(field_keys))
                for canonical_type, field_keys in sorted(config.field_policy.required_fields.items(), key=lambda item: item[0])
                if canonical_type in export_types
            },
            "description_required_sections": {
                canonical_type: sorted(list(field_keys))
                for canonical_type, field_keys in sorted(
                    config.field_policy.description_required_sections.items(), key=lambda item: item[0]
                )
                if canonical_type in export_types
            },
            "description_optional_sections": {
                canonical_type: sorted(list(field_keys))
                for canonical_type, field_keys in sorted(
                    config.field_policy.description_optional_sections.items(), key=lambda item: item[0]
                )
                if canonical_type in export_types
            },
            "generated_required_fields": {
                canonical_type: sorted(list(field_keys))
                for canonical_type, field_keys in sorted(
                    config.generated_required_fields_by_type().items(), key=lambda item: item[0]
                )
                if canonical_type in export_types
            },
            "effective_required_fields": {
                canonical_type: sorted(list(field_keys))
                for canonical_type, field_keys in sorted(
                    config.effective_required_fields_by_type().items(), key=lambda item: item[0]
                )
                if canonical_type in export_types
            },
            "export_work_item_types": sorted(list(export_types)),
        },
        "validation": {
            "mapping_coverage_issues": coverage_issues,
            "strict_ready": len(coverage_issues) == 0,
        },
    }


def export_agent_contract(
    out_path: str = "config/generated/agent_contract.yaml",
    policy_dir: Optional[Path] = None,
    generated_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    resolved_policy_dir = policy_dir or policy_config_dir()
    field_policy_path = resolved_policy_dir / "field_policy.yaml"

    contract = load_effective_contract(policy_dir=resolved_policy_dir, generated_dir=generated_dir)
    field_policy_updated = _sync_field_policy_required_fields(contract, field_policy_path=field_policy_path)
    if field_policy_updated:
        contract = load_effective_contract(policy_dir=resolved_policy_dir, generated_dir=generated_dir)

    snapshot = build_agent_contract_snapshot(contract)
    destination = Path(out_path)
    ensure_dir(destination.parent)
    atomic_write_text(
        destination,
        render_yaml_with_header(
            snapshot,
            [
                "MACHINE-GENERATED FILE. DO NOT EDIT BY HAND.",
                "Generated by `adoctl contract export`.",
                "Edit config/policy/*.yaml (and refresh config/generated/wit_contract.yaml) to change this contract.",
            ],
        ),
    )
    return {
        "output_path": str(destination),
        "strict_ready": snapshot["validation"]["strict_ready"],
        "field_policy_updated": field_policy_updated,
    }
