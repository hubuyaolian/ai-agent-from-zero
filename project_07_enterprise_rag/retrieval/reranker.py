"""教学版重排器。"""

from __future__ import annotations

from langchain_core.documents import Document

from project_07_enterprise_rag.config import RERANK_THRESHOLD
from project_07_enterprise_rag.retrieval.keyword_search import tokenize


class LocalReranker:
    """无需额外模型调用的本地重排器。

    生产系统应替换为 Qwen3 Reranker、bge-reranker、Cohere Rerank 等专用模型。
    """

    def rerank(
        self,
        query: str,
        docs: list[Document],
        *,
        threshold: float = RERANK_THRESHOLD,
        top_k: int | None = None,
    ) -> list[Document]:
        query_tokens = set(tokenize(query))
        scored_docs = []
        for doc in docs:
            doc_tokens = set(tokenize(doc.page_content))
            overlap = len(query_tokens & doc_tokens)
            heading = str(doc.metadata.get("heading_path", ""))
            heading_overlap = len(query_tokens & set(tokenize(heading)))
            rrf_score = float(doc.metadata.get("rrf_score", 0.0))
            score = min(10.0, overlap * 1.5 + heading_overlap * 2.0 + rrf_score * 100)
            candidate = Document(page_content=doc.page_content, metadata=dict(doc.metadata))
            candidate.metadata["rerank_score"] = round(score, 3)
            if score >= threshold:
                scored_docs.append(candidate)

        scored_docs.sort(key=lambda item: item.metadata.get("rerank_score", 0.0), reverse=True)
        if top_k is not None:
            return scored_docs[:top_k]
        return scored_docs
