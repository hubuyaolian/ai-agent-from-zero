"""Chroma 向量检索封装。"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from common.config import get_model_config
from project_07_enterprise_rag.config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL
from project_07_enterprise_rag.governance.access_filter import AccessFilter, UserContext


class VectorStoreManager:
    """ChromaDB 向量存储管理器。"""

    def __init__(
        self,
        persist_directory: str | Path = CHROMA_DIR,
        *,
        collection_name: str = COLLECTION_NAME,
        embedding_provider: str = "qwen",
        embedding_model: str = EMBEDDING_MODEL,
    ):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.access_filter = AccessFilter()
        self._vectorstore = None

    @property
    def vectorstore(self):
        if self._vectorstore is None:
            self._vectorstore = self._create_vectorstore()
        return self._vectorstore

    def add_documents(self, docs: list[Document]) -> None:
        if not docs:
            return
        ids = [doc.metadata["chunk_id"] for doc in docs]
        self.vectorstore.add_documents(docs, ids=ids)

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        *,
        user_context: UserContext | None = None,
    ) -> list[Document]:
        search_k = k * 4 if user_context is not None else k
        docs = self.vectorstore.similarity_search(query, k=search_k)
        if user_context is not None:
            docs = self.access_filter.filter_docs(docs, user_context)
        return docs[:k]

    def delete_by_doc_id(self, doc_id: str) -> int:
        data = self.vectorstore.get(where={"doc_id": doc_id})
        ids = data.get("ids", [])
        if ids:
            self.vectorstore.delete(ids=ids)
        return len(ids)

    def get_stats(self) -> dict:
        data = self.vectorstore.get()
        metadatas = data.get("metadatas", [])
        doc_ids = set()
        for metadata in metadatas:
            if metadata and metadata.get("doc_id"):
                doc_ids.add(metadata["doc_id"])
        return {"chunk_count": len(data.get("ids", [])), "document_count": len(doc_ids)}

    def _create_vectorstore(self):
        try:
            from langchain_chroma import Chroma
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise ImportError("向量检索需要安装 langchain-chroma 和 langchain-openai") from exc

        config = get_model_config(self.embedding_provider)
        if not config.get("api_key"):
            raise RuntimeError(
                f"缺少 {self.embedding_provider} API Key，无法创建 Embedding。"
                "请配置 .env，或只运行不需要向量化的离线模块。"
            )
        embeddings = OpenAIEmbeddings(
            model=self.embedding_model,
            base_url=config["base_url"],
            api_key=config["api_key"],
        )
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=embeddings,
            persist_directory=str(self.persist_directory),
        )

