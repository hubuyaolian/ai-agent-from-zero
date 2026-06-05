"""项目级配置。

这些默认值面向本地教学运行。生产环境应通过环境变量、配置中心或部署平台注入。
"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "runtime_data"
DOCS_DIR = DATA_DIR / "docs"
CHROMA_DIR = DATA_DIR / "chroma"
BM25_DIR = DATA_DIR / "bm25"
DB_PATH = DATA_DIR / "enterprise_rag.sqlite3"
AUDIT_DB_PATH = DATA_DIR / "audit_log.sqlite3"

COLLECTION_NAME = os.getenv("ENTERPRISE_RAG_COLLECTION", "enterprise_rag")
DEFAULT_TENANT_ID = os.getenv("ENTERPRISE_RAG_TENANT_ID", "default")
DEFAULT_ACL_TAGS = os.getenv("ENTERPRISE_RAG_ACL_TAGS", "public")

LLM_PROVIDER = os.getenv("ENTERPRISE_RAG_LLM_PROVIDER", "xiaomi mimo")
EMBEDDING_PROVIDER = os.getenv("ENTERPRISE_RAG_EMBEDDING_PROVIDER", "local")
EMBEDDING_MODEL = os.getenv("ENTERPRISE_RAG_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

CHUNK_SIZE = int(os.getenv("ENTERPRISE_RAG_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("ENTERPRISE_RAG_CHUNK_OVERLAP", "100"))
MIN_CHUNK_SIZE = int(os.getenv("ENTERPRISE_RAG_MIN_CHUNK_SIZE", "100"))

VECTOR_TOP_K = int(os.getenv("ENTERPRISE_RAG_VECTOR_TOP_K", "8"))
KEYWORD_TOP_K = int(os.getenv("ENTERPRISE_RAG_KEYWORD_TOP_K", "8"))
FINAL_TOP_K = int(os.getenv("ENTERPRISE_RAG_FINAL_TOP_K", "5"))
RRF_K = int(os.getenv("ENTERPRISE_RAG_RRF_K", "60"))
RERANK_THRESHOLD = float(os.getenv("ENTERPRISE_RAG_RERANK_THRESHOLD", "3.0"))
QUALITY_THRESHOLD = int(os.getenv("ENTERPRISE_RAG_QUALITY_THRESHOLD", "7"))
MAX_RETRY = int(os.getenv("ENTERPRISE_RAG_MAX_RETRY", "2"))


def ensure_runtime_dirs() -> None:
    """创建本项目运行所需的本地目录。"""
    for path in (DATA_DIR, DOCS_DIR, CHROMA_DIR, BM25_DIR):
        path.mkdir(parents=True, exist_ok=True)

