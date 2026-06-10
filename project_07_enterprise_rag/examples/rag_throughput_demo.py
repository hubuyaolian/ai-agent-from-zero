"""RAG 吞吐量与瓶颈估算的可选教学示例。"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf


@dataclass(frozen=True)
class RAGStage:
    """RAG 流水线中的一个阶段。

    phase 相同的阶段代表可以并行执行，例如向量检索和 BM25 检索。
    """

    name: str
    latency_ms: float
    concurrency: int
    phase: int

    @property
    def capacity_qps(self) -> float:
        """估算该阶段理论吞吐：并发槽位 / 单次耗时。"""
        if self.latency_ms <= 0:
            return inf
        return self.concurrency * 1000 / self.latency_ms


@dataclass(frozen=True)
class Bottleneck:
    """按吞吐能力排序后的瓶颈视图。"""

    name: str
    phase: int
    latency_ms: float
    concurrency: int
    capacity_qps: float


def estimate_latency_ms(stages: list[RAGStage]) -> float:
    """估算单个请求端到端延迟。

    同一个 phase 内的阶段按并行处理计算，只取最慢阶段。
    不同 phase 之间按顺序相加。
    """
    phase_to_latency: dict[int, float] = {}
    for stage in stages:
        phase_to_latency[stage.phase] = max(
            phase_to_latency.get(stage.phase, 0),
            stage.latency_ms,
        )
    return sum(phase_to_latency[phase] for phase in sorted(phase_to_latency))


def estimate_pipeline_capacity_qps(stages: list[RAGStage]) -> float:
    """估算流水线吞吐上限，由最小阶段吞吐决定。"""
    if not stages:
        return 0
    return min(stage.capacity_qps for stage in stages)


def find_bottlenecks(stages: list[RAGStage], limit: int = 3) -> list[Bottleneck]:
    """找出吞吐能力最低的阶段。"""
    ordered = sorted(stages, key=lambda stage: stage.capacity_qps)
    return [
        Bottleneck(
            name=stage.name,
            phase=stage.phase,
            latency_ms=stage.latency_ms,
            concurrency=stage.concurrency,
            capacity_qps=stage.capacity_qps,
        )
        for stage in ordered[:limit]
    ]


def default_rag_profile(answer_generation_concurrency: int = 4) -> list[RAGStage]:
    """构造一个教学用 RAG profile。

    数字不是生产基准，只用于说明瓶颈分析方法。
    """
    return [
        RAGStage("intent_rewrite", latency_ms=800, concurrency=8, phase=1),
        RAGStage("vector_search", latency_ms=60, concurrency=32, phase=2),
        RAGStage("bm25_search", latency_ms=40, concurrency=32, phase=2),
        RAGStage("rrf_merge", latency_ms=5, concurrency=64, phase=3),
        RAGStage("reranker", latency_ms=300, concurrency=8, phase=4),
        RAGStage(
            "answer_generation",
            latency_ms=4000,
            concurrency=answer_generation_concurrency,
            phase=5,
        ),
        RAGStage("citation_check", latency_ms=80, concurrency=16, phase=6),
        RAGStage("quality_check", latency_ms=1000, concurrency=8, phase=7),
    ]
