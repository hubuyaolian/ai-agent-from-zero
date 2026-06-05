"""Project 09 Dev Team CLI。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from project_09_dev_team.agents.roles import default_roles
from project_09_dev_team.config import OUTPUT_DIR, ensure_runtime_dirs
from project_09_dev_team.graph.workflow import DevTeamWorkflow, recent_runs


def run_project(args: argparse.Namespace) -> None:
    workflow = DevTeamWorkflow()
    result = workflow.run(" ".join(args.requirement))
    print(result.summary())


def preview_plan(args: argparse.Namespace) -> None:
    workflow = DevTeamWorkflow()
    plan = workflow.plan_only(" ".join(args.requirement))
    print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))


def show_team(_: argparse.Namespace) -> None:
    roles = default_roles()
    for role in roles.values():
        responsibilities = "、".join(role.responsibilities)
        tools = ", ".join(role.tools)
        print(f"{role.display_name} ({role.name})")
        print(f"  职责: {responsibilities}")
        print(f"  工具: {tools}")


def show_history(args: argparse.Namespace) -> None:
    print(json.dumps(recent_runs(args.limit), ensure_ascii=False, indent=2))


def show_artifacts(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    rows = []
    for path in sorted(Path(OUTPUT_DIR).glob("*/DELIVERY_REPORT.md")):
        rows.append({"project": path.parent.name, "report": str(path)})
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project 09 Dev Team")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="运行开发团队")
    run_parser.add_argument("requirement", nargs="+")
    run_parser.set_defaults(func=run_project)

    plan_parser = subparsers.add_parser("plan", help="只生成计划")
    plan_parser.add_argument("requirement", nargs="+")
    plan_parser.set_defaults(func=preview_plan)

    team_parser = subparsers.add_parser("team", help="查看团队角色")
    team_parser.set_defaults(func=show_team)

    history_parser = subparsers.add_parser("history", help="查看最近运行")
    history_parser.add_argument("--limit", type=int, default=5)
    history_parser.set_defaults(func=show_history)

    artifacts_parser = subparsers.add_parser("artifacts", help="查看已交付产物")
    artifacts_parser.set_defaults(func=show_artifacts)
    return parser


def interactive_shell() -> None:
    parser = build_parser()
    print("多智能体协同开发助手。输入 /team、/history、/artifacts、/quit。")
    while True:
        try:
            line = input("dev-team> ").strip()
        except EOFError:
            break
        if not line:
            continue
        if line in {"/quit", "quit", "exit"}:
            break
        if line == "/team":
            show_team(argparse.Namespace())
            continue
        if line == "/history":
            show_history(argparse.Namespace(limit=5))
            continue
        if line == "/artifacts":
            show_artifacts(argparse.Namespace())
            continue
        args = parser.parse_args(["run", *line.split()])
        args.func(args)


def main() -> None:
    ensure_runtime_dirs()
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        interactive_shell()
        return
    args.func(args)


if __name__ == "__main__":
    main()
