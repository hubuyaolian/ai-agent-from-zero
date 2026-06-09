"""Agentic RAG 可选示例测试。"""

from __future__ import annotations

import unittest

from project_07_enterprise_rag.examples.agentic_rag_demo import (
    AgenticRAGDemo,
    InMemoryKeywordRetriever,
    KnowledgeChunk,
)


class AgenticRAGExampleTest(unittest.TestCase):
    def test_decomposes_complex_question_and_collects_evidence(self) -> None:
        retriever = InMemoryKeywordRetriever(
            [
                KnowledgeChunk("A", "产品 A 的核心供应商是华东制造一厂。"),
                KnowledgeChunk("B", "产品 B 的核心供应商是北方零件二厂。"),
                KnowledgeChunk("C", "产品 C 只用于内部测试。"),
            ]
        )
        demo = AgenticRAGDemo(retriever=retriever, max_steps=4)

        result = demo.answer("产品 A 和产品 B 分别由哪些供应商负责？")

        self.assertFalse(result.refused)
        self.assertEqual(result.subquestions, ["产品 A 供应商", "产品 B 供应商"])
        self.assertIn("华东制造一厂", result.answer)
        self.assertIn("北方零件二厂", result.answer)
        self.assertEqual([item.chunk_id for item in result.evidence], ["A", "B"])
        self.assertLessEqual(len(result.trace), 4)

    def test_refuses_when_evidence_is_missing(self) -> None:
        retriever = InMemoryKeywordRetriever(
            [KnowledgeChunk("A", "产品 A 的供应商是华东制造一厂。")]
        )
        demo = AgenticRAGDemo(retriever=retriever, max_steps=3)

        result = demo.answer("产品 A 和产品 Z 分别由哪些供应商负责？")

        self.assertTrue(result.refused)
        self.assertIn("产品 Z 供应商", result.missing_evidence)
        self.assertIn("证据不足", result.answer)


if __name__ == "__main__":
    unittest.main()
