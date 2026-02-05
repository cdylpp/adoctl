from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from adoctl.ado_client.models import ADOConfig
from adoctl.sync.ado_sync import sync_ado_to_yaml


def _add_global_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--org-url", required=True, help='ADO org URL, e.g. "https://dev.azure.com/MyOrg"')
    parser.add_argument("--project", help="ADO project name (required for paths/wit/teams)")
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
    subparsers = parser.add_subparsers(dest="command", required=True)

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
    group.add_argument("--wit-only", action="store_true", help="Sync WIT fields only")
    group.add_argument("--teams", action="store_true", help="Sync teams only")

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
    if args.wit_only:
        return ["wit"]
    if args.teams:
        return ["teams"]
    return ["projects", "teams", "paths", "wit"]


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "sync":
        pat = _load_pat_from_env(args.pat_env)
        cfg = ADOConfig(org_url=args.org_url, project=args.project, pat=pat, api_version=args.api_version)
        sections = _sync_sections(args)
        sync_ado_to_yaml(cfg=cfg, out_dir=args.out_dir, wit_names=args.wit, sections=sections)
        return 0

    if args.command == "outbox" and args.outbox_cmd == "validate":
        print("outbox validate: not implemented yet", file=sys.stderr)
        return 2

    if args.command == "write":
        print("write: not implemented yet", file=sys.stderr)
        return 2

    parser.print_help()
    return 2

