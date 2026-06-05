# Day 18 课程：企业级 RAG 架构入门 — 混合检索、权限过滤与评估基线 🏗️

在 Day 10 中，我们构建了一个基础的 RAG 知识库问答应用。它能够加载文档、分块、向量化、检索并生成回答——但对于企业场景，这个基础版本存在几个核心缺陷：

1. **单路检索盲区**：仅依赖向量语义检索，遇到"关键词精确匹配"类问题（如产品编号、专有名词）容易漏检。
2. **分块质量粗糙**：固定字符数切割会截断语义段落，导致检索到的上下文不完整。
3. **无对话记忆**：每次问答完全独立，无法处理多轮对话中的指代消解（如"它支持什么格式？"中的"它"指什么）。
4. **无来源溯源**：回答无法追溯到具体文档和页码，用户无法验证答案的可信度。
5. **无质量闭环**：检索到的文档可能完全不相关，但系统仍会强行生成回答（幻觉风险）。

今天的课程会从架构层面补齐这些能力，构建一套**企业级 RAG 的教学版雏形**。注意：这里的代码仍以学习和本地验证为目标，不应直接等同于生产系统。真正的企业级落地还需要权限隔离、审计、索引生命周期、自动化评估和运维监控。

> 技术状态说明（2026）：向量检索 + BM25 + RRF 融合 + Reranker 仍是主流 RAG 检索路线，不落后。但具体模型和基础设施要更新：新建 Qwen 检索项目优先考虑 `text-embedding-v4` 或 Qwen3 Embedding/Reranker；`text-embedding-v3` 更适合兼容已有 v3 索引。ChromaDB、SQLite、pickle 在本课中作为本地教学实现，生产环境通常会换成托管向量检索、全文检索、对象存储和权限系统。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：企业级 RAG 的架构演进](#第一部分企业级-rag-的架构演进)
3. [第二部分：文档摄取与智能分块](#第二部分文档摄取与智能分块)
4. [第三部分：多路召回与融合检索](#第三部分多路召回与融合检索)
5. [第四部分：权限过滤、索引治理与评估基线](#第四部分权限过滤索引治理与评估基线)
6. [核心原理深度解析](#核心原理深度解析)
7. [课后练习](#课后练习)

---

## 学习目标
- 理解基础 RAG 到企业级 RAG 的架构演进路线。
- 掌握标题感知 + 语义边界的混合分块策略。
- 理解向量检索、BM25 关键词检索和 RRF 融合的原理。
- 掌握专用 Reranker 与 LLM 重排的差异和适用边界。
- 理解文档元数据、权限过滤、版本治理对企业 RAG 的影响。
- 建立最小可用的 RAG 评估基线，而不是只看单次回答效果。

---

## 第一部分：企业级 RAG 的架构演进

### 1. 基础 RAG 的架构回顾

Day 10 的基础 RAG 是一条简单的线性流水线：

```
文档 → 固定分块 → Embedding → ChromaDB → 向量检索 Top-K → Prompt + LLM → 回答
```

这条流水线能工作，但每个环节都是"最简实现"，在企业场景下会遇到各种瓶颈。

### 2. 基础 RAG 的五大瓶颈

| 瓶颈 | 原因 | 后果 |
|------|------|------|
| 检索盲区 | 仅语义检索，对精确关键词匹配弱 | 专有名词、产品编号类问题漏检 |
| 分块截断 | 固定字符数切割，不顾语义边界 | 上下文被拦腰截断，LLM 看到残缺信息 |
| 上下文断裂 | 每次问答独立，无历史记忆 | "它是什么？"无法理解"它"指代什么 |
| 幻觉风险 | 检索结果可能不相关但仍生成 | 编造不存在的"事实" |
| 不可溯源 | 回答无法关联到原文出处 | 用户无法验证可信度 |

### 3. 企业级 RAG 的整体架构

针对上述瓶颈，企业级 RAG 至少要在七个层面做升级：

```
┌─────────────────────────────────────────────────────────────┐
│                  企业级 RAG 教学版架构                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─── 文档摄取层 ───┐    ┌─── 检索增强层 ───┐              │
│  │ DocumentLoader   │    │ VectorRetriever   │              │
│  │ (PDF/DOCX/MD/TXT)│    │ (ChromaDB 语义)   │              │
│  │       ↓          │    │       +           │              │
│  │ HybridChunker    │    │ BM25Retriever     │              │
│  │ (标题感知+语义)   │    │ (jieba 关键词)    │              │
│  │       ↓          │    │       ↓           │              │
│  │ Metadata治理      │    │ RRF 融合排序      │              │
│  └──────────────────┘    │       ↓           │              │
│                          │ Reranker          │              │
│  ┌─── 记忆管理层 ───┐    │ (精排+过滤)       │              │
│  │ ConversationStore│    └───────────────────┘              │
│  │ (SQLite 多会话)   │              ↓                      │
│  │       +          │    ┌─── 生成与溯源层 ───┐             │
│  │ IntentResolver   │    │ Prompt + LLM      │              │
│  │ (指代消解)        │    │       ↓           │              │
│  └──────────────────┘    │ QualityChecker    │              │
│                          │ (证据评估+重试)    │              │
│                          │       ↓           │              │
│                          │ CitationVerifier  │              │
│                          │ (引用校验+溯源)    │              │
│                          └───────────────────┘              │
│                                     ↓                      │
│  ┌─── 治理与评估层 ───┐    ┌─── 编排层 ───┐                 │
│  │ ACL/tenant filter  │    │ LangGraph    │                 │
│  │ Eval dataset       │    │ 状态图+重试   │                 │
│  │ Audit log          │    └──────────────┘                 │
│  └────────────────────┘                                      │
└─────────────────────────────────────────────────────────────┘
```

### 4. 目录结构设计

```
project_07_enterprise_rag/
├── config.py                    # 项目级配置（路径、模型、阈值）
├── main.py                      # CLI 入口
├── ingestion/                   # 文档摄取与预处理
│   ├── __init__.py
│   ├── loader.py                # DocumentLoaderFactory
│   └── chunker.py               # HybridChunker
├── retrieval/                   # 检索与重排
│   ├── __init__.py
│   ├── vector_store.py          # VectorStoreManager
│   ├── keyword_search.py        # KeywordSearcher
│   ├── hybrid_retriever.py      # HybridRetriever
│   └── reranker.py              # Reranker
├── governance/                  # 权限、版本与审计
│   ├── __init__.py
│   ├── metadata.py              # DocumentMetadata / ChunkMetadata
│   ├── access_filter.py         # tenant_id + acl_tags 过滤
│   └── audit_log.py             # 检索与回答审计
├── evaluation/                  # RAG 质量评估
│   ├── __init__.py
│   ├── datasets.py              # eval questions + gold evidence
│   └── metrics.py               # Recall@K / MRR / groundedness
├── memory/                      # 对话记忆
│   ├── __init__.py
│   └── conversation_store.py    # ConversationStore
├── citation/                    # 来源溯源
│   ├── __init__.py
│   └── source_tracker.py        # SourceTracker
├── graph/                       # LangGraph 工作流
│   ├── __init__.py
│   ├── state.py                 # EnterpriseRAGState
│   └── workflow.py              # LangGraph 状态图
└── requirements.txt
```

---

## 第二部分：文档摄取与智能分块

### 1. DocumentLoaderFactory — 多格式统一加载

Day 10 只支持 `.txt` 和 `.md`。企业场景需要处理 PDF、Word 文档等格式。我们设计一个工厂类，根据文件扩展名自动选择加载器：

| 格式 | LangChain 加载器 | 额外依赖 |
|------|------------------|---------|
| `.pdf` | `PyPDFLoader` | `pypdf` |
| `.docx` | `Docx2txtLoader` | `docx2txt` |
| `.md` | 自定义读取 | — |
| `.txt` | 自定义读取 | — |

```python
class DocumentLoaderFactory:
    """文档加载器工厂。"""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}

    @classmethod
    def load(cls, file_path: str) -> List[Document]:
        """根据文件扩展名自动选择加载器，统一输出 List[Document]。"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的格式: {ext}")

        loader_map = {
            ".pdf": cls._load_pdf,
            ".docx": cls._load_docx,
            ".md": cls._load_markdown,
            ".txt": cls._load_text,
        }
        return loader_map[ext](file_path)

    @classmethod
    def load_directory(cls, dir_path: str) -> List[Document]:
        """递归加载目录下所有支持的文档。"""
        # 遍历目录，过滤 SUPPORTED_EXTENSIONS，逐个调用 load()
```

每个 Document 的 metadata 不能只保留文件名。教学版至少统一包含：

| 字段 | 说明 |
|------|------|
| `doc_id` | 文档稳定 ID，优先由文件路径 + 内容 hash 生成 |
| `source` | 原始文件路径或对象存储 URI |
| `page` | 页码或段落位置 |
| `format` | 文件类型 |
| `content_hash` | 内容 hash，用于去重和判断是否需要重建索引 |
| `version` | 文档版本号或导入批次 |
| `tenant_id` | 租户或组织 ID |
| `acl_tags` | 可访问角色、部门或用户组 |

生产场景还要处理扫描 PDF 的 OCR、表格结构、图片说明、HTML 噪音、附件版本和删除传播。本课只实现最小字段，但要从一开始保留这些扩展位。

### 2. HybridChunker — 标题感知 + 语义边界分块

Day 10 使用的 `RecursiveCharacterTextSplitter` 是按固定字符数切割的，它有一个致命问题：

```
原文：
┌─────────────────────────────────────┐
│ # 部署指南                          │
│ ## 1. 环境准备                      │
│ 需要 Python 3.10+、Docker 20.10+... │
│ ## 2. 配置说明                      │  ← 固定 300 字符截断点
│ 数据库连接字符串格式为...            │  ← 被切到下一个 chunk
└─────────────────────────────────────┘

固定分块结果：
chunk 1: "# 部署指南\n## 1. 环境准备\n需要 Python 3.10+..."  ← 完整
chunk 2: "数据库连接字符串格式为..."                              ← 丢失标题上下文！
```

chunk 2 丢失了"## 2. 配置说明"的标题，LLM 看到这段文字时不知道它属于哪个章节。

**HybridChunker 的两阶段策略**：

**阶段 1：标题感知切分** — 按文档的标题结构（Markdown 的 `#`/`##`/`###`，或自然段落边界）将文档拆分为语义段落。每个段落保持主题完整。

**阶段 2：语义边界微调** — 对超长段落使用 `RecursiveCharacterTextSplitter` 二次切分（示例参数：chunk_size=500, chunk_overlap=100），确保不超出 Embedding 模型的最佳输入长度；对过短段落（<100 字符）合并到相邻段落。

参数不是固定真理。不同模型、文档类型和语言会改变最佳 chunk 大小。更严谨的做法是把 chunk 参数纳入评估实验，用 Recall@K、引用准确率和人工抽查决定默认值。

```python
class HybridChunker:
    """混合分块器：标题感知 + 语义边界微调。"""

    def __init__(self, chunk_size=500, chunk_overlap=100, min_chunk_size=100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def split(self, documents: List[Document]) -> List[Document]:
        """对文档列表执行两阶段分块。"""
        result = []
        for doc in documents:
            # 阶段 1: 标题感知切分
            sections = self._split_by_headings(doc)
            # 阶段 2: 语义边界微调
            for section in sections:
                if len(section.page_content) > self.chunk_size:
                    result.extend(self._recursive_split(section))
                elif len(section.page_content) < self.min_chunk_size:
                    # 过短段落合并到相邻段落（逻辑略）
                    pass
                else:
                    result.append(section)
        return result
```

每个 chunk 的 metadata 继承父文档字段，并新增：

| 字段 | 说明 |
|------|------|
| `chunk_id` | 稳定块 ID，建议 `doc_id + content_hash + chunk_index` |
| `chunk_index` | 当前版本内的块编号 |
| `heading_path` | 标题层级路径，如 `"部署指南 > 配置说明"` |
| `char_start` / `char_end` | 在原文中的字符范围，便于回溯和高亮 |

后续 RRF 融合、引用标注和删除更新都应使用 `chunk_id`，不要只依赖 `source + chunk_index`。

---

## 第三部分：多路召回与融合检索

### 1. 为什么需要多路召回？

向量语义检索擅长"意思相近"的匹配，但对精确关键词匹配天然偏弱：

| 问题类型 | 向量检索 | BM25 关键词检索 |
|---------|---------|---------------|
| "LangGraph 的核心概念" | ✅ 语义相近，容易命中 | ⚠️ 需要分词精确匹配 |
| "产品编号 SKU-2024-A" | ❌ 语义检索无法匹配编号 | ✅ 精确关键词匹配 |
| "RAG 和微调的区别" | ✅ 语义匹配 | ⚠️ 可能匹配到不相关的 RAG 文档 |
| "部署报错 ERR_CONN_REFUSED" | ❌ 错误码语义无关 | ✅ 精确匹配错误码 |

**结论**：两种检索方式互补，融合使用效果最佳。

### 2. 向量检索 — VectorStoreManager

复用 Day 9-10 的 Qwen Embedding + ChromaDB 模式，封装为类：

```python
class VectorStoreManager:
    """ChromaDB 向量存储管理器。"""

    def __init__(self, persist_directory, embedding_provider="qwen"):
        self.embeddings = self._create_embeddings(embedding_provider)
        self.persist_directory = persist_directory

    def add_documents(self, docs, collection_name="default"):
        """批量入库：分块 → Embedding → 存入 ChromaDB。"""

    def similarity_search(self, query, k=5, collection_name="default"):
        """向量相似检索，返回 Top-K 文档。"""

    def delete_collection(self, collection_name="default"):
        """删除整个集合。"""

    def get_stats(self):
        """获取集合统计信息（文档数、chunk 数等）。"""
```

Embedding 可以通过 `OpenAIEmbeddings` 接入 Qwen 兼容接口。新建项目优先考虑 `text-embedding-v4` 或 Qwen3 Embedding；如果 Day 9 已经用 `text-embedding-v3` 建过索引，继续使用 v3 是为了兼容旧向量空间，不能和 v4/Qwen3 向量混入同一集合。

### 3. 关键词检索 — KeywordSearcher (BM25)

BM25 是信息检索领域的经典算法，基于词频-逆文档频率（TF-IDF）的改进版本。它不依赖语义，而是通过**词频统计**计算文档与查询的相关性。

中文场景下需要先分词。教学版用 `jieba` 足够理解原理；生产环境通常会使用 Elasticsearch、Azure AI Search、OpenSearch、PostgreSQL FTS 或其他全文检索服务，并配置中文分词器、同义词、停用词和字段权重。

```python
class KeywordSearcher:
    """BM25 关键词检索器，支持 jieba 中文分词。"""

    def __init__(self, index_dir):
        self.index_dir = index_dir
        self._indexes = {}   # collection_name → BM25Okapi 实例
        self._docs = {}      # collection_name → List[Document]

    def index_documents(self, docs, collection_name="default"):
        """构建 BM25 索引：jieba 分词 → BM25Okapi → pickle 持久化。"""
        tokenized = [list(jieba.cut(doc.page_content)) for doc in docs]
        self._indexes[collection_name] = BM25Okapi(tokenized)
        self._docs[collection_name] = docs
        # 持久化到 pickle 文件

    def search(self, query, k=5, collection_name="default"):
        """BM25 检索，返回 Top-K 文档，格式与向量检索统一。"""
        query_tokens = list(jieba.cut(query))
        scores = self._indexes[collection_name].get_scores(query_tokens)
        # 按分数降序取 Top-K
```

注意：pickle 只适合本地可信环境。不要在生产系统中加载外部来源的 pickle 文件；生产索引应由受控服务或安全的序列化格式管理。

### 4. HybridRetriever — RRF 融合

**倒数排名融合 (Reciprocal Rank Fusion, RRF)** 是一种简单有效的多路结果融合算法：

```
向量检索 Top-K₁ ──→ 排名列表 R₁
                          │
BM25 检索 Top-K₂ ──→ 排名列表 R₂
                          │
                    ┌─────▼──────┐
                    │  RRF 融合   │
                    │             │
                    │ score(d) =  │
                    │  Σ 1/(k+rank)│
                    │             │
                    └─────┬──────┘
                          │
                    合并去重 Top-K
```

RRF 公式：`score(d) = Σ 1/(k + rank_i(d))`

其中 `k` 是平滑常数（默认 60），`rank_i(d)` 是文档 d 在第 i 路检索中的排名位置。

```python
class HybridRetriever:
    """多路召回 + RRF 融合检索器。"""

    def __init__(self, vector_manager, keyword_searcher, rrf_k=60):
        self.vector_manager = vector_manager
        self.keyword_searcher = keyword_searcher
        self.rrf_k = rrf_k

    def retrieve(self, query, k=5, collection_name="default"):
        """多路召回 + RRF 融合。"""
        # 路线 1: 向量检索 Top-K
        vector_docs = self.vector_manager.similarity_search(
            query, k=k, collection_name=collection_name
        )
        # 路线 2: BM25 检索 Top-K
        keyword_docs = self.keyword_searcher.search(
            query, k=k, collection_name=collection_name
        )
        # RRF 融合
        return self._rrf_fuse(vector_docs, keyword_docs, k)

    def _rrf_fuse(self, vector_docs, keyword_docs, k):
        """对两路结果执行 RRF 融合排序。"""
        scores = {}
        for rank, doc in enumerate(vector_docs):
            doc_id = doc.metadata["chunk_id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (self.rrf_k + rank + 1)
        for rank, doc in enumerate(keyword_docs):
            doc_id = doc.metadata["chunk_id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (self.rrf_k + rank + 1)
        # 按融合分数降序排列，取 Top-K
```

### 5. Reranker — 专用重排优先，LLM 打分作为教学兜底

RRF 融合后的候选文档可能仍包含低相关度的结果。生产系统优先使用专用 Reranker（如 Qwen3 Reranker、bge-reranker、Cohere Rerank 等），因为它们延迟更低、输出更稳定，也更适合批量候选排序。

本课为了降低依赖，可以先用 LLM 对候选文档逐一打分（1-10），过滤低于阈值的文档：

```python
RERANK_PROMPT = """
你是一个文档相关性评估专家。

用户问题: {query}
候选文档内容: {doc_content}

请评估该文档与用户问题的相关性，打分 1-10：
- 1-3: 完全不相关
- 4-5: 部分相关
- 6-7: 较为相关
- 8-10: 高度相关

只输出一个数字。
"""
```

重排流程：
1. 多路召回先取较大的候选集，例如向量 Top-20 + BM25 Top-20。
2. 使用专用 Reranker 或轻量 LLM 对候选文档打分。
3. 输出结构化分数和理由，避免只解析自由文本。
4. 过滤低于阈值（默认 5 分）的文档。
5. 按分数降序返回最终 Top-K。

> 💡 **性能优化**：为避免逐个文档串行调用 LLM，可以将多个文档拼入同一次 Prompt 中批量打分。

---

## 第四部分：权限过滤、索引治理与评估基线

### 1. 权限过滤必须发生在生成前

企业 RAG 的第一条红线是：用户不能通过问答看到自己无权访问的文档。权限过滤不能只放在 UI 层，而要进入检索路径：

```
用户身份 → tenant_id / roles / groups
     ↓
查询改写
     ↓
向量检索 + BM25 检索（带 metadata filter）
     ↓
RRF 融合
     ↓
Reranker
     ↓
回答生成
```

教学版可以先实现一个简单的 `AccessFilter`：

```python
class AccessFilter:
    """基于租户和 ACL 标签过滤可见 chunk。"""

    def filter_docs(self, docs, user_context):
        allowed = []
        for doc in docs:
            meta = doc.metadata
            same_tenant = meta.get("tenant_id") == user_context.tenant_id
            acl_tags = set(meta.get("acl_tags", []))
            can_access = bool(acl_tags & set(user_context.roles))
            if same_tenant and can_access:
                allowed.append(doc)
        return allowed
```

如果向量库支持 metadata filter，应尽量在检索时过滤；如果不支持，也必须在 rerank 和生成前做二次过滤。

### 2. 索引生命周期

真实文档会更新、删除、撤权。RAG 索引必须能处理这些变化：

| 场景 | 要求 |
|------|------|
| 文档新增 | 写入向量索引、全文索引和文档 registry |
| 文档更新 | 通过 `content_hash` 判断变化，只重建受影响 chunk |
| 文档删除 | 删除向量索引和 BM25 索引中的相关 chunk |
| 权限变化 | 更新 metadata filter，不一定重算 embedding |
| 模型升级 | 新建集合重建索引，不混用不同 embedding 空间 |

### 3. 最小评估基线

不要只靠“问几个问题看起来不错”。本项目至少维护一份 `evaluation/datasets.py`：

```python
EVAL_CASES = [
    {
        "question": "员工入职满一年后年假是多少天？",
        "expected_answer_contains": ["15 天"],
        "gold_chunk_ids": ["employee_handbook:v2024:chunk_018"],
        "type": "fact_lookup",
    },
    {
        "question": "SKU-2024-A 的保修周期是什么？",
        "expected_answer_contains": ["12 个月"],
        "gold_chunk_ids": ["product_policy:v3:chunk_041"],
        "type": "exact_match",
    },
]
```

建议先记录四类指标：

| 指标 | 用途 |
|------|------|
| Recall@K | 正确证据是否被检索到 |
| MRR / nDCG | 正确证据排名是否靠前 |
| Citation Accuracy | 回答引用是否真的支撑句子 |
| Groundedness | 回答是否只基于证据 |

离线评估通过后，再做 10 轮以上真实问答验收。

---

## 核心原理深度解析

### 基础 RAG vs. 企业级 RAG 的完整对比

| 维度 | 基础 RAG (Day 10) | 企业级 RAG 入门版 (Day 18-19) |
|------|-------------------|----------------------|
| 文档格式 | .txt / .md | PDF / DOCX / MD / TXT |
| 分块策略 | 固定字符数 | 标题感知 + 语义边界 |
| 检索方式 | 单路向量检索 | 向量 + BM25 双路 + RRF 融合 |
| 重排序 | 无 | 专用 Reranker 优先，LLM 打分兜底 |
| 对话记忆 | 无 | SQLite 多会话 + 指代消解 |
| 来源溯源 | 无 | 引用标注 + 引用校验 + 末尾引用列表 |
| 权限隔离 | 无 | tenant_id + acl_tags 过滤 |
| 质量控制 | 无 | 检索评估 + groundedness 检查 + 重试策略 |
| 编排方式 | LCEL 链 | LangGraph 状态图 |

### RRF 融合的直觉解释

为什么 RRF 用 `1/(k + rank)` 而不是直接相加分数？

因为不同检索路的分数尺度不同：向量检索返回余弦相似度（0-1），BM25 返回 TF-IDF 分数（可能 0-30+）。直接相加就像"1 美元 + 1 人民币 = 2 ？"——单位不同无法相加。

RRF 的巧妙之处在于：**它把分数转换为排名**。排名是跨系统可比较的——"第一名"在哪个系统里都是"第一名"。`1/(k + rank)` 让排名靠前的文档获得更高权重，但衰减平滑（第 1 名和第 2 名的差距不会太大），避免某一路的结果完全主导融合结果。

### BM25 与向量检索的互补性分析

```
知识类型图谱：

  精确匹配 ◄───────────────────► 语义理解
  (产品编号、错误码、专有名词)    (概念解释、对比分析)
       │                              │
    BM25 擅长                     向量检索擅长
       │                              │
       └──────── 融合覆盖 ◄───────────┘
```

实践数据参考（来自多篇 RAG 论文）：

| 检索方式 | 精确匹配类问题召回率 | 语义理解类问题召回率 | 综合 |
|---------|-------------------|-------------------|------|
| 纯向量 | ~60% | ~85% | ~72% |
| 纯 BM25 | ~90% | ~55% | ~72% |
| RRF 融合 | ~88% | ~83% | **~86%** |

融合检索在两类问题上都接近"取长补短"的效果。

### 混合分块的 heading_path 设计

heading_path 是我们为每个 chunk 附加的元数据，记录该 chunk 在文档标题层级中的位置：

```
文档结构：
# 部署指南
## 1. 环境准备
### 1.1 Python 环境
### 1.2 Docker 环境
## 2. 配置说明

chunk 的 heading_path：
- chunk 1: "部署指南 > 1. 环境准备 > 1.1 Python 环境"
- chunk 2: "部署指南 > 1. 环境准备 > 1.2 Docker 环境"
- chunk 3: "部署指南 > 2. 配置说明"
```

这个元数据有两个用途：
1. **检索增强**：用户问"怎么配置 Docker 环境"时，heading_path 中包含"Docker"的 chunk 可以获得额外加分
2. **溯源展示**：引用列表中显示"来源：部署指南 > 1. 环境准备 > 1.2 Docker 环境"，比只显示文件名更有定位价值

### 当前技术路线是否落后？

不落后，但要分清“方法”和“实现”：

| 项目 | 判断 |
|------|------|
| 混合检索（向量 + BM25） | 仍是主流，Azure AI Search、Elasticsearch 等都支持类似路线 |
| RRF 融合 | 仍常用，适合融合不同分数尺度的排序结果 |
| Reranker | 仍必要，但生产上优先专用 reranker，不建议长期用通用 LLM 逐条评分 |
| ChromaDB | 适合本地教学和小型原型，企业生产要看权限、扩展性和运维要求 |
| SQLite 会话存储 | 适合本地教学，不适合多实例服务的共享状态 |
| `text-embedding-v3` | 可继续兼容旧索引，新项目应评估 `text-embedding-v4` 或 Qwen3 Embedding |

---

## 课后练习

1. **分块效果对比**：对同一份 Markdown 文档，分别使用 `RecursiveCharacterTextSplitter`（固定分块）和 `HybridChunker`（混合分块）进行切分，对比分块后每个 chunk 的语义完整性。

2. **RRF 参数实验**：调整 RRF 的平滑常数 `k`（尝试 10、30、60、100），对比同一组测试问题的融合检索效果。思考 `k` 值的大小分别偏向哪一路检索结果。

3. **单路 vs. 双路检索对比**：准备 10 个测试问题（5 个精确匹配类 + 5 个语义理解类），分别使用纯向量检索、纯 BM25 检索、RRF 融合检索，记录每种方式的 Top-3 召回率。

4. **Reranker 阈值调优**：调整 LLM Reranker 的过滤阈值（3、5、7），观察对最终回答质量的影响。阈值过低会怎样？过高会怎样？

5. **权限过滤测试**：构造两个不同 `tenant_id` 的用户，验证用户 A 无法检索到用户 B 的文档。

6. **索引更新测试**：导入同一份文档的两个版本，验证只保留最新版本可见，旧版本不会继续被回答引用。

7. **Flake8 自检**：确保代码通过 `flake8 project_07_enterprise_rag/` 的检查。
