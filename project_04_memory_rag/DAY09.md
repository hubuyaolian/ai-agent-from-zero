# Day 9 课程：Embedding 与向量检索 — 让 Agent 理解语义 🔮

在 Day 8 中，我们用 SQLite 实现了按 Key 精确查询的长期记忆。但这种"精确匹配"有一个根本性的局限：**它不理解语义。**

例如，你存了一条记忆 `key="fav_language", value="Python"`。当用户问"我喜欢什么编程语言？"时，你的代码需要知道"喜欢什么编程语言"对应的 key 正好是 `fav_language`——这完全依赖于硬编码映射。

但如果用户问的是"我擅长哪门语言？"、"我常用什么语言写代码？"——这些表述的含义和 `fav_language` 是一样的，但字面完全不同，精确匹配就彻底失效了。

**Embedding（向量嵌入）** 技术正是为解决这个问题而生：把文本转化为高维向量，语义相近的文本向量距离自然就近，实现**按语义检索**而非按关键词匹配。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：Embedding 原理](#第一部分embedding-原理)
3. [第二部分：ChromaDB 向量数据库](#第二部分chromadb-向量数据库)
4. [第三部分：文档加载与文本分块](#第三部分文档加载与文本分块)
5. [核心原理深度解析](#核心原理深度解析)
6. [课后练习](#课后练习)

---

## 学习目标
- 理解 Embedding 的数学本质：文本 → 高维向量 → 余弦相似度。
- 掌握使用 LangChain 调用 Embedding 模型将文本向量化。
- 学会使用 ChromaDB 进行向量的增删改查。
- 掌握文档加载（PDF / TXT / Markdown）和文本分块（Chunking）的最佳实践。

---

## 第一部分：Embedding 原理

### 1. 什么是 Embedding？

Embedding 是一种将非结构化数据（文本、图片、音频等）转化为固定长度的**数值向量**的技术。

```
"今天北京天气很好"  →  [0.12, -0.34, 0.56, ..., 0.78]   # 1536 维向量
"北京今日天气晴朗"  →  [0.11, -0.33, 0.55, ..., 0.77]   # 语义相似 → 向量接近
"量子力学的基本原理"  →  [0.89, 0.12, -0.67, ..., 0.03]   # 语义不同 → 向量远离
```

### 2. 语义相似度的度量

两个向量之间的"距离"可以用**余弦相似度 (Cosine Similarity)** 来衡量：

```
                A · B
cos(θ) = ─────────────────
            ||A|| × ||B||
```

- 值域：`[-1, 1]`
- `1` 表示完全相同方向（语义一致）
- `0` 表示正交（语义无关）
- `-1` 表示完全相反方向（语义相反）

### 3. Embedding 模型

生成 Embedding 向量需要专门的 Embedding 模型（不同于生成文本的 Chat 模型）：

| 模型 | 提供商 | 向量维度 | 特点 |
|------|-------|---------|------|
| `text-embedding-3-small` | OpenAI | 1536 | 性价比高 |
| `text-embedding-v3` | 阿里云（通义） | 1024 | 中文效果好 |
| `embedding-3` | 智谱 | 2048 | 国产可选 |
| `models/text-embedding-004` | Google | 768 | Gemini 生态 |

在 LangChain 中调用 Embedding 模型：

```python
from langchain_openai import OpenAIEmbeddings

# 使用 DeepSeek / Qwen 等兼容 OpenAI 接口的 Embedding
embeddings = OpenAIEmbeddings(
    model="text-embedding-v3",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key="your_api_key"
)

# 将单条文本向量化
vector = embeddings.embed_query("今天天气真好")
print(f"向量维度: {len(vector)}")  # 1024
print(f"前 5 维: {vector[:5]}")     # [0.12, -0.34, ...]
```

> [!WARNING]
> ### ⚠️ 国产 Embedding 模型 API 的兼容性警告
> 很多国产大模型云厂商（如阿里云通义千问、智谱清言、Kimi 等）虽然宣称提供“OpenAI 兼容接口”，但它们的 **Embedding API 在内部请求参数和返回数据层级上可能与 OpenAI 存在细微差别**。
> 例如，某些厂商对于 `text-embedding-3-small` 这类 OpenAI 特有参数会直接报错；又或者在 LangChain 的 `OpenAIEmbeddings` 调用中，智谱等特定接口可能会由于接口包装层解析不到 `data[0].embedding` 路径而抛出 `KeyError`。
>
> **💡 国产模型 Embedding 兼容性最佳实践**：
> 1. **优先推荐通义千问**：通义千问的 `text-embedding-v3` 接口在 compatible-mode（兼容模式）下的 API 返回结构与 OpenAI 几乎 100% 对齐，调用最稳定，且非常适合中文语义处理。
> 2. **选用厂商原生适配器**：如果遇到 `OpenAIEmbeddings` 报 `KeyError` 或参数不识别等兼容性错误，**绝不要勉强通过修改 base_url 去套用 OpenAIEmbeddings**。应该优先使用该厂商在 LangChain 中的原生生态包。例如，对于智谱 AI，建议安装 `langchain-zhipu` 并使用 `ZhipuAIEmbeddings` 代替 `OpenAIEmbeddings`。
> 3. **调试与重试思路**：遇到问题时，可以使用 python 的 `requests` 库手动 POST 厂商的 Embedding 实体接口，查看其响应体的 JSON 树状层级，确认其返回结构中是 `embedding` 还是 `embeddings`，以及外层包装是否为 `data`，以便定制化解决。

# 批量向量化
vectors = embeddings.embed_documents([
    "今天天气真好",
    "明天会下雨吗",
    "Python 是最好的语言"
])
```

> 📖 **代码实战**：查看并运行 [04_embedding_basics.py](file:///Users/huangyang/code/agent/project_04_memory_rag/04_embedding_basics.py)

---

## 第二部分：ChromaDB 向量数据库

### 1. 为什么需要向量数据库？

当你有成千上万的文档块需要检索时，不可能每次都用 Python 遍历所有向量计算余弦相似度。向量数据库使用专门的索引算法（如 HNSW、IVF）来实现**毫秒级的近似最近邻搜索 (ANN)**。

### 2. ChromaDB 简介

ChromaDB 是一个开源、轻量级的向量数据库，特别适合学习和原型开发：
- **零配置**：`pip install chromadb` 即可使用，数据默认存储在本地文件。
- **内嵌模式**：直接在 Python 进程内运行，不需要启动独立服务。
- **LangChain 集成**：有官方的 LangChain 适配器。

### 3. ChromaDB 的核心操作

#### 创建集合 (Collection)
集合类似于关系型数据库中的"表"，用于存储一类相关的向量：

```python
from langchain_chroma import Chroma

# 创建或连接一个向量集合
vectorstore = Chroma(
    collection_name="my_knowledge",    # 集合名称
    embedding_function=embeddings,     # Embedding 模型
    persist_directory="./chroma_db"    # 持久化存储目录
)
```

#### 添加文档
```python
from langchain_core.documents import Document

# 创建文档对象（包含文本内容和元数据）
docs = [
    Document(
        page_content="LangChain 是一个用于构建 LLM 应用的框架。",
        metadata={"source": "langchain_intro.md", "chapter": 1}
    ),
    Document(
        page_content="LangGraph 是 LangChain 的 Agent 编排框架。",
        metadata={"source": "langgraph_intro.md", "chapter": 1}
    ),
]

# 添加到向量库（自动调用 Embedding 模型进行向量化）
vectorstore.add_documents(docs)
```

#### 相似度检索
```python
# 检索与查询最相似的 Top-K 个文档
results = vectorstore.similarity_search(
    query="什么是 LangChain？",
    k=3  # 返回最相似的 3 个文档
)

for doc in results:
    print(f"内容: {doc.page_content}")
    print(f"来源: {doc.metadata['source']}")
```

#### 带分数的检索
```python
# 检索并返回相似度分数
results = vectorstore.similarity_search_with_score(
    query="Agent 框架有哪些？",
    k=3
)

for doc, score in results:
    print(f"相似度: {score:.4f} | 内容: {doc.page_content}")
```

> 📖 **代码实战**：查看并运行 [05_vector_store.py](file:///Users/huangyang/code/agent/project_04_memory_rag/05_vector_store.py)

---

## 第三部分：文档加载与文本分块

### 1. 文档加载 (Document Loading)

LangChain 提供了丰富的文档加载器，支持从各种格式中读取文本：

| 加载器 | 支持格式 | 使用场景 |
|-------|---------|---------|
| `TextLoader` | `.txt` | 纯文本文件 |
| `UnstructuredMarkdownLoader` | `.md` | Markdown 文档 |
| `PyPDFLoader` | `.pdf` | PDF 文件 |
| `CSVLoader` | `.csv` | 表格数据 |
| `DirectoryLoader` | 整个目录 | 批量加载多个文件 |

```python
from langchain_community.document_loaders import TextLoader

# 加载单个文本文件
loader = TextLoader("knowledge/intro.txt", encoding="utf-8")
documents = loader.load()

# 每个 Document 对象包含：
# - page_content: 文本内容
# - metadata: 元数据（文件路径、页码等）
```

### 2. 文本分块 (Text Splitting / Chunking)

这是 RAG 系统中**对检索效果影响最大**的环节之一。

#### 为什么需要分块？
- 大模型的上下文窗口有限，不能一次性塞进整篇文档。
- Embedding 模型对短文本的语义表示更精确（长文本会"稀释"语义）。
- 检索时需要返回精确相关的**片段**，而不是整篇文档。

#### 分块策略

```
原始文档 (10000 字)
    │
    ▼ 分块
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Chunk 1  │ │ Chunk 2  │ │ Chunk 3  │ │ Chunk 4  │
│ 500 字   │ │ 500 字   │ │ 500 字   │ │ 500 字   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
     ↑               ↑
     └── 重叠区域 ───┘  (overlap = 100 字)
```

- **chunk_size**：每个块的目标大小（通常 200-1000 字符）。
- **chunk_overlap**：相邻块之间的重叠区域（通常是 chunk_size 的 10%-20%）。重叠是为了防止关键信息恰好被截断在两个块的边界上。

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 创建分块器
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       # 每个块最大 500 字符
    chunk_overlap=100,    # 相邻块重叠 100 字符
    separators=["\n\n", "\n", "。", "！", "？", " ", ""]
    # 优先按段落分割，其次按句子，最后按字符
)

# 对文档进行分块
chunks = text_splitter.split_documents(documents)
print(f"原始文档数: {len(documents)}")
print(f"分块后数量: {len(chunks)}")
```

#### 分块大小的权衡

| chunk_size | 检索精度 | 上下文完整性 | 向量数量 |
|-----------|---------|------------|---------|
| 过小 (100字) | ⭐⭐⭐ 高（精确定位） | ⭐ 低（上下文断裂） | 多（存储成本高） |
| 适中 (500字) | ⭐⭐ 中（平衡） | ⭐⭐ 中（基本完整） | 适中 |
| 过大 (2000字) | ⭐ 低（噪音多） | ⭐⭐⭐ 高（上下文丰富） | 少 |

> 📖 **代码实战**：查看并运行 [06_document_loader.py](file:///Users/huangyang/code/agent/project_04_memory_rag/06_document_loader.py) 和 [07_text_splitter.py](file:///Users/huangyang/code/agent/project_04_memory_rag/07_text_splitter.py)

---

## 核心原理深度解析

### 向量检索的底层算法：HNSW

ChromaDB 默认使用 **HNSW (Hierarchical Navigable Small World)** 算法进行近似最近邻搜索：

```
Layer 3:  ○ ─────────────── ○  (最稀疏层，快速粗定位)
          │                 │
Layer 2:  ○ ── ○ ─── ○ ── ○  (中间层)
          │    │     │    │
Layer 1:  ○─○─○─○─○─○─○─○─○  (最密层，精确搜索)
```

- 搜索从最高层开始，快速跳跃到目标区域附近。
- 逐层下降，在更密集的层中精确定位最近的邻居。
- 时间复杂度：$O(\log N)$，远优于暴力搜索的 $O(N)$。

### Embedding 的训练原理（直觉理解）

Embedding 模型是如何学会"语义相似的文本 → 相似的向量"的？

核心思路是**对比学习 (Contrastive Learning)**：
1. 准备大量的"相似文本对"（如：问题-答案、同义句）和"不相似文本对"。
2. 训练模型：让相似文本对的向量距离尽可能近，不相似文本对的向量距离尽可能远。
3. 经过海量数据的训练后，模型就学会了把语义编码到向量空间中。

---

## 课后练习

1. **语义相似度实验**：准备 10 个中文句子（5 对语义相似的），用 Embedding 模型将它们向量化，计算并打印所有句子两两之间的余弦相似度矩阵，验证语义相似的句子是否真的向量距离更近。

2. **分块策略对比**：对同一篇长文档，分别使用 `chunk_size=200`、`chunk_size=500`、`chunk_size=1000` 进行分块，然后对同一个查询进行相似度检索，对比不同分块大小下的检索结果差异。

3. **多格式文档加载**：准备一个包含 `.txt`、`.md`、`.pdf` 文件的目录，使用 `DirectoryLoader` 批量加载，观察不同格式的文档在加载后的 `metadata` 差异。

4. **Flake8 自检**：确保代码通过 `flake8 project_04_memory_rag/` 的检查。
