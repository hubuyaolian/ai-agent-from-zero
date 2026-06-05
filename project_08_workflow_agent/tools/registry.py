"""统一工具注册中心。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from project_08_workflow_agent.governance.policy import UserContext


@dataclass
class ToolMeta:
    """工具元信息。"""

    name: str
    group: str
    description: str
    required_args: list[str] = field(default_factory=list)
    sensitive: bool = False
    allowed_roles: list[str] = field(default_factory=lambda: ["user"])
    fallback: str | None = None
    rate_limit: int = 0
    idempotent: bool = True
    timeout_seconds: int = 30


@dataclass
class Tool:
    """简单工具包装器，保持和 LangChain Tool 类似的 invoke 接口。"""

    name: str
    description: str
    func: Callable[..., str]

    def invoke(self, args: dict) -> str:
        return self.func(**args)


class ToolRegistry:
    """统一工具注册、参数校验、权限检查和调用日志。"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._metas: dict[str, ToolMeta] = {}
        self._call_log: list[dict] = []

    def register(
        self,
        name: str,
        func: Callable[..., str],
        *,
        description: str,
        group: str,
        required_args: list[str] | None = None,
        sensitive: bool = False,
        allowed_roles: list[str] | None = None,
        fallback: str | None = None,
        rate_limit: int = 0,
        idempotent: bool = True,
    ) -> None:
        tool = Tool(name=name, description=description, func=func)
        meta = ToolMeta(
            name=name,
            group=group,
            description=description,
            required_args=required_args or [],
            sensitive=sensitive,
            allowed_roles=allowed_roles or ["user"],
            fallback=fallback,
            rate_limit=rate_limit,
            idempotent=idempotent,
        )
        self._tools[name] = tool
        self._metas[name] = meta

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_meta(self, name: str) -> ToolMeta | None:
        return self._metas.get(name)

    def get_fallback(self, name: str) -> Tool | None:
        meta = self._metas.get(name)
        if meta and meta.fallback:
            return self._tools.get(meta.fallback)
        return None

    def list_all(self) -> list[Tool]:
        return list(self._tools.values())

    def list_by_group(self, group: str) -> list[Tool]:
        return [self._tools[name] for name, meta in self._metas.items() if meta.group == group]

    def groups(self) -> list[str]:
        return sorted({meta.group for meta in self._metas.values()})

    def validate_args(self, name: str, args: dict) -> tuple[bool, str]:
        meta = self._metas.get(name)
        if meta is None:
            return False, f"未知工具: {name}"
        missing = [field for field in meta.required_args if field not in args or args[field] in (None, "")]
        if missing:
            return False, f"缺少必填参数: {missing}"
        return True, ""

    def can_execute(self, name: str, user_context: UserContext) -> bool:
        meta = self._metas.get(name)
        if meta is None:
            return False
        return bool(set(meta.allowed_roles) & user_context.roles)

    def invoke(self, name: str, args: dict, user_context: UserContext) -> str:
        tool = self.get(name)
        if tool is None:
            raise ValueError(f"工具未注册: {name}")
        ok, reason = self.validate_args(name, args)
        if not ok:
            raise ValueError(reason)
        if not self.can_execute(name, user_context):
            raise PermissionError(f"当前角色无权执行工具: {name}")

        started_at = time.perf_counter()
        try:
            result = tool.invoke(args)
            duration_ms = (time.perf_counter() - started_at) * 1000
            self.log_call(name, args, result, True, duration_ms)
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - started_at) * 1000
            self.log_call(name, args, str(exc), False, duration_ms)
            raise

    def log_call(
        self,
        tool_name: str,
        args: dict,
        result: str,
        success: bool,
        duration_ms: float,
    ) -> None:
        self._call_log.append(
            {
                "tool": tool_name,
                "args_preview": str(args)[:200],
                "result_preview": str(result)[:200],
                "success": success,
                "duration_ms": round(duration_ms, 2),
            }
        )

    def call_log(self) -> list[dict]:
        return list(self._call_log)


def create_registry() -> ToolRegistry:
    """创建默认工具注册中心。"""
    from project_08_workflow_agent.reports.report_generator import generate_daily_report
    from project_08_workflow_agent.tools.data_tools import calc_csv_statistics, read_csv_summary
    from project_08_workflow_agent.tools.file_tools import archive_files, read_file, write_file
    from project_08_workflow_agent.tools.notify_tools import send_notification

    registry = ToolRegistry()
    registry.register(
        "read_file",
        read_file,
        description="读取 data/ 或 reports/ 下的文本文件",
        group="file",
        required_args=["filepath"],
    )
    registry.register(
        "write_file",
        write_file,
        description="写入 data/ 或 reports/ 下的文本文件",
        group="file",
        required_args=["filepath", "content"],
        sensitive=True,
    )
    registry.register(
        "archive_files",
        archive_files,
        description="归档 data/ 或 reports/ 下匹配文件",
        group="file",
        required_args=["source_dir", "archive_dir"],
        sensitive=True,
        idempotent=False,
    )
    registry.register(
        "read_csv_summary",
        read_csv_summary,
        description="读取 CSV 并返回列名、行数和预览",
        group="data",
        required_args=["filepath"],
    )
    registry.register(
        "calc_csv_statistics",
        calc_csv_statistics,
        description="统计 CSV 的数值列",
        group="data",
        required_args=["filepath"],
    )
    registry.register(
        "generate_daily_report",
        generate_daily_report,
        description="从 CSV 生成日报 CSV 文件",
        group="report",
        required_args=["data_path", "output_path"],
        sensitive=True,
    )
    registry.register(
        "send_notification",
        send_notification,
        description="模拟发送通知并写入本地通知日志",
        group="notify",
        required_args=["title", "content"],
        sensitive=True,
        idempotent=False,
    )
    return registry

