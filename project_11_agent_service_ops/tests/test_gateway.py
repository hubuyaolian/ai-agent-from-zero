"""模型网关与成本治理测试。"""

from __future__ import annotations

import unittest

from project_11_agent_service_ops.gateway.cost_tracker import BudgetTracker
from project_11_agent_service_ops.gateway.model_gateway import (
    BudgetExceededError,
    ModelGateway,
    ModelRoute,
)


class GatewayTest(unittest.TestCase):
    def test_preferred_unavailable_model_falls_back(self) -> None:
        gateway = ModelGateway(
            routes=[
                ModelRoute(
                    name="primary",
                    provider="demo",
                    priority=1,
                    max_context_tokens=1000,
                    input_cost_per_1k_cents=0.1,
                    output_cost_per_1k_cents=0.1,
                    available=False,
                ),
                ModelRoute(
                    name="backup",
                    provider="demo",
                    priority=2,
                    max_context_tokens=1000,
                    input_cost_per_1k_cents=0.1,
                    output_cost_per_1k_cents=0.1,
                ),
            ],
            budget_tracker=BudgetTracker(daily_budget_cents=10),
        )

        response = gateway.generate(
            prompt="请总结 Agent 服务上线检查项",
            tenant_id="tenant-a",
            preferred_model="primary",
        )

        self.assertEqual(response.model_name, "backup")
        self.assertTrue(response.fallback_used)
        self.assertIn("降级", response.route_reason)

    def test_budget_rejection_blocks_model_call(self) -> None:
        gateway = ModelGateway(
            routes=[
                ModelRoute(
                    name="expensive",
                    provider="demo",
                    priority=1,
                    max_context_tokens=1000,
                    input_cost_per_1k_cents=100,
                    output_cost_per_1k_cents=100,
                )
            ],
            budget_tracker=BudgetTracker(daily_budget_cents=0.001),
        )

        with self.assertRaisesRegex(BudgetExceededError, "预算不足"):
            gateway.generate(
                prompt="这是一个会产生明显成本的请求",
                tenant_id="tenant-a",
                max_output_tokens=200,
            )

    def test_cost_snapshot_is_grouped_by_tenant(self) -> None:
        tracker = BudgetTracker(daily_budget_cents=10)
        gateway = ModelGateway(
            routes=[
                ModelRoute(
                    name="cheap",
                    provider="demo",
                    priority=1,
                    max_context_tokens=1000,
                    input_cost_per_1k_cents=0.1,
                    output_cost_per_1k_cents=0.1,
                )
            ],
            budget_tracker=tracker,
        )

        gateway.generate("hello", tenant_id="tenant-a")
        gateway.generate("world", tenant_id="tenant-a")

        snapshot = tracker.snapshot()
        self.assertIn("tenant-a", snapshot)
        self.assertGreater(snapshot["tenant-a"], 0)


if __name__ == "__main__":
    unittest.main()
