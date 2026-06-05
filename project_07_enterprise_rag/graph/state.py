"""工作流状态定义。"""

from __future__ import annotations

from typing import TypedDict

from langchain_core.documents import Document

from project_07_enterprise_rag.governance.access_filter import UserContext


class EnterpriseRAGState(TypedDict, total=False):
    session_id: str
    query: str
    rewritten_query: str
    user_context: UserContext
    retrieval_plan: dict
    retrieved_docs: list[Document]
    reranked_docs: list[Document]
    source_map: dict
    answer: str
    citations: list[str]
    citation_check: dict
    quality_score: int
    quality_reason: str
    needs_retry: bool
    retry_count: int

    # --- 新增 Guardrail 安全持久状态 ---
    guardrail_blocked: bool      # 是否被安全防御阻断
    guardrail_reason: str        # 被阻断的具体说明
    input_was_masked: bool       # 输入是否曾被隐私脱敏掩码过滤


