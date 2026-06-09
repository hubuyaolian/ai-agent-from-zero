"""结构化输出 schema 可选示例测试。"""

from __future__ import annotations

import unittest

from project_09_dev_team.examples.structured_output_schema_demo import (
    SchemaValidationError,
    validate_development_plan_payload,
)


class StructuredSchemaExampleTest(unittest.TestCase):
    def test_validates_payload_before_building_development_plan(self) -> None:
        payload = {
            "project_name": "todo_app",
            "requirement": "做一个待办事项管理应用",
            "summary": "本地待办事项管理 CLI",
            "modules": [
                {"path": "models.py", "responsibility": "数据模型"},
                {"path": "tests/test_commands.py", "responsibility": "命令测试"},
            ],
            "tasks": [
                {
                    "task_id": "T1",
                    "target_agent": "developer",
                    "description": "实现数据模型",
                    "module": "models",
                    "priority": "high",
                    "dependencies": [],
                    "acceptance_criteria": "字段有类型注解",
                },
                {
                    "task_id": "T2",
                    "target_agent": "tester",
                    "description": "编写测试",
                    "module": "tests",
                    "priority": "normal",
                    "dependencies": ["T1"],
                    "acceptance_criteria": "测试覆盖新增命令",
                },
            ],
            "interfaces": ["add(title)", "list_all()"],
        }

        plan = validate_development_plan_payload(payload)

        self.assertEqual(plan.project_name, "todo_app")
        self.assertEqual([task.task_id for task in plan.tasks], ["T1", "T2"])
        self.assertEqual(plan.modules[0]["path"], "models.py")

    def test_rejects_unsafe_module_path(self) -> None:
        payload = {
            "project_name": "bad_app",
            "requirement": "写入越界文件",
            "summary": "不安全计划",
            "modules": [{"path": "../secrets.py", "responsibility": "越界写入"}],
            "tasks": [],
            "interfaces": [],
        }

        with self.assertRaisesRegex(SchemaValidationError, "不安全路径"):
            validate_development_plan_payload(payload)

    def test_rejects_unknown_agent_and_missing_dependency(self) -> None:
        payload = {
            "project_name": "bad_app",
            "requirement": "做一个应用",
            "summary": "不安全计划",
            "modules": [{"path": "main.py", "responsibility": "入口"}],
            "tasks": [
                {
                    "task_id": "T1",
                    "target_agent": "root",
                    "description": "执行任意命令",
                    "module": "main",
                    "dependencies": ["missing"],
                }
            ],
            "interfaces": [],
        }

        with self.assertRaisesRegex(SchemaValidationError, "未知 Agent"):
            validate_development_plan_payload(payload)


if __name__ == "__main__":
    unittest.main()
