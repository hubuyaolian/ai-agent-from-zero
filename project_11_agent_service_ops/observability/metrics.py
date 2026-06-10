"""服务指标统计。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricsSnapshot:
    """当前服务指标快照。"""

    request_count: int
    error_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_cents: float
    average_latency_ms: float
    model_calls: dict[str, int]


class MetricsRegistry:
    """内存指标注册表。"""

    def __init__(self) -> None:
        self.request_count = 0
        self.error_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_cents = 0.0
        self.latencies_ms: list[float] = []
        self.model_calls: dict[str, int] = {}

    def record_success(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost_cents: float,
        latency_ms: float,
    ) -> None:
        """记录一次成功请求。"""
        self.request_count += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_cents += cost_cents
        self.latencies_ms.append(latency_ms)
        self.model_calls[model_name] = self.model_calls.get(model_name, 0) + 1

    def record_error(self) -> None:
        """记录一次失败请求。"""
        self.request_count += 1
        self.error_count += 1

    def snapshot(self) -> MetricsSnapshot:
        """返回当前指标快照。"""
        avg_latency = (
            sum(self.latencies_ms) / len(self.latencies_ms) if self.latencies_ms else 0.0
        )
        return MetricsSnapshot(
            request_count=self.request_count,
            error_count=self.error_count,
            total_input_tokens=self.total_input_tokens,
            total_output_tokens=self.total_output_tokens,
            total_cost_cents=round(self.total_cost_cents, 6),
            average_latency_ms=round(avg_latency, 3),
            model_calls=dict(self.model_calls),
        )
