from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from adoctl.config.paths import generated_config_dir, policy_config_dir
from adoctl.util.fs import atomic_write_text, ensure_dir
from adoctl.util.yaml_emit import render_yaml_with_header


@dataclass(frozen=True)
class WitMapConfig:
    canonical_to_ado: Dict[str, str]


@dataclass(frozen=True)
class FieldMapping:
    canonical_key: str
    reference_name: str
    applies_to: Tuple[str, ...]
    description: Optional[str] = None


@dataclass(frozen=True)
class FieldMapConfig:
    canonical_to_ado: Dict[str, FieldMapping]


@dataclass(frozen=True)
class LinkPolicyConfig:
    allowed_link_types: Tuple[str, ...]
    max_depth: int
    forbid_double_nesting: Tuple[str, ...]


@dataclass(frozen=True)
class StandardsPolicyConfig:
    required_tags: Tuple[str, ...]
    work_item_standards: Dict[str, Dict[str, Any]]


@dataclass(frozen=True)
class FieldPolicyConfig:
    allowed_fields: Dict[str, Tuple[str, ...]]
    required_fields: Dict[str, Tuple[str, ...]]
    export_work_item_types: Tuple[str, ...]
    description_required_sections: Dict[str, Tuple[str, ...]]
    description_optional_sections: Dict[str, Tuple[str, ...]]
    owner_identity_format: str = "display_name"


@dataclass(frozen=True)
class GeneratedWitType:
    field_reference_names: Set[str]
    required_field_reference_names: Set[str]


@dataclass(frozen=True)
class GeneratedWitContract:
    work_item_types: Dict[str, GeneratedWitType]


