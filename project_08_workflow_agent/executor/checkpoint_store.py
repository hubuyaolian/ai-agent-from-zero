"""本地 checkpoint 存储。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from project_08_workflow_agent.config import CHECKPOINT_DIR
from project_08_workflow_agent.planner.models import ExecutionPlan


@dataclass
class WorkflowCheckpoint:
    """一次工作流运行的可恢复快照。"""

    run_id: str
    status: str
    plan: dict
    step_results: list[dict]
    pending_approvals: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_dict(cls, payload: dict) -> "WorkflowCheckpoint":
        return cls(**payload)

    def execution_plan(self) -> ExecutionPlan:
        return ExecutionPlan.from_dict(self.plan)


class CheckpointStore:
    """基于 JSON 文件的本地 checkpoint 存储。"""

    def __init__(self, checkpoint_dir: str | Path = CHECKPOINT_DIR):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save(self, checkpoint: WorkflowCheckpoint) -> WorkflowCheckpoint:
        checkpoint.updated_at = datetime.now(timezone.utc).isoformat()
        path = self._path(checkpoint.run_id)
        path.write_text(
            json.dumps(asdict(checkpoint), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return checkpoint

    def load(self, run_id: str) -> WorkflowCheckpoint:
        path = self._path(run_id)
        if not path.exists():
            raise FileNotFoundError(f"未找到 checkpoint: {run_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return WorkflowCheckpoint.from_dict(payload)

    def list(self, limit: int = 20) -> list[WorkflowCheckpoint]:
        paths = sorted(self.checkpoint_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        checkpoints = []
        for path in paths[:limit]:
            checkpoints.append(WorkflowCheckpoint.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        return checkpoints

    def _path(self, run_id: str) -> Path:
        safe_id = "".join(ch for ch in run_id if ch.isalnum() or ch in {"-", "_"})
        if not safe_id:
            raise ValueError("run_id 不能为空")
        return self.checkpoint_dir / f"{safe_id}.json"
