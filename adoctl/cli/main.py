from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from adoctl.ado_client.models import ADOConfig
from adoctl.cli.home import run_home_screen_loop
from adoctl.config.contract_export import export_agent_contract
from adoctl.config.contract_lint import lint_contract
from adoctl.config.context import CLIContext, load_cli_context, load_local_project_defaults, save_cli_context
from adoctl.config.instruction_set_export import export_instruction_set
from adoctl.config.wiki_policy_bootstrap import bootstrap_field_policy_from_docs
from adoctl.outbox.validate import validate_outbox
from adoctl.outbox.write import write_outbox
from adoctl.sync.ado_sync import sync_ado_to_yaml
from adoctl.sync.wit_bootstrap import bootstrap_wit_contracts_from_extract


def _add_global_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--org-url", help='ADO org URL, e.g. "https://dev.azure.com/MyOrg"')
    parser.add_argument("--project", help="ADO project name")
    parser.add_argument("--team", help="Team name to store in local CLI context")
    parser.add_argument("--current-iteration", help="Current iteration path to store in local CLI context")
    parser.add_argument(
        "--pat-env",
        default="ADO_PAT",
        help="Environment variable name that contains the PAT (default: ADO_PAT)",
    )
    parser.add_argument(
        "--api-version",
        default="6.0",
        help="ADO REST API version (default: 6.0)",
    )


