"""模型网关：路由、fallback、预算检查和演示响应生成。"""

from __future__ import annotations

from dataclasses import dataclass

from project_11_agent_service_ops.config import DEFAULT_MAX_OUTPUT_TOKENS
from project_11_agent_service_ops.gateway.cost_tracker import (
    BudgetTracker,
    UsageRecord,
    estimate_tokens,
)


class BudgetExceededError(RuntimeError):
    """预算不足时抛出。"""


@dataclass(frozen=True)
class ModelRoute:
    """一个可被网关路由的模型配置。"""

    name: str
    provider: str
    priority: int
    max_context_tokens: int
    input_cost_per_1k_cents: float
    output_cost_per_1k_cents: float
    available: bool = True


@dataclass(frozen=True)
class GatewayResponse:
    """模型网关返回给服务层的标准结果。"""

    model_name: str
    provider: str
    text: str
    input_tokens: int
    output_tokens: int
    cost_cents: float
    fallback_used: bool
    route_reason: str


def default_routes() -> list[ModelRoute]:
    """本地教学用的模型路由表。"""
    return [
        ModelRoute(
            name="deepseek-chat",
            provider="deepseek",
            priority=10,
            max_context_tokens=64000,
            input_cost_per_1k_cents=0.014,
            output_cost_per_1k_cents=0.028,
        ),
        ModelRoute(
            name="qwen-plus",
            provider="qwen",
            priority=20,
            max_context_tokens=32000,
            input_cost_per_1k_cents=0.04,
            output_cost_per_1k_cents=0.12,
        ),
        ModelRoute(
            name="glm-4-flash",
            provider="glm",
            priority=30,
            max_context_tokens=16000,
            input_cost_per_1k_cents=0.0,
            output_cost_per_1k_cents=0.0,
        ),
    ]


class ModelGateway:
    """生产模型网关的教学版。

    它不直接调用外部模型，而是演示模型调用前后必须经过的治理动作：
    选择模型、检查上下文、计算预算、记录成本和标记 fallback。
    """

    def __init__(self, routes: list[ModelRoute], budget_tracker: BudgetTracker) -> None:
        self.routes = sorted(routes, key=lambda item: item.priority)
        self.budget_tracker = budget_tracker

    def generate(
        self,
        prompt: str,
        tenant_id: str,
        preferred_model: str | None = None,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ) -> GatewayResponse:
        """选择模型并返回可预测的演示响应。"""
        route, fallback_used, route_reason = self._select_route(
            prompt=prompt,
            preferred_model=preferred_model,
        )
        input_tokens = estimate_tokens(prompt)
        output_tokens = min(max_output_tokens, max(12, input_tokens * 2))
        cost_cents = self._estimate_cost(route, input_tokens, output_tokens)

        decision = self.budget_tracker.check(tenant_id, cost_cents)
        if not decision.allowed:
            raise BudgetExceededError(decision.reason)

        text = (
            f"已通过 {route.provider}/{route.name} 处理请求。"
            f"生产系统会在这里返回真实 Agent 结果。问题摘要：{prompt[:40]}"
        )
        self.budget_tracker.record(
            UsageRecord(
                tenant_id=tenant_id,
                model_name=route.name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_cents=cost_cents,
            )
        )
        return GatewayResponse(
            model_name=route.name,
            provider=route.provider,
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_cents=round(cost_cents, 6),
            fallback_used=fallback_used,
            route_reason=route_reason,
        )

    def _select_route(
        self,
        prompt: str,
        preferred_model: str | None,
    ) -> tuple[ModelRoute, bool, str]:
        input_tokens = estimate_tokens(prompt)
        available_routes = [
            route
            for route in self.routes
            if route.available and input_tokens <= route.max_context_tokens
        ]
        if not available_routes:
            raise RuntimeError("没有可用模型能承载当前上下文")

        if preferred_model:
            for route in available_routes:
                if route.name == preferred_model:
                    return route, False, "命中首选模型"
            return available_routes[0], True, "首选模型不可用，已降级到默认可用模型"

        return available_routes[0], False, "按优先级选择默认模型"

    @staticmethod
    def _estimate_cost(
        route: ModelRoute,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        input_cost = input_tokens / 1000 * route.input_cost_per_1k_cents
        output_cost = output_tokens / 1000 * route.output_cost_per_1k_cents
        return input_cost + output_cost
