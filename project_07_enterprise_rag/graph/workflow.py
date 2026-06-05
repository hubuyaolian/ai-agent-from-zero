"""企业级 RAG 教学版工作流，基于真实 LangGraph StateGraph 实现。"""

from __future__ import annotations

import json
import re

from langchain_core.documents import Document
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from project_07_enterprise_rag.citation.source_tracker import CitationVerifier, SourceTracker
from project_07_enterprise_rag.config import FINAL_TOP_K, MAX_RETRY, QUALITY_THRESHOLD
from project_07_enterprise_rag.governance.access_filter import UserContext
from project_07_enterprise_rag.governance.audit_log import AuditLog
from project_07_enterprise_rag.governance.guardrail import GuardrailManager
from project_07_enterprise_rag.graph.state import EnterpriseRAGState
from project_07_enterprise_rag.memory.conversation_store import ConversationStore


class EnterpriseRAGWorkflow:
    """基于 LangGraph StateGraph 编排的 RAG 工作流，支持 Checkpoint 隔离与 Guardrails 防御。"""

    def __init__(
        self,
        *,
        conversation_store: ConversationStore,
        hybrid_retriever,
        reranker,
        source_tracker: SourceTracker,
        citation_verifier: CitationVerifier,
        audit_log: AuditLog,
        chat_model=None,
    ):
        self.conversation_store = conversation_store
        self.hybrid_retriever = hybrid_retriever
        self.reranker = reranker
        self.source_tracker = source_tracker
        self.citation_verifier = citation_verifier
        self.audit_log = audit_log
        self.chat_model = chat_model

        # 1. 实例化安全防御管理器
        self.guardrail_manager = GuardrailManager()

        # 2. 构建并编译 LangGraph 图
        self.compiled_graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建真正的状态图并绑定 MemorySaver Checkpointer。"""
        graph = StateGraph(EnterpriseRAGState)

        # 注册所有工作流节点
        graph.add_node("input_guardrail", self.input_guardrail_node)
        graph.add_node("intent_resolver", self.intent_resolver)
        graph.add_node("hybrid_retriever", self.hybrid_retriever_node)
        graph.add_node("retrieval_guardrail", self.retrieval_guardrail_node)
        graph.add_node("reranker", self.reranker_node)
        graph.add_node("answer_generator", self.answer_generator)
        graph.add_node("citation_verifier", self.citation_verifier_node)
        graph.add_node("quality_checker", self.quality_checker)
        graph.add_node("output_guardrail", self.output_guardrail_node)
        graph.add_node("response_formatter", self.response_formatter)

        # 设定入口节点
        graph.set_entry_point("input_guardrail")

        # input_guardrail 后的条件路由边
        graph.add_conditional_edges(
            "input_guardrail",
            self.route_after_input_guardrail,
            {
                "blocked": "response_formatter",
                "passed": "intent_resolver",
            },
        )

        # 常规线性流转
        graph.add_edge("intent_resolver", "hybrid_retriever")
        graph.add_edge("hybrid_retriever", "retrieval_guardrail")
        graph.add_edge("retrieval_guardrail", "reranker")
        graph.add_edge("reranker", "answer_generator")
        graph.add_edge("answer_generator", "citation_verifier")
        graph.add_edge("citation_verifier", "quality_checker")

        # quality_checker 后的重试/通过条件路由边
        graph.add_conditional_edges(
            "quality_checker",
            self.route_quality,
            {
                "retry": "hybrid_retriever",
                "pass": "output_guardrail",
            },
        )

        # 输出与格式化
        graph.add_edge("output_guardrail", "response_formatter")
        graph.add_edge("response_formatter", END)

        # 教学版 MemorySaver checkpointer 注册
        return graph.compile(checkpointer=MemorySaver())

    def ask(
        self,
        query: str,
        *,
        session_id: str,
        user_context: UserContext,
    ) -> EnterpriseRAGState:
        """外层向后兼容的调用接口，内部运行编译后的 LangGraph 图。"""
        # 1. 外部仅执行隐私掩码，局部生成干净已掩码文本，确保 PII 不进 Checkpoint
        masked_query = self.guardrail_manager.mask_pii(query)
        input_was_masked = masked_query != query

        initial_state: EnterpriseRAGState = {
            "session_id": session_id,
            "query": masked_query,  # 此时 query 已 100% 脱敏
            "user_context": user_context,
            "retrieval_plan": {"top_k": FINAL_TOP_K},
            "retry_count": 0,
            "guardrail_blocked": False,
            "guardrail_reason": "",
            "input_was_masked": input_was_masked,
        }

        # 2. 调用已编译图执行，并配合 thread_id 实现持久化会话隔离
        config = {"configurable": {"thread_id": session_id}}
        final_state = self.compiled_graph.invoke(initial_state, config=config)
        return final_state

    # ==========================================
    #             图节点函数定义
    # ==========================================

    def input_guardrail_node(self, state: EnterpriseRAGState) -> dict:
        """输入安全防御节点。在图内对脱敏后 query 执行注入特征检测并记录审计。"""
        query = state.get("query", "")
        safe, reason = self.guardrail_manager.detect_injection(query)

        if not safe:
            # 记录注入审计
            self.audit_log.record(
                state["session_id"],
                "guardrail_blocked",
                {"reason": reason},
            )
            # 填满所有必需字段，杜绝 response_formatter KeyError
            return {
                "guardrail_blocked": True,
                "guardrail_reason": reason,
                "answer": f"抱歉，系统检测到敏感内容被拦截：{reason}",
                "rewritten_query": "",
                "citation_check": {
                    "passed": True,
                    "used_source_ids": [],
                    "reason": "guardrail_blocked",
                },
                "quality_score": 0,
                "quality_reason": "安全防御拦截",
                "needs_retry": False,
            }

        # 正常通过，记录审计
        self.audit_log.record(
            state["session_id"],
            "guardrail_checked",
            {"input_was_masked": state.get("input_was_masked", False)},
        )
        return {"guardrail_blocked": False, "guardrail_reason": "", "needs_retry": False}


    def intent_resolver(self, state: EnterpriseRAGState) -> dict:
        """查询改写节点。"""
        history = self.conversation_store.get_history(state["session_id"], limit=6)
        query = state["query"]
        rewritten_query = query
        if self._looks_like_follow_up(query) and history:
            rewritten_query = self._local_rewrite(query, history)
        self.audit_log.record(
            state["session_id"],
            "intent_resolved",
            {"query": query, "rewritten_query": rewritten_query},
        )
        return {"rewritten_query": rewritten_query}

    def hybrid_retriever_node(self, state: EnterpriseRAGState) -> dict:
        """多路混合检索节点。"""
        plan = state.get("retrieval_plan", {})
        docs = self.hybrid_retriever.retrieve(
            state["rewritten_query"],
            k=plan.get("top_k", FINAL_TOP_K),
            query_variants=plan.get("query_variants"),
            user_context=state["user_context"],
        )
        cleaned_docs = [self.guardrail_manager.mask_document(doc) for doc in docs]
        self.audit_log.record(
            state["session_id"],
            "retrieved",
            {
                "rewritten_query": state["rewritten_query"],
                "chunk_ids": [doc.metadata.get("chunk_id") for doc in cleaned_docs],
                "plan": plan,
            },
        )
        return {"retrieved_docs": cleaned_docs}

    def retrieval_guardrail_node(self, state: EnterpriseRAGState) -> dict:
        """检索隐私清洗节点。防止外部文档本身的敏感 PII 流入状态图 checkpoint。"""
        retrieved = state.get("retrieved_docs", [])
        cleaned = []
        for doc in retrieved:
            cleaned.append(self.guardrail_manager.mask_document(doc))
        return {"retrieved_docs": cleaned}

    def reranker_node(self, state: EnterpriseRAGState) -> dict:
        """重排节点。使用已清洗的 retrieved_docs 状态。"""
        docs = self.reranker.rerank(
            state["rewritten_query"],
            state["retrieved_docs"],
            top_k=FINAL_TOP_K,
        )
        cleaned_docs = [self.guardrail_manager.mask_document(doc) for doc in docs]
        self.audit_log.record(
            state["session_id"],
            "reranked",
            {"chunk_ids": [doc.metadata.get("chunk_id") for doc in cleaned_docs]},
        )
        return {"reranked_docs": cleaned_docs}

    def answer_generator(self, state: EnterpriseRAGState) -> dict:
        """回答生成节点。"""
        source_map = self.guardrail_manager.mask_value(
            self.source_tracker.build_source_map(state["reranked_docs"])
        )
        if not source_map:
            return {
                "source_map": source_map,
                "answer": "根据现有资料无法回答此问题。",
            }

        if self.chat_model is None:
            answer = self._local_answer(state["query"], source_map)
        else:
            answer = self._llm_answer(state["query"], source_map)
        return {"source_map": source_map, "answer": answer}

    def citation_verifier_node(self, state: EnterpriseRAGState) -> dict:
        """引用验证节点。"""
        check = self.citation_verifier.verify(state["answer"], state["source_map"])
        citations = []
        if check.get("passed"):
            citations = [
                self.source_tracker.format_citation_list(
                    check.get("used_source_ids", []),
                    state["source_map"],
                )
            ]
        self.audit_log.record(
            state["session_id"],
            "citation_checked",
            {"check": check},
        )
        return {"citation_check": check, "citations": citations}

    def quality_checker(self, state: EnterpriseRAGState) -> dict:
        """回答质量自检节点。"""
        citation_passed = state["citation_check"].get("passed", False)
        has_docs = bool(state["source_map"])
        unable_answer = "无法回答" in state["answer"] or "没有相关信息" in state["answer"]

        if citation_passed and (has_docs or unable_answer):
            score = 8
            reason = "回答有可追溯引用，或明确说明资料不足。"
        else:
            score = 4
            reason = state["citation_check"].get("reason", "引用或证据不足。")

        should_retry = score < QUALITY_THRESHOLD and state.get("retry_count", 0) < MAX_RETRY
        update = {
            "quality_score": score,
            "quality_reason": reason,
            "needs_retry": should_retry,
        }
        if should_retry:
            retry_count = state.get("retry_count", 0) + 1
            plan = dict(state.get("retrieval_plan", {}))
            plan["top_k"] = min(int(plan.get("top_k", FINAL_TOP_K)) * 2, 20)
            if retry_count >= 2:
                plan["query_variants"] = self._query_variants(state["rewritten_query"])
            update["retry_count"] = retry_count
            update["retrieval_plan"] = plan
        self.audit_log.record(
            state["session_id"],
            "quality_checked",
            {key: update[key] for key in ("quality_score", "quality_reason", "needs_retry")},
        )
        return update

    def output_guardrail_node(self, state: EnterpriseRAGState) -> dict:
        """输出防泄漏脱敏节点。对最终的 answer 和 citations 全覆盖脱敏。"""
        answer = self.guardrail_manager.mask_pii(state.get("answer", ""))
        citations = state.get("citations", [])
        cleaned_citations = [self.guardrail_manager.mask_pii(cit) for cit in citations]
        return {
            "answer": answer,
            "citations": cleaned_citations,
        }


    def response_formatter(self, state: EnterpriseRAGState) -> dict:
        """格式化输出并归档记录节点。"""
        formatted = state["answer"]
        if state.get("citations") and state["citations"][0]:
            formatted += "\n\n参考来源:\n" + state["citations"][0]

        self.conversation_store.add_message(state["session_id"], "user", state["query"])
        answer_id = self.conversation_store.add_message(
            state["session_id"],
            "assistant",
            formatted,
            metadata={
                "rewritten_query": state["rewritten_query"],
                "quality_score": state["quality_score"],
                "quality_reason": state["quality_reason"],
                "used_sources": state["citation_check"].get("used_source_ids", []),
            },
        )
        return {"formatted_answer": formatted, "answer_id": answer_id}

    # ==========================================
    #            图条件路由边函数
    # ==========================================

    def route_after_input_guardrail(self, state: EnterpriseRAGState) -> str:
        """输入安全拦截条件路由。"""
        return "blocked" if state.get("guardrail_blocked") else "passed"

    def route_quality(self, state: EnterpriseRAGState) -> str:
        """生成答复质量条件路由。"""
        return "retry" if state.get("needs_retry") else "pass"

    # ==========================================
    #             局部算法辅助函数
    # ==========================================

    def _llm_answer(self, query: str, source_map: dict[str, dict]) -> str:
        context = self.source_tracker.format_sources_for_prompt(source_map)
        prompt = (
            "你是一个严谨的知识库问答助手。只基于参考资料回答用户问题。\n"
            "如果资料不足，请回答“根据现有资料无法回答此问题”。\n"
            "每个事实句末尾必须标注来源编号，如 [S1]。\n\n"
            f"参考资料:\n{context}\n\n"
            f"用户问题: {query}\n"
        )
        response = self.chat_model.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)

    def _local_answer(self, query: str, source_map: dict[str, dict]) -> str:
        answer_parts = []
        for source_id, info in list(source_map.items())[:2]:
            snippet = self._first_sentence(info["snippet"])
            answer_parts.append(f"{snippet} [{source_id}]")
        if not answer_parts:
            return "根据现有资料无法回答此问题。"
        return " ".join(answer_parts)

    def _local_rewrite(self, query: str, history: list[dict]) -> str:
        previous_user_messages = [item["content"] for item in history if item["role"] == "user"]
        if not previous_user_messages:
            return query
        return f"{previous_user_messages[-1]}；追问：{query}"

    def _query_variants(self, query: str) -> list[str]:
        clean_query = query.strip()
        return [
            clean_query,
            re.sub(r"[？?。.!！]", "", clean_query),
            f"{clean_query} 相关规定 具体条款",
        ]

    @staticmethod
    def _looks_like_follow_up(query: str) -> bool:
        follow_up_markers = ("它", "这个", "那个", "呢", "上述", "前面")
        return any(marker in query for marker in follow_up_markers)

    @staticmethod
    def _first_sentence(text: str) -> str:
        parts = re.split(r"(?<=[。！？.!?])", text.strip())
        for part in parts:
            if part.strip():
                return part.strip()
        return text.strip()[:120]
