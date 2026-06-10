"""RAG 吞吐量估算可选示例测试。"""

from __future__ import annotations

import unittest

from project_07_enterprise_rag.examples.rag_throughput_demo import (
    RAGStage,
    default_rag_profile,
    estimate_latency_ms,
    estimate_pipeline_capacity_qps,
    find_bottlenecks,
)


class RAGThroughputExampleTest(unittest.TestCase):
    def test_parallel_retrieval_uses_slowest_stage_latency(self) -> None:
        stages = [
            RAGStage("rewrite", latency_ms=300, concurrency=8, phase=1),
            RAGStage("vector_search", latency_ms=60, concurrency=32, phase=2),
            RAGStage("bm25_search", latency_ms=40, concurrency=32, phase=2),
            RAGStage("answer_generation", latency_ms=1200, concurrency=4, phase=3),
        ]

        self.assertEqual(estimate_latency_ms(stages), 1560)

    def test_answer_generation_is_default_bottleneck(self) -> None:
        profile = default_rag_profile()

        bottlenecks = find_bottlenecks(profile, limit=2)

        self.assertEqual(bottlenecks[0].name, "answer_generation")
        self.assertLess(
            estimate_pipeline_capacity_qps(profile),
            bottlenecks[1].capacity_qps,
        )

    def test_increasing_bottleneck_concurrency_raises_capacity(self) -> None:
        baseline = default_rag_profile(answer_generation_concurrency=4)
        scaled = default_rag_profile(answer_generation_concurrency=16)

        self.assertGreater(
            estimate_pipeline_capacity_qps(scaled),
            estimate_pipeline_capacity_qps(baseline),
        )


if __name__ == "__main__":
    unittest.main()
