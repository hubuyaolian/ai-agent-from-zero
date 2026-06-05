"""开发 Agent。"""

from __future__ import annotations

from project_09_dev_team.messages.models import Artifact, DevelopmentPlan, TestReport


class DeveloperAgent:
    """生成结构化代码产物。"""

    def develop(self, plan: DevelopmentPlan, previous_report: TestReport | None = None) -> list[Artifact]:
        if plan.project_name == "calculator_cli":
            return self._calculator_artifacts()
        if plan.project_name == "notes_cli":
            return self._notes_artifacts()
        return self._todo_artifacts()

    def _todo_artifacts(self) -> list[Artifact]:
        return [
            Artifact(
                "models.py",
                '''"""Todo data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class TodoItem:
    id: str
    title: str
    done: bool = False
    created_at: str = ""

    @classmethod
    def create(cls, title: str) -> "TodoItem":
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("title cannot be empty")
        return cls(
            id=uuid4().hex[:8],
            title=clean_title,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "TodoItem":
        return cls(
            id=str(payload["id"]),
            title=str(payload["title"]),
            done=bool(payload.get("done", False)),
            created_at=str(payload.get("created_at", "")),
        )
''',
            ),
            Artifact(
                "storage.py",
                '''"""JSON file storage."""

from __future__ import annotations

import json
from pathlib import Path

from models import TodoItem


class TodoStorage:
    def __init__(self, path: str | Path = "todos.json"):
        self.path = Path(path)

    def load(self) -> list[TodoItem]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        except json.JSONDecodeError:
            return []
        return [TodoItem.from_dict(item) for item in raw]

    def save(self, items: list[TodoItem]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.to_dict() for item in items]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
''',
            ),
            Artifact(
                "commands.py",
                '''"""Todo command layer."""

from __future__ import annotations

from models import TodoItem
from storage import TodoStorage


class TodoCommands:
    def __init__(self, storage: TodoStorage):
        self.storage = storage

    def add(self, title: str) -> TodoItem:
        items = self.storage.load()
        item = TodoItem.create(title)
        items.append(item)
        self.storage.save(items)
        return item

    def list_all(self) -> list[TodoItem]:
        return self.storage.load()

    def toggle(self, item_id: str) -> TodoItem:
        items = self.storage.load()
        for item in items:
            if item.id == item_id:
                item.done = not item.done
                self.storage.save(items)
                return item
        raise KeyError(f"todo not found: {item_id}")

    def delete(self, item_id: str) -> bool:
        items = self.storage.load()
        kept = [item for item in items if item.id != item_id]
        if len(kept) == len(items):
            return False
        self.storage.save(kept)
        return True
''',
            ),
            Artifact(
                "main.py",
                '''"""Todo CLI."""

from __future__ import annotations

import argparse

from commands import TodoCommands
from storage import TodoStorage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Todo CLI")
    parser.add_argument("--db", default="todos.json")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("title")
    subparsers.add_parser("list")
    toggle_parser = subparsers.add_parser("toggle")
    toggle_parser.add_argument("item_id")
    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("item_id")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    commands = TodoCommands(TodoStorage(args.db))
    if args.command == "add":
        item = commands.add(args.title)
        print(f"added {item.id}: {item.title}")
    elif args.command == "list":
        for item in commands.list_all():
            mark = "x" if item.done else " "
            print(f"[{mark}] {item.id} {item.title}")
    elif args.command == "toggle":
        item = commands.toggle(args.item_id)
        print(f"toggled {item.id}: {item.done}")
    elif args.command == "delete":
        print("deleted" if commands.delete(args.item_id) else "not found")


if __name__ == "__main__":
    main()
''',
            ),
            Artifact(
                "tests/test_commands.py",
                '''"""Todo command tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commands import TodoCommands
from storage import TodoStorage


class TodoCommandsTest(unittest.TestCase):
    def test_add_toggle_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            commands = TodoCommands(TodoStorage(Path(tmpdir) / "todos.json"))
            item = commands.add("write tests")
            self.assertEqual(item.title, "write tests")
            self.assertFalse(item.done)
            toggled = commands.toggle(item.id)
            self.assertTrue(toggled.done)
            self.assertTrue(commands.delete(item.id))
            self.assertEqual(commands.list_all(), [])

    def test_empty_title_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            commands = TodoCommands(TodoStorage(Path(tmpdir) / "todos.json"))
            with self.assertRaises(ValueError):
                commands.add("   ")


if __name__ == "__main__":
    unittest.main()
''',
            ),
        ]

    def _calculator_artifacts(self) -> list[Artifact]:
        return [
            Artifact(
                "calculator.py",
                '''"""Calculator functions."""

from __future__ import annotations


def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("cannot divide by zero")
    return a / b
''',
            ),
            Artifact(
                "tests/test_calculator.py",
                '''"""Calculator tests."""

import unittest

from calculator import add, divide, multiply, subtract


class CalculatorTest(unittest.TestCase):
    def test_operations(self) -> None:
        self.assertEqual(add(1, 2), 3)
        self.assertEqual(subtract(5, 3), 2)
        self.assertEqual(multiply(4, 3), 12)
        self.assertEqual(divide(8, 2), 4)

    def test_divide_by_zero(self) -> None:
        with self.assertRaises(ZeroDivisionError):
            divide(1, 0)
''',
            ),
        ]

    def _notes_artifacts(self) -> list[Artifact]:
        artifacts = self._todo_artifacts()
        for artifact in artifacts:
            artifact.content = artifact.content.replace("Todo", "Note").replace("todo", "note")
            artifact.content = artifact.content.replace("todos", "notes")
        return artifacts
