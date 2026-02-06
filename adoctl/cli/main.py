from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from adoctl.ado_client.models import ADOConfig
from adoctl.cli.home import run_home_screen_loop
from adoctl.config.context import CLIContext, load_cli_context, save_cli_context
from adoctl.sync.ado_sync import sync_ado_to_yaml


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

    subparsers.add_parser("home", help="Show interactive home screen")

    context_cmd = subparsers.add_parser("context", help="View or update local CLI context")
    context_sub = context_cmd.add_subparsers(dest="context_cmd", required=True)
    context_sub.add_parser("show", help="Show currently saved context values")
    context_set = context_sub.add_parser("set", help="Set one or more context values")
    context_set.add_argument("--org-url", help='ADO org URL, e.g. "https://dev.azure.com/MyOrg"')
    context_set.add_argument("--project", help="ADO project name")
    context_set.add_argument("--team", help="Team name")
    context_set.add_argument("--current-iteration", help="Current iteration path")

    outbox = subparsers.add_parser("outbox", help="Outbox commands")
    outbox_sub = outbox.add_subparsers(dest="outbox_cmd", required=True)
    validate = outbox_sub.add_parser("validate", help="Validate outbox bundles (schema → policy → metadata)")
    validate.add_argument("bundle", nargs="?", help="Path to a bundle JSON file")
    validate.add_argument("--all", action="store_true", help="Validate all bundles in outbox/ready")

    write = subparsers.add_parser("write", help="Write validated bundles to ADO (not implemented yet)")
    write.add_argument("bundle", nargs="?", help="Path to a validated bundle JSON file")
    write.add_argument("--all-validated", action="store_true", help="Write all bundles in outbox/validated")
    write.add_argument("--dry-run", action="store_true", help="Print plan only; do not write to ADO")

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
    return ["projects", "paths", "teams", "wit"]


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
        org_url = args.org_url or context.org_url
        project = args.project or context.project

        if not org_url:
            parser.error("Missing org URL. Pass --org-url or set it via `adoctl home` / `adoctl context set --org-url`.")
        if any(section in {"paths", "teams", "wit"} for section in sections) and not project:
            parser.error(
                "Missing project. Pass --project or set it via `adoctl home` / `adoctl context set --project`."
            )

        pat = _load_pat_from_env(args.pat_env)
        cfg = ADOConfig(org_url=org_url, project=project, pat=pat, api_version=args.api_version)
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

    if args.command == "outbox" and args.outbox_cmd == "validate":
        print("outbox validate: not implemented yet", file=sys.stderr)
        return 2

    if args.command == "write":
        print("write: not implemented yet", file=sys.stderr)
        return 2

    parser.print_help()
    return 2
