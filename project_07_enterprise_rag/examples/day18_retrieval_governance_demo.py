"""Day 18: 检索与治理基础的本地演示脚本。

这个脚本不调用 LLM 和远端 Embedding，只演示企业级 RAG 的几个基础件：
- 文档加载与标题感知分块
- BM25 精确关键词检索
- 向量检索 + BM25 的 RRF 融合接口
- tenant_id + acl_tags 权限过滤
"""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from langchain_core.documents import Document

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from project_07_enterprise_rag.governance import UserContext
from project_07_enterprise_rag.governance.access_filter import AccessFilter
from project_07_enterprise_rag.governance.metadata import normalize_document_metadata
from project_07_enterprise_rag.ingestion import DocumentLoaderFactory, HybridChunker
from project_07_enterprise_rag.retrieval import HybridRetriever, KeywordSearcher


def make_document(
    source: str,
    content: str,
    *,
    tenant_id: str = "default",
    acl_tags: str = "public",
) -> Document:
    """构造带企业级 metadata 的教学文档。"""
    metadata = normalize_document_metadata(
        source,
        content,
        tenant_id=tenant_id,
        acl_tags=acl_tags,
        version="v1",
    )
    return Document(page_content=content, metadata=metadata)


class FakeVectorManager:
    """小型假向量检索器，用于演示 HybridRetriever 的融合接口。"""

    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.access_filter = AccessFilter()

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        *,
        user_context: UserContext | None = None,
    ) -> list[Document]:
        query = query.lower()
        scored: list[tuple[int, Document]] = []
        for doc in self.docs:
            content = doc.page_content.lower()
            score = 0
            if "sku" in query and "sku" in content:
                score += 3
            if "保修" in query and "保修" in content:
                score += 2
            if "年假" in query and "年假" in content:
                score += 3
            if "入职" in query and "入职" in content:
                score += 1
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        docs = [Document(page_content=doc.page_content, metadata=dict(doc.metadata)) for _, doc in scored]
        if user_context is not None:
            docs = self.access_filter.filter_docs(docs, user_context)
        return docs[:k]


def print_docs(step_title: str, docs: list[Document]) -> None:
    print(f"\n[{step_title}]")
    if not docs:
        print("无可见结果")
        return
    for index, doc in enumerate(docs, start=1):
        metadata = doc.metadata
        print(
            f"{index}. chunk_id={metadata.get('chunk_id')} "
            f"acl={metadata.get('acl_tags')} "
            f"tenant={metadata.get('tenant_id')} "
            f"rrf={metadata.get('rrf_score', '-')}"
        )
        print(f"   {doc.page_content[:80]}")


def main() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    day18_path = project_dir / "DAY18.md"

    print("=== Day 18 企业级 RAG：检索与治理基础演示 ===")

    loaded_docs = DocumentLoaderFactory.load(day18_path, tenant_id="default", acl_tags="public")
    day18_chunks = HybridChunker().split(loaded_docs)
    sample_chunk = day18_chunks[0]
    print("\n[1] 文档加载与标题感知分块")
    print(f"加载文档数: {len(loaded_docs)}")
    print(f"切分 chunk 数: {len(day18_chunks)}")
    print(f"样例 heading_path: {sample_chunk.metadata.get('heading_path')}")
    print(f"样例 chunk_id: {sample_chunk.metadata.get('chunk_id')}")

    sample_docs = [
        make_document(
            "employee_handbook.md",
            "# 员工手册\n## 年假制度\n员工入职满一年后，每年享有 15 天年假。",
            acl_tags="hr",
        ),
        make_document(
            "product_policy.md",
            "# 产品政策\n## SKU-2024-A\nSKU-2024-A 的保修周期为 12 个月。",
            acl_tags="public",
        ),
        make_document(
            "tenant_b_budget.md",
            "# 预算文件\nB 租户下一季度预算为 800 万元。",
            tenant_id="tenant-b",
            acl_tags="public",
        ),
    ]
    sample_chunks = HybridChunker(chunk_size=240, chunk_overlap=40).split(sample_docs)

    with TemporaryDirectory() as tmp_dir:
        keyword_searcher = KeywordSearcher(tmp_dir)
        keyword_searcher.index_documents(sample_chunks, "day18_demo")
        retriever = HybridRetriever(
            FakeVectorManager(sample_chunks),
            keyword_searcher,
            collection_name="day18_demo",
        )

        public_user = UserContext.from_values(tenant_id="default", roles="public")
        hr_user = UserContext.from_values(tenant_id="default", roles="public,hr")

        keyword_docs = keyword_searcher.search(
            "SKU-2024-A 的保修周期是什么？",
            k=3,
            collection_name="day18_demo",
            user_context=public_user,
        )
        print_docs("2. BM25 精确词召回：SKU-2024-A", keyword_docs)

        public_leave_docs = retriever.retrieve(
            "员工入职满一年后年假是多少天？",
            k=3,
            user_context=public_user,
        )
        print_docs("3. 权限过滤：public 用户查 HR 年假", public_leave_docs)

        hr_leave_docs = retriever.retrieve(
            "员工入职满一年后年假是多少天？",
            k=3,
            user_context=hr_user,
        )
        print_docs("4. 权限过滤：HR 用户查年假", hr_leave_docs)

        fused_docs = retriever.retrieve(
            "SKU-2024-A 的保修周期是什么？",
            k=3,
            user_context=public_user,
        )
        print_docs("5. RRF 融合检索结果", fused_docs)

    print("\n结论: Day 18 的重点不是让模型回答，而是先保证证据能被召回、能融合、能溯源、且不会越权。")


if __name__ == "__main__":
    main()
