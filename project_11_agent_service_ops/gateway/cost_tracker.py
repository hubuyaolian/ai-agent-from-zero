"""成本统计与预算控制。

真实生产系统通常从模型网关或账单平台拿 token 与费用。本课程用可预测的
估算器演示成本治理链路，便于离线测试。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time


def estimate_tokens(text: str) -> int:
    """用字符长度近似 token 数，保证测试可预测。"""
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, (len(stripped) + 3) // 4)


@dataclass(frozen=True)
class UsageRecord:
    """一次模型调用的费用记录。"""

    tenant_id: str
    model_name: str
    input_tokens: int
    output_tokens: int
    cost_cents: float
    timestamp: float = field(default_factory=time)


@dataclass(frozen=True)
class BudgetDecision:
    """预算检查结果。"""

    allowed: bool
    spent_cents: float
    estimated_cents: float
    budget_cents: float
    reason: str


class BudgetTracker:
    """按租户累计成本，并在调用前做预算判断。"""

    def __init__(self, daily_budget_cents: float) -> None:
        self.daily_budget_cents = daily_budget_cents
        self._records: list[UsageRecord] = []

    def spent_for_tenant(self, tenant_id: str) -> float:
        """返回租户当前累计费用。"""
        return sum(
            record.cost_cents for record in self._records if record.tenant_id == tenant_id
        )

    def check(self, tenant_id: str, estimated_cents: float) -> BudgetDecision:
        """检查本次调用是否会超过预算。"""
        spent = self.spent_for_tenant(tenant_id)
        projected = spent + estimated_cents
        if projected > self.daily_budget_cents:
            return BudgetDecision(
                allowed=False,
                spent_cents=round(spent, 6),
                estimated_cents=round(estimated_cents, 6),
                budget_cents=round(self.daily_budget_cents, 6),
                reason="预算不足，拒绝本次模型调用",
            )
        return BudgetDecision(
            allowed=True,
            spent_cents=round(spent, 6),
            estimated_cents=round(estimated_cents, 6),
            budget_cents=round(self.daily_budget_cents, 6),
            reason="预算充足",
        )

    def record(self, record: UsageRecord) -> None:
        """记录一次实际调用费用。"""
        self._records.append(record)

    def snapshot(self) -> dict[str, float]:
        """返回租户费用快照。"""
        result: dict[str, float] = {}
        for record in self._records:
            result.setdefault(record.tenant_id, 0.0)
            result[record.tenant_id] += record.cost_cents
        return {tenant_id: round(cost, 6) for tenant_id, cost in result.items()}