def _load_pat_from_env(var_name: str) -> str:
    pat = os.environ.get(var_name, "").strip()
    if not pat:
        raise RuntimeError(f"Missing PAT: set environment variable {var_name}.")
    return pat


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adoctl", description="ADO decomposition outbox + writer CLI")
    subparsers = parser.add_subparsers(dest="command", required=False)

    sync = subparsers.add_parser("sync", help="Sync ADO metadata into config/generated")
    _add_global_args(sync)
    sync.add_argument("--out-dir", default="config/generated", help="Output directory for generated YAML")
    sync.add_argument(
        "--wit",
        action="append",
        default=None,
        help='Work item type name to include (repeatable). Example: --wit "Feature" --wit "User Story"',
    )
    group = sync.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Sync projects, teams, paths, and WIT (default)")
    group.add_argument("--projects", action="store_true", help="Sync projects only")
    group.add_argument("--paths", action="store_true", help="Sync area + iteration paths only")
    group.add_argument("--teams-only", action="store_true", help="Sync teams only")
    group.add_argument("--wit-only", action="store_true", help="Sync WIT fields only")
    group.add_argument(
        "--planning-only",
        action="store_true",
        help="Sync planning metadata (team-scoped paths + Objectives/Key Results) only",
    )

    subparsers.add_parser("home", help="Show interactive home screen")

    context_cmd = subparsers.add_parser("context", help="View or update local CLI context")
    context_sub = context_cmd.add_subparsers(dest="context_cmd", required=True)
    context_sub.add_parser("show", help="Show currently saved context values")
    context_set = context_sub.add_parser("set", help="Set one or more context values")
    context_set.add_argument("--org-url", help='ADO org URL, e.g. "https://dev.azure.com/MyOrg"')
    context_set.add_argument("--project", help="ADO project name")
    context_set.add_argument("--team", help="Team name")
    context_set.add_argument("--current-iteration", help="Current iteration path")

    bootstrap = subparsers.add_parser(
        "bootstrap-wit-contracts",
        help="Initialize WIT contract YAML files from a local extracted JSON payload",
    )
    bootstrap.add_argument(
        "--input",
        default="data.json",
        help="Path to extracted WIT JSON payload (default: data.json)",
    )
    bootstrap.add_argument(
        "--out-dir",
        default="config/generated",
        help="Output directory for generated contract YAML files",
    )

    contract = subparsers.add_parser("contract", help="Contract commands")
    contract_sub = contract.add_subparsers(dest="contract_cmd", required=True)
    contract_export = contract_sub.add_parser("export", help="Export effective agent contract snapshot")
    contract_export.add_argument(
        "--out",
        default="config/generated/agent_contract.yaml",
        help="Output path for exported contract snapshot",
    )
    contract_export.add_argument(
        "--policy-dir",
        default="config/policy",
        help="Policy config directory",
    )
    contract_export.add_argument(
        "--generated-dir",
        default="config/generated",
        help="Generated config directory",
    )
    contract_lint = contract_sub.add_parser(
        "lint",
        help="Lint field policy, standards, field map, and generated metadata consistency",
    )
    contract_lint.add_argument(
        "--policy-dir",
        default="config/policy",
        help="Policy config directory",
    )
    contract_lint.add_argument(
        "--generated-dir",
        default="config/generated",
        help="Generated config directory",
    )
    contract_lint.add_argument(
        "--out",
        default=None,
        help="Optional output path for lint report YAML",
    )

    policy = subparsers.add_parser("policy", help="Policy commands")
    policy_sub = policy.add_subparsers(dest="policy_cmd", required=True)
    policy_bootstrap = policy_sub.add_parser(
        "bootstrap-from-docs",
        help="One-time bootstrap of field policy wiki metadata from docs/*.md",
    )
    policy_bootstrap.add_argument(
        "--docs-dir",
        default="docs",
        help="Directory containing team wiki markdown files",
    )
    policy_bootstrap.add_argument(
        "--out",
        default="config/policy/field_policy.yaml",
        help="Field policy YAML output path",
    )

    instruction_set = subparsers.add_parser(
        "instruction-set",
        help="Export portable instruction-set contracts for external agents",
    )
    instruction_set_sub = instruction_set.add_subparsers(dest="instruction_set_cmd", required=True)
    instruction_set_export = instruction_set_sub.add_parser(
        "export",
        help="Refresh instruction_set/contracts from generated contract, planning context, and schema",
    )
    instruction_set_export.add_argument(
        "--out-dir",
        default="instruction_set",
        help="Instruction-set root directory",
    )
    instruction_set_export.add_argument(
        "--policy-dir",
        default="config/policy",
        help="Policy config directory",
    )
    instruction_set_export.add_argument(
        "--generated-dir",
        default="config/generated",
        help="Generated config directory",
    )
    instruction_set_export.add_argument(
        "--schema",
        default="schema/bundle.schema.json",
        help="Bundle JSON schema path",
    )
    instruction_set_export.add_argument(
        "--skip-contract-export",
        action="store_true",
        help="Do not run contract export before copying artifacts",
    )

    outbox = subparsers.add_parser("outbox", help="Outbox commands")
    outbox_sub = outbox.add_subparsers(dest="outbox_cmd", required=True)
    validate = outbox_sub.add_parser("validate", help="Validate outbox bundles (schema → policy → metadata)")
    validate.add_argument("bundle", nargs="?", help="Path to a bundle JSON file")
    validate.add_argument("--all", action="store_true", help="Validate all bundles in outbox/ready")
    validate.add_argument(
        "--policy-dir",
        default="config/policy",
        help="Policy config directory",
    )
    validate.add_argument(
        "--generated-dir",
        default="config/generated",
        help="Generated config directory",
    )
    validate.add_argument(
        "--schema",
        default="schema/bundle.schema.json",
        help="Bundle JSON schema path",
    )

    write = subparsers.add_parser("write", help="Write validated bundles to ADO")
    _add_global_args(write)
    write.add_argument("bundle", nargs="?", help="Path to a validated bundle JSON file")
    write.add_argument("--all-validated", action="store_true", help="Write all bundles in outbox/validated")
    write.add_argument("--dry-run", action="store_true", help="Print plan only; do not write to ADO")
    write.add_argument("--area", help="Override area path for all work items in the run")
    write.add_argument("--iteration", help="Override iteration path for all work items in the run")
    write.add_argument(
        "--policy-dir",
        default="config/policy",
        help="Policy config directory",
    )
    write.add_argument(
        "--generated-dir",
        default="config/generated",
        help="Generated config directory",
    )
    write.add_argument(
        "--outbox-root",
        default="outbox",
        help="Outbox root directory",
    )

    return parser


def _sync_sections(args: argparse.Namespace) -> List[str]:
    if args.projects:
        return ["projects"]
    if args.paths:
        return ["paths"]
    if args.teams_only:
        return ["teams"]
    if args.wit_only:
        return ["wit"]
    if args.planning_only:
        return ["planning"]
    return ["projects", "paths", "teams", "wit", "planning"]


