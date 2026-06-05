"""工作流状态对象。"""

from __future__ import annotations

from dataclasses import dataclass, field

from project_09_dev_team.messages.models import Artifact, DevelopmentPlan, TestReport


@dataclass
class DevTeamState:
    """便于后续迁移到 LangGraph StateGraph 的本地状态对象。"""

    requirement: str
    run_id: str
    plan: DevelopmentPlan | None = None
    code_artifacts: list[Artifact] = field(default_factory=list)
    doc_artifacts: list[Artifact] = field(default_factory=list)
    test_report: TestReport | None = None
    fix_count: int = 0
    stage: str = "planning"
