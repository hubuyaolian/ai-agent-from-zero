"""多 Agent 协作数据结构。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentMessage:
    """Agent 间传递的消息。"""

    sender: str
    receiver: str
    msg_type: str
    content: str
    correlation_id: str
    attachments: dict = field(default_factory=dict)
    priority: str = "normal"
    message_id: str = field(default_factory=lambda: uuid4().hex[:12])
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaskAssignment:
    """规划 Agent 下发的任务。"""

    task_id: str
    target_agent: str
    description: str
    module: str
    priority: str = "normal"
    dependencies: list[str] = field(default_factory=list)
    acceptance_criteria: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaskResult:
    """Agent 执行任务后的结果。"""

    task_id: str
    agent: str
    status: str
    output: str
    artifacts: list[str] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Artifact:
    """代码或文档产物。"""

    path: str
    content: str
    artifact_type: str = "code"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DevelopmentPlan:
    """一次开发需求的结构化计划。"""

    project_name: str
    requirement: str
    summary: str
    modules: list[dict]
    tasks: list[TaskAssignment]
    interfaces: list[str]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["tasks"] = [task.to_dict() for task in self.tasks]
        return payload


@dataclass
class TestIssue:
    """测试 Agent 发现的问题。"""

    severity: str
    location: str
    description: str
    suggestion: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TestReport:
    """测试报告。"""

    passed: bool
    summary: str
    issues: list[TestIssue] = field(default_factory=list)
    command: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""

    def high_or_critical_issues(self) -> list[TestIssue]:
        return [issue for issue in self.issues if issue.severity in {"CRITICAL", "HIGH"}]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["issues"] = [issue.to_dict() for issue in self.issues]
        return payload
