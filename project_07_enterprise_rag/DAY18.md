# Day 18 课程：企业级 RAG 架构设计 — 从单路检索到多路融合 🏗️

在 Day 10 中，我们构建了一个基础的 RAG 知识库问答应用。它能够加载文档、分块、向量化、检索并生成回答——但对于企业场景，这个基础版本存在几个核心缺陷：

1. **单路检索盲区**：仅依赖向量语义检索，遇到"关键词精确匹配"类问题（如产品编号、专有名词）容易漏检。
2. **分块质量粗糙**：固定字符数切割会截断语义段落，导致检索到的上下文不完整。
3. **无对话记忆**：每次问答完全独立，无法处理多轮对话中的指代消解（如"它支持什么格式？"中的"它"指什么）。
4. **无来源溯源**：回答无法追溯到具体文档和页码，用户无法验证答案的可信度。
5. **无质量闭环**：检索到的文档可能完全不相关，但系统仍会强行生成回答（幻觉风险）。

今天的课程将从架构层面解决这些问题，设计一套**企业级 RAG 系统**。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：企业级 RAG 的架构演进](#第一部分企业级-rag-的架构演进)
3. [第二部分：文档摄取与智能分块](#第二部分文档摄取与智能分块)
4. [第三部分：多路召回与融合检索](#第三部分多路召回与融合检索)
5. [核心原理深度解析](#核心原理深度解析)
6. [课后练习](#课后练习)

---

## 学习目标
- 理解基础 RAG 到企业级 RAG 的架构演进路线。
- 掌握标题感知 + 语义边界的混合分块策略。
- 理解向量检索、BM25 关键词检索和 RRF 融合的原理。
- 掌握 LLM 重排序（Reranker）的设计与实现。
- 理解对话记忆如何解决多轮问答中的指代消解问题。

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

针对上述瓶颈，企业级 RAG 在五个层面做了升级：

```
┌─────────────────────────────────────────────────────────────┐
│                     企业级 RAG 架构                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─── 文档摄取层 ───┐    ┌─── 检索增强层 ───┐              │
│  │ DocumentLoader   │    │ VectorRetriever   │              │
│  │ (PDF/DOCX/MD/TXT)│    │ (ChromaDB 语义)   │              │
│  │       ↓          │    │       +           │              │
│  │ HybridChunker    │    │ BM25Retriever     │              │
│  │ (标题感知+语义)   │    │ (jieba 关键词)    │              │
│  │       ↓          │    │       ↓           │              │
│  │ Embedding+入库    │    │ RRF 融合排序      │              │
│  └──────────────────┘    │       ↓           │              │
│                          │ LLM Reranker      │              │
│  ┌─── 记忆管理层 ───┐    │ (精排+过滤)       │              │
│  │ ConversationStore│    └───────────────────┘              │
│  │ (SQLite 多会话)   │              ↓                      │
│  │       +          │    ┌─── 生成与溯源层 ───┐             │
│  │ IntentResolver   │    │ Prompt + LLM      │              │
│  │ (指代消解)        │    │       ↓           │              │
│  └──────────────────┘    │ QualityChecker    │              │
│                          │ (质量自评+重试)    │              │
│                          │       ↓           │              │
│                          │ SourceTracker     │              │
│                          │ (引用标注+溯源)    │              │
│                          └───────────────────┘              │
│                                     ↓                      │
│                          ┌─── 编排层 ───┐                   │
│                          │ LangGraph    │                   │
│                          │ 6 节点状态图  │                   │
│                          └──────────────┘                   │
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
│   └── reranker.py              # LLMReranker
├── memory/                      # 对话记忆
│   ├── __init__.py
│   └── conversation_store.py    # ConversationStore
├── citation/                    # 来源溯源
│   ├── __init__.py
│   └── source_tracker.py        # SourceTracker
├── graph/                       # LangGraph 工作流
│   ├── __init__.py
│   ├── state.py                 # EnterpriseRAGState
│   └── workflow.py              # 6 节点状态图
└── requirements.txt
```

---

## 第二部分：文档摄取与智能分块

### 1. DocumentLoaderFactory — 多格式统一加载

Day 10 只支持 `.txt` 和 `.md`。企业场景需要处理 PDF、Word 文档等格式。我们设计一个工厂类，根据文件扩展名自动选择加载器：

| 格式 | LangChain 加载器 | 额外依赖 |
|------|------------------|---------|
| `.pdf` | `PyPDFLoader` | `pypdf` |
| `.docx` | `Docx2txtLoader` | `python-docx` |
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

每个 Document 的 metadata 统一包含 `source`（文件路径）、`page`（页码）、`format`（文件类型），为后续溯源提供基础。

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

**阶段 2：语义边界微调** — 对超长段落使用 `RecursiveCharacterTextSplitter` 二次切分（chunk_size=500, chunk_overlap=100），确保不超出 Embedding 模型的最佳输入长度；对过短段落（<100 字符）合并到相邻段落。

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

每个 chunk 的 metadata 继承父文档的 `source`/`page`/`format`，并新增 `chunk_index`（块编号）和 `heading_path`（标题层级路径，如 `"部署指南 > 配置说明"`），方便后续溯源定位。

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

Embedding 使用 Qwen 的 `text-embedding-v3` 模型，通过 `OpenAIEmbeddings` 类接入（与 Day 9 相同）。

### 3. 关键词检索 — KeywordSearcher (BM25)

BM25 是信息检索领域的经典算法，基于词频-逆文档频率（TF-IDF）的改进版本。它不依赖语义，而是通过**词频统计**计算文档与查询的相关性。

中文场景下需要先用 jieba 分词：

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
            doc_id = doc.metadata.get("source", "") + str(doc.metadata.get("chunk_index", ""))
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (self.rrf_k + rank + 1)
        for rank, doc in enumerate(keyword_docs):
            doc_id = doc.metadata.get("source", "") + str(doc.metadata.get("chunk_index", ""))
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (self.rrf_k + rank + 1)
        # 按融合分数降序排列，取 Top-K
```

### 5. LLMReranker — LLM 打分重排

RRF 融合后的候选文档可能仍包含低相关度的结果。我们用 LLM 对候选文档逐一打分（1-10），过滤低于阈值的文档：

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
1. 将每个候选文档与问题一起提交给轻量 LLM
2. 解析返回的评分数字
3. 过滤低于阈值（默认 5 分）的文档
4. 按分数降序返回

> 💡 **性能优化**：为避免逐个文档串行调用 LLM，可以将多个文档拼入同一次 Prompt 中批量打分。

---

## 核心原理深度解析

### 基础 RAG vs. 企业级 RAG 的完整对比

| 维度 | 基础 RAG (Day 10) | 企业级 RAG (Day 18-19) |
|------|-------------------|----------------------|
| 文档格式 | .txt / .md | PDF / DOCX / MD / TXT |
| 分块策略 | 固定字符数 | 标题感知 + 语义边界 |
| 检索方式 | 单路向量检索 | 向量 + BM25 双路 + RRF 融合 |
| 重排序 | 无 | LLM 打分精排 |
| 对话记忆 | 无 | SQLite 多会话 + 指代消解 |
| 来源溯源 | 无 | 引用标注 [1][2] + 末尾引用列表 |
| 质量控制 | 无 | LLM 自评 + 重试循环 |
| 编排方式 | LCEL 链 | LangGraph 6 节点状态图 |

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

---

## 课后练习

1. **分块效果对比**：对同一份 Markdown 文档，分别使用 `RecursiveCharacterTextSplitter`（固定分块）和 `HybridChunker`（混合分块）进行切分，对比分块后每个 chunk 的语义完整性。

2. **RRF 参数实验**：调整 RRF 的平滑常数 `k`（尝试 10、30、60、100），对比同一组测试问题的融合检索效果。思考 `k` 值的大小分别偏向哪一路检索结果。

3. **单路 vs. 双路检索对比**：准备 10 个测试问题（5 个精确匹配类 + 5 个语义理解类），分别使用纯向量检索、纯 BM25 检索、RRF 融合检索，记录每种方式的 Top-3 召回率。

4. **Reranker 阈值调优**：调整 LLM Reranker 的过滤阈值（3、5、7），观察对最终回答质量的影响。阈值过低会怎样？过高会怎样？

5. **Flake8 自检**：确保代码通过 `flake8 project_07_enterprise_rag/` 的检查。
