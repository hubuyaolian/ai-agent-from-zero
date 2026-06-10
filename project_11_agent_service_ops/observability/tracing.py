"""Trace 事件记录。"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from uuid import uuid4


@dataclass(frozen=True)
class TraceEvent:
    """一次可观测事件。"""

    run_id: str
    span_id: str
    name: str
    attributes: dict[str, object]
    parent_span_id: str | None = None
    timestamp: float = field(default_factory=time)


class TraceRecorder:
    """内存 trace 记录器。"""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    def new_run_id(self) -> str:
        """创建一次 Agent 调用的 run_id。"""
        return f"run_{uuid4().hex[:12]}"

    def record(
        self,
        run_id: str,
        name: str,
        attributes: dict[str, object] | None = None,
        parent_span_id: str | None = None,
    ) -> TraceEvent:
        """记录一个 span 事件。"""
        event = TraceEvent(
            run_id=run_id,
            span_id=f"span_{uuid4().hex[:12]}",
            parent_span_id=parent_span_id,
            name=name,
            attributes=attributes or {},
        )
        self._events.append(event)
        return event

    def events_for_run(self, run_id: str) -> list[TraceEvent]:
        """按 run_id 查询事件。"""
        return [event for event in self._events if event.run_id == run_id]

    def to_dicts(self, run_id: str | None = None) -> list[dict[str, object]]:
        """输出可序列化事件。"""
        events = self._events if run_id is None else self.events_for_run(run_id)
        return [
            {
                "run_id": event.run_id,
                "span_id": event.span_id,
                "parent_span_id": event.parent_span_id,
                "name": event.name,
                "attributes": event.attributes,
                "timestamp": round(event.timestamp, 6),
            }
            for event in events
        ]
