"""工作流图入口。"""

from __future__ import annotations

from project_08_workflow_agent.executor.workflow_engine import WorkflowEngine
from project_08_workflow_agent.tools.registry import create_registry


def create_workflow_engine() -> WorkflowEngine:
    """创建本地工作流引擎；生产版可在这里切换为 LangGraph 实现。"""
    registry = create_registry()
    return WorkflowEngine(registry=registry)
