"""工作流计划数据结构。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def _stable_hash(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class Step:
    """单个可执行步骤。"""

    id: str
    name: str
    tool: str
    args: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    requires_approval: bool = False
    idempotency_key: str | None = None
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "Step":
        return cls(**payload)


@dataclass
class ExecutionPlan:
    """一次用户任务的执行计划。"""

    instruction: str
    steps: list[Step]
    plan_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.plan_id:
            self.plan_id = self.compute_hash()

    def compute_hash(self) -> str:
        payload = {
            "instruction": self.instruction,
            "steps": [step.to_dict() for step in self.steps],
        }
        return _stable_hash(payload)

    def to_dict(self) -> dict:
        return {
            "instruction": self.instruction,
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ExecutionPlan":
        steps = [Step.from_dict(item) for item in payload.get("steps", [])]
        return cls(
            instruction=payload.get("instruction", ""),
            steps=steps,
            plan_id=payload.get("plan_id", ""),
            created_at=payload.get("created_at", datetime.now(timezone.utc).isoformat()),
        )
