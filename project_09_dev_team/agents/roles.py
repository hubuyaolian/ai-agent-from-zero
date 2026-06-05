"""Agent 角色定义。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRole:
    """一个团队角色的职责和权限边界。"""

    name: str
    display_name: str
    responsibilities: tuple[str, ...]
    tools: tuple[str, ...]


def default_roles() -> dict[str, AgentRole]:
    """返回教学项目默认四角色。"""
    return {
        "planner": AgentRole(
            name="planner",
            display_name="规划Agent",
            responsibilities=("需求分析", "任务拆解", "接口设计"),
            tools=("list_files", "read_file", "emit_plan"),
        ),
        "developer": AgentRole(
            name="developer",
            display_name="开发Agent",
            responsibilities=("代码生成", "Bug 修复", "结构化产物输出"),
            tools=("read_file", "emit_artifact"),
        ),
        "tester": AgentRole(
            name="tester",
            display_name="测试Agent",
            responsibilities=("静态检查", "白名单测试", "质量门禁"),
            tools=("read_file", "run_tests"),
        ),
        "docwriter": AgentRole(
            name="docwriter",
            display_name="文档Agent",
            responsibilities=("README", "API 文档", "架构文档"),
            tools=("read_file", "emit_artifact"),
        ),
    }
