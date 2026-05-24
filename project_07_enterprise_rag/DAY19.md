# Day 19 课程：企业级 RAG 工作流编排 — 对话记忆、来源溯源与质量闭环 🔄

在 Day 18 中，我们完成了企业级 RAG 的"数据入口"和"检索增强"两层设计——从多格式加载、混合分块到多路融合检索。但一个完整的企业级应用还需要解决三个关键问题：

1. **对话记忆**：用户可能连续追问，如"LangGraph 支持哪些功能？→ 它的性能怎么样？"。第二个问题中的"它"指代 LangGraph，系统必须从对话历史中理解这种指代关系。
2. **来源溯源**：企业场景中，回答必须可验证。用户需要知道"这个答案来自哪份文档的第几页"。
3. **质量闭环**：检索到的文档可能完全不相关，LLM 仍会基于无关上下文生成"看似合理但实际错误"的答案。需要一个质量检查机制来拦截这类幻觉。

今天我们将用 LangGraph 编排一个包含上述三个能力的完整工作流。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：对话记忆与指代消解](#第一部分对话记忆与指代消解)
3. [第二部分：来源溯源与引用标注](#第二部分来源溯源与引用标注)
4. [第三部分：LangGraph 工作流编排](#第三部分langgraph-工作流编排)
5. [第四部分：完整 CLI 应用](#第四部分完整-cli-应用)
6. [核心原理深度解析](#核心原理深度解析)
7. [课后练习](#课后练习)

---

## 学习目标
- 掌握 SQLite 会话存储与多会话管理。
- 理解 LLM 指代消解（Intent Resolution）的原理与实现。
- 掌握来源追踪、引用标注和溯源列表的设计。
- 学会用 LangGraph 编排 6 节点 RAG 工作流，含质量检查与重试循环。
- 构建完整的企业级 RAG CLI 应用。

---

## 第一部分：对话记忆与指代消解

### 1. 为什么 RAG 需要对话记忆？

基础 RAG 是"无状态"的——每次问答完全独立。但在真实使用中，用户几乎不会只问一个问题就离开：

```
用户: LangGraph 是什么？
AI:   LangGraph 是 LangChain 团队开发的 Agent 编排框架...

用户: 它支持哪些功能？          ← "它"指代 LangGraph
AI:   ??? （无记忆的系统不知道"它"是什么）

用户: 能举个例子吗？            ← 指代上文的"功能"
AI:   ??? （更加迷失）
```

没有对话记忆，LLM 只看到"它支持哪些功能？"，完全无法理解用户的真实意图。

### 2. ConversationStore — SQLite 会话存储

我们使用 SQLite 持久化对话历史，支持多会话隔离：

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,       -- 会话 ID
    role TEXT NOT NULL,             -- 消息角色 (user/assistant/system)
    content TEXT NOT NULL,          -- 消息内容
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id);
```

```python
class ConversationStore:
    """SQLite 对话历史存储。"""

    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def add_message(self, session_id: str, role: str, content: str):
        """插入一条消息到指定会话。"""

    def get_history(self, session_id: str, limit: int = 20) -> list:
        """获取指定会话最近 N 条消息。"""

    def clear_session(self, session_id: str):
        """清空指定会话的所有消息。"""

    def list_sessions(self) -> list:
        """列出所有会话 ID 及最后活跃时间。"""
```

与 Day 8 的 `MemoryStore`（存 KV 结构化记忆）不同，`ConversationStore` 存的是**原始对话消息**，目的是为 LLM 提供完整的上下文来理解指代关系。

### 3. IntentResolver — LLM 指代消解

有了对话历史，下一步是让 LLM 基于**历史上下文**改写用户的当前问题，消除指代：

```python
INTENT_RESOLVER_PROMPT = """
你是一个查询改写专家。根据对话历史，将用户当前问题改写为一个独立的、
无需上下文即可理解的检索查询。

对话历史:
{history}

用户当前问题: {query}

改写要求:
1. 将代词（它、这个、那个）替换为实际指代的实体
2. 将省略的信息补充完整
3. 只输出改写后的查询，不要解释

改写后的查询:
"""
```

**改写示例**：

| 对话历史 | 用户问题 | 改写后 |
|---------|---------|--------|
| "LangGraph 是一个 Agent 框架" | "它支持哪些功能？" | "LangGraph 支持哪些功能？" |
| "RAG 是检索增强生成" | "它和微调有什么区别？" | "RAG 和微调有什么区别？" |
| "产品 A 的价格是 100 元" | "产品 B 呢？" | "产品 B 的价格是多少？" |

改写后的查询将用于后续的检索，而不是用原始的含指代问题去检索——否则向量检索和 BM25 都无法正确匹配指代词。

---

## 第二部分：来源溯源与引用标注

### 1. 为什么需要来源溯源？

在企业场景中，RAG 系统的回答直接关系到业务决策。如果回答无法追溯到原始文档，用户就无法验证其可信度：

```
❌ 无溯源的回答:
"根据公司规定，员工可以享受 15 天年假。"
→ 用户无法确认这个信息是否真实，是否来自最新的制度文件。

✅ 有溯源的回答:
"根据公司规定，员工可以享受 15 天年假。[1]

📖 参考来源:
[1] 《员工手册 2024 版》第 3 章 > 休假制度，第 45 页"
→ 用户可以直接翻到原文验证。
```

### 2. SourceTracker — 引用注入与格式化

SourceTracker 负责两个任务：

**任务 1：引用标注** — 在 LLM 生成的回答中注入 `[1]`、`[2]` 标记：

```python
class SourceTracker:
    """来源追踪与引用标注。"""

    def inject_sources(self, answer: str, retrieved_docs: list) -> str:
        """在回答文本中注入引用编号标记。

        策略：让 LLM 在生成回答时，在引用了某个文档的位置标注 [1] 等标记。
        这通过在 Prompt 中明确要求来实现，而非后处理。
        """
```

实际上，引用标注最可靠的方式是在 RAG Prompt 中**直接要求 LLM 标注引用**：

```python
RAG_ANSWER_PROMPT = """
你是一个严谨的知识库问答助手。请基于以下参考资料回答用户的问题。

严格要求：
1. 只基于参考资料中明确提到的信息回答
2. 如果参考资料中没有相关信息，请回答"根据现有资料无法回答此问题"
3. 在引用某个参考资料的段落末尾标注来源编号，如 [1]、[2]
4. 不要编造参考资料中没有的内容

参考资料：
{context}

用户问题：{question}
"""
```

**任务 2：引用列表生成** — 在回答末尾附加结构化的来源列表：

```python
    def format_citation_list(self, retrieved_docs: list) -> str:
        """生成末尾引用列表。"""
        citations = []
        for i, doc in enumerate(retrieved_docs):
            source = doc.metadata.get("source", "未知来源")
            page = doc.metadata.get("page", "")
            heading = doc.metadata.get("heading_path", "")
            snippet = doc.page_content[:100] + "..."
            citations.append(
                f"[{i + 1}] {os.path.basename(source)}"
                f"{' > ' + heading if heading else ''}"
                f"，第 {page} 页\n    摘要: {snippet}"
            )
        return "\n".join(citations)
```

输出效果：

```
AI > 根据员工手册，正式员工入职满一年后可享受 15 天年假。[1]
兼职员工按工作时长折算年假天数。[2]

📖 参考来源:
[1] 员工手册_2024.md > 休假制度 > 年假，第 3 页
    摘要: 正式员工入职满一年后，每年可享受 15 天带薪年假...
[2] 员工手册_2024.md > 休假制度 > 兼职员工，第 4 页
    摘要: 兼职员工年假天数按实际工作时长折算...
```

### 3. build_source_map — 文档 ID 映射

为每个检索到的文档构建唯一标识映射，供 LangGraph 状态流转和引用溯源使用：

```python
    def build_source_map(self, retrieved_docs: list) -> dict:
        """构建 doc_id → source_info 映射。"""
        source_map = {}
        for i, doc in enumerate(retrieved_docs):
            doc_id = f"doc_{i + 1}"
            source_map[doc_id] = {
                "index": i + 1,
                "source": doc.metadata.get("source", "未知"),
                "page": doc.metadata.get("page", ""),
                "heading_path": doc.metadata.get("heading_path", ""),
                "snippet": doc.page_content[:200],
            }
        return source_map
```

---

## 第三部分：LangGraph 工作流编排

### 1. EnterpriseRAGState — 状态定义

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class EnterpriseRAGState(TypedDict):
    """企业级 RAG 工作流状态。"""
    messages: Annotated[list, add_messages]  # 对话消息
    query: str                                # 当前用户问题
    rewritten_query: str                      # 改写后的问题
    retrieved_docs: list                      # 检索到的文档
    reranked_docs: list                       # 重排后的文档
    answer: str                               # 生成的回答
    citations: list                           # 引用来源列表
    quality_score: int                        # 回答质量评分 (1-10)
    needs_retry: bool                         # 是否需要重试
```

### 2. 6 节点状态图

```
START
  │
  ▼
┌─────────────────┐
│ intent_resolver  │  对话历史 + 当前问题 → LLM 改写为独立查询
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ hybrid_retriever │  向量检索 + BM25 检索 → RRF 融合
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   reranker       │  LLM 打分精排，过滤低相关文档
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ answer_generator │  基于重排文档 + LLM 生成回答，注入引用
└────────┬────────┘
         │
         ▼
┌─────────────────┐     needs_retry=True
│ quality_checker  │────────────────────────► hybrid_retriever
│ (LLM 自评)       │        (最多 2 次)
└────────┬────────┘
         │ needs_retry=False
         ▼
┌─────────────────┐
│ response_formatter│  格式化输出 + 写入 ConversationStore
└────────┬────────┘
         │
         ▼
        END
```

### 3. 各节点实现要点

#### intent_resolver 节点

```python
def intent_resolver(state: EnterpriseRAGState) -> dict:
    """意图解析：基于对话历史改写用户问题。"""
    history = conversation_store.get_history(current_session_id)
    history_text = format_history(history)
    rewritten = model.invoke(
        INTENT_RESOLVER_PROMPT.format(
            history=history_text,
            query=state["query"]
        )
    )
    return {"rewritten_query": rewritten.content}
```

#### hybrid_retriever 节点

```python
def hybrid_retriever(state: EnterpriseRAGState) -> dict:
    """混合检索：向量 + BM25 → RRF 融合。"""
    docs = hybrid_retriever_instance.retrieve(
        query=state["rewritten_query"],
        k=VECTOR_SEARCH_K
    )
    return {"retrieved_docs": docs}
```

#### reranker 节点

```python
def reranker(state: EnterpriseRAGState) -> dict:
    """LLM 重排序：对候选文档逐一打分，过滤低相关文档。"""
    scored_docs = llm_reranker.rerank(
        query=state["rewritten_query"],
        docs=state["retrieved_docs"],
        threshold=RERANK_THRESHOLD
    )
    return {"reranked_docs": scored_docs}
```

#### answer_generator 节点

```python
def answer_generator(state: EnterpriseRAGState) -> dict:
    """回答生成：基于重排文档 + LLM，要求标注引用。"""
    context = format_docs_with_indices(state["reranked_docs"])
    answer = model.invoke(
        RAG_ANSWER_PROMPT.format(context=context, question=state["query"])
    )
    citations = source_tracker.format_citation_list(state["reranked_docs"])
    return {"answer": answer.content, "citations": [citations]}
```

#### quality_checker 节点

```python
QUALITY_CHECK_PROMPT = """
你是一个回答质量评估专家。请评估以下 RAG 回答的质量。

用户问题: {query}
参考文档数量: {doc_count}
生成的回答: {answer}

请从以下维度打分 (1-10)：
1. 完整性：回答是否完整覆盖了用户的问题？
2. 准确性：回答是否基于参考文档，而非编造？
3. 相关性：回答是否与问题直接相关？

如果总分低于 {threshold}，说明回答质量不足，需要重新检索。

输出格式:
SCORE: <1-10>
REASON: <简短说明>
NEEDS_RETRY: <YES/NO>
"""

def quality_checker(state: EnterpriseRAGState) -> dict:
    """质量检查：LLM 自评回答质量，低于阈值标记重试。"""
    evaluation = model.invoke(
        QUALITY_CHECK_PROMPT.format(
            query=state["query"],
            doc_count=len(state["reranked_docs"]),
            answer=state["answer"],
            threshold=QUALITY_THRESHOLD
        )
    )
    score = parse_score(evaluation.content)
    needs_retry = score < QUALITY_THRESHOLD
    return {"quality_score": score, "needs_retry": needs_retry}
```

#### response_formatter 节点

```python
def response_formatter(state: EnterpriseRAGState) -> dict:
    """格式化输出：拼装回答 + 引用列表，写入对话历史。"""
    formatted = state["answer"]
    if state["citations"]:
        formatted += "\n\n📖 参考来源:\n" + state["citations"][0]

    # 写入对话历史
    conversation_store.add_message(current_session_id, "user", state["query"])
    conversation_store.add_message(current_session_id, "assistant", formatted)

    return {"messages": [
        HumanMessage(content=state["query"]),
        AIMessage(content=formatted),
    ]}
```

### 4. 条件边：质量检查后的路由

```python
def route_after_quality_check(state: EnterpriseRAGState) -> str:
    """质量检查后路由：需要重试回到检索，否则输出。"""
    if state["needs_retry"]:
        return "retry"
    return "finish"

workflow.add_conditional_edges(
    "quality_checker",
    route_after_quality_check,
    {
        "retry": "hybrid_retriever",
        "finish": "response_formatter",
    }
)
```

重试次数限制：在 `EnterpriseRAGState` 中增加 `retry_count: int` 字段，每次重试递增，达到 `MAX_RETRY`（默认 2 次）后强制跳转到 `response_formatter`。

### 5. 图的编译

```python
def build_workflow():
    """构建并编译企业级 RAG 工作流。"""
    workflow = StateGraph(EnterpriseRAGState)

    # 添加 6 个节点
    workflow.add_node("intent_resolver", intent_resolver)
    workflow.add_node("hybrid_retriever", hybrid_retriever)
    workflow.add_node("reranker", reranker)
    workflow.add_node("answer_generator", answer_generator)
    workflow.add_node("quality_checker", quality_checker)
    workflow.add_node("response_formatter", response_formatter)

    # 设置入口
    workflow.set_entry_point("intent_resolver")

    # 顺序边
    workflow.add_edge("intent_resolver", "hybrid_retriever")
    workflow.add_edge("hybrid_retriever", "reranker")
    workflow.add_edge("reranker", "answer_generator")
    workflow.add_edge("answer_generator", "quality_checker")
    workflow.add_edge("response_formatter", END)

    # 条件边：质量检查后决定是否重试
    workflow.add_conditional_edges(
        "quality_checker",
        route_after_quality_check,
        {"retry": "hybrid_retriever", "finish": "response_formatter"}
    )

    # MemorySaver 存档（支持断点恢复）
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
```

---

## 第四部分：完整 CLI 应用

### 1. CLI 命令设计

```
📚 企业级 RAG 智能知识库问答系统
================================

文档管理:
  /import <路径>         导入单个文档（PDF/DOCX/MD/TXT）
  /import_dir <目录>     批量导入目录下所有文档
  /list                  列出已导入文档
  /delete <名称>         删除指定文档
  /stats                 查看知识库统计信息

会话管理:
  /history               查看当前会话历史
  /clear                 清空当前会话
  /session <id>          切换到指定会话

系统:
  /quit                  退出应用

其他: 直接输入问题进行智能问答
```

### 2. 问答交互流程

```
👤 用户 > /import ./docs/员工手册_2024.md
✅ 成功导入: 员工手册_2024.md (12 个文本块已入库)

👤 用户 > 年假有多少天？

🤔 正在分析问题...
📝 改写查询: "员工手册中年假有多少天"
🔍 混合检索中... (向量 Top-5 + BM25 Top-5 → RRF 融合)
📊 LLM 重排序... (5 个候选 → 3 个高相关)
✍️ 生成回答中...
✅ 质量评分: 8/10

🤖 AI > 根据员工手册，正式员工入职满一年后可享受 15 天带薪年假。[1]
兼职员工年假天数按实际工作时长折算。[2]

📖 参考来源:
[1] 员工手册_2024.md > 休假制度 > 年假，第 3 页
[2] 员工手册_2024.md > 休假制度 > 兼职员工，第 4 页

👤 用户 > 兼职员工呢？

🤔 正在分析问题...
📝 改写查询: "兼职员工的年假天数规定"
🔍 混合检索中...
📊 LLM 重排序...
✍️ 生成回答中...
✅ 质量评分: 9/10

🤖 AI > 兼职员工的年假天数按实际工作时长折算，每周工作满 20 小时
可享受 1.5 天年假。[1]

📖 参考来源:
[1] 员工手册_2024.md > 休假制度 > 兼职员工，第 4 页
```

### 3. 主循环实现

```python
def run_cli_app():
    """CLI 主循环。"""
    app = build_workflow()
    print_welcome()

    current_session = DEFAULT_SESSION_ID
    thread_config = {"configurable": {"thread_id": current_session}}

    while True:
        try:
            user_input = input("👤 用户 > ").strip()
            if not user_input:
                continue

            # 处理斜杠命令
            if user_input.startswith("/"):
                handle_command(user_input, current_session)
                continue

            # 问答交互
            result = app.invoke(
                {"query": user_input},
                thread_config
            )
            print(f"\n🤖 AI > {result['answer']}")
            if result.get("citations"):
                print(f"\n📖 参考来源:\n{result['citations'][0]}")

        except (KeyboardInterrupt, EOFError):
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
```

---

## 核心原理深度解析

### LangGraph vs. LCEL 链的编排对比

| 维度 | LCEL 链 (Day 10) | LangGraph (Day 19) |
|------|-------------------|-------------------|
| 流程定义 | 线性管道 `A \| B \| C` | 有向图，支持循环和条件分支 |
| 状态管理 | 隐式（管道输出传递） | 显式 TypedDict + Reducer |
| 条件分支 | 不支持 | 条件边（如质量检查→重试/输出） |
| 重试循环 | 不支持 | 条件边回环（如 quality_checker → hybrid_retriever） |
| 断点调试 | 不支持 | MemorySaver + checkpoint |
| 可视化 | 无 | `graph.get_graph().draw_mermaid()` |

### 质量闭环的本质：Self-Reflection 在 RAG 中的应用

Day 13 的 Self-Reflection 模式是"Agent 检查自己的输出并纠错"。Day 19 的质量闭环是同样的思路应用在 RAG 场景：

```
Day 13 Self-Reflection:          Day 19 质量闭环:
生成回答 → 评估 → 不满意 → 重新生成   检索 → 生成 → 评估 → 不满意 → 重新检索+生成
```

但有一个关键区别：Day 13 的重试是重新生成（同样的输入），而 Day 19 的重试是重新检索（不同的文档子集），因为 RAG 的回答质量主要取决于检索质量，而非生成质量。

### 指代消解的替代方案

| 方案 | 优点 | 缺点 |
|------|------|------|
| LLM 改写（我们的方案） | 灵活，能处理复杂指代 | 额外一次 LLM 调用 |
| 简单拼接历史 | 零额外调用 | 拼接后查询可能过长，影响检索精度 |
| 规则替换 | 速度快，无 LLM 开销 | 只能处理预定义模式（"它"→上一个实体） |

LLM 改写是最通用的方案，也是生产环境中常用的做法。

### 企业级 RAG 的性能考量

| 组件 | 延迟 | 优化策略 |
|------|------|---------|
| 文档导入 | 秒级（一次性） | 异步批量处理 |
| 向量检索 | ~50ms | ChromaDB 内置 HNSW 索引 |
| BM25 检索 | ~10ms | 内存中计算，极快 |
| RRF 融合 | ~1ms | 纯数值计算 |
| LLM Reranker | ~2-5s | 批量打分 / 用轻量模型 |
| 意图改写 | ~1-2s | 缓存常见改写 |
| 回答生成 | ~3-8s | 流式输出提升体验 |
| 质量检查 | ~1-2s | 只在首次低分时重试 |

总体延迟约 **8-20 秒**（含重试），可通过流式输出和缓存优化到 **5-10 秒**的体感延迟。

---

## 课后练习

1. **指代消解效果测试**：设计 5 组多轮对话（每组 3-5 轮），测试 IntentResolver 的改写准确率。关注：代词替换、省略补充、上下文推断。

2. **质量闭环实验**：准备 3 个"刁钻问题"（知识库中没有明确答案的问题），观察 QualityChecker 是否能正确判定需要重试，以及重试后是否能给出合理的"无法回答"响应。

3. **引用溯源完整性检查**：对 10 个问答结果，逐一验证回答中标注的 `[1]`、`[2]` 引用是否与实际参考文档内容一致。统计引用准确率。

4. **架构扩展思考**：如果需要支持"跨文档对比"类问题（如"对比文档 A 和文档 B 中关于 XX 的不同观点"），当前的架构需要做哪些改动？画出改动后的工作流图。

5. **端到端验收**：导入一份真实文档（技术文档、公司制度、学习笔记等），进行 10 轮以上连续问答，记录每个环节的输出质量，写一份简短的体验报告。

6. **Flake8 自检**：确保代码通过 `flake8 project_07_enterprise_rag/` 的检查。
