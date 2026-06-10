"""Agent hooks 生命周期可选示例测试。"""

from __future__ import annotations

import unittest

from project_08_workflow_agent.examples.hook_lifecycle_demo import (
    HookLifecycle,
    HookResult,
    ToolCall,
)


class HookLifecycleExampleTest(unittest.TestCase):
    def test_pre_hook_rewrites_args_and_post_hook_records_feedback(self) -> None:
        lifecycle = HookLifecycle()
        captured_args: list[dict] = []

        def normalize_content(call: ToolCall) -> HookResult:
            return HookResult(
                updated_args={
                    **call.args,
                    "content": call.args["content"].strip(),
                    "filepath": "reports/normalized.txt",
                }
            )

        def collect_feedback(call: ToolCall, output: str) -> HookResult:
            return HookResult(feedback_message=f"{call.tool_name} finished: {output}")

        def write_file(filepath: str, content: str) -> str:
            captured_args.append({"filepath": filepath, "content": content})
            return f"write:{filepath}:{content}"

        lifecycle.on_pre_tool_use(normalize_content)
        lifecycle.on_post_tool_use(collect_feedback)

        result = lifecycle.run_tool(
            ToolCall(
                tool_name="write_file",
                args={"filepath": "reports/raw.txt", "content": "  hello  "},
            ),
            write_file,
        )

        self.assertEqual(
            captured_args,
            [{"filepath": "reports/normalized.txt", "content": "hello"}],
        )
        self.assertEqual(result.output, "write:reports/normalized.txt:hello")
        self.assertEqual(result.final_args["content"], "hello")
        self.assertEqual(
            result.feedback_messages,
            ["write_file finished: write:reports/normalized.txt:hello"],
        )

    def test_pre_hook_blocks_before_tool_executes(self) -> None:
        lifecycle = HookLifecycle()
        calls: list[str] = []

        def block_unsafe_path(call: ToolCall) -> HookResult:
            if str(call.args.get("filepath", "")).startswith("../"):
                return HookResult(block_reason="拒绝访问工作区外路径")
            return HookResult()

        def read_file(filepath: str) -> str:
            calls.append(filepath)
            return "content"

        lifecycle.on_pre_tool_use(block_unsafe_path)

        with self.assertRaisesRegex(PermissionError, "拒绝访问工作区外路径"):
            lifecycle.run_tool(
                ToolCall(tool_name="read_file", args={"filepath": "../secrets.txt"}),
                read_file,
            )

        self.assertEqual(calls, [])

    def test_sensitive_tool_requires_permission_hook_approval(self) -> None:
        lifecycle = HookLifecycle()

        def export_customer(customer_id: str) -> str:
            return f"export:{customer_id}"

        with self.assertRaisesRegex(PermissionError, "敏感工具需要明确审批"):
            lifecycle.run_tool(
                ToolCall(
                    tool_name="crm_export_customer",
                    args={"customer_id": "C001"},
                    sensitive=True,
                ),
                export_customer,
            )

        lifecycle.on_permission_request(
            lambda call: HookResult(approved=False, block_reason="仅管理员可导出")
        )
        with self.assertRaisesRegex(PermissionError, "仅管理员可导出"):
            lifecycle.run_tool(
                ToolCall(
                    tool_name="crm_export_customer",
                    args={"customer_id": "C001"},
                    sensitive=True,
                ),
                export_customer,
            )

        allow_lifecycle = HookLifecycle()
        allow_lifecycle.on_permission_request(lambda call: HookResult(approved=True))

        result = allow_lifecycle.run_tool(
            ToolCall(
                tool_name="crm_export_customer",
                args={"customer_id": "C001"},
                sensitive=True,
            ),
            export_customer,
        )

        self.assertEqual(result.output, "export:C001")


if __name__ == "__main__":
    unittest.main()