@dataclass(frozen=True)
class EffectiveContractConfig:
    wit_map: WitMapConfig
    field_map: FieldMapConfig
    field_policy: FieldPolicyConfig
    link_policy: LinkPolicyConfig
    standards: StandardsPolicyConfig
    generated_wit_contract: GeneratedWitContract

    def resolve_ado_wit(self, canonical_type: str) -> str:
        try:
            return self.wit_map.canonical_to_ado[canonical_type]
        except KeyError as exc:
            raise KeyError(f"Unknown canonical type '{canonical_type}' in wit map.") from exc

    def resolve_ado_field(self, canonical_field_key: str, canonical_type: Optional[str] = None) -> str:
        mapping = self.field_map.canonical_to_ado.get(canonical_field_key)
        if mapping is None:
            raise KeyError(f"Unknown canonical field key '{canonical_field_key}' in field map.")
        if canonical_type and mapping.applies_to and canonical_type not in mapping.applies_to:
            raise KeyError(
                f"Canonical field key '{canonical_field_key}' is not allowed for canonical type '{canonical_type}'."
            )
        return mapping.reference_name

    def agent_contract_export_types(self) -> Tuple[str, ...]:
        if self.field_policy.export_work_item_types:
            return self.field_policy.export_work_item_types
        return tuple(sorted(self.wit_map.canonical_to_ado.keys()))

    def validate_mapping_coverage(self) -> List[str]:
        issues: List[str] = []
        export_types = set(self.agent_contract_export_types())

        for export_type in export_types:
            if export_type not in self.wit_map.canonical_to_ado:
                issues.append(
                    f"field_policy agent_contract_export includes unknown canonical type '{export_type}'."
                )

        for canonical_type, ado_wit in self.wit_map.canonical_to_ado.items():
            if ado_wit not in self.generated_wit_contract.work_item_types:
                issues.append(
                    f"wit_map missing in generated metadata: canonical '{canonical_type}' -> ADO '{ado_wit}'."
                )

        for field_key, mapping in self.field_map.canonical_to_ado.items():
            for canonical_type in mapping.applies_to:
                ado_wit = self.wit_map.canonical_to_ado.get(canonical_type)
                if not ado_wit:
                    issues.append(
                        f"field_map references canonical type '{canonical_type}' for field '{field_key}', "
                        "but that type is absent in wit_map."
                    )
                    continue
                wit_contract = self.generated_wit_contract.work_item_types.get(ado_wit)
                if wit_contract is None:
                    issues.append(
                        f"field_map references ADO WIT '{ado_wit}' for field '{field_key}', but it is absent in generated metadata."
                    )
                    continue
                if mapping.reference_name not in wit_contract.field_reference_names:
                    issues.append(
                        f"field_map reference '{mapping.reference_name}' for canonical field '{field_key}' "
                        f"is absent in generated metadata for ADO WIT '{ado_wit}'."
                    )

        policy_type_rules = {
            "required_fields": self.field_policy.required_fields,
            "allowed_fields": self.field_policy.allowed_fields,
        }
        for rule_name, type_to_fields in policy_type_rules.items():
            for canonical_type, field_keys in type_to_fields.items():
                if canonical_type not in export_types:
                    continue
                if canonical_type not in self.wit_map.canonical_to_ado:
                    issues.append(
                        f"field_policy {rule_name} references unknown canonical type '{canonical_type}'."
                    )
                for field_key in field_keys:
                    mapping = self.field_map.canonical_to_ado.get(field_key)
                    if mapping is None:
                        issues.append(
                            f"field_policy {rule_name} references unknown canonical field key '{field_key}'."
                        )
                        continue
                    if mapping.applies_to and canonical_type not in mapping.applies_to:
                        issues.append(
                            f"field_policy {rule_name} includes '{field_key}' for '{canonical_type}', "
                            "but field_map does not allow that type."
                        )

        return issues

    def generated_required_fields_by_type(self) -> Dict[str, Set[str]]:
        required: Dict[str, Set[str]] = {canonical_type: set() for canonical_type in self.wit_map.canonical_to_ado}

        for mapping in self.field_map.canonical_to_ado.values():
            for canonical_type in mapping.applies_to:
                ado_wit = self.wit_map.canonical_to_ado.get(canonical_type)
                if not ado_wit:
                    continue
                wit_contract = self.generated_wit_contract.work_item_types.get(ado_wit)
                if not wit_contract:
                    continue
                if mapping.reference_name in wit_contract.required_field_reference_names:
                    required.setdefault(canonical_type, set()).add(mapping.canonical_key)

        return required

    def effective_required_fields_by_type(self) -> Dict[str, Set[str]]:
        effective = self.generated_required_fields_by_type()

        for canonical_type, field_keys in self.field_policy.required_fields.items():
            bucket = effective.setdefault(canonical_type, set())
            bucket.update(field_keys)

        return effective


