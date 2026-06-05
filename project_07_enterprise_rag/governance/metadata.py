"""文档和 chunk metadata 工具。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterable


def compute_content_hash(content: str) -> str:
    """计算文本内容 hash，便于去重、更新检测和 chunk 稳定编号。"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def normalize_acl_tags(tags: str | Iterable[str] | None) -> str:
    """将 ACL 标签统一为逗号分隔字符串，兼容 Chroma metadata 限制。"""
    if tags is None:
        return "public"
    if isinstance(tags, str):
        raw_tags = tags.split(",")
    else:
        raw_tags = list(tags)
    clean_tags = []
    for tag in raw_tags:
        clean = str(tag).strip()
        if clean:
            clean_tags.append(clean)
    if not clean_tags:
        return "public"
    return ",".join(sorted(set(clean_tags)))


def parse_acl_tags(tags: str | Iterable[str] | None) -> set[str]:
    """将 metadata 中的 ACL 标签解析为集合。"""
    if tags is None:
        return set()
    if isinstance(tags, str):
        return {item.strip() for item in tags.split(",") if item.strip()}
    return {str(item).strip() for item in tags if str(item).strip()}


def build_doc_id(source: str, content_hash: str, version: str = "v1") -> str:
    """生成稳定文档 ID。"""
    file_stem = Path(source).stem or "document"
    safe_stem = "".join(ch if ch.isalnum() else "_" for ch in file_stem).strip("_")
    return f"{safe_stem}:{version}:{content_hash[:8]}"


def build_chunk_id(doc_id: str, content_hash: str, chunk_index: int) -> str:
    """生成稳定 chunk ID。"""
    return f"{doc_id}:chunk_{chunk_index:04d}:{content_hash[:8]}"


def normalize_document_metadata(
    source: str,
    content: str,
    *,
    page: int | str = "",
    doc_format: str | None = None,
    tenant_id: str = "default",
    acl_tags: str | Iterable[str] | None = None,
    version: str = "v1",
) -> dict:
    """为加载后的 Document 生成标准 metadata。"""
    absolute_source = os.path.abspath(source)
    content_hash = compute_content_hash(content)
    final_format = doc_format or Path(source).suffix.lower().lstrip(".")
    return {
        "doc_id": build_doc_id(absolute_source, content_hash, version),
        "source": absolute_source,
        "page": page,
        "format": final_format,
        "content_hash": content_hash,
        "version": version,
        "tenant_id": tenant_id,
        "acl_tags": normalize_acl_tags(acl_tags),
    }

