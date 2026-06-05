"""治理模块：metadata、权限过滤和审计。"""

from project_07_enterprise_rag.governance.access_filter import AccessFilter, UserContext
from project_07_enterprise_rag.governance.guardrail import GuardrailManager
from project_07_enterprise_rag.governance.metadata import (
    build_chunk_id,
    compute_content_hash,
    normalize_acl_tags,
    normalize_document_metadata,
    parse_acl_tags,
)

__all__ = [
    "AccessFilter",
    "UserContext",
    "GuardrailManager",
    "build_chunk_id",
    "compute_content_hash",
    "normalize_acl_tags",
    "normalize_document_metadata",
    "parse_acl_tags",
]


