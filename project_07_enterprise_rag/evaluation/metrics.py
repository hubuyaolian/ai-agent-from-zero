"""RAG 检索指标。"""

from __future__ import annotations

from langchain_core.documents import Document


def recall_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int) -> float:
    if not gold_ids:
        return 0.0
    retrieved_set = set(retrieved_ids[:k])
    gold_set = set(gold_ids)
    return len(retrieved_set & gold_set) / len(gold_set)


def mrr(retrieved_ids: list[str], gold_ids: list[str]) -> float:
    gold_set = set(gold_ids)
    for index, chunk_id in enumerate(retrieved_ids):
        if chunk_id in gold_set:
            return 1.0 / (index + 1)
    return 0.0


def evaluate_retrieval(cases: list[dict], retrieval_results: list[list[Document]], k: int = 5) -> dict:
    recalls = []
    reciprocal_ranks = []
    for case, docs in zip(cases, retrieval_results):
        retrieved_ids = [doc.metadata.get("chunk_id", "") for doc in docs]
        gold_ids = case.get("gold_chunk_ids", [])
        recalls.append(recall_at_k(retrieved_ids, gold_ids, k))
        reciprocal_ranks.append(mrr(retrieved_ids, gold_ids))
    if not cases:
        return {"recall_at_k": 0.0, "mrr": 0.0, "case_count": 0}
    return {
        "recall_at_k": sum(recalls) / len(recalls),
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks),
        "case_count": len(cases),
    }

