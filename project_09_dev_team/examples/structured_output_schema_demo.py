"""结构化输出校验可选教学示例。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from project_09_dev_team.delivery import validate_artifact_path
from project_09_dev_team.messages.models import DevelopmentPlan, TaskAssignment


class SchemaValidationError(ValueError):
    """模型输出不满足开发计划 schema。"""


ALLOWED_AGENTS = {"planner", "developer", "tester", "docwriter"}


def validate_development_plan_payload(payload: Mapping[str, Any]) -> DevelopmentPlan:
    """把不可信 dict 校验后转换为 DevelopmentPlan。"""
    project_name = _required_text(payload, "project_name")
    requirement = _required_text(payload, "requirement")
    summary = _required_text(payload, "summary")
    modules = _validate_modules(payload.get("modules"))
    tasks = _validate_tasks(payload.get("tasks"))
    interfaces = _validate_string_list(payload.get("interfaces"), "interfaces")
    return DevelopmentPlan(
        project_name=project_name,
        requirement=requirement,
        summary=summary,
        modules=modules,
        tasks=tasks,
        interfaces=interfaces,
    )


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SchemaValidationError(f"缺少必填文本字段: {field}")
    return value.strip()


def _validate_modules(raw_modules: Any) -> list[dict]:
    if not isinstance(raw_modules, list):
        raise SchemaValidationError("modules 必须是列表")
    modules: list[dict] = []
    for index, module in enumerate(raw_modules):
        if not isinstance(module, Mapping):
            raise SchemaValidationError(f"modules[{index}] 必须是对象")
        path = _required_text(module, "path")
        try:
            validate_artifact_path(path)
        except ValueError as exc:
            raise SchemaValidationError(f"不安全路径: {path}") from exc
        modules.append(
            {
                "path": path,
                "responsibility": _required_text(module, "responsibility"),
            }
        )
    return modules


def _validate_tasks(raw_tasks: Any) -> list[TaskAssignment]:
    if not isinstance(raw_tasks, list):
        raise SchemaValidationError("tasks 必须是列表")

    seen_task_ids: set[str] = set()
    pending_tasks: list[TaskAssignment] = []
    for index, task in enumerate(raw_tasks):
        if not isinstance(task, Mapping):
            raise SchemaValidationError(f"tasks[{index}] 必须是对象")
        task_id = _required_text(task, "task_id")
        if task_id in seen_task_ids:
            raise SchemaValidationError(f"重复 task_id: {task_id}")
        seen_task_ids.add(task_id)

        target_agent = _required_text(task, "target_agent")
        if target_agent not in ALLOWED_AGENTS:
            raise SchemaValidationError(f"未知 Agent: {target_agent}")

        dependencies = _validate_string_list(task.get("dependencies", []), "dependencies")
        pending_tasks.append(
            TaskAssignment(
                task_id=task_id,
                target_agent=target_agent,
                description=_required_text(task, "description"),
                module=_required_text(task, "module"),
                priority=str(task.get("priority") or "normal"),
                dependencies=dependencies,
                acceptance_criteria=str(task.get("acceptance_criteria") or ""),
            )
        )

    for task in pending_tasks:
        for dependency in task.dependencies:
            if dependency not in seen_task_ids:
                raise SchemaValidationError(f"未知依赖: {dependency}")
    return pending_tasks


def _validate_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SchemaValidationError(f"{field} 必须是列表")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise SchemaValidationError(f"{field}[{index}] 必须是非空字符串")
        result.append(item.strip())
    return result


def main() -> None:
    """运行一个本地演示。"""
    plan = validate_development_plan_payload(
        {
            "project_name": "todo_app",
            "requirement": "做一个待办事项管理应用",
            "summary": "本地待办事项管理 CLI",
            "modules": [{"path": "models.py", "responsibility": "数据模型"}],
            "tasks": [
                {
                    "task_id": "T1",
                    "target_agent": "developer",
                    "description": "实现数据模型",
                    "module": "models",
                }
            ],
            "interfaces": ["add(title)"],
        }
    )
    print(plan.to_dict())


if __name__ == "__main__":
    main()
