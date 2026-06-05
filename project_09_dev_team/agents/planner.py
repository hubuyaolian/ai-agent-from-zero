"""规划 Agent。"""

from __future__ import annotations

from project_09_dev_team.messages.models import DevelopmentPlan, TaskAssignment


class PlannerAgent:
    """规则式需求规划器，后续可替换为 LLM 结构化输出。"""

    def plan(self, requirement: str) -> DevelopmentPlan:
        text = requirement.strip()
        project_name = self._project_name(text)
        tasks = [
            TaskAssignment(
                task_id="T1",
                target_agent="developer",
                module="models",
                description="定义核心数据模型",
                priority="high",
                acceptance_criteria="模型字段清晰，有类型注解。",
            ),
            TaskAssignment(
                task_id="T2",
                target_agent="developer",
                module="storage",
                description="实现本地文件存储",
                priority="high",
                dependencies=["T1"],
                acceptance_criteria="文件不存在、空文件、损坏 JSON 都能处理。",
            ),
            TaskAssignment(
                task_id="T3",
                target_agent="developer",
                module="commands",
                description="实现核心业务命令",
                priority="high",
                dependencies=["T1", "T2"],
                acceptance_criteria="新增、查询、更新、删除等核心流程可测试。",
            ),
            TaskAssignment(
                task_id="T4",
                target_agent="developer",
                module="tests",
                description="编写单元测试",
                priority="high",
                dependencies=["T1", "T2", "T3"],
                acceptance_criteria="白名单 unittest 能通过。",
            ),
        ]
        return DevelopmentPlan(
            project_name=project_name,
            requirement=text,
            summary=self._summary(project_name),
            modules=self._modules(project_name),
            tasks=tasks,
            interfaces=self._interfaces(project_name),
        )

    @staticmethod
    def _project_name(requirement: str) -> str:
        lowered = requirement.lower()
        if "计算器" in requirement or "calculator" in lowered:
            return "calculator_cli"
        if "笔记" in requirement or "note" in lowered or "markdown" in lowered:
            return "notes_cli"
        return "todo_app"

    @staticmethod
    def _summary(project_name: str) -> str:
        summaries = {
            "calculator_cli": "命令行计算器，支持基础四则运算。",
            "notes_cli": "本地笔记管理 CLI，支持创建、搜索和标签。",
            "todo_app": "本地待办事项管理 CLI，支持增删改查和完成状态切换。",
        }
        return summaries[project_name]

    @staticmethod
    def _modules(project_name: str) -> list[dict]:
        if project_name == "calculator_cli":
            return [
                {"path": "calculator.py", "responsibility": "计算逻辑"},
                {"path": "main.py", "responsibility": "CLI 入口"},
                {"path": "tests/test_calculator.py", "responsibility": "单元测试"},
            ]
        if project_name == "notes_cli":
            return [
                {"path": "models.py", "responsibility": "笔记数据模型"},
                {"path": "storage.py", "responsibility": "JSON 文件存储"},
                {"path": "commands.py", "responsibility": "笔记命令"},
                {"path": "tests/test_commands.py", "responsibility": "单元测试"},
            ]
        return [
            {"path": "models.py", "responsibility": "TodoItem 数据模型"},
            {"path": "storage.py", "responsibility": "JSON 文件存储"},
            {"path": "commands.py", "responsibility": "待办命令"},
            {"path": "main.py", "responsibility": "CLI 入口"},
            {"path": "tests/test_commands.py", "responsibility": "单元测试"},
        ]

    @staticmethod
    def _interfaces(project_name: str) -> list[str]:
        if project_name == "calculator_cli":
            return ["add(a, b)", "subtract(a, b)", "multiply(a, b)", "divide(a, b)"]
        if project_name == "notes_cli":
            return ["create_note(title, body, tags)", "search_notes(query)", "list_notes()"]
        return ["add(title)", "list_all()", "toggle(item_id)", "delete(item_id)"]
