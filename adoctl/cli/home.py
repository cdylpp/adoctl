from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from adoctl.config.context import CLIContext, load_cli_context, save_cli_context
from adoctl.config.paths import generated_config_dir


def _value_or_placeholder(value: Optional[str]) -> str:
    return value if value else "<not set>"


def render_home_screen(context: CLIContext) -> str:
    width = 72
    line = "=" * width
    title = "ADOCTL HOME"
    sections = [
        line,
        f"{title:^{width}}",
        line,
        f"ORG URL           : {_value_or_placeholder(context.org_url)}",
        f"PROJECT           : {_value_or_placeholder(context.project)}",
        f"TEAM              : {_value_or_placeholder(context.team)}",
        f"CURRENT ITERATION : {_value_or_placeholder(context.current_iteration)}",
        line,
        "1) Set org URL",
        "2) Set project",
        "3) Select team",
        "4) Set current iteration",
        "5) Exit",
    ]
    return "\n".join(sections)


def load_generated_teams(
    project: Optional[str],
    teams_path: Optional[Path] = None,
) -> List[str]:
    if not project:
        return []

    path = teams_path or (generated_config_dir() / "teams.yaml")
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        return []

    file_project = data.get("project")
    if isinstance(file_project, str) and file_project.strip() and file_project.strip() != project:
        return []

    names: List[str] = []
    for team in data.get("teams", []):
        if not isinstance(team, dict):
            continue
        name = team.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return sorted(set(names))


def _prompt_input(label: str) -> Optional[str]:
    value = input(f"{label}: ").strip()
    if not value:
        return None
    return value


def _choose_team(context: CLIContext) -> CLIContext:
    teams = load_generated_teams(project=context.project)
    if not teams:
        manual = _prompt_input("No synced teams found. Enter team name (blank to cancel)")
        if manual is None:
            return context
        return replace(context, team=manual)

    print("Select a team:")
    for idx, team in enumerate(teams, start=1):
        print(f"{idx}) {team}")
    print("m) Enter team name manually")
    print("c) Cancel")

    choice = input("Choice: ").strip().lower()
    if choice == "c" or not choice:
        return context
    if choice == "m":
        manual = _prompt_input("Team name")
        if manual is None:
            return context
        return replace(context, team=manual)

    try:
        idx = int(choice)
    except ValueError:
        print("Invalid selection.")
        return context

    if idx < 1 or idx > len(teams):
        print("Invalid selection.")
        return context
    return replace(context, team=teams[idx - 1])


def apply_home_menu_choice(context: CLIContext, choice: str) -> Tuple[CLIContext, bool]:
    normalized = choice.strip()
    if normalized == "1":
        value = _prompt_input("Org URL")
        if value is not None:
            context = replace(context, org_url=value)
        return context, False
    if normalized == "2":
        value = _prompt_input("Project")
        if value is not None:
            context = replace(context, project=value)
        return context, False
    if normalized == "3":
        return _choose_team(context), False
    if normalized == "4":
        value = _prompt_input("Current iteration")
        if value is not None:
            context = replace(context, current_iteration=value)
        return context, False
    if normalized == "5":
        return context, True

    print("Invalid selection.")
    return context, False


def run_home_screen_loop() -> int:
    context = load_cli_context()
    while True:
        print(render_home_screen(context))
        context, should_exit = apply_home_menu_choice(context, input("Select an option: "))
        save_cli_context(context)
        if should_exit:
            return 0
