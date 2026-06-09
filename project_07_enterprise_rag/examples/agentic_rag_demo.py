"""Agentic RAG 可选教学示例。

这个示例刻意不接真实 LLM 和向量库，只演示生产系统需要保留的
决策边界：查询拆解、检索循环、证据检查和最大步数。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class KnowledgeChunk:
    """内存知识片段。"""

    chunk_id: str
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalTrace:
    """一次检索决策记录。"""

    step: int
    query: str
    found_chunk_ids: list[str]


@dataclass(frozen=True)
class AgenticRAGResult:
    """Agentic RAG 示例输出。"""

    answer: str
    evidence: list[KnowledgeChunk]
    subquestions: list[str]
    missing_evidence: list[str]
    trace: list[RetrievalTrace]
    refused: bool = False


class InMemoryKeywordRetriever:
    """极简关键词检索器，用于演示多次检索决策。"""

    def __init__(self, chunks: list[KnowledgeChunk]):
        self.chunks = chunks

    def search(self, query: str, *, k: int = 2) -> list[KnowledgeChunk]:
        query_terms = self._terms(query)
        required_products = [term for term in query_terms if term.startswith("产品")]
        scored: list[tuple[int, KnowledgeChunk]] = []
        for chunk in self.chunks:
            normalized_content = re.sub(r"\s+", "", chunk.content.upper())
            has_required_products = all(
                product in normalized_content
                for product in required_products
            )
            if required_products and not has_required_products:
                continue
            content_terms = self._terms(chunk.content)
            score = sum(
                1
                for term in query_terms
                if term in content_terms or term in normalized_content
            )
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[:k]]

    @staticmethod
    def _terms(text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text.upper())
        terms = re.findall(r"产品\s*[A-Z]|[A-Z]\d*|[\u4e00-\u9fff]+", normalized)
        return [term.replace(" ", "") for term in terms]


class AgenticRAGDemo:
    """受控的 Agentic RAG 教学流程。"""

    def __init__(self, retriever: InMemoryKeywordRetriever, *, max_steps: int = 4):
        self.retriever = retriever
        self.max_steps = max_steps

    def answer(self, question: str) -> AgenticRAGResult:
        subquestions = self._decompose(question)
        evidence: list[KnowledgeChunk] = []
        trace: list[RetrievalTrace] = []
        missing: list[str] = []
        seen_chunk_ids: set[str] = set()

        for step, subquestion in enumerate(subquestions, start=1):
            if step > self.max_steps:
                missing.append(f"{subquestion}（超过最大步数）")
                continue

            chunks = self.retriever.search(subquestion, k=1)
            trace.append(
                RetrievalTrace(
                    step=step,
                    query=subquestion,
                    found_chunk_ids=[chunk.chunk_id for chunk in chunks],
                )
            )
            if not chunks:
                missing.append(subquestion)
                continue

            chunk = chunks[0]
            if chunk.chunk_id not in seen_chunk_ids:
                evidence.append(chunk)
                seen_chunk_ids.add(chunk.chunk_id)

        if missing:
            return AgenticRAGResult(
                answer=f"证据不足，无法可靠回答：{', '.join(missing)}",
                evidence=evidence,
                subquestions=subquestions,
                missing_evidence=missing,
                trace=trace,
                refused=True,
            )

        answer = "；".join(chunk.content for chunk in evidence)
        return AgenticRAGResult(
            answer=answer,
            evidence=evidence,
            subquestions=subquestions,
            missing_evidence=[],
            trace=trace,
        )

    @staticmethod
    def _decompose(question: str) -> list[str]:
        product_ids = []
        for match in re.findall(r"产品\s*([A-Za-z])", question):
            product = f"产品 {match.upper()}"
            if product not in product_ids:
                product_ids.append(product)
        if len(product_ids) >= 2 and "供应商" in question:
            return [f"{product} 供应商" for product in product_ids]
        return [question.strip()]


def main() -> None:
    """运行一个本地演示。"""
    retriever = InMemoryKeywordRetriever(
        [
            KnowledgeChunk("A", "产品 A 的核心供应商是华东制造一厂。"),
            KnowledgeChunk("B", "产品 B 的核心供应商是北方零件二厂。"),
        ]
    )
    result = AgenticRAGDemo(retriever).answer(
        "产品 A 和产品 B 分别由哪些供应商负责？"
    )
    print(result.answer)


if __name__ == "__main__":
    main()
