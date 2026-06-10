"""FastAPI 路由定义。"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from project_11_agent_service_ops.api.schemas import (
    ChatRequest,
    ChatResponse,
    EvalResponse,
    HealthResponse,
    MetricsResponse,
)
from project_11_agent_service_ops.service import AgentService


def create_router(service: AgentService) -> APIRouter:
    """创建绑定具体服务实例的路由。"""
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="agent-service-ops")

    @router.post("/chat", response_model=ChatResponse)
    def chat(
        request: ChatRequest,
        x_api_key: str | None = Header(default=None),
    ) -> ChatResponse:
        response = service.chat(
            api_key=x_api_key,
            message=request.message,
            preferred_model=request.preferred_model,
        )
        return ChatResponse(**response.__dict__)

    @router.post("/stream")
    def stream(
        request: ChatRequest,
        x_api_key: str | None = Header(default=None),
    ) -> StreamingResponse:
        response = service.chat(
            api_key=x_api_key,
            message=request.message,
            preferred_model=request.preferred_model,
        )

        def events() -> Iterator[str]:
            for chunk in _split_stream_text(response.answer):
                yield f"data: {chunk}\n\n"
            yield f"event: done\ndata: {response.run_id}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    @router.get("/metrics", response_model=MetricsResponse)
    def metrics(x_api_key: str | None = Header(default=None)) -> MetricsResponse:
        snapshot = service.metrics_snapshot(api_key=x_api_key)
        return MetricsResponse(**snapshot.__dict__)

    @router.post("/eval/smoke", response_model=EvalResponse)
    def smoke_eval(x_api_key: str | None = Header(default=None)) -> EvalResponse:
        result = service.smoke_eval(api_key=x_api_key)
        return EvalResponse(**result.__dict__)

    return router


def _split_stream_text(text: str) -> list[str]:
    """把演示回答拆成 SSE 片段。"""
    chunks = [chunk for chunk in text.replace("。", "。\n").splitlines() if chunk]
    return chunks or [text]