def _merge_context(
    base: CLIContext,
    org_url: Optional[str] = None,
    project: Optional[str] = None,
    team: Optional[str] = None,
    current_iteration: Optional[str] = None,
) -> CLIContext:
    return CLIContext(
        org_url=org_url or base.org_url,
        project=project or base.project,
        team=team or base.team,
        current_iteration=current_iteration or base.current_iteration,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    context = load_cli_context()

    if args.command is None or args.command == "home":
        return run_home_screen_loop()

    if args.command == "context":
        if args.context_cmd == "show":
            print(f"org_url: {context.org_url or '<not set>'}")
            print(f"project: {context.project or '<not set>'}")
            print(f"team: {context.team or '<not set>'}")
            print(f"current_iteration: {context.current_iteration or '<not set>'}")
            return 0

        if args.context_cmd == "set":
            updated = _merge_context(
                context,
                org_url=args.org_url,
                project=args.project,
                team=args.team,
                current_iteration=args.current_iteration,
            )
            if updated == context:
                parser.error("No updates provided. Pass at least one of --org-url/--project/--team/--current-iteration.")
            save_cli_context(updated)
            print("Context updated.")
            return 0

    if args.command == "sync":
        sections = _sync_sections(args)
        local_project_defaults = load_local_project_defaults()
        org_url = args.org_url or context.org_url
        project = args.project or context.project or local_project_defaults.project
        project_id = None
        if project and local_project_defaults.project and project == local_project_defaults.project:
            project_id = local_project_defaults.project_id

        if not org_url:
            parser.error("Missing org URL. Pass --org-url or set it via `adoctl home` / `adoctl context set --org-url`.")
        if any(section in {"paths", "teams", "wit", "planning"} for section in sections) and not project:
            parser.error(
                "Missing project. Pass --project or set it via `adoctl home` / `adoctl context set --project`."
            )

        pat = _load_pat_from_env(args.pat_env)
        cfg = ADOConfig(
            org_url=org_url,
            project=project,
            project_id=project_id,
            pat=pat,
            api_version=args.api_version,
        )
        sync_ado_to_yaml(cfg=cfg, out_dir=args.out_dir, wit_names=args.wit, sections=sections)
        save_cli_context(
            _merge_context(
                context,
                org_url=org_url,
                project=project,
                team=args.team,
                current_iteration=args.current_iteration,
            )
        )
        return 0

    if args.command == "bootstrap-wit-contracts":
        result = bootstrap_wit_contracts_from_extract(input_json=args.input, out_dir=args.out_dir)
        print(f"Created {result['work_item_type_count']} WIT contract files in {result['contracts_dir']}")
        print(f"Aggregate contract: {result['aggregate_path']}")
        return 0

    if args.command == "contract" and args.contract_cmd == "export":
        result = export_agent_contract(
            out_path=args.out,
            policy_dir=Path(args.policy_dir),
            generated_dir=Path(args.generated_dir),
        )
        strict_status = "ready" if result["strict_ready"] else "not ready"
        print(f"Contract exported: {result['output_path']}")
        print(f"Mapping coverage status: {strict_status}")
        if result.get("field_policy_updated"):
            print("field_policy.yaml was updated with generated required fields.")
        return 0

    if args.command == "contract" and args.contract_cmd == "lint":
        report = lint_contract(
            policy_dir=Path(args.policy_dir),
            generated_dir=Path(args.generated_dir),
            out_path=args.out,
        )
        summary = report["summary"]
        status = "ready" if report["strict_ready"] else "not ready"
        print(f"Contract lint status: {status}")
        print(f"Errors: {summary['errors']}  Warnings: {summary['warnings']}  Info: {summary['info']}")
        for finding in report["findings"]:
            print(
                f"[{finding['severity']}] {finding['code']} {finding['path']}: "
                f"{finding['message']} Suggestion: {finding['suggestion']}"
            )
        if "output_path" in report:
            print(f"Lint report: {report['output_path']}")
        return 0 if report["strict_ready"] else 2

    if args.command == "policy" and args.policy_cmd == "bootstrap-from-docs":
        result = bootstrap_field_policy_from_docs(
            docs_dir=args.docs_dir,
            out_path=args.out,
        )
        print(f"Field policy bootstrapped: {result['output_path']}")
        print(f"Docs processed: {result['source_count']}")
        print(f"WIT metadata captured: {result['work_item_count']}")
        return 0

    if args.command == "instruction-set" and args.instruction_set_cmd == "export":
        try:
            result = export_instruction_set(
                instruction_set_dir=args.out_dir,
                policy_dir=Path(args.policy_dir),
                generated_dir=Path(args.generated_dir),
                schema_path=args.schema,
                run_contract_export=not args.skip_contract_export,
            )
        except Exception as exc:  # noqa: BLE001 - CLI surface should return actionable errors
            print(f"instruction-set export: {exc}", file=sys.stderr)
            return 2

        contract_export_result = result.get("contract_export")
        if contract_export_result is not None:
            strict_status = "ready" if contract_export_result["strict_ready"] else "not ready"
            print(f"Contract export status: {strict_status}")
            print(f"Contract output: {contract_export_result['output_path']}")
        print(f"Instruction set contracts refreshed: {result['contracts_dir']}")
        for copied_file in result["copied_files"]:
            print(f"Copied {copied_file['source']} -> {copied_file['destination']}")
        return 0

    if args.command == "outbox" and args.outbox_cmd == "validate":
        try:
            result = validate_outbox(
                bundle=args.bundle,
                validate_all=args.all,
                policy_dir=Path(args.policy_dir),
                generated_dir=Path(args.generated_dir),
                schema_path=Path(args.schema),
            )
        except Exception as exc:  # noqa: BLE001 - CLI surface should return actionable errors
            print(f"outbox validate: {exc}", file=sys.stderr)
            return 2

        print(
            "Validated bundles: "
            f"{result['validated_count']} total, {result['passed_count']} passed, {result['failed_count']} failed"
        )
        for entry in result["results"]:
            if entry["result"] == "passed":
                if entry["moved_bundle_path"]:
                    print(f"PASS {entry['bundle_path']} -> {entry['moved_bundle_path']}")
                else:
                    print(f"PASS {entry['bundle_path']}")
            else:
                message = f"FAIL {entry['bundle_path']}"
                if entry["moved_bundle_path"]:
                    message += f" -> {entry['moved_bundle_path']}"
                if entry["report_path"]:
                    message += f" (report: {entry['report_path']})"
                print(message)
        return 0 if result["strict_ready"] else 2

    if args.command == "write":
        if args.all_validated and args.bundle:
            parser.error("Pass either a bundle path or --all-validated, not both.")
        if not args.all_validated and not args.bundle:
            parser.error("Provide a bundle path or pass --all-validated.")

        org_url = args.org_url or context.org_url
        local_project_defaults = load_local_project_defaults()
        project = args.project or context.project or local_project_defaults.project
        if not org_url:
            parser.error("Missing org URL. Pass --org-url or set it via `adoctl context set --org-url`.")
        if not project:
            parser.error("Missing project. Pass --project or set it via `adoctl context set --project`.")

        pat: Optional[str] = None
        if not args.dry_run:
            pat = _load_pat_from_env(args.pat_env)

        try:
            result = write_outbox(
                bundle=args.bundle,
                write_all_validated=args.all_validated,
                dry_run=args.dry_run,
                org_url=org_url,
                project=project,
                pat=pat,
                api_version=args.api_version,
                area_override=args.area,
                iteration_override=args.iteration,
                policy_dir=Path(args.policy_dir),
                generated_dir=Path(args.generated_dir),
                outbox_root=Path(args.outbox_root),
            )
        except Exception as exc:  # noqa: BLE001 - CLI surface should return actionable errors
            print(f"write: {exc}", file=sys.stderr)
            return 2

        save_cli_context(
            _merge_context(
                context,
                org_url=org_url,
                project=project,
                team=args.team,
                current_iteration=args.current_iteration,
            )
        )

        mode = "dry-run" if result["dry_run"] else "write"
        print(
            f"Write run ({mode}): {result['processed_count']} processed, "
            f"{result['succeeded_count']} succeeded, {result['failed_count']} failed"
        )
        for entry in result["results"]:
            if entry["result"] == "passed":
                message = f"PASS {entry['bundle_path']}"
                if entry["moved_bundle_path"]:
                    message += f" -> {entry['moved_bundle_path']}"
                print(message)
            else:
                print(f"FAIL {entry['bundle_path']}: {entry['error']}")

            for op in entry["operations"]:
                line = f"  {op['method']} {op['url']}"
                if op.get("local_id"):
                    line += f" (local_id={op['local_id']})"
                print(line)
        print(f"Audit: {result['audit_path']}")
        return 0 if result["strict_ready"] else 2

    parser.print_help()
    return 2
