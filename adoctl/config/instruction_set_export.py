from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from adoctl.config.contract_export import export_agent_contract
from adoctl.util.fs import atomic_write_text, ensure_dir


BASE_INSTRUCTION_FILES: Tuple[Tuple[str, str], ...] = (
    ("01 Required Inputs", "01_required_inputs.md"),
    ("02 Contracts And Rules", "02_contracts_and_rules.md"),
    ("03 Output Expectations", "03_output_expectations.md"),
    ("04 Generation Workflow", "04_generation_workflow.md"),
    ("05 Efficiency Notes", "05_efficiency_notes.md"),
)


def _read_required_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact not found: {path}")
    return path.read_text(encoding="utf-8").rstrip()


def _resolve_instruction_source(output_root: Path, filename: str) -> Path:
    candidate = output_root / filename
    if candidate.exists():
        return candidate
    fallback = Path("instruction_set") / filename
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        f"Missing required instruction source file '{filename}' in {output_root} or {fallback.parent}."
    )


def _render_markdown_section(title: str, body: str) -> str:
    return f"## {title}\n\n{body}\n"


def _render_fenced_section(title: str, language: str, content: str) -> str:
    return f"## {title}\n\n```{language}\n{content}\n```\n"


def export_instruction_set(
    instruction_set_dir: str = "instruction_set",
    policy_dir: Optional[Path] = None,
    generated_dir: Optional[Path] = None,
    schema_path: str = "schema/bundle.schema.json",
    run_contract_export: bool = True,
) -> Dict[str, Any]:
    output_root = Path(instruction_set_dir)
    ensure_dir(output_root)
    instruction_set_path = output_root / "instruction_set.md"

    resolved_generated_dir = generated_dir or Path("config/generated")
    resolved_schema_path = Path(schema_path)
    generated_contract_path = resolved_generated_dir / "agent_contract.yaml"
    generated_planning_path = resolved_generated_dir / "planning_context.yaml"

    contract_export_result: Optional[Dict[str, Any]] = None
    if run_contract_export:
        contract_export_result = export_agent_contract(
            out_path=str(generated_contract_path),
            policy_dir=policy_dir,
            generated_dir=resolved_generated_dir,
        )

    section_texts: List[str] = [
        "# Portable Agent Instruction Set\n",
        (
            "This document is machine-assembled by `adoctl instruction-set export` and is intended to be shared "
            "as a single, complete instruction payload for external agents.\n"
        ),
        (
            "When earlier sections reference `contracts/agent_contract.yaml`, `contracts/bundle.schema.json`, "
            "or `contracts/planning_context.yaml`, use sections 06, 07, and 08 in this document.\n"
        ),
    ]
    sections: List[Dict[str, str]] = []

    for title, filename in BASE_INSTRUCTION_FILES:
        source_path = _resolve_instruction_source(output_root=output_root, filename=filename)
        section_texts.append(_render_markdown_section(title=title, body=_read_required_text(source_path)))
        sections.append({"title": title, "source": str(source_path), "format": "markdown"})

    contract_text = _read_required_text(generated_contract_path)
    schema_text = _read_required_text(resolved_schema_path)
    planning_text = _read_required_text(generated_planning_path)

    section_texts.append(_render_fenced_section("06 Agent Contract", "yaml", contract_text))
    section_texts.append(_render_fenced_section("07 Bundle Schema", "json", schema_text))
    section_texts.append(_render_fenced_section("08 Planning Context", "yaml", planning_text))
    sections.extend(
        [
            {"title": "06 Agent Contract", "source": str(generated_contract_path), "format": "yaml"},
            {"title": "07 Bundle Schema", "source": str(resolved_schema_path), "format": "json"},
            {"title": "08 Planning Context", "source": str(generated_planning_path), "format": "yaml"},
        ]
    )

    atomic_write_text(instruction_set_path, "\n".join(section_texts).rstrip() + "\n")

    return {
        "instruction_set_dir": str(output_root),
        "instruction_set_markdown_path": str(instruction_set_path),
        "sections": sections,
        "contract_export": contract_export_result,
    }
