"""企业级 RAG 教学版 CLI。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.config import list_available_providers
from common.model_factory import create_model
from project_07_enterprise_rag.citation import CitationVerifier, SourceTracker
from project_07_enterprise_rag.config import (
    AUDIT_DB_PATH,
    BM25_DIR,
    CHROMA_DIR,
    COLLECTION_NAME,
    DB_PATH,
    DEFAULT_ACL_TAGS,
    DEFAULT_TENANT_ID,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    FINAL_TOP_K,
    LLM_PROVIDER,
    ensure_runtime_dirs,
)
from project_07_enterprise_rag.evaluation.runner import run_retrieval_eval
from project_07_enterprise_rag.governance import UserContext
from project_07_enterprise_rag.governance.audit_log import AuditLog
from project_07_enterprise_rag.graph import EnterpriseRAGWorkflow
from project_07_enterprise_rag.ingestion import DocumentLoaderFactory, HybridChunker
from project_07_enterprise_rag.memory import ConversationStore
from project_07_enterprise_rag.retrieval import (
    HybridRetriever,
    KeywordSearcher,
    LocalReranker,
    VectorStoreManager,
)


def build_components(enable_llm: bool = False) -> dict:
    ensure_runtime_dirs()
    keyword_searcher = KeywordSearcher(BM25_DIR)
    vector_manager = VectorStoreManager(
        CHROMA_DIR,
        collection_name=COLLECTION_NAME,
        embedding_provider=EMBEDDING_PROVIDER,
        embedding_model=EMBEDDING_MODEL,
    )
    hybrid_retriever = HybridRetriever(
        vector_manager,
        keyword_searcher,
        collection_name=COLLECTION_NAME,
    )
    chat_model = None
    if enable_llm:
        chat_model = create_model(provider=LLM_PROVIDER, temperature=0.0)
    source_tracker = SourceTracker()
    workflow = EnterpriseRAGWorkflow(
        conversation_store=ConversationStore(DB_PATH),
        hybrid_retriever=hybrid_retriever,
        reranker=LocalReranker(),
        source_tracker=source_tracker,
        citation_verifier=CitationVerifier(source_tracker),
        audit_log=AuditLog(AUDIT_DB_PATH),
        chat_model=chat_model,
    )
    return {
        "keyword_searcher": keyword_searcher,
        "vector_manager": vector_manager,
        "hybrid_retriever": hybrid_retriever,
        "workflow": workflow,
        "conversation_store": workflow.conversation_store,
        "audit_log": workflow.audit_log,
    }


def import_path(path: str, components: dict, user_context: UserContext) -> int:
    target = Path(path)
    loader_kwargs = {
        "tenant_id": user_context.tenant_id,
        "acl_tags": user_context.roles,
    }
    if target.is_dir():
        docs = DocumentLoaderFactory.load_directory(target, **loader_kwargs)
    else:
        docs = DocumentLoaderFactory.load(target, **loader_kwargs)

    chunks = HybridChunker().split(docs)
    keyword_searcher: KeywordSearcher = components["keyword_searcher"]
    existing_docs = keyword_searcher.get_all_documents(COLLECTION_NAME)
    keyword_searcher.index_documents(existing_docs + chunks, COLLECTION_NAME)

    try:
        components["vector_manager"].add_documents(chunks)
    except RuntimeError as exc:
        print(f"⚠️ 向量索引未写入: {exc}")
        print("   已完成 BM25 索引，可继续用关键词检索教学路径。")
    return len(chunks)


def print_welcome(enable_llm: bool) -> None:
    print("\n" + "=" * 64)
    print("企业级 RAG 教学版 CLI")
    print("=" * 64)
    print("文档:")
    print("  /import <文件或目录>       导入 PDF/DOCX/MD/TXT")
    print("  /list                     列出 BM25 索引中的文档")
    print("  /delete <doc_id>           删除指定 doc_id")
    print("  /stats                    查看索引统计")
    print("会话:")
    print("  /history                  查看当前会话历史")
    print("  /clear                    清空当前会话")
    print("  /session <id>             切换会话")
    print("  /user <tenant> <roles>    切换租户和角色，例如 /user default public,hr")
    print("评估与审计:")
    print("  /eval                     运行最小检索评估集")
    print("  /audit                    查看当前会话审计日志")
    print("系统:")
    print("  /quit                     退出")
    print("=" * 64)
    mode = "LLM 生成" if enable_llm else "本地生成兜底"
    print(f"当前模式: {mode}；可直接输入问题开始问答。")
    print("=" * 64 + "\n")


def main() -> None:
    enable_llm = os.getenv("ENTERPRISE_RAG_ENABLE_LLM", "0") == "1"
    if enable_llm and LLM_PROVIDER not in list_available_providers():
        print(f"⚠️ 未检测到 {LLM_PROVIDER} API Key，自动切换到本地生成兜底模式。")
        enable_llm = False

    components = build_components(enable_llm=enable_llm)
    session_id = "default"
    user_context = UserContext.from_values(
        tenant_id=DEFAULT_TENANT_ID,
        roles=DEFAULT_ACL_TAGS,
    )
    print_welcome(enable_llm)

    while True:
        try:
            user_input = input(f"[{session_id}/{user_context.tenant_id}] > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见。")
            break

        if not user_input:
            continue
        if user_input.startswith("/"):
            parts = user_input.split(" ", 1)
            command = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if command == "/quit":
                print("再见。")
                break
            if command == "/import":
                if not arg:
                    print("用法: /import <文件或目录>")
                    continue
                try:
                    count = import_path(arg, components, user_context)
                    print(f"✅ 导入完成，共写入 {count} 个 chunk。")
                except Exception as exc:
                    print(f"❌ 导入失败: {exc}")
                continue
            if command == "/list":
                docs = components["keyword_searcher"].get_all_documents(COLLECTION_NAME)
                doc_ids = sorted({doc.metadata.get("doc_id", "") for doc in docs})
                if not doc_ids:
                    print("当前索引为空。")
                for doc_id in doc_ids:
                    print(f"- {doc_id}")
                continue
            if command == "/delete":
                if not arg:
                    print("用法: /delete <doc_id>")
                    continue
                keyword_deleted = components["keyword_searcher"].delete_by_doc_id(arg, COLLECTION_NAME)
                try:
                    vector_deleted = components["vector_manager"].delete_by_doc_id(arg)
                except RuntimeError:
                    vector_deleted = 0
                print(f"✅ 删除完成：BM25 {keyword_deleted} 个 chunk，向量库 {vector_deleted} 个 chunk。")
                continue
            if command == "/stats":
                keyword_docs = components["keyword_searcher"].get_all_documents(COLLECTION_NAME)
                doc_count = len({doc.metadata.get("doc_id") for doc in keyword_docs})
                print(f"BM25 文档数: {doc_count}")
                print(f"BM25 chunk 数: {len(keyword_docs)}")
                try:
                    print(f"向量库统计: {components['vector_manager'].get_stats()}")
                except RuntimeError as exc:
                    print(f"向量库不可用: {exc}")
                continue
            if command == "/history":
                for item in components["conversation_store"].get_history(session_id):
                    print(f"[{item['role']}] {item['content']}")
                continue
            if command == "/clear":
                deleted = components["conversation_store"].clear_session(session_id)
                print(f"已清空 {deleted} 条会话消息。")
                continue
            if command == "/session":
                if not arg:
                    print("用法: /session <id>")
                    continue
                session_id = arg
                print(f"已切换会话: {session_id}")
                continue
            if command == "/user":
                user_parts = arg.split(" ", 1)
                if len(user_parts) != 2:
                    print("用法: /user <tenant> <roles>")
                    continue
                user_context = UserContext.from_values(
                    tenant_id=user_parts[0],
                    roles=user_parts[1],
                )
                print(f"已切换用户上下文: tenant={user_context.tenant_id}, roles={sorted(user_context.roles)}")
                continue
            if command == "/eval":
                metrics = run_retrieval_eval(components["hybrid_retriever"], user_context, k=FINAL_TOP_K)
                print(f"评估结果: {metrics}")
                continue
            if command == "/audit":
                events = components["audit_log"].list_events(session_id)
                for event in events:
                    print(f"[{event['id']}] {event['event_type']} {event['created_at']}")
                    print(event["payload"])
                continue

            print(f"未知命令: {command}")
            continue

        state = components["workflow"].ask(
            user_input,
            session_id=session_id,
            user_context=user_context,
        )
        print("\nAI:")
        print(state["formatted_answer"])
        print(f"\n质量评分: {state['quality_score']}/10 - {state['quality_reason']}")
        print()


if __name__ == "__main__":
    main()
