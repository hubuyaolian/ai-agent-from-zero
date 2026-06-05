"""Agent 间消息总线。"""

from __future__ import annotations

from project_09_dev_team.messages.models import AgentMessage


class MessageBus:
    """带优先级和历史记录的内存消息总线。"""

    _priority_order = {"high": 0, "normal": 1, "low": 2}

    def __init__(self):
        self._queue: list[AgentMessage] = []
        self._history: list[AgentMessage] = []

    def send(self, message: AgentMessage) -> None:
        self._queue.append(message)
        self._queue.sort(key=lambda item: self._priority_order.get(item.priority, 1))
        self._history.append(message)

    def receive(self, receiver: str) -> list[AgentMessage]:
        messages = [message for message in self._queue if message.receiver == receiver]
        self._queue = [message for message in self._queue if message.receiver != receiver]
        return messages

    def broadcast(self, sender: str, correlation_id: str, msg_type: str, content: str) -> None:
        for receiver in ("planner", "developer", "tester", "docwriter"):
            if receiver == sender:
                continue
            self.send(
                AgentMessage(
                    sender=sender,
                    receiver=receiver,
                    msg_type=msg_type,
                    content=content,
                    correlation_id=correlation_id,
                    priority="low",
                )
            )

    def history(self, agent: str | None = None) -> list[AgentMessage]:
        if agent is None:
            return list(self._history)
        return [
            message
            for message in self._history
            if message.sender == agent or message.receiver == agent
        ]

    def pending(self) -> list[AgentMessage]:
        return list(self._queue)
