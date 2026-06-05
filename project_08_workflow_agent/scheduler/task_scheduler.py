"""轻量本地调度记录。

这里不伪装成生产级调度器，只负责记录和展示任务。生产环境可替换为
APScheduler、Celery Beat、Prefect 或 Temporal。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from project_08_workflow_agent.config import SCHEDULE_FILE


@dataclass
class ScheduledTask:
    """本地计划任务记录。"""

    name: str
    schedule: str
    instruction: str
    task_id: str = field(default_factory=lambda: uuid4().hex[:12])
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TaskScheduler:
    """基于 JSON 文件的调度元数据管理。"""

    def __init__(self, path: str | Path = SCHEDULE_FILE):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, name: str, schedule: str, instruction: str) -> ScheduledTask:
        task = ScheduledTask(name=name, schedule=schedule, instruction=instruction)
        tasks = self.list_tasks()
        tasks.append(task)
        self._save(tasks)
        return task

    def list_tasks(self) -> list[ScheduledTask]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        return [ScheduledTask(**item) for item in raw]

    def remove(self, task_id: str) -> bool:
        tasks = self.list_tasks()
        kept = [task for task in tasks if task.task_id != task_id]
        self._save(kept)
        return len(kept) != len(tasks)

    def _save(self, tasks: list[ScheduledTask]) -> None:
        payload = [asdict(task) for task in tasks]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
