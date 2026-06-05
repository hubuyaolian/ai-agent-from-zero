"""工作流运行态。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkflowRuntimeState:
    """便于后续替换成 LangGraph StateGraph 的最小状态对象。"""

    instruction: str
    plan_id: str = ""
    current_step: str = ""
    pending_approvals: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    results: dict[str, str] = field(default_factory=dict)
