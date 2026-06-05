"""Project 08 Workflow Agent 命令行入口。"""

from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict

from project_08_workflow_agent.config import ensure_runtime_dirs
from project_08_workflow_agent.executor.checkpoint_store import CheckpointStore
from project_08_workflow_agent.executor.workflow_engine import WorkflowEngine
from project_08_workflow_agent.governance.audit_log import AuditLog
from project_08_workflow_agent.governance.policy import UserContext
from project_08_workflow_agent.planner.task_planner import TaskPlanner
from project_08_workflow_agent.scheduler.task_scheduler import TaskScheduler
from project_08_workflow_agent.tools.registry import create_registry


def build_engine() -> WorkflowEngine:
    registry = create_registry()
    planner = TaskPlanner(registry)
    return WorkflowEngine(registry=registry, planner=planner, audit_log=AuditLog())


def run_instruction(args: argparse.Namespace) -> None:
    engine = build_engine()
    context = UserContext.from_values(
        user_id=args.user,
        roles=args.roles,
        auto_approve=args.approve,
    )
    result = engine.run(" ".join(args.instruction), context)
    print_workflow_result(result)


def preview_plan(args: argparse.Namespace) -> None:
    registry = create_registry()
    planner = TaskPlanner(registry)
    plan = planner.create_plan(" ".join(args.instruction))
    print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))


def resume_run(args: argparse.Namespace) -> None:
    engine = build_engine()
    context = UserContext.from_values(
        user_id=args.user,
        roles=args.roles,
        auto_approve=args.approve,
    )
    result = engine.resume(args.run_id, context)
    print_workflow_result(result)


def print_workflow_result(result) -> None:
    print(result.summary())
    if result.status == "waiting_approval":
        print(f"审批后继续执行: python -m project_08_workflow_agent.main resume {result.run_id} --approve")


def list_tools(args: argparse.Namespace) -> None:
    registry = create_registry()
    groups = [args.group] if args.group else registry.groups()
    for group in groups:
        tools = registry.list_by_group(group)
        if not tools:
            continue
        print(f"[{group}]")
        for tool in tools:
            meta = registry.get_meta(tool.name)
            sensitive = " sensitive" if meta and meta.sensitive else ""
            print(f"- {tool.name}{sensitive}: {tool.description}")


def show_history(args: argparse.Namespace) -> None:
    audit_log = AuditLog()
    events = audit_log.recent_events(limit=args.limit)
    print(json.dumps(events, ensure_ascii=False, indent=2))


def show_errors(args: argparse.Namespace) -> None:
    audit_log = AuditLog()
    events = audit_log.recent_errors(limit=args.limit)
    print(json.dumps(events, ensure_ascii=False, indent=2))


def handle_schedule(args: argparse.Namespace) -> None:
    scheduler = TaskScheduler()
    if args.schedule_action == "add":
        task = scheduler.add(args.name, args.schedule, " ".join(args.instruction))
        print(json.dumps(asdict(task), ensure_ascii=False, indent=2))
    elif args.schedule_action == "list":
        tasks = [asdict(task) for task in scheduler.list_tasks()]
        print(json.dumps(tasks, ensure_ascii=False, indent=2))
    elif args.schedule_action == "remove":
        removed = scheduler.remove(args.task_id)
        print("已删除" if removed else "未找到任务")


