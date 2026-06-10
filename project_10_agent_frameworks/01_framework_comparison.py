"""主流 Agent 框架对比与选型入口脚本。

用法：
    python project_10_agent_frameworks/01_framework_comparison.py
    python project_10_agent_frameworks/01_framework_comparison.py --scenario rag
    python project_10_agent_frameworks/01_framework_comparison.py --interactive
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from project_10_agent_frameworks.examples.framework_selection_matrix import (  # noqa: E402
    FrameworkRecommendation,
    list_frameworks,
    recommend_frameworks,
)


SCENARIOS: dict[str, set[str]] = {
    "rag": {"rag_heavy", "data_connectors", "retrieval", "indexing"},
    "workflow": {"state_graph", "checkpoint", "human_in_loop", "long_running"},
    "openai": {"openai_native", "handoff", "guardrails", "tracing", "sandbox"},
    "typed": {"typed_output", "dependency_injection", "eval", "python"},
    "multi_agent": {"multi_agent", "research_multi_agent", "code_execution"},
    "team": {"role_team", "delegation", "business_automation", "multi_agent"},
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent 框架对比与选型演示")
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        help="使用预设场景直接输出推荐",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="通过终端问答选择需求标签",
    )
    args = parser.parse_args()

    print("主流 Agent 框架选型")
    print("=" * 40)
    print_framework_table()

    capabilities: set[str] = set()
    if args.scenario:
        capabilities = SCENARIOS[args.scenario]
        print(f"\n预设场景: {args.scenario}")
    elif args.interactive:
        capabilities = ask_capabilities()

    if capabilities:
        print_recommendations(recommend_frameworks(capabilities))


def print_framework_table() -> None:
    """打印简短框架对比表。"""
    print("\n框架概览:")
    for framework in list_frameworks():
        best_for = "、".join(framework.best_for[:2])
        print(f"- {framework.name:<20} [{framework.tier}] {best_for}")


def ask_capabilities() -> set[str]:
    """通过简单问答收集 capability tags。"""
    questions = [
        ("是否以 RAG / 文档问答 / 检索为核心？", {"rag_heavy", "retrieval"}),
        ("是否需要 checkpoint、人工审批或长程状态？", {"state_graph", "checkpoint"}),
        (
            "是否深度使用 OpenAI runtime、handoff 或 sandbox？",
            {"openai_native", "handoff"},
        ),
        ("是否要求强结构化输出和类型校验？", {"typed_output", "eval"}),
        ("是否是多 Agent 协作或代码执行实验？", {"multi_agent", "code_execution"}),
        ("是否是角色团队式业务自动化？", {"role_team", "business_automation"}),
    ]
    selected: set[str] = set()
    print("\n交互式选型，输入 y/n：")
    for question, tags in questions:
        answer = input(f"{question} ").strip().lower()
        if answer in {"y", "yes", "是"}:
            selected.update(tags)
    return selected


def print_recommendations(recommendations: list[FrameworkRecommendation]) -> None:
    """打印推荐结果。"""
    print("\n推荐结果:")
    if not recommendations:
        print("- 未提供需求标签，无法给出有效推荐。")
        return

    for index, item in enumerate(recommendations, start=1):
        matched = "、".join(item.matched_capabilities) or "无"
        print(f"{index}. {item.framework.name}  score={item.score}")
        print(f"   匹配能力: {matched}")
        print(f"   定位: {item.framework.positioning}")


if __name__ == "__main__":
    main()
