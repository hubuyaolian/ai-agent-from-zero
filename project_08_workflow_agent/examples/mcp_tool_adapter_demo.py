"""MCP 工具描述适配到 ToolRegistry 的可选教学示例。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from project_08_workflow_agent.tools.registry import ToolRegistry


@dataclass(frozen=True)
class MCPToolDescriptor:
    """简化版 MCP tool descriptor。

    真实 MCP server 还会提供 resources、prompts、transport 等能力。
    这里仅保留 ToolRegistry 需要治理的字段。
    """

    name: str
    description: str
    required_args: list[str] = field(default_factory=list)
    group: str = "mcp"
    sensitive: bool = False
    allowed_roles: list[str] = field(default_factory=lambda: ["user"])
    fallback: str | None = None
    rate_limit: int = 0
    idempotent: bool = True


def register_mcp_tools(
    registry: ToolRegistry,
    descriptors: list[MCPToolDescriptor],
    implementations: dict[str, Callable[..., str]],
) -> None:
    """把 MCP 工具描述注册进本地治理层。"""
    for descriptor in descriptors:
        implementation = implementations.get(descriptor.name)
        if implementation is None:
            raise ValueError(f"MCP 工具缺少本地执行实现: {descriptor.name}")
        registry.register(
            descriptor.name,
            implementation,
            description=descriptor.description,
            group=descriptor.group,
            required_args=descriptor.required_args,
            sensitive=descriptor.sensitive,
            allowed_roles=descriptor.allowed_roles,
            fallback=descriptor.fallback,
            rate_limit=descriptor.rate_limit,
            idempotent=descriptor.idempotent,
        )


def main() -> None:
    """运行一个本地演示。"""
    from project_08_workflow_agent.governance.policy import UserContext

    registry = ToolRegistry()
    register_mcp_tools(
        registry,
        [
            MCPToolDescriptor(
                name="crm_lookup_customer",
                description="查询 CRM 客户摘要",
                required_args=["customer_id"],
                group="crm",
                allowed_roles=["analyst"],
            )
        ],
        {"crm_lookup_customer": lambda customer_id: f"customer:{customer_id}"},
    )
    print(
        registry.invoke(
            "crm_lookup_customer",
            {"customer_id": "C001"},
            UserContext.from_values(roles="analyst"),
        )
    )


if __name__ == "__main__":
    main()
