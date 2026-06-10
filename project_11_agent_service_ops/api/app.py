"""FastAPI 应用工厂。"""

from __future__ import annotations

from fastapi import FastAPI

from project_11_agent_service_ops.api.errors import register_exception_handlers
from project_11_agent_service_ops.api.routes import create_router
from project_11_agent_service_ops.config import ensure_runtime_dirs
from project_11_agent_service_ops.service import AgentService


def create_app() -> FastAPI:
    """创建 Agent 服务应用。"""
    ensure_runtime_dirs()
    service = AgentService.create_default()
    app = FastAPI(
        title="Project 11 Agent Service Ops",
        version="0.1.0",
        description="AI Agent 生产化服务与运维教学项目",
    )
    register_exception_handlers(app)
    app.include_router(create_router(service))
    return app


app = create_app()
