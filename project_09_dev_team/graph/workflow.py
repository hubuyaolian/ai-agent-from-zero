"""多智能体开发团队本地编排。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from project_09_dev_team.agents.developer import DeveloperAgent
from project_09_dev_team.agents.docwriter import DocWriterAgent
from project_09_dev_team.agents.planner import PlannerAgent
from project_09_dev_team.agents.tester import TesterAgent
from project_09_dev_team.config import LOG_DIR, MAX_FIX_ROUNDS, ensure_runtime_dirs
from project_09_dev_team.delivery import DeliveryManager, DeliveryResult
from project_09_dev_team.messages.bus import MessageBus
from project_09_dev_team.messages.models import AgentMessage, DevelopmentPlan, TestReport


@dataclass
class DevTeamResult:
    """一次开发团队运行结果。"""

    run_id: str
    status: str
    plan: DevelopmentPlan
    test_report: TestReport
    delivery: DeliveryResult
    messages: list[AgentMessage]

    def summary(self) -> str:
        lines = [
            f"状态: {self.status}",
            f"运行 ID: {self.run_id}",
            f"项目: {self.plan.project_name}",
            f"测试: {self.test_report.summary}",
            f"交付目录: {self.delivery.project_dir}",
            f"交付报告: {self.delivery.report_path}",
            f"消息数: {len(self.messages)}",
        ]
        if self.test_report.issues:
            lines.append("问题:")
            for issue in self.test_report.issues:
                lines.append(f"- {issue.severity} {issue.location}: {issue.description}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "plan": self.plan.to_dict(),
            "test_report": self.test_report.to_dict(),
            "delivery": self.delivery.to_dict(),
            "messages": [message.to_dict() for message in self.messages],
        }


class DevTeamWorkflow:
    """顺序编排四个 Agent，保留可迁移到 LangGraph 的状态边界。"""

    def __init__(
        self,
        planner: PlannerAgent | None = None,
        developer: DeveloperAgent | None = None,
        tester: TesterAgent | None = None,
        docwriter: DocWriterAgent | None = None,
        delivery_manager: DeliveryManager | None = None,
        max_fix_rounds: int = MAX_FIX_ROUNDS,
        record_history: bool = True,
    ):
        self.planner = planner or PlannerAgent()
        self.developer = developer or DeveloperAgent()
        self.tester = tester or TesterAgent()
        self.docwriter = docwriter or DocWriterAgent()
        self.delivery_manager = delivery_manager or DeliveryManager()
        self.max_fix_rounds = max_fix_rounds
        self.record_history = record_history

    def plan_only(self, requirement: str) -> DevelopmentPlan:
        return self.planner.plan(requirement)

    def run(self, requirement: str) -> DevTeamResult:
        ensure_runtime_dirs()
        run_id = uuid4().hex[:12]
        bus = MessageBus()

        plan = self.planner.plan(requirement)
        self._send(bus, run_id, "planner", "developer", "task", f"生成开发计划: {plan.project_name}", {"plan": plan.to_dict()})

        code_artifacts = self.developer.develop(plan)
        self._send(
            bus,
            run_id,
            "developer",
            "tester",
            "result",
            f"提交 {len(code_artifacts)} 个代码产物",
            {"artifacts": [artifact.to_dict() for artifact in code_artifacts]},
        )

        test_report = self.tester.review(code_artifacts)
        fix_count = 0
        while test_report.high_or_critical_issues() and fix_count < self.max_fix_rounds:
            self._send(
                bus,
                run_id,
                "tester",
                "developer",
                "bug",
                f"发现 {len(test_report.high_or_critical_issues())} 个高优先级问题",
                {"issues": [issue.to_dict() for issue in test_report.issues]},
                priority="high",
            )
            fix_count += 1
            code_artifacts = self.developer.develop(plan, test_report)
            test_report = self.tester.review(code_artifacts)

        self._send(
            bus,
            run_id,
            "tester",
            "docwriter",
            "result",
            test_report.summary,
            {"test_report": test_report.to_dict()},
        )

        doc_artifacts = self.docwriter.write_docs(plan, test_report)
        self._send(
            bus,
            run_id,
            "docwriter",
            "delivery",
            "result",
            f"提交 {len(doc_artifacts)} 个文档产物",
            {"artifacts": [artifact.to_dict() for artifact in doc_artifacts]},
        )

        delivery = self.delivery_manager.deliver(
            plan,
            code_artifacts,
            doc_artifacts,
            test_report,
            bus.history(),
        )
        status = "delivered" if delivery.quality_passed else "delivered_with_issues"
        result = DevTeamResult(run_id, status, plan, test_report, delivery, bus.history())
        if self.record_history:
            self._record_history(result)
        return result

    @staticmethod
    def _send(
        bus: MessageBus,
        run_id: str,
        sender: str,
        receiver: str,
        msg_type: str,
        content: str,
        attachments: dict,
        priority: str = "normal",
    ) -> None:
        bus.send(
            AgentMessage(
                sender=sender,
                receiver=receiver,
                msg_type=msg_type,
                content=content,
                correlation_id=run_id,
                attachments=attachments,
                priority=priority,
            )
        )

    @staticmethod
    def _record_history(result: DevTeamResult) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = LOG_DIR / "runs.jsonl"
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")


def recent_runs(limit: int = 10) -> list[dict]:
    path = Path(LOG_DIR) / "runs.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-limit:]]
