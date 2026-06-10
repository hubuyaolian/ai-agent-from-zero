"""把前面课程项目映射到 Agent 框架能力。"""

from __future__ import annotations

from dataclasses import dataclass

from project_10_agent_frameworks.examples.framework_selection_matrix import (
    FrameworkRecommendation,
    recommend_frameworks,
)


@dataclass(frozen=True)
class ProjectFrameworkMapping:
    """课程项目到框架推荐的映射结果。"""

    project: str
    capabilities: frozenset[str]
    recommendations: tuple[FrameworkRecommendation, ...]
    explanation: str


_PROJECT_CAPABILITIES: dict[str, frozenset[str]] = {
    "project_07_enterprise_rag": frozenset(
        {
            "rag_heavy",
            "data_connectors",
            "retrieval",
            "indexing",
            "rag_workflow",
            "checkpoint",
        }
    ),
    "project_08_workflow_agent": frozenset(
        {
            "state_graph",
            "checkpoint",
            "human_in_loop",
            "long_running",
            "workflow",
            "guardrails",
            "tracing",
        }
    ),
    "project_09_dev_team": frozenset(
        {
            "multi_agent",
            "research_multi_agent",
            "role_team",
            "code_execution",
            "long_running",
            "human_in_loop",
        }
    ),
}


def map_project_to_frameworks(project: str) -> ProjectFrameworkMapping:
    """根据课程项目能力标签推荐合适框架。"""
    capabilities = _PROJECT_CAPABILITIES.get(project)
    if capabilities is None:
        raise KeyError(f"未知课程项目: {project}")

    recommendations = tuple(recommend_frameworks(set(capabilities), limit=3))
    explanation = (
        f"{project} 是课程项目，不是要求迁移到某个框架；"
        "这里的推荐用于理解能力映射和生产化取舍。"
    )
    return ProjectFrameworkMapping(
        project=project,
        capabilities=capabilities,
        recommendations=recommendations,
        explanation=explanation,
    )
