"""通知工具。"""

from __future__ import annotations

from datetime import datetime

from project_08_workflow_agent.config import OUTPUT_DIR


def send_notification(title: str, content: str, channel: str = "local") -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "notifications.log"
    timestamp = datetime.now().isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] [{channel}] {title}: {content}\n")
    return f"通知已写入本地日志: {title}"
