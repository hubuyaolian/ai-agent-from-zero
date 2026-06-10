"""Agent 框架选型示例测试。"""

from __future__ import annotations

import subprocess
import sys
import unittest

from project_10_agent_frameworks.examples.agent_capability_mapper import (
    map_project_to_frameworks,
)
from project_10_agent_frameworks.examples.framework_selection_matrix import (
    get_framework,
    list_capability_definitions,
    list_frameworks,
    recommend_frameworks,
)


class FrameworkSelectionTest(unittest.TestCase):
    def test_lists_core_and_research_frameworks(self) -> None:
        names = {framework.name for framework in list_frameworks()}

        self.assertIn("LangGraph", names)
        self.assertIn("OpenAI Agents SDK", names)
        self.assertIn("PydanticAI", names)
        self.assertIn("AutoGen", names)
        self.assertIn("AgentScope", names)
        self.assertIn("CAMEL", names)

    def test_langgraph_is_best_for_stateful_long_running_workflow(self) -> None:
        recommendations = recommend_frameworks(
            {"state_graph", "checkpoint", "human_in_loop", "long_running"}
        )

        self.assertEqual(recommendations[0].framework.name, "LangGraph")
        self.assertIn("checkpoint", recommendations[0].matched_capabilities)

    def test_openai_agents_sdk_is_best_for_openai_native_runtime(self) -> None:
        recommendations = recommend_frameworks(
            {"openai_native", "handoff", "guardrails", "tracing", "sandbox"}
        )

        self.assertEqual(recommendations[0].framework.name, "OpenAI Agents SDK")
        self.assertIn("handoff", recommendations[0].matched_capabilities)

    def test_pydanticai_is_best_for_type_safe_business_outputs(self) -> None:
        recommendations = recommend_frameworks(
            {"typed_output", "dependency_injection", "eval", "python"}
        )

        self.assertEqual(recommendations[0].framework.name, "PydanticAI")
        self.assertIn("typed_output", recommendations[0].matched_capabilities)

    def test_llamaindex_is_best_for_rag_heavy_agent(self) -> None:
        recommendations = recommend_frameworks(
            {"rag_heavy", "data_connectors", "retrieval", "indexing"}
        )

        self.assertEqual(recommendations[0].framework.name, "LlamaIndex Agents")

    def test_framework_lookup_exposes_tier_and_positioning(self) -> None:
        camel = get_framework("CAMEL")

        self.assertEqual(camel.tier, "research")
        self.assertIn("role_playing", camel.capabilities)

    def test_maps_existing_course_projects_to_frameworks(self) -> None:
        p07 = map_project_to_frameworks("project_07_enterprise_rag")
        p08 = map_project_to_frameworks("project_08_workflow_agent")
        p09 = map_project_to_frameworks("project_09_dev_team")

        self.assertEqual(p07.recommendations[0].framework.name, "LlamaIndex Agents")
        self.assertEqual(p08.recommendations[0].framework.name, "LangGraph")
        self.assertIn(
            p09.recommendations[0].framework.name,
            {"AutoGen", "CrewAI", "LangGraph"},
        )
        self.assertIn("课程项目", p09.explanation)

    def test_empty_capabilities_return_no_recommendations(self) -> None:
        self.assertEqual(recommend_frameworks(set()), [])

    def test_unknown_project_raises_key_error(self) -> None:
        with self.assertRaisesRegex(KeyError, "未知课程项目"):
            map_project_to_frameworks("project_unknown")

    def test_limit_zero_returns_no_recommendations(self) -> None:
        self.assertEqual(recommend_frameworks({"python"}, limit=0), [])

    def test_equal_score_keeps_catalog_order(self) -> None:
        recommendations = recommend_frameworks({"python"}, limit=3)

        self.assertEqual(
            [item.framework.name for item in recommendations],
            ["LangGraph", "OpenAI Agents SDK", "PydanticAI"],
        )

    def test_capability_definitions_cover_common_tags(self) -> None:
        definitions = list_capability_definitions()

        self.assertEqual(
            definitions["state_graph"],
            "用显式状态、节点和边编排 Agent 工作流。",
        )
        self.assertIn("RAG", definitions["rag_heavy"])

    def test_entry_script_prints_recommendations(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "project_10_agent_frameworks/01_framework_comparison.py",
                "--scenario",
                "rag",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("主流 Agent 框架选型", completed.stdout)
        self.assertIn("LlamaIndex Agents", completed.stdout)


if __name__ == "__main__":
    unittest.main()
