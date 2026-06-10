"""Agent hooks 生命周期的可选教学示例。

示例刻意保持轻量：它不改动主项目的 WorkflowEngine，只演示一次工具调用
如何被 pre / permission / post 三类 hook 包住。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ToolCall:
    """一次待执行的工具调用。"""

    tool_name: str
    args: dict
    user_id: str = "local-user"
    sensitive: bool = False


@dataclass
class HookResult:
    """hook 返回值。

    - block_reason：阻止工具继续执行。
    - updated_args：改写工具入参。
    - approved：审批敏感工具，None 表示不表态。
    - feedback_message：给调用链追加后置反馈。
    """

    block_reason: str = ""
    updated_args: dict | None = None
    approved: bool | None = None
    feedback_message: str = ""


@dataclass
class HookedToolResult:
    """带 hooks 执行后的工具结果。"""

    output: str
    final_args: dict
    feedback_messages: list[str] = field(default_factory=list)


PreToolUseHook = Callable[[ToolCall], HookResult]
PermissionRequestHook = Callable[[ToolCall], HookResult]
PostToolUseHook = Callable[[ToolCall, str], HookResult]


class HookLifecycle:
    """围绕工具调用的简化 hooks 管理器。"""

    def __init__(self):
        self._pre_tool_use_hooks: list[PreToolUseHook] = []
        self._permission_request_hooks: list[PermissionRequestHook] = []
        self._post_tool_use_hooks: list[PostToolUseHook] = []

    def on_pre_tool_use(self, hook: PreToolUseHook) -> None:
        self._pre_tool_use_hooks.append(hook)

    def on_permission_request(self, hook: PermissionRequestHook) -> None:
        self._permission_request_hooks.append(hook)

    def on_post_tool_use(self, hook: PostToolUseHook) -> None:
        self._post_tool_use_hooks.append(hook)

    def run_tool(self, call: ToolCall, tool_func: Callable[..., str]) -> HookedToolResult:
        current_call = ToolCall(
            tool_name=call.tool_name,
            args=dict(call.args),
            user_id=call.user_id,
            sensitive=call.sensitive,
        )

        for hook in self._pre_tool_use_hooks:
            outcome = hook(current_call)
            if outcome.block_reason:
                raise PermissionError(outcome.block_reason)
            if outcome.updated_args is not None:
                current_call.args = dict(outcome.updated_args)

        if current_call.sensitive:
            self._enforce_permission(current_call)

        output = tool_func(**current_call.args)
        feedback_messages: list[str] = []
        for hook in self._post_tool_use_hooks:
            outcome = hook(current_call, output)
            if outcome.feedback_message:
                feedback_messages.append(outcome.feedback_message)

        return HookedToolResult(
            output=output,
            final_args=dict(current_call.args),
            feedback_messages=feedback_messages,
        )

    def _enforce_permission(self, call: ToolCall) -> None:
        approved = False
        for hook in self._permission_request_hooks:
            outcome = hook(call)
            if outcome.approved is False:
                raise PermissionError(outcome.block_reason or "敏感工具审批被拒绝")
            if outcome.approved is True:
                approved = True

        if not approved:
            raise PermissionError("敏感工具需要明确审批")
