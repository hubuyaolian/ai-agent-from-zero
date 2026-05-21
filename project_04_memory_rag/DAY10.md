# Day 10 课程：完整 RAG Agent — 从文档到智能问答 📚

经过 Day 9 的学习，我们已经掌握了 RAG 的三大基础组件：**Embedding 向量化**、**ChromaDB 向量存储**、**文档加载与分块**。

今天我们要把这些零件**组装成一台完整的机器**——一个能够读取你的私有文档、理解其中的内容、并准确回答相关问题的 RAG Agent。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：最简 RAG 流水线](#第一部分最简-rag-流水线)
3. [第二部分：RAG 作为 Agent 的工具](#第二部分rag-作为-agent-的工具)
4. [第三部分：个人知识库问答应用](#第三部分个人知识库问答应用)
5. [核心原理深度解析](#核心原理深度解析)
6. [课后练习](#课后练习)

---

## 学习目标
- 掌握完整的 RAG 流水线：加载 → 分块 → 嵌入 → 存储 → 检索 → 生成。
- 理解 Retriever（检索器）在 LangChain 中的抽象。
- 学会将 RAG 检索封装为 Agent 的一个工具，与其他工具协同工作。
- 从零搭建一个支持多文档导入和智能问答的个人知识库应用。

---

## 第一部分：最简 RAG 流水线

### 1. RAG 是什么？

**RAG (Retrieval-Augmented Generation，检索增强生成)** 是当前最实用的大模型应用模式之一。它的核心思路是：

> 不要让大模型凭自己的"记忆"回答问题，而是先从外部知识库中**检索**最相关的文档片段，然后把这些片段作为上下文**喂给**大模型，让它基于真实资料生成回答。

```
用户提问                     知识库 (ChromaDB)
"LangGraph 是什么？"              │
      │                          │
      ▼                          ▼
┌─────────────┐         ┌──────────────────┐
│ Embedding   │────────►│ 相似度检索 Top-K   │
│ 向量化查询   │         │ (HNSW 算法)       │
└─────────────┘         └────────┬─────────┘
                                 │
                    检索到的文档片段:
                    "LangGraph 是 LangChain 的
                     Agent 编排框架，使用图结构..."
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │ 大模型 (LLM)            │
                    │ System: 基于以下资料回答  │
                    │ Context: [检索到的片段]   │
                    │ Question: [用户问题]     │
                    └────────────┬───────────┘
                                 │
                                 ▼
                    "LangGraph 是由 LangChain 团队
                     开发的 Agent 编排框架，它将
                     Agent 的执行流程建模为有向图..."
```

### 2. RAG 的完整流水线

RAG 分为**离线索引阶段**和**在线查询阶段**：

#### 离线索引阶段（一次性执行）
```
原始文档           文本分块            向量化              存入向量库
(.txt/.md/.pdf) → [chunk1, chunk2] → [vec1, vec2, ...] → ChromaDB
```

#### 在线查询阶段（每次用户提问时）
```
用户问题 → 向量化 → 检索 Top-K → 拼接 Prompt → LLM 生成 → 返回答案
```

### 3. 用 LangChain 实现最简 RAG

```python
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ---- 离线索引 ----
# 1. 加载文档
docs = loader.load()
# 2. 分块
chunks = text_splitter.split_documents(docs)
# 3. 存入向量库（自动调用 Embedding 模型）
vectorstore = Chroma.from_documents(chunks, embeddings)

# ---- 在线查询 ----
# 4. 创建检索器
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 5. 构建 RAG Prompt
rag_prompt = ChatPromptTemplate.from_template("""
基于以下参考资料回答用户的问题。如果资料中没有相关信息，请如实说明。

参考资料：
{context}

用户问题：{question}

请用中文回答：
""")

# 6. 组装 RAG 链
def format_docs(docs):
    """将检索到的文档列表格式化为纯文本。"""
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | rag_prompt
    | model
    | StrOutputParser()
)

# 7. 使用
answer = rag_chain.invoke("LangGraph 的核心概念有哪些？")
print(answer)
```

> 📖 **代码实战**：查看并运行 [08_simple_rag.py](file:///Users/huangyang/code/agent/project_04_memory_rag/08_simple_rag.py)

---

## 第二部分：RAG 作为 Agent 的工具

### 1. 为什么要把 RAG 变成工具？

在第一部分中，RAG 链是一个独立的流水线。但在实际应用中，Agent 不一定每次都需要检索知识库——有些问题（如"1+1等于几？"）大模型可以直接回答，不需要浪费检索资源。

最佳实践是：**把 RAG 检索封装为 Agent 的一个工具，让大模型自主决定什么时候使用它。**

```python
@tool
def search_knowledge_base(query: str) -> str:
    """从个人知识库中检索与查询相关的信息。

    当用户询问特定的技术文档、项目资料、或私有知识库中的内容时，
    使用此工具进行检索。

    Args:
        query: 用户的问题或检索关键词。

    Returns:
        检索到的最相关文档片段。
    """
    # 调用 retriever 检索
    docs = retriever.invoke(query)
    # 格式化检索结果
    if not docs:
        return "知识库中未找到相关信息。"
    results = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "未知来源")
        results.append(f"[资料 {i + 1}] (来源: {source})\n{doc.page_content}")
    return "\n\n".join(results)
```

### 2. RAG Tool + 其他工具的协同

```
用户: "帮我查一下项目文档中关于部署的说明，然后把要点整理成一个清单，保存到 deploy_checklist.txt"

Agent 思考流程:
├── 步骤 1: 调用 search_knowledge_base("部署说明")   ← RAG 工具
│   → 检索到 3 段相关文档
├── 步骤 2: 基于检索结果，整理要点清单               ← LLM 自身能力
└── 步骤 3: 调用 write_file("deploy_checklist.txt")  ← 文件工具
    → 保存成功
```

> 📖 **代码实战**：查看并运行 [09_rag_agent.py](file:///Users/huangyang/code/agent/project_04_memory_rag/09_rag_agent.py)

---

## 第三部分：个人知识库问答应用

将所有能力整合，构建一个完整的个人知识库问答应用。

### 1. 功能架构

```
KnowledgeBaseApp
├── DocumentManager            # 文档管理
│   ├── /import <路径>         # 导入文档（支持 .txt / .md / .pdf）
│   ├── /import_dir <目录>     # 批量导入整个目录
│   ├── /list_docs             # 列出已导入的文档
│   └── /delete_doc <名称>     # 删除指定文档
│
├── VectorStore (ChromaDB)     # 向量存储
│   ├── 自动分块 + Embedding
│   └── 持久化到本地目录
│
├── RAGEngine                  # 检索增强生成引擎
│   ├── Retriever              # 检索器（Top-K 语义检索）
│   ├── Prompt Template        # RAG 提示词模板
│   └── LLM                   # 大模型生成
│
└── CLI Interface
    ├── 直接提问               # 基于知识库的智能问答
    ├── /source                # 显示上次回答的参考来源
    ├── /stats                 # 显示知识库统计信息
    └── /quit                  # 退出
```

### 2. 使用流程演示

```
📚 个人知识库问答系统
================================

> /import ./docs/langchain_guide.md
✅ 成功导入文档: langchain_guide.md (分为 24 个文本块)

> /import ./docs/python_best_practices.txt
✅ 成功导入文档: python_best_practices.txt (分为 18 个文本块)

> /stats
📊 知识库统计:
   - 文档数量: 2
   - 文本块数量: 42
   - 向量维度: 1024

> LangChain 中的 LCEL 是什么？
🤖 LCEL（LangChain Expression Language）是 LangChain 提供的一种声明式链构建语法。
   它使用管道操作符 `|` 将多个组件串联起来...

   📖 参考来源:
   [1] langchain_guide.md (第 3 章)
   [2] langchain_guide.md (第 5 章)
```

### 3. RAG 的质量优化技巧

| 优化维度 | 技巧 | 效果 |
|---------|------|------|
| 分块策略 | 按语义段落分块，而非固定字符数 | 减少语义截断 |
| 检索数量 | 根据问题复杂度动态调整 K 值 | 平衡精确度与噪音 |
| 重排序 | 对检索结果用 LLM 重新打分排序 | 提高相关性 |
| Prompt | 明确指示"仅基于资料回答，不确定时说不知道" | 减少幻觉 |
| 元数据过滤 | 按文档来源、日期等过滤检索范围 | 提高针对性 |

> 📖 **代码实战**：查看并运行 [10_knowledge_base_app.py](file:///Users/huangyang/code/agent/project_04_memory_rag/10_knowledge_base_app.py)

---

## 核心原理深度解析

### RAG vs. 微调 (Fine-tuning) 的选择

| 维度 | RAG | 微调 |
|------|-----|------|
| 知识更新 | 即时（替换文档即可） | 需要重新训练 |
| 成本 | 低（只需向量库 + API 调用） | 高（需要 GPU + 训练时间） |
| 准确性 | 可追溯来源，可验证 | 知识内化，不可追溯 |
| 适用场景 | 事实性问答、文档检索 | 风格模仿、领域专精 |
| 幻觉风险 | 较低（有真实文档约束） | 较高 |
| 实施难度 | ⭐⭐ 简单 | ⭐⭐⭐⭐ 复杂 |

> **结论**：对于大多数企业级应用，RAG 是首选方案。微调通常只在需要模型"内化"某种特殊能力（如行业术语理解、特殊输出格式）时才考虑。

### 检索器 (Retriever) 的进阶模式

LangChain 提供了多种检索器，满足不同场景：

```
Retriever 家族
├── VectorStoreRetriever       # 基础语义检索（我们正在用的）
├── MultiQueryRetriever        # 自动将用户问题改写为多个查询，合并结果
├── ContextualCompressionRetriever  # 对检索结果进行压缩，去除无关部分
├── EnsembleRetriever          # 混合检索（语义 + 关键词 BM25）
├── SelfQueryRetriever         # LLM 自动从问题中提取元数据过滤条件
└── ParentDocumentRetriever    # 检索小块，返回大块（解决上下文不完整问题）
```

### RAG 的"幻觉"问题与缓解

即使使用了 RAG，大模型仍然可能产生"幻觉"（编造不存在的内容）。缓解策略包括：

1. **Prompt 约束**：在系统提示中明确要求"仅基于提供的资料回答，如果资料中没有相关信息，请回答'根据现有资料无法回答此问题'"。
2. **来源引用**：要求模型在回答中标注引用来源（如"根据资料[1]..."），便于用户验证。
3. **置信度过滤**：当检索结果的相似度分数低于阈值时，直接告知用户"未找到相关信息"，而不是强行生成。

### 4. 跨阶段整合：将 RAG 工具集成到 Day 7 的 LangGraph Agent 中

在 Day 10 中，我们学会了用 `@tool` 将 RAG 知识库检索定义为一个工具。很多学员在学完这里后，会面临如何将它与 Day 7 的“多工具 LangGraph Agent”进行整合的疑问。

实际上，因为我们遵循了**统一的 `@tool` 规范**，整合工作极其简单！只需要两步：
1. 从 `tools/` 目录下（或者你单独定义 RAG 工具的文件中）导入它。
2. 把它作为普通的工具，放入到工具列表中，绑定到大模型，并提供给 LangGraph 的工具节点。

以下是完整的整合概念代码示例：

```python
# 示例代码：多工具 LangGraph Agent + RAG 知识库工具
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# 1. 导入已有的基础工具和新增的 RAG 知识库工具
from project_03_tool_agent.tools import ALL_TOOLS  # calculator, web_search 等
from project_04_memory_rag.DAY10 import search_knowledge_base  # RAG 检索工具

# 2. 组装最终的工具列表
MY_AGENT_TOOLS = ALL_TOOLS + [search_knowledge_base]

# 3. 创建绑定了全部工具的 LLM
model = ChatOpenAI(model="qwen-plus").bind_tools(MY_AGENT_TOOLS)

# 4. 定义 LangGraph 状态
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# 5. 定义节点逻辑
def call_model(state: AgentState):
    """大模型节点逻辑。"""
    response = model.invoke(state["messages"])
    return {"messages": [response]}

# 6. 构建状态图
workflow = StateGraph(AgentState)

# 添加大模型节点和工具节点
workflow.add_node("agent", call_model)
workflow.add_node("action", ToolNode(MY_AGENT_TOOLS))  # 自动执行 RAG 或其他基础工具

# 设置节点边关系
workflow.set_entry_point("agent")

def should_continue(state: AgentState):
    """条件路由：根据大模型是否输出 tool_calls 决定去往何处。"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "action"
    return END

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "action": "action",
        "end": END
    }
)
workflow.add_edge("action", "agent")

app = workflow.compile()
```

> 💡 **架构的优雅之处**：
> 通过 `@tool` 这一层标准抽象，**你的 RAG 知识库与计算器、网络搜索工具在地位上是完全平等的**。大模型会根据用户提问，自动选择是调用 `calculator` 计算，还是调用 `search_knowledge_base` 搜索私有文档，真正实现“混合能力编排”！

---

## 课后练习

1. **导入你自己的文档**：选择你手头的任意文档（学习笔记、技术文档等），导入到知识库应用中，测试问答效果。

2. **检索质量评估**：准备 5 个你知道答案的问题，分别检索并记录：(a) 检索到的文档是否真的包含答案，(b) 大模型基于检索结果生成的回答是否准确。计算准确率。

3. **多查询检索**：使用 `MultiQueryRetriever` 替换基础检索器，对比同一组问题的检索效果差异。`MultiQueryRetriever` 会自动将用户问题改写为 3-5 个不同表述的查询。

4. **混合检索**：尝试使用 `EnsembleRetriever` 将语义检索与关键词检索（BM25）结合，测试对中文技术文档的检索效果是否有改善。

5. **Flake8 自检**：确保代码通过 `flake8 project_04_memory_rag/` 的检查。
