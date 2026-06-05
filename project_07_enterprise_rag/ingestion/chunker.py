"""标题感知 + 递归边界分块器。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_core.documents import Document

from project_07_enterprise_rag.config import CHUNK_OVERLAP, CHUNK_SIZE, MIN_CHUNK_SIZE
from project_07_enterprise_rag.governance.metadata import build_chunk_id, compute_content_hash


@dataclass
class _Section:
    content: str
    heading_path: str
    char_start: int
    char_end: int


class HybridChunker:
    """按 Markdown 标题和自然段落分块，再对超长段落递归切分。"""

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        min_chunk_size: int = MIN_CHUNK_SIZE,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self._splitter = self._create_splitter()

    def split(self, documents: list[Document]) -> list[Document]:
        chunks: list[Document] = []
        for doc in documents:
            doc_chunks = self._split_one_document(doc)
            chunks.extend(doc_chunks)
        return chunks

    def _split_one_document(self, doc: Document) -> list[Document]:
        sections = self._split_by_headings(doc.page_content)
        merged_sections = self._merge_short_sections(sections)
        chunks: list[Document] = []
        chunk_index = 0

        for section in merged_sections:
            parts = self._recursive_split(section.content)
            cursor = section.char_start
            for part in parts:
                stripped = part.strip()
                if not stripped:
                    continue
                part_start = doc.page_content.find(stripped[:20], cursor)
                if part_start < 0:
                    part_start = cursor
                part_end = part_start + len(stripped)
                metadata = dict(doc.metadata or {})
                metadata.update(
                    {
                        "chunk_index": chunk_index,
                        "heading_path": section.heading_path,
                        "char_start": part_start,
                        "char_end": part_end,
                    }
                )
                chunk_hash = compute_content_hash(stripped)
                metadata["chunk_id"] = build_chunk_id(
                    metadata["doc_id"],
                    chunk_hash,
                    chunk_index,
                )
                chunks.append(Document(page_content=stripped, metadata=metadata))
                chunk_index += 1
                cursor = part_end

        return chunks

    def _split_by_headings(self, text: str) -> list[_Section]:
        heading_stack: list[tuple[int, str]] = []
        sections: list[_Section] = []
        current_lines: list[str] = []
        current_heading = ""
        current_start = 0
        offset = 0

        lines = text.splitlines(keepends=True)
        for line in lines:
            heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line.strip())
            if heading_match:
                if current_lines:
                    content = "".join(current_lines).strip()
                    if content:
                        sections.append(
                            _Section(
                                content=content,
                                heading_path=current_heading,
                                char_start=current_start,
                                char_end=offset,
                            )
                        )
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, title))
                current_heading = " > ".join(item[1] for item in heading_stack)
                current_lines = [line]
                current_start = offset
            else:
                if not current_lines:
                    current_start = offset
                current_lines.append(line)
            offset += len(line)

        if current_lines:
            content = "".join(current_lines).strip()
            if content:
                sections.append(
                    _Section(
                        content=content,
                        heading_path=current_heading,
                        char_start=current_start,
                        char_end=len(text),
                    )
                )

        if sections:
            return sections
        return [_Section(content=text.strip(), heading_path="", char_start=0, char_end=len(text))]

    def _merge_short_sections(self, sections: list[_Section]) -> list[_Section]:
        if not sections:
            return []

        merged: list[_Section] = []
        pending: _Section | None = None
        for section in sections:
            if pending is None:
                pending = section
                continue
            if len(pending.content) < self.min_chunk_size:
                combined_heading = section.heading_path or pending.heading_path
                pending = _Section(
                    content=f"{pending.content}\n\n{section.content}",
                    heading_path=combined_heading,
                    char_start=pending.char_start,
                    char_end=section.char_end,
                )
            else:
                merged.append(pending)
                pending = section
        if pending is not None:
            merged.append(pending)
        return merged

    def _recursive_split(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        if self._splitter is not None:
            return self._splitter.split_text(text)

        parts = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        for start in range(0, len(text), step):
            parts.append(text[start : start + self.chunk_size])
        return parts

    def _create_splitter(self):
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            return None
        return RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        )
