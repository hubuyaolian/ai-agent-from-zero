"""权限与路径安全策略。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from project_08_workflow_agent.config import PROJECT_DIR, SAFE_ROOTS


@dataclass(frozen=True)
class UserContext:
    """当前执行用户上下文。"""

    user_id: str = "local-user"
    roles: set[str] = field(default_factory=lambda: {"user"})
    auto_approve: bool = False

    @classmethod
    def from_values(
        cls,
        *,
        user_id: str = "local-user",
        roles: str | Iterable[str] | None = None,
        auto_approve: bool = False,
    ) -> "UserContext":
        if roles is None:
            role_set = {"user"}
        elif isinstance(roles, str):
            role_set = {item.strip() for item in roles.split(",") if item.strip()}
        else:
            role_set = {str(item).strip() for item in roles if str(item).strip()}
        if not role_set:
            role_set = {"user"}
        return cls(user_id=user_id, roles=role_set, auto_approve=auto_approve)


def resolve_safe_path(filepath: str | Path) -> Path:
    """将文件路径限制在项目 data/ 或 reports/ 下。"""
    path = Path(filepath)
    if not path.is_absolute():
        if path.parts and path.parts[0] == PROJECT_DIR.name:
            path = Path(*path.parts[1:])
        path = PROJECT_DIR / path
    resolved = path.resolve()
    for root in SAFE_ROOTS:
        root_resolved = root.resolve()
        if resolved == root_resolved or root_resolved in resolved.parents:
            return resolved
    allowed = ", ".join(str(root) for root in SAFE_ROOTS)
    raise PermissionError(f"路径不在允许目录内: {filepath}。允许目录: {allowed}")
