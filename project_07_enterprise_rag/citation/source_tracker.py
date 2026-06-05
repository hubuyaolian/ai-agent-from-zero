"""回答引用映射和校验。"""

from __future__ import annotations

import os
import re

from langchain_core.documents import Document


class SourceTracker:
    """构建 source_id 映射并格式化引用列表。"""

    def build_source_map(self, retrieved_docs: list[Document]) -> dict[str, dict]:
        source_map = {}
        for index, doc in enumerate(retrieved_docs):
            source_id = f"S{index + 1}"
            source_map[source_id] = {
                "source_id": source_id,
                "chunk_id": doc.metadata.get("chunk_id", ""),
                "doc_id": doc.metadata.get("doc_id", ""),
                "source": doc.metadata.get("source", "未知来源"),
                "page": doc.metadata.get("page", ""),
                "heading_path": doc.metadata.get("heading_path", ""),
                "snippet": doc.page_content[:300],
            }
        return source_map

    def format_sources_for_prompt(self, source_map: dict[str, dict]) -> str:
        if not source_map:
            return "无可用参考资料。"
        parts = []
        for source_id, info in source_map.items():
            heading = f" > {info['heading_path']}" if info.get("heading_path") else ""
            page = f"，第 {info['page']} 页" if info.get("page") != "" else ""
            parts.append(
                f"[{source_id}] {os.path.basename(info['source'])}{heading}{page}\n"
                f"{info['snippet']}"
            )
        return "\n\n".join(parts)

    def extract_used_source_ids(self, answer: str) -> list[str]:
        return sorted(set(re.findall(r"\[(S\d+)\]", answer)))

    def format_citation_list(self, used_source_ids: list[str], source_map: dict[str, dict]) -> str:
        citations = []
        for source_id in used_source_ids:
            info = source_map[source_id]
            heading = f" > {info['heading_path']}" if info.get("heading_path") else ""
            page = f"，第 {info['page']} 页" if info.get("page") != "" else ""
            citations.append(
                f"[{source_id}] {os.path.basename(info['source'])}{heading}{page}\n"
                f"    摘要: {info['snippet']}"
            )
        return "\n".join(citations)


class CitationVerifier:
    """检查回答中的引用 ID 是否存在，并避免无引用事实回答直接通过。"""

    def __init__(self, source_tracker: SourceTracker | None = None):
        self.source_tracker = source_tracker or SourceTracker()

    def verify(self, answer: str, source_map: dict[str, dict]) -> dict:
        used_ids = self.source_tracker.extract_used_source_ids(answer)
        missing = [source_id for source_id in used_ids if source_id not in source_map]
        if missing:
            return {
                "passed": False,
                "used_source_ids": used_ids,
                "reason": f"回答引用了不存在的来源: {', '.join(missing)}",
            }

        unable_answer = "无法回答" in answer or "没有相关信息" in answer
        if source_map and not used_ids and not unable_answer:
            return {
                "passed": False,
                "used_source_ids": used_ids,
                "reason": "回答包含事实陈述但没有引用来源。",
            }

        return {"passed": True, "used_source_ids": used_ids, "reason": "引用格式校验通过。"}