def handle_checkpoints(args: argparse.Namespace) -> None:
    store = CheckpointStore()
    if args.checkpoint_action == "list":
        rows = []
        for checkpoint in store.list(limit=args.limit):
            rows.append(
                {
                    "run_id": checkpoint.run_id,
                    "status": checkpoint.status,
                    "pending_approvals": checkpoint.pending_approvals,
                    "updated_at": checkpoint.updated_at,
                }
            )
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif args.checkpoint_action == "show":
        checkpoint = store.load(args.run_id)
        print(json.dumps(asdict(checkpoint), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project 08 Workflow Agent")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="执行一条自然语言任务")
    run_parser.add_argument("instruction", nargs="+")
    run_parser.add_argument("--approve", action="store_true", help="允许执行敏感步骤")
    run_parser.add_argument("--user", default="local-user")
    run_parser.add_argument("--roles", default="user")
    run_parser.set_defaults(func=run_instruction)

    plan_parser = subparsers.add_parser("plan", help="只生成执行计划，不执行")
    plan_parser.add_argument("instruction", nargs="+")
    plan_parser.set_defaults(func=preview_plan)

    resume_parser = subparsers.add_parser("resume", help="从 checkpoint 恢复执行")
    resume_parser.add_argument("run_id")
    resume_parser.add_argument("--approve", action="store_true", help="允许执行敏感步骤")
    resume_parser.add_argument("--user", default="local-user")
    resume_parser.add_argument("--roles", default="user")
    resume_parser.set_defaults(func=resume_run)

    tools_parser = subparsers.add_parser("tools", help="列出工具")
    tools_parser.add_argument("--group", default="")
    tools_parser.set_defaults(func=list_tools)

    history_parser = subparsers.add_parser("history", help="查看最近审计日志")
    history_parser.add_argument("--limit", type=int, default=10)
    history_parser.set_defaults(func=show_history)

    errors_parser = subparsers.add_parser("errors", help="查看最近错误")
    errors_parser.add_argument("--limit", type=int, default=10)
    errors_parser.set_defaults(func=show_errors)

    schedule_parser = subparsers.add_parser("schedule", help="管理本地调度记录")
    schedule_sub = schedule_parser.add_subparsers(dest="schedule_action", required=True)
    add_parser = schedule_sub.add_parser("add")
    add_parser.add_argument("name")
    add_parser.add_argument("schedule")
    add_parser.add_argument("instruction", nargs="+")
    add_parser.set_defaults(func=handle_schedule)
    list_parser = schedule_sub.add_parser("list")
    list_parser.set_defaults(func=handle_schedule)
    remove_parser = schedule_sub.add_parser("remove")
    remove_parser.add_argument("task_id")
    remove_parser.set_defaults(func=handle_schedule)

    checkpoint_parser = subparsers.add_parser("checkpoints", help="查看本地 checkpoint")
    checkpoint_sub = checkpoint_parser.add_subparsers(dest="checkpoint_action", required=True)
    checkpoint_list = checkpoint_sub.add_parser("list")
    checkpoint_list.add_argument("--limit", type=int, default=10)
    checkpoint_list.set_defaults(func=handle_checkpoints)
    checkpoint_show = checkpoint_sub.add_parser("show")
    checkpoint_show.add_argument("run_id")
    checkpoint_show.set_defaults(func=handle_checkpoints)
    return parser


def interactive_shell() -> None:
    engine = build_engine()
    scheduler = TaskScheduler()
    print("Workflow Agent 已启动。输入 /tools、/history、/checkpoints、/schedule list、/quit。")
    while True:
        try:
            line = input("workflow> ").strip()
        except EOFError:
            break
        if not line:
            continue
        if line in {"/quit", "quit", "exit"}:
            break
        if line.startswith("/tools"):
            list_tools(argparse.Namespace(group=""))
            continue
        if line.startswith("/history"):
            show_history(argparse.Namespace(limit=10))
            continue
        if line.startswith("/checkpoints"):
            handle_checkpoints(argparse.Namespace(checkpoint_action="list", limit=10))
            continue
        if line.startswith("/resume"):
            parts = shlex.split(line[len("/resume") :].strip())
            approve = "--approve" in parts
            parts = [part for part in parts if part != "--approve"]
            if not parts:
                print("用法: /resume <run_id> [--approve]")
                continue
            context = UserContext(auto_approve=approve)
            result = engine.resume(parts[0], context)
            print_workflow_result(result)
            continue
        if line.startswith("/schedule list"):
            tasks = [asdict(task) for task in scheduler.list_tasks()]
            print(json.dumps(tasks, ensure_ascii=False, indent=2))
            continue
        approve = False
        if line.startswith("/run"):
            parts = shlex.split(line[len("/run") :].strip())
            approve = "--approve" in parts
            parts = [part for part in parts if part != "--approve"]
            line = " ".join(parts)
        context = UserContext(auto_approve=approve)
        result = engine.run(line, context)
        print_workflow_result(result)


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
