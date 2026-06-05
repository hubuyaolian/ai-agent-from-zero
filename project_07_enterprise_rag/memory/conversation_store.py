"""SQLite 会话存储。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class ConversationStore:
    """保存多会话对话历史和回答审计摘要。"""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)")

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> int:
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversations (session_id, role, content, metadata_json)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, metadata_json),
            )
            return int(cursor.lastrowid)

    def get_history(self, session_id: str, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, role, content, metadata_json, timestamp
                FROM conversations
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

        history = []
        for row in reversed(rows):
            history.append(
                {
                    "id": row[0],
                    "role": row[1],
                    "content": row[2],
                    "metadata": json.loads(row[3] or "{}"),
                    "timestamp": row[4],
                }
            )
        return history

    def clear_session(self, session_id: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            return int(cursor.rowcount)

    def list_sessions(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT session_id, MAX(timestamp) AS last_active, COUNT(*) AS message_count
                FROM conversations
                GROUP BY session_id
                ORDER BY last_active DESC
                """
            ).fetchall()
        return [
            {"session_id": row[0], "last_active": row[1], "message_count": row[2]}
            for row in rows
        ]

