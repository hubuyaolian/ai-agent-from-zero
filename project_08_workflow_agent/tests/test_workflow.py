"""Workflow Agent 核心行为测试。"""

from __future__ import annotations

import tempfile
import unittest

from project_08_workflow_agent.error_handler.retry import RetryHandler
from project_08_workflow_agent.executor.checkpoint_store import CheckpointStore
from project_08_workflow_agent.executor.workflow_engine import WorkflowEngine
from project_08_workflow_agent.governance.audit_log import AuditLog
from project_08_workflow_agent.governance.policy import UserContext, resolve_safe_path
from project_08_workflow_agent.planner.models import ExecutionPlan, Step
from project_08_workflow_agent.tools.data_tools import calc_csv_statistics
from project_08_workflow_agent.tools.registry import ToolRegistry


class WorkflowAgentTest(unittest.TestCase):
    def test_safe_path_rejects_directory_traversal(self) -> None:
        with self.assertRaises(PermissionError):
            resolve_safe_path("../secrets.txt")

    def test_csv_statistics_uses_project_data(self) -> None:
        result = calc_csv_statistics("data/sales.csv")
        self.assertIn("units: count=4", result)
        self.assertIn("revenue: count=4", result)

    def test_safe_path_accepts_project_prefixed_relative_path(self) -> None:
        path = resolve_safe_path("project_08_workflow_agent/data/sales.csv")
        self.assertEqual(path.name, "sales.csv")

    def test_waiting_approval_can_resume_without_repeating_successful_steps(self) -> None:
        calls: list[str] = []

        def read_value(filepath: str) -> str:
            calls.append(f"read:{filepath}")
            return "read ok"

        def write_value(filepath: str, content: str) -> str:
            calls.append(f"write:{filepath}:{content}")
            return "write ok"

        def notify(title: str, content: str) -> str:
            calls.append(f"notify:{title}:{content}")
            return "notify ok"

        registry = ToolRegistry()
        registry.register(
            "read_value",
            read_value,
            description="读取测试值",
            group="test",
            required_args=["filepath"],
        )
        registry.register(
            "write_value",
            write_value,
            description="写入测试值",
            group="test",
            required_args=["filepath", "content"],
            sensitive=True,
        )
        registry.register(
            "notify",
            notify,
            description="发送测试通知",
            group="test",
            required_args=["title", "content"],
            sensitive=True,
            idempotent=False,
        )
        plan = ExecutionPlan(
            instruction="测试审批恢复",
            steps=[
                Step(id="read", name="读取", tool="read_value", args={"filepath": "data/sales.csv"}),
                Step(
                    id="write",
                    name="写入",
                    tool="write_value",
                    args={"filepath": "reports/test.txt", "content": "{{read}}"},
                    depends_on=["read"],
                    requires_approval=True,
                ),
                Step(
                    id="notify",
                    name="通知",
                    tool="notify",
                    args={"title": "完成", "content": "{{write}}"},
                    depends_on=["write"],
                    requires_approval=True,
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            audit_log = AuditLog(tmpdir)
            checkpoint_store = CheckpointStore(tmpdir)
            engine = WorkflowEngine(
                registry=registry,
                audit_log=audit_log,
                retry_handler=RetryHandler(audit_log=audit_log),
                checkpoint_store=checkpoint_store,
            )

            waiting = engine.execute_plan(plan, UserContext(auto_approve=False))
            self.assertEqual(waiting.status, "waiting_approval")
            self.assertEqual(calls, ["read:data/sales.csv"])
            checkpoint = checkpoint_store.load(waiting.run_id)
            self.assertEqual(checkpoint.pending_approvals, ["write"])

            resumed = engine.resume(waiting.run_id, UserContext(auto_approve=True))
            self.assertEqual(resumed.status, "success")
            self.assertEqual(
                calls,
                [
                    "read:data/sales.csv",
                    "write:reports/test.txt:read ok",
                    "notify:完成:write ok",
                ],
            )


if __name__ == "__main__":
    unittest.main()
