"""FastAPI 全局异常映射。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from project_11_agent_service_ops.gateway.model_gateway import BudgetExceededError
from project_11_agent_service_ops.security.auth import AuthenticationError
from project_11_agent_service_ops.service import RateLimitedError


def register_exception_handlers(app: FastAPI) -> None:
    """注册服务异常到 HTTP 状态码的映射。"""

    @app.exception_handler(AuthenticationError)
    async def handle_auth_error(
        _request: Request,
        exc: AuthenticationError,
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(RateLimitedError)
    async def handle_rate_limit_error(
        _request: Request,
        exc: RateLimitedError,
    ) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    @app.exception_handler(BudgetExceededError)
    async def handle_budget_error(
        _request: Request,
        exc: BudgetExceededError,
    ) -> JSONResponse:
        return JSONResponse(status_code=402, content={"detail": str(exc)})
