"""JSONL 审计日志。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from project_08_workflow_agent.config import LOG_DIR


class AuditLog:
    """记录工具调用、计划、执行结果和异常。"""

    def __init__(self, log_dir: str | Path = LOG_DIR):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def record(self, event_type: str, payload: dict) -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        path = self.log_dir / f"workflow_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def record_error(self, payload: dict) -> dict:
        entry = self.record("error", payload)
        path = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def recent_events(self, limit: int = 20) -> list[dict]:
        paths = sorted(self.log_dir.glob("workflow_*.jsonl"))
        return self._read_tail(paths, limit)

    def recent_errors(self, limit: int = 20) -> list[dict]:
        paths = sorted(self.log_dir.glob("errors_*.jsonl"))
        return self._read_tail(paths, limit)

    @staticmethod
    def _read_tail(paths: list[Path], limit: int) -> list[dict]:
        entries = []
        for path in reversed(paths):
            lines = path.read_text(encoding="utf-8").splitlines()
            for line in reversed(lines):
                if line.strip():
                    entries.append(json.loads(line))
                if len(entries) >= limit:
                    return entries
        return entries
