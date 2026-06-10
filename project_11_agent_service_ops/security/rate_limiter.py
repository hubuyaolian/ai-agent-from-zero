"""令牌桶限流。"""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True)
class RateLimitDecision:
    """一次限流判断结果。"""

    allowed: bool
    remaining_tokens: float
    retry_after_seconds: float
    reason: str


class TokenBucket:
    """单个租户或用户的令牌桶。"""

    def __init__(self, capacity: int, refill_per_second: float) -> None:
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.tokens = float(capacity)
        self.updated_at = monotonic()

    def allow(self, cost: float = 1.0, now: float | None = None) -> RateLimitDecision:
        """尝试消耗令牌。"""
        current = monotonic() if now is None else now
        elapsed = max(0.0, current - self.updated_at)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)
        self.updated_at = current

        if self.tokens >= cost:
            self.tokens -= cost
            return RateLimitDecision(
                allowed=True,
                remaining_tokens=round(self.tokens, 6),
                retry_after_seconds=0.0,
                reason="允许调用",
            )

        missing = cost - self.tokens
        retry_after = missing / self.refill_per_second if self.refill_per_second > 0 else 0.0
        return RateLimitDecision(
            allowed=False,
            remaining_tokens=round(self.tokens, 6),
            retry_after_seconds=round(retry_after, 6),
            reason="请求过快，触发限流",
        )


class TenantRateLimiter:
    """按租户维护令牌桶。"""

    def __init__(self, capacity: int, refill_per_second: float) -> None:
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self._buckets: dict[str, TokenBucket] = {}

    def allow(self, tenant_id: str, now: float | None = None) -> RateLimitDecision:
        """检查租户是否允许继续调用。"""
        bucket = self._buckets.setdefault(
            tenant_id,
            TokenBucket(
                capacity=self.capacity,
                refill_per_second=self.refill_per_second,
            ),
        )
        return bucket.allow(now=now)
