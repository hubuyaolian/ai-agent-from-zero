"""MCP 工具适配可选示例测试。"""

from __future__ import annotations

import unittest

from project_08_workflow_agent.examples.mcp_tool_adapter_demo import (
    MCPToolDescriptor,
    register_mcp_tools,
)
from project_08_workflow_agent.governance.policy import UserContext
from project_08_workflow_agent.tools.registry import ToolRegistry


class MCPAdapterExampleTest(unittest.TestCase):
    def test_registers_mcp_descriptor_but_registry_keeps_governance(self) -> None:
        registry = ToolRegistry()
        descriptors = [
            MCPToolDescriptor(
                name="crm_lookup_customer",
                description="查询 CRM 客户摘要",
                required_args=["customer_id"],
                group="crm",
                sensitive=False,
                allowed_roles=["analyst"],
            ),
            MCPToolDescriptor(
                name="crm_export_customer",
                description="导出 CRM 客户数据",
                required_args=["customer_id", "target_path"],
                group="crm",
                sensitive=True,
                allowed_roles=["admin"],
                idempotent=False,
            ),
        ]

        register_mcp_tools(
            registry,
            descriptors,
            implementations={
                "crm_lookup_customer": lambda customer_id: f"customer:{customer_id}",
                "crm_export_customer": lambda customer_id, target_path: (
                    f"export:{customer_id}->{target_path}"
                ),
            },
        )

        lookup_meta = registry.get_meta("crm_lookup_customer")
        export_meta = registry.get_meta("crm_export_customer")
        self.assertIsNotNone(lookup_meta)
        self.assertIsNotNone(export_meta)
        self.assertEqual(lookup_meta.required_args, ["customer_id"])
        self.assertTrue(export_meta.sensitive)
        self.assertFalse(export_meta.idempotent)

        analyst = UserContext.from_values(roles="analyst")
        admin = UserContext.from_values(roles="admin")
        self.assertEqual(
            registry.invoke("crm_lookup_customer", {"customer_id": "C001"}, analyst),
            "customer:C001",
        )
        with self.assertRaises(PermissionError):
            registry.invoke(
                "crm_export_customer",
                {"customer_id": "C001", "target_path": "reports/customer.csv"},
                analyst,
            )
        self.assertEqual(
            registry.invoke(
                "crm_export_customer",
                {"customer_id": "C001", "target_path": "reports/customer.csv"},
                admin,
            ),
            "export:C001->reports/customer.csv",
        )
        self.assertEqual(len(registry.call_log()), 2)


if __name__ == "__main__":
    unittest.main()