def _load_yaml_mapping(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Config file must decode to a mapping: {path}")
    return payload


def _require_schema_version(payload: Dict[str, Any], path: Path) -> None:
    value = payload.get("schema_version")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid schema_version in {path}")


def load_wit_map(path: Optional[Path] = None) -> WitMapConfig:
    config_path = path or (policy_config_dir() / "wit_map.yaml")
    payload = _load_yaml_mapping(config_path)
    _require_schema_version(payload, config_path)

    raw_map = payload.get("canonical_to_ado")
    if not isinstance(raw_map, dict):
        raise ValueError(f"canonical_to_ado must be a mapping in {config_path}")

    parsed: Dict[str, str] = {}
    for canonical_type, ado_wit in raw_map.items():
        if not isinstance(canonical_type, str) or not canonical_type.strip():
            raise ValueError(f"wit_map contains invalid canonical type key in {config_path}")
        if not isinstance(ado_wit, str) or not ado_wit.strip():
            raise ValueError(f"wit_map contains invalid ADO WIT value for '{canonical_type}' in {config_path}")
        parsed[canonical_type.strip()] = ado_wit.strip()
    return WitMapConfig(canonical_to_ado=parsed)


def load_field_map(path: Optional[Path] = None) -> FieldMapConfig:
    config_path = path or (policy_config_dir() / "field_map.yaml")
    payload = _load_yaml_mapping(config_path)
    _require_schema_version(payload, config_path)

    raw_map = payload.get("canonical_to_ado")
    if not isinstance(raw_map, dict):
        raise ValueError(f"canonical_to_ado must be a mapping in {config_path}")

    parsed: Dict[str, FieldMapping] = {}
    for canonical_key, value in raw_map.items():
        if not isinstance(canonical_key, str) or not canonical_key.strip():
            raise ValueError(f"field_map contains invalid canonical field key in {config_path}")
        if not isinstance(value, dict):
            raise ValueError(f"field_map entry for '{canonical_key}' must be a mapping in {config_path}")

        reference_name = value.get("reference_name")
        if not isinstance(reference_name, str) or not reference_name.strip():
            raise ValueError(
                f"field_map entry for '{canonical_key}' must include non-empty reference_name in {config_path}"
            )

        applies_to = value.get("applies_to", [])
        if not isinstance(applies_to, list):
            raise ValueError(f"field_map entry for '{canonical_key}' applies_to must be a list in {config_path}")
        applies_to_parsed: List[str] = []
        for canonical_type in applies_to:
            if not isinstance(canonical_type, str) or not canonical_type.strip():
                raise ValueError(
                    f"field_map entry for '{canonical_key}' contains invalid applies_to canonical type in {config_path}"
                )
            applies_to_parsed.append(canonical_type.strip())

        description = value.get("description")
        if description is not None and not isinstance(description, str):
            raise ValueError(f"field_map entry for '{canonical_key}' description must be a string in {config_path}")

        parsed[canonical_key.strip()] = FieldMapping(
            canonical_key=canonical_key.strip(),
            reference_name=reference_name.strip(),
            applies_to=tuple(applies_to_parsed),
            description=description.strip() if isinstance(description, str) and description.strip() else None,
        )

    return FieldMapConfig(canonical_to_ado=parsed)


def load_link_policy(path: Optional[Path] = None) -> LinkPolicyConfig:
    config_path = path or (policy_config_dir() / "link_policy.yaml")
    payload = _load_yaml_mapping(config_path)
    _require_schema_version(payload, config_path)

    allowed_link_types = payload.get("allowed_link_types")
    if not isinstance(allowed_link_types, list) or any(not isinstance(item, str) for item in allowed_link_types):
        raise ValueError(f"allowed_link_types must be a list[str] in {config_path}")

    max_depth = payload.get("max_depth")
    if not isinstance(max_depth, int) or max_depth < 1:
        raise ValueError(f"max_depth must be a positive integer in {config_path}")

    forbid_double_nesting = payload.get("forbid_double_nesting")
    if not isinstance(forbid_double_nesting, list) or any(
        not isinstance(item, str) for item in forbid_double_nesting
    ):
        raise ValueError(f"forbid_double_nesting must be a list[str] in {config_path}")

    return LinkPolicyConfig(
        allowed_link_types=tuple(allowed_link_types),
        max_depth=max_depth,
        forbid_double_nesting=tuple(forbid_double_nesting),
    )


def load_standards_policy(path: Optional[Path] = None) -> StandardsPolicyConfig:
    config_path = path or (policy_config_dir() / "standards.yaml")
    payload = _load_yaml_mapping(config_path)
    _require_schema_version(payload, config_path)

    raw_work_item_standards = payload.get("work_item_standards", {})
    if not isinstance(raw_work_item_standards, dict):
        raise ValueError(f"work_item_standards must be a mapping in {config_path}")
    work_item_standards: Dict[str, Dict[str, Any]] = {}
    for canonical_type, value in raw_work_item_standards.items():
        if not isinstance(canonical_type, str) or not canonical_type.strip():
            raise ValueError(f"work_item_standards contains invalid canonical type key in {config_path}")
        if not isinstance(value, dict):
            raise ValueError(f"work_item_standards['{canonical_type}'] must be an object in {config_path}")
        work_item_standards[canonical_type.strip()] = value

    required_tags = payload.get("required_tags", [])
    if not isinstance(required_tags, list) or any(not isinstance(item, str) for item in required_tags):
        raise ValueError(f"required_tags must be a list[str] in {config_path}")

    return StandardsPolicyConfig(
        required_tags=tuple(required_tags),
        work_item_standards=work_item_standards,
    )


def _parse_type_to_field_keys(payload: Dict[str, Any], key: str, config_path: Path) -> Dict[str, Tuple[str, ...]]:
    raw_value = payload.get(key, {})
    if not isinstance(raw_value, dict):
        raise ValueError(f"{key} must be a mapping of canonical type -> list[str] in {config_path}")

    parsed: Dict[str, Tuple[str, ...]] = {}
    for canonical_type, fields in raw_value.items():
        if not isinstance(canonical_type, str) or not canonical_type.strip():
            raise ValueError(f"{key} contains invalid canonical type key in {config_path}")
        if not isinstance(fields, list) or any(not isinstance(item, str) or not item.strip() for item in fields):
            raise ValueError(f"{key} for '{canonical_type}' must be list[str] in {config_path}")

        deduped: List[str] = []
        seen: Set[str] = set()
        for item in fields:
            normalized = item.strip()
            if normalized in seen:
                continue
            deduped.append(normalized)
            seen.add(normalized)
        parsed[canonical_type.strip()] = tuple(deduped)
    return parsed


def _parse_export_work_item_types(payload: Dict[str, Any], config_path: Path) -> Tuple[str, ...]:
    block = payload.get("agent_contract_export", {})
    if block is None:
        return tuple()
    if not isinstance(block, dict):
        raise ValueError(f"agent_contract_export must be a mapping in {config_path}")
    raw_items = block.get("include_work_item_types", [])
    if not isinstance(raw_items, list) or any(not isinstance(item, str) or not item.strip() for item in raw_items):
        raise ValueError(f"agent_contract_export.include_work_item_types must be list[str] in {config_path}")
    seen: Set[str] = set()
    parsed: List[str] = []
    for item in raw_items:
        normalized = item.strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        parsed.append(normalized)
    return tuple(parsed)


def _parse_owner_identity_format(payload: Dict[str, Any], config_path: Path) -> str:
    block = payload.get("owner_identity", {})
    if block is None:
        return "display_name"
    if not isinstance(block, dict):
        raise ValueError(f"owner_identity must be a mapping in {config_path}")
    raw_format = block.get("format", "display_name")
    if not isinstance(raw_format, str) or not raw_format.strip():
        raise ValueError(f"owner_identity.format must be a non-empty string in {config_path}")
    normalized = raw_format.strip().lower()
    if normalized not in {"display_name", "unique_name", "either"}:
        raise ValueError(
            f"owner_identity.format must be one of display_name|unique_name|either in {config_path}"
        )
    return normalized


def load_field_policy(path: Optional[Path] = None) -> FieldPolicyConfig:
    config_path = path or (policy_config_dir() / "field_policy.yaml")
    payload = _load_yaml_mapping(config_path)
    _require_schema_version(payload, config_path)

    allowed_fields = _parse_type_to_field_keys(payload, "allowed_fields", config_path)
    required_fields = _parse_type_to_field_keys(payload, "required_fields", config_path)
    description_required_sections = _parse_type_to_field_keys(payload, "description_required_sections", config_path)
    description_optional_sections = _parse_type_to_field_keys(payload, "description_optional_sections", config_path)
    export_work_item_types = _parse_export_work_item_types(payload, config_path)
    owner_identity_format = _parse_owner_identity_format(payload, config_path)

    return FieldPolicyConfig(
        allowed_fields=allowed_fields,
        required_fields=required_fields,
        export_work_item_types=export_work_item_types,
        description_required_sections=description_required_sections,
        description_optional_sections=description_optional_sections,
        owner_identity_format=owner_identity_format,
    )


def save_field_policy(field_policy: FieldPolicyConfig, path: Optional[Path] = None) -> Path:
    config_path = path or (policy_config_dir() / "field_policy.yaml")
    ensure_dir(config_path.parent)

    payload = {
        "schema_version": "1.0",
        "agent_contract_export": {
            "include_work_item_types": list(field_policy.export_work_item_types),
        },
        "allowed_fields": {
            canonical_type: sorted(list(field_keys))
            for canonical_type, field_keys in sorted(field_policy.allowed_fields.items(), key=lambda item: item[0])
        },
        "required_fields": {
            canonical_type: sorted(list(field_keys))
            for canonical_type, field_keys in sorted(field_policy.required_fields.items(), key=lambda item: item[0])
        },
        "description_required_sections": {
            canonical_type: sorted(list(field_keys))
            for canonical_type, field_keys in sorted(
                field_policy.description_required_sections.items(), key=lambda item: item[0]
            )
        },
        "description_optional_sections": {
            canonical_type: sorted(list(field_keys))
            for canonical_type, field_keys in sorted(
                field_policy.description_optional_sections.items(), key=lambda item: item[0]
            )
        },
        "owner_identity": {
            "format": field_policy.owner_identity_format,
        },
    }

    atomic_write_text(
        config_path,
        render_yaml_with_header(
            payload,
            [
                "USER-MANAGED POLICY FILE. SAFE TO EDIT.",
                "Defines canonical field requirements and export scope for agent contract generation.",
                "Some required_fields may be auto-promoted by `adoctl contract export` based on ADO-required fields.",
            ],
        ),
    )
    return config_path


def load_generated_wit_contract(path: Optional[Path] = None) -> GeneratedWitContract:
    config_path = path or (generated_config_dir() / "wit_contract.yaml")
    payload = _load_yaml_mapping(config_path)
    _require_schema_version(payload, config_path)

    raw_wit = payload.get("work_item_types")
    if not isinstance(raw_wit, dict):
        raise ValueError(f"work_item_types must be a mapping in {config_path}")

    parsed: Dict[str, GeneratedWitType] = {}
    for wit_name, wit_payload in raw_wit.items():
        if not isinstance(wit_name, str) or not wit_name.strip():
            raise ValueError(f"work_item_types contains invalid key in {config_path}")
        if not isinstance(wit_payload, dict):
            raise ValueError(f"work_item_types['{wit_name}'] must be an object in {config_path}")

        fields = wit_payload.get("fields")
        if not isinstance(fields, list):
            raise ValueError(f"work_item_types['{wit_name}'].fields must be a list in {config_path}")

        field_refs: Set[str] = set()
        required_refs: Set[str] = set()
        for field in fields:
            if not isinstance(field, dict):
                continue
            reference_name = field.get("reference_name")
            if not isinstance(reference_name, str):
                reference_name = field.get("referenceName")
            if not isinstance(reference_name, str) or not reference_name.strip():
                continue
            reference_name = reference_name.strip()
            field_refs.add(reference_name)
            required = field.get("required")
            always_required = field.get("alwaysRequired")
            if required is True or always_required is True:
                required_refs.add(reference_name)

        parsed[wit_name.strip()] = GeneratedWitType(
            field_reference_names=field_refs,
            required_field_reference_names=required_refs,
        )

    return GeneratedWitContract(work_item_types=parsed)


def load_effective_contract(
    policy_dir: Optional[Path] = None,
    generated_dir: Optional[Path] = None,
) -> EffectiveContractConfig:
    resolved_policy_dir = policy_dir or policy_config_dir()
    resolved_generated_dir = generated_dir or generated_config_dir()
    return EffectiveContractConfig(
        wit_map=load_wit_map(resolved_policy_dir / "wit_map.yaml"),
        field_map=load_field_map(resolved_policy_dir / "field_map.yaml"),
        field_policy=load_field_policy(resolved_policy_dir / "field_policy.yaml"),
        link_policy=load_link_policy(resolved_policy_dir / "link_policy.yaml"),
        standards=load_standards_policy(resolved_policy_dir / "standards.yaml"),
        generated_wit_contract=load_generated_wit_contract(resolved_generated_dir / "wit_contract.yaml"),
    )
