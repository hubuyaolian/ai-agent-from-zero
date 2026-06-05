"""多智能体开发团队核心行为测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from project_09_dev_team.delivery import DeliveryManager, validate_artifact_path
from project_09_dev_team.graph.workflow import DevTeamWorkflow
from project_09_dev_team.messages.bus import MessageBus
from project_09_dev_team.messages.models import AgentMessage


class DevTeamTest(unittest.TestCase):
    def test_message_bus_receives_high_priority_first(self) -> None:
        bus = MessageBus()
        bus.send(AgentMessage("tester", "developer", "info", "low", "run-1", priority="low"))
        bus.send(AgentMessage("tester", "developer", "bug", "critical", "run-1", priority="high"))

        messages = bus.receive("developer")
        self.assertEqual([message.content for message in messages], ["critical", "low"])

    def test_artifact_path_rejects_unsafe_paths(self) -> None:
        with self.assertRaises(ValueError):
            validate_artifact_path("../secrets.py")
        with self.assertRaises(ValueError):
            validate_artifact_path("/tmp/secrets.py")

    def test_full_todo_workflow_delivers_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = DevTeamWorkflow(
                delivery_manager=DeliveryManager(tmpdir),
                record_history=False,
            )
            result = workflow.run("做一个待办事项管理应用，支持增删改查，数据存到本地文件")

            self.assertEqual(result.status, "delivered")
            self.assertTrue(result.test_report.passed)
            project_dir = Path(result.delivery.project_dir)
            self.assertTrue((project_dir / "models.py").exists())
            self.assertTrue((project_dir / "tests/test_commands.py").exists())
            self.assertTrue((project_dir / "README.md").exists())
            self.assertTrue((project_dir / "DELIVERY_REPORT.md").exists())


if __name__ == "__main__":
    unittest.main()
