"""HTTP API 请求与响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求。"""

    message: str = Field(min_length=1, description="用户输入")
    preferred_model: str | None = Field(default=None, description="首选模型名")


class ChatResponse(BaseModel):
    """聊天响应。"""

    run_id: str
    answer: str
    model_name: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_cents: float
    fallback_used: bool
    route_reason: str


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str
    service: str


class MetricsResponse(BaseModel):
    """指标响应。"""

    request_count: int
    error_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_cents: float
    average_latency_ms: float
    model_calls: dict[str, int]


class EvalResponse(BaseModel):
    """冒烟评估响应。"""

    total: int
    passed: int
    failed_questions: tuple[str, ...]
    score: float
