"""多格式文档加载器。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document

from project_07_enterprise_rag.config import DEFAULT_ACL_TAGS, DEFAULT_TENANT_ID
from project_07_enterprise_rag.governance.metadata import normalize_document_metadata


class DocumentLoaderFactory:
    """根据扩展名加载 PDF、DOCX、Markdown 和 TXT 文档。"""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}

    @classmethod
    def load(
        cls,
        file_path: str | os.PathLike,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        acl_tags: str | Iterable[str] = DEFAULT_ACL_TAGS,
        version: str = "v1",
    ) -> list[Document]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        if not path.is_file():
            raise ValueError(f"不是文件: {path}")

        ext = path.suffix.lower()
        if ext not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的格式: {ext}")

        if ext == ".pdf":
            docs = cls._load_pdf(path)
        elif ext == ".docx":
            docs = cls._load_docx(path)
        else:
            docs = cls._load_text(path)

        normalized_docs = []
        for doc in docs:
            metadata = normalize_document_metadata(
                str(path),
                doc.page_content,
                page=doc.metadata.get("page", ""),
                doc_format=ext.lstrip("."),
                tenant_id=tenant_id,
                acl_tags=acl_tags,
                version=version,
            )
            metadata.update(doc.metadata or {})
            metadata["source"] = os.path.abspath(str(path))
            metadata["tenant_id"] = tenant_id
            metadata["acl_tags"] = metadata.get("acl_tags") or DEFAULT_ACL_TAGS
            normalized_docs.append(Document(page_content=doc.page_content, metadata=metadata))
        return normalized_docs

    @classmethod
    def load_directory(
        cls,
        dir_path: str | os.PathLike,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        acl_tags: str | Iterable[str] = DEFAULT_ACL_TAGS,
        version: str = "v1",
    ) -> list[Document]:
        root = Path(dir_path)
        if not root.exists():
            raise FileNotFoundError(f"目录不存在: {root}")
        if not root.is_dir():
            raise ValueError(f"不是目录: {root}")

        docs: list[Document] = []
        for file_path in sorted(root.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in cls.SUPPORTED_EXTENSIONS:
                docs.extend(
                    cls.load(
                        file_path,
                        tenant_id=tenant_id,
                        acl_tags=acl_tags,
                        version=version,
                    )
                )
        return docs

    @staticmethod
    def _load_text(path: Path) -> list[Document]:
        content = path.read_text(encoding="utf-8")
        return [
            Document(
                page_content=content,
                metadata={
                    "source": os.path.abspath(str(path)),
                    "page": "",
                    "format": path.suffix.lower().lstrip("."),
                },
            )
        ]

    @staticmethod
    def _load_pdf(path: Path) -> list[Document]:
        try:
            from langchain_community.document_loaders import PyPDFLoader
        except ImportError as exc:
            raise ImportError("加载 PDF 需要安装 langchain-community 和 pypdf") from exc
        loader = PyPDFLoader(str(path))
        return loader.load()

    @staticmethod
    def _load_docx(path: Path) -> list[Document]:
        try:
            from langchain_community.document_loaders import Docx2txtLoader
        except ImportError as exc:
            raise ImportError("加载 DOCX 需要安装 langchain-community 和 docx2txt") from exc
        loader = Docx2txtLoader(str(path))
        return loader.load()

