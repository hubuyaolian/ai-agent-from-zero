"""Agent 工具调用压力治理的可选教学示例。"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RateLimitDecision:
    """限流判断结果。"""

    allowed: bool
    retry_after_seconds: float = 0
    reason: str = ""


class SlidingWindowRateLimiter:
    """按 key 做滑动窗口限流。"""

    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, now: float) -> RateLimitDecision:
        calls = self._calls[key]
        while calls and now - calls[0] >= self.window_seconds:
            calls.popleft()

        if len(calls) >= self.max_calls:
            retry_after = self.window_seconds - (now - calls[0])
            return RateLimitDecision(
                allowed=False,
                retry_after_seconds=max(0, retry_after),
                reason="调用过于频繁",
            )

        calls.append(now)
        return RateLimitDecision(allowed=True)


@dataclass(frozen=True)
class CircuitDecision:
    """熔断判断结果。"""

    allowed: bool
    retry_after_seconds: float = 0
    reason: str = ""


class CircuitBreaker:
    """针对连续失败工具的简单熔断器。"""

    def __init__(self, failure_threshold: int, recovery_seconds: float):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failure_count = 0
        self.opened_at: float | None = None
        self.state = "closed"

    def before_call(self, now: float) -> CircuitDecision:
        if self.state != "open":
            return CircuitDecision(allowed=True)

        assert self.opened_at is not None
        elapsed = now - self.opened_at
        if elapsed >= self.recovery_seconds:
            self.state = "half_open"
            return CircuitDecision(allowed=True)

        return CircuitDecision(
            allowed=False,
            retry_after_seconds=self.recovery_seconds - elapsed,
            reason="工具连续失败，熔断中",
        )

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None
        self.state = "closed"

    def record_failure(self, now: float) -> None:
        self.failure_count += 1
        if self.state == "half_open" or self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.opened_at = now


@dataclass(frozen=True)
class GovernedCallResult:
    """经过压力治理后的工具调用结果。"""

    status: str
    output: str = ""
    reason: str = ""
    retry_after_seconds: float = 0


class AgentPressureGovernor:
    """把限流和熔断包在工具调用之前。"""

    def __init__(
        self,
        rate_limiter: SlidingWindowRateLimiter,
        circuit_breaker: CircuitBreaker,
    ):
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker

    def run(
        self,
        tool_name: str,
        user_id: str,
        *,
        now: float,
        operation: Callable[[], str],
    ) -> GovernedCallResult:
        limit_key = f"{user_id}:{tool_name}"
        limit_decision = self.rate_limiter.check(limit_key, now)
        if not limit_decision.allowed:
            return GovernedCallResult(
                status="rate_limited",
                reason=limit_decision.reason,
                retry_after_seconds=limit_decision.retry_after_seconds,
            )

        circuit_decision = self.circuit_breaker.before_call(now)
        if not circuit_decision.allowed:
            return GovernedCallResult(
                status="circuit_open",
                reason=circuit_decision.reason,
                retry_after_seconds=circuit_decision.retry_after_seconds,
            )

        try:
            output = operation()
        except Exception as exc:
            self.circuit_breaker.record_failure(now)
            return GovernedCallResult(status="failed", reason=str(exc))

        self.circuit_breaker.record_success()
        return GovernedCallResult(status="success", output=output)
