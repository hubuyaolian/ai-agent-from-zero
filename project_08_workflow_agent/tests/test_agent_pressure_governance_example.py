"""Agent 压力治理可选示例测试。"""

from __future__ import annotations

import unittest

from project_08_workflow_agent.examples.agent_pressure_governance_demo import (
    AgentPressureGovernor,
    CircuitBreaker,
    SlidingWindowRateLimiter,
)


class AgentPressureGovernanceExampleTest(unittest.TestCase):
    def test_sliding_window_rate_limiter_blocks_bursts(self) -> None:
        limiter = SlidingWindowRateLimiter(max_calls=2, window_seconds=60)
        breaker = CircuitBreaker(failure_threshold=3, recovery_seconds=30)
        governor = AgentPressureGovernor(limiter, breaker)

        def tool() -> str:
            return "ok"

        first = governor.run("send_notification", "user-1", now=0, operation=tool)
        second = governor.run("send_notification", "user-1", now=10, operation=tool)
        third = governor.run("send_notification", "user-1", now=20, operation=tool)
        after_window = governor.run("send_notification", "user-1", now=61, operation=tool)

        self.assertEqual(first.status, "success")
        self.assertEqual(second.status, "success")
        self.assertEqual(third.status, "rate_limited")
        self.assertEqual(third.retry_after_seconds, 40)
        self.assertEqual(after_window.status, "success")

    def test_circuit_breaker_blocks_after_repeated_failures(self) -> None:
        limiter = SlidingWindowRateLimiter(max_calls=10, window_seconds=60)
        breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=30)
        governor = AgentPressureGovernor(limiter, breaker)

        def failing_tool() -> str:
            raise RuntimeError("upstream timeout")

        first = governor.run("crm_lookup", "user-1", now=0, operation=failing_tool)
        second = governor.run("crm_lookup", "user-1", now=1, operation=failing_tool)
        blocked = governor.run("crm_lookup", "user-1", now=2, operation=lambda: "ok")

        self.assertEqual(first.status, "failed")
        self.assertEqual(second.status, "failed")
        self.assertEqual(blocked.status, "circuit_open")
        self.assertEqual(blocked.retry_after_seconds, 29)

    def test_circuit_breaker_recovers_after_cooldown(self) -> None:
        limiter = SlidingWindowRateLimiter(max_calls=10, window_seconds=60)
        breaker = CircuitBreaker(failure_threshold=1, recovery_seconds=30)
        governor = AgentPressureGovernor(limiter, breaker)

        governor.run(
            "crm_lookup",
            "user-1",
            now=0,
            operation=lambda: (_ for _ in ()).throw(RuntimeError("fail")),
        )
        blocked = governor.run("crm_lookup", "user-1", now=10, operation=lambda: "ok")
        recovered = governor.run("crm_lookup", "user-1", now=31, operation=lambda: "ok")

        self.assertEqual(blocked.status, "circuit_open")
        self.assertEqual(recovered.status, "success")
        self.assertEqual(breaker.state, "closed")


if __name__ == "__main__":
    unittest.main()
