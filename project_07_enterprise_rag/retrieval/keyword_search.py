"""BM25 关键词检索。"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document

from project_07_enterprise_rag.config import BM25_DIR
from project_07_enterprise_rag.governance.access_filter import AccessFilter, UserContext


def tokenize(text: str) -> list[str]:
    """中文优先使用 jieba，缺失时退回正则 token。"""
    try:
        import jieba

        base_tokens = [token.strip().lower() for token in jieba.cut(text) if token.strip()]
    except ImportError:
        base_tokens = re.findall(r"[\w-]+", text.lower())

    expanded_tokens = list(base_tokens)
    chinese_segments = re.findall(r"[\u4e00-\u9fff]+", text)
    for segment in chinese_segments:
        if len(segment) <= 1:
            expanded_tokens.append(segment)
            continue
        for ngram_size in (2, 3):
            for start in range(0, max(0, len(segment) - ngram_size + 1)):
                expanded_tokens.append(segment[start : start + ngram_size])
    return expanded_tokens


class _SimpleBM25:
    """小型 BM25 实现，避免教学项目强依赖外部包才能运行。"""

    def __init__(self, tokenized_docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.tokenized_docs = tokenized_docs
        self.k1 = k1
        self.b = b
        self.doc_count = len(tokenized_docs)
        self.doc_lens = [len(doc) for doc in tokenized_docs]
        self.avgdl = sum(self.doc_lens) / self.doc_count if self.doc_count else 0.0
        self.df: dict[str, int] = {}
        for doc_tokens in tokenized_docs:
            for token in set(doc_tokens):
                self.df[token] = self.df.get(token, 0) + 1

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        scores = []
        for doc_tokens, doc_len in zip(self.tokenized_docs, self.doc_lens):
            term_counts: dict[str, int] = {}
            for token in doc_tokens:
                term_counts[token] = term_counts.get(token, 0) + 1
            score = 0.0
            for token in query_tokens:
                if token not in term_counts:
                    continue
                df = self.df.get(token, 0)
                idf = math.log(1 + (self.doc_count - df + 0.5) / (df + 0.5))
                tf = term_counts[token]
                denom = tf + self.k1 * (1 - self.b + self.b * doc_len / (self.avgdl or 1))
                score += idf * (tf * (self.k1 + 1)) / denom
            scores.append(score)
        return scores


class KeywordSearcher:
    """BM25 关键词检索器，支持本地 JSON 持久化。"""

    def __init__(self, index_dir: str | Path = BM25_DIR):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._docs: dict[str, list[Document]] = {}
        self._indexes: dict[str, _SimpleBM25] = {}
        self.access_filter = AccessFilter()

    def index_documents(self, docs: list[Document], collection_name: str = "default") -> None:
        docs_copy = [Document(page_content=doc.page_content, metadata=dict(doc.metadata)) for doc in docs]
        tokenized_docs = [tokenize(doc.page_content) for doc in docs_copy]
        self._docs[collection_name] = docs_copy
        self._indexes[collection_name] = _SimpleBM25(tokenized_docs)
        self._persist(collection_name)

    def search(
        self,
        query: str,
        k: int = 5,
        collection_name: str = "default",
        user_context: UserContext | None = None,
    ) -> list[Document]:
        self._ensure_loaded(collection_name)
        docs = self._docs.get(collection_name, [])
        if not docs:
            return []

        query_tokens = tokenize(query)
        index = _SimpleBM25([tokenize(doc.page_content) for doc in docs])
        scores = index.get_scores(query_tokens)
        ranked_pairs = sorted(zip(docs, scores), key=lambda item: item[1], reverse=True)

        ranked_docs = []
        for doc, score in ranked_pairs:
            if score <= 0:
                continue
            candidate = Document(page_content=doc.page_content, metadata=dict(doc.metadata))
            candidate.metadata["keyword_score"] = float(score)
            ranked_docs.append(candidate)

        if user_context is not None:
            ranked_docs = self.access_filter.filter_docs(ranked_docs, user_context)
        return ranked_docs[:k]

    def get_all_documents(self, collection_name: str = "default") -> list[Document]:
        self._ensure_loaded(collection_name)
        return list(self._docs.get(collection_name, []))

    def delete_by_doc_id(self, doc_id: str, collection_name: str = "default") -> int:
        self._ensure_loaded(collection_name)
        docs = self._docs.get(collection_name, [])
        kept = [doc for doc in docs if doc.metadata.get("doc_id") != doc_id]
        deleted_count = len(docs) - len(kept)
        self.index_documents(kept, collection_name)
        return deleted_count

    def _persist(self, collection_name: str) -> None:
        path = self._index_path(collection_name)
        records = []
        for doc in self._docs.get(collection_name, []):
            records.append({"page_content": doc.page_content, "metadata": doc.metadata})
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def _ensure_loaded(self, collection_name: str) -> None:
        if collection_name in self._docs:
            return
        path = self._index_path(collection_name)
        if not path.exists():
            self._docs[collection_name] = []
            self._indexes[collection_name] = _SimpleBM25([])
            return
        raw_records = json.loads(path.read_text(encoding="utf-8"))
        docs = [
            Document(page_content=record["page_content"], metadata=record.get("metadata", {}))
            for record in raw_records
        ]
        self.index_documents(docs, collection_name)

    def _index_path(self, collection_name: str) -> Path:
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", collection_name)
        return self.index_dir / f"{safe_name}.json"
