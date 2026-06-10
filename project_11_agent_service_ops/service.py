"""Agent 服务运行时编排。

这个类是 FastAPI 和核心治理模块之间的边界：接口层只负责 HTTP，
服务层负责鉴权、限流、模型网关、trace、metrics 和 eval。
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from project_11_agent_service_ops.config import (
    DAILY_BUDGET_CENTS,
    RATE_LIMIT_CAPACITY,
    RATE_LIMIT_REFILL_PER_SECOND,
)
from project_11_agent_service_ops.evaluation.smoke_eval import (
    SmokeEvalResult,
    SmokeEvaluator,
)
from project_11_agent_service_ops.gateway.cost_tracker import BudgetTracker
from project_11_agent_service_ops.gateway.model_gateway import (
    BudgetExceededError,
    GatewayResponse,
    ModelGateway,
    default_routes,
)
from project_11_agent_service_ops.observability.metrics import (
    MetricsRegistry,
    MetricsSnapshot,
)
from project_11_agent_service_ops.observability.tracing import TraceRecorder
from project_11_agent_service_ops.security.auth import APIKeyAuthenticator
from project_11_agent_service_ops.security.rate_limiter import TenantRateLimiter


class RateLimitedError(RuntimeError):
    """请求触发限流。"""


@dataclass(frozen=True)
class ServiceResponse:
    """服务层返回给接口层的标准响应。"""

    run_id: str
    answer: str
    model_name: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_cents: float
    fallback_used: bool
    route_reason: str


class AgentService:
    """Agent 生产服务的最小闭环。"""

    def __init__(
        self,
        authenticator: APIKeyAuthenticator,
        rate_limiter: TenantRateLimiter,
        gateway: ModelGateway,
        metrics: MetricsRegistry,
        traces: TraceRecorder,
    ) -> None:
        self.authenticator = authenticator
        self.rate_limiter = rate_limiter
        self.gateway = gateway
        self.metrics = metrics
        self.traces = traces

    @classmethod
    def create_default(cls) -> "AgentService":
        """构造本地教学服务。"""
        budget_tracker = BudgetTracker(daily_budget_cents=DAILY_BUDGET_CENTS)
        return cls(
            authenticator=APIKeyAuthenticator.from_config(),
            rate_limiter=TenantRateLimiter(
                capacity=RATE_LIMIT_CAPACITY,
                refill_per_second=RATE_LIMIT_REFILL_PER_SECOND,
            ),
            gateway=ModelGateway(default_routes(), budget_tracker),
            metrics=MetricsRegistry(),
            traces=TraceRecorder(),
        )

    def chat(
        self,
        api_key: str | None,
        message: str,
        preferred_model: str | None = None,
    ) -> ServiceResponse:
        """执行一次受治理的 Agent 请求。"""
        started = perf_counter()
        run_id = self.traces.new_run_id()

        try:
            context = self.authenticator.authenticate(api_key)
            self.authenticator.require_scope(context, "chat")
            self.traces.record(
                run_id,
                "auth.accepted",
                {"tenant_id": context.tenant_id, "user_id": context.user_id},
            )

            decision = self.rate_limiter.allow(context.tenant_id)
            self.traces.record(
                run_id,
                "rate_limit.checked",
                {"allowed": decision.allowed, "remaining": decision.remaining_tokens},
            )
            if not decision.allowed:
                raise RateLimitedError(decision.reason)

            gateway_response = self.gateway.generate(
                prompt=message,
                tenant_id=context.tenant_id,
                preferred_model=preferred_model,
            )
            self.traces.record(
                run_id,
                "model_gateway.completed",
                {
                    "model": gateway_response.model_name,
                    "fallback_used": gateway_response.fallback_used,
                    "cost_cents": gateway_response.cost_cents,
                },
            )
            self._record_success(gateway_response, started)
            return ServiceResponse(
                run_id=run_id,
                answer=gateway_response.text,
                model_name=gateway_response.model_name,
                provider=gateway_response.provider,
                input_tokens=gateway_response.input_tokens,
                output_tokens=gateway_response.output_tokens,
                cost_cents=gateway_response.cost_cents,
                fallback_used=gateway_response.fallback_used,
                route_reason=gateway_response.route_reason,
            )
        except (BudgetExceededError, RateLimitedError, RuntimeError):
            self.metrics.record_error()
            self.traces.record(run_id, "request.failed", {})
            raise

    def metrics_snapshot(self, api_key: str | None) -> MetricsSnapshot:
        """返回服务指标。"""
        context = self.authenticator.authenticate(api_key)
        self.authenticator.require_scope(context, "metrics")
        return self.metrics.snapshot()

    def smoke_eval(self, api_key: str | None) -> SmokeEvalResult:
        """运行线上冒烟评估。"""
        context = self.authenticator.authenticate(api_key)
        self.authenticator.require_scope(context, "eval")
        evaluator = SmokeEvaluator(self.gateway)
        return evaluator.run(tenant_id=context.tenant_id)

    def _record_success(
        self,
        gateway_response: GatewayResponse,
        started: float,
    ) -> None:
        latency_ms = (perf_counter() - started) * 1000
        self.metrics.record_success(
            model_name=gateway_response.model_name,
            input_tokens=gateway_response.input_tokens,
            output_tokens=gateway_response.output_tokens,
            cost_cents=gateway_response.cost_cents,
            latency_ms=latency_ms,
        )
