"""检索前后的权限过滤。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from langchain_core.documents import Document

from project_07_enterprise_rag.governance.metadata import parse_acl_tags


@dataclass(frozen=True)
class UserContext:
    """当前用户的最小权限上下文。"""

    user_id: str = "local-user"
    tenant_id: str = "default"
    roles: set[str] = field(default_factory=lambda: {"public"})

    @classmethod
    def from_values(
        cls,
        *,
        user_id: str = "local-user",
        tenant_id: str = "default",
        roles: str | Iterable[str] | None = None,
    ) -> "UserContext":
        if roles is None:
            role_set = {"public"}
        elif isinstance(roles, str):
            role_set = {item.strip() for item in roles.split(",") if item.strip()}
        else:
            role_set = {str(item).strip() for item in roles if str(item).strip()}
        if not role_set:
            role_set = {"public"}
        return cls(user_id=user_id, tenant_id=tenant_id, roles=role_set)


class AccessFilter:
    """基于 tenant_id 和 acl_tags 的最小权限过滤器。"""

    def can_access(self, doc: Document, user_context: UserContext) -> bool:
        metadata = doc.metadata or {}
        doc_tenant = metadata.get("tenant_id", "default")
        if doc_tenant != user_context.tenant_id:
            return False

        acl_tags = parse_acl_tags(metadata.get("acl_tags", "public"))
        if not acl_tags:
            return True
        if "public" in acl_tags:
            return True
        return bool(acl_tags & user_context.roles)

    def filter_docs(
        self,
        docs: Iterable[Document],
        user_context: UserContext,
    ) -> list[Document]:
        """过滤出当前用户可访问的文档。"""
        allowed_docs = []
        for doc in docs:
            if self.can_access(doc, user_context):
                allowed_docs.append(doc)
        return allowed_docs

