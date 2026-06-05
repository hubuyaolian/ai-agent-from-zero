"""向量 + BM25 + RRF 混合检索。"""

from __future__ import annotations

from langchain_core.documents import Document

from project_07_enterprise_rag.config import FINAL_TOP_K, KEYWORD_TOP_K, RRF_K, VECTOR_TOP_K
from project_07_enterprise_rag.governance.access_filter import UserContext


class HybridRetriever:
    """多路召回 + RRF 融合检索器。"""

    def __init__(
        self,
        vector_manager,
        keyword_searcher,
        *,
        rrf_k: int = RRF_K,
        collection_name: str = "default",
    ):
        self.vector_manager = vector_manager
        self.keyword_searcher = keyword_searcher
        self.rrf_k = rrf_k
        self.collection_name = collection_name

    def retrieve(
        self,
        query: str,
        *,
        k: int = FINAL_TOP_K,
        vector_k: int = VECTOR_TOP_K,
        keyword_k: int = KEYWORD_TOP_K,
        query_variants: list[str] | None = None,
        user_context: UserContext | None = None,
    ) -> list[Document]:
        queries = [query]
        if query_variants:
            queries.extend(query_variants)

        vector_docs: list[Document] = []
        keyword_docs: list[Document] = []
        for one_query in queries:
            try:
                vector_docs.extend(
                    self.vector_manager.similarity_search(
                        one_query,
                        k=vector_k,
                        user_context=user_context,
                    )
                )
            except RuntimeError:
                # 缺少 API Key 时仍允许 BM25-only 教学检索。
                pass
            keyword_docs.extend(
                self.keyword_searcher.search(
                    one_query,
                    k=keyword_k,
                    collection_name=self.collection_name,
                    user_context=user_context,
                )
            )
        return self._rrf_fuse(vector_docs, keyword_docs, k)

    def _rrf_fuse(
        self,
        vector_docs: list[Document],
        keyword_docs: list[Document],
        k: int,
    ) -> list[Document]:
        scores: dict[str, float] = {}
        docs_by_id: dict[str, Document] = {}

        for rank, doc in enumerate(vector_docs):
            chunk_id = doc.metadata.get("chunk_id")
            if not chunk_id:
                continue
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (self.rrf_k + rank + 1)
            docs_by_id[chunk_id] = doc

        for rank, doc in enumerate(keyword_docs):
            chunk_id = doc.metadata.get("chunk_id")
            if not chunk_id:
                continue
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (self.rrf_k + rank + 1)
            docs_by_id[chunk_id] = doc

        ranked_ids = sorted(scores.keys(), key=lambda item: scores[item], reverse=True)
        fused_docs = []
        for chunk_id in ranked_ids[:k]:
            doc = Document(
                page_content=docs_by_id[chunk_id].page_content,
                metadata=dict(docs_by_id[chunk_id].metadata),
            )
            doc.metadata["rrf_score"] = scores[chunk_id]
            fused_docs.append(doc)
        return fused_docs

