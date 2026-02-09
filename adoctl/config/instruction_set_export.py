from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from adoctl.config.contract_export import export_agent_contract
from adoctl.util.fs import ensure_dir


def _copy_required_file(source: Path, destination: Path) -> Dict[str, str]:
    if not source.exists():
        raise FileNotFoundError(f"Required artifact not found: {source}")
    ensure_dir(destination.parent)
    shutil.copyfile(source, destination)
    return {"source": str(source), "destination": str(destination)}


def export_instruction_set(
    instruction_set_dir: str = "instruction_set",
    policy_dir: Optional[Path] = None,
    generated_dir: Optional[Path] = None,
    schema_path: str = "schema/bundle.schema.json",
    run_contract_export: bool = True,
) -> Dict[str, Any]:
    output_root = Path(instruction_set_dir)
    contracts_dir = output_root / "contracts"

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

    copied_files = [
        _copy_required_file(generated_contract_path, contracts_dir / "agent_contract.yaml"),
        _copy_required_file(resolved_schema_path, contracts_dir / "bundle.schema.json"),
        _copy_required_file(generated_planning_path, contracts_dir / "planning_context.yaml"),
    ]

    return {
        "instruction_set_dir": str(output_root),
        "contracts_dir": str(contracts_dir),
        "copied_files": copied_files,
        "contract_export": contract_export_result,
    }
