# 企业级 RAG 系统深度追问面试题库

> 基于 `project_07_enterprise_rag` 项目源码生成，涵盖架构设计、文档摄取、检索策略、安全治理、LangGraph 编排、质量评估和生产化扩展共 7 大维度 40 题。
>
> **建议使用方式**：让候选人先画出端到端链路，再按模块逐层追问。强候选人应能把文档治理、权限过滤、checkpoint 安全、引用可验证性、评估指标和生产化替代方案串成闭环。

---

## 一、企业级 RAG 架构设计（6 题）

### Q1. 模块拆分的设计意图

这个项目为什么要拆成 `ingestion`、`retrieval`、`governance`、`graph`、`citation`、`evaluation` 这些模块，而不是写成一条线性 RAG pipeline？

- 追问：如果要把它生产化，哪些模块边界最关键？
- 追问：哪些教学版实现不能直接上生产？

### Q2. 端到端工作流完整链路

请完整描述一次用户提问从进入系统到返回答案的工作流，说明每个节点的职责和状态流转。

- 追问：`input_guardrail → intent_resolver → hybrid_retriever → retrieval_guardrail → reranker → answer_generator → citation_verifier → quality_checker → output_guardrail → response_formatter` 每个节点分别解决什么风险？哪些属于检索质量控制，哪些属于安全治理？
- 追问：为什么 `input_guardrail` 放在最前面而不是检索之后？（零成本拦截：被拦截后直接跳到 `response_formatter`，跳过检索和重排，节省 API 调用费用）

### Q3. "能回答"不等于"可信赖"

基础 RAG 在企业场景下最容易失败在哪里？单路向量检索、无权限过滤、无引用校验、无评估闭环分别会造成什么业务后果？

- 追问：为什么"能回答"不等于"可信赖"？
- 追问：企业知识库问答为什么宁可拒答，也不能编造？

### Q4. 为什么选择 LangGraph StateGraph

这个系统为什么选择 LangGraph `StateGraph` 而不是简单的函数链式调用？`conditional_edges` 解决了什么问题？

- 追问：条件路由、重试循环、checkpoint、会话隔离分别体现在哪里？
- 追问：如果未来加入人工审批或异步索引任务，LangGraph 能带来什么扩展性？

### Q5. 状态定义的工程权衡

`EnterpriseRAGState` 用 `TypedDict(total=False)` 定义状态，而不是 Pydantic `BaseModel`。`total=False` 意味着所有字段可选——这两种方式有什么权衡？

- 追问：如果某个节点意外写入了一个不在 `TypedDict` 定义中的字段，LangGraph 会怎么处理？
- 追问：`guardrail_blocked` 和 `input_was_masked` 这两个状态字段的生命周期有何不同？

### Q6. 生产化改造优先级

如果你负责这个项目的生产化改造，会优先改哪三处？

- 追问：你会如何排序安全、性能、评估和可观测性的优先级？
- 追问：哪些能力必须先有自动化测试，再允许上线？

---

## 二、文档摄取与索引治理（6 题）

### Q7. 多格式文档加载与统一 metadata

`DocumentLoaderFactory` 为什么要统一 PDF、DOCX、Markdown、TXT 的输出 metadata？`doc_id`、`content_hash`、`version`、`source`、`page`、`tenant_id`、`acl_tags` 各自服务什么治理目标？

- 追问：如果缺少 `content_hash`，文档更新检测和去重会遇到什么问题？
- 追问：它的延迟导入（lazy import）策略体现在哪里？用户只处理 TXT/MD 时不需要安装哪些依赖？

### Q8. 标题感知分块策略

`HybridChunker` 为什么要做"标题感知 + 递归边界"两阶段分块，而不是直接固定长度切分？

- 追问：`heading_path`、`char_start`、`char_end` 对检索、引用、审计和原文高亮有什么价值？（Reranker 中对 heading 命中给 2.0 权重加分）
- 追问：`chunk_overlap=100` 的滑动窗口重叠为什么重要？去掉会有什么后果？
- 追问：如果文档是 PDF 格式（没有 Markdown 标题），这个分块器会退化成什么行为？

### Q9. 稳定 chunk_id 的工程意义

`build_chunk_id` 的格式是 `{doc_id}:chunk_{index:04d}:{content_hash[:8]}`。为什么 chunk_id 要包含 content_hash？

- 追问：内容哈希使 chunk_id 具备幂等性——同一文档重复导入时相同 ID 覆盖而非重复插入。如果文档中间插入一段文字，旧 chunk 的引用和评估集会发生什么变化？
- 追问：`build_doc_id` 中 `version` 字段的存在意义是什么？（支持同一文件的多版本共存，如 v1/v2 策略文档）

### Q10. 双路索引写入的降级策略

导入文档时，BM25 索引和向量索引的写入逻辑有什么区别？为什么向量索引用 `try/except` 包裹而 BM25 不用？

- 追问：BM25 写入时先 `get_all_documents` 再拼接新 chunks 后全量重建索引，在大数据量下有什么问题？如何改进？
- 追问：向量检索持续失败时系统自动退回 BM25-only 模式，这种降级对用户透明，有什么方式可以让用户感知？

### Q11. 索引一致性维护

如果文档更新、删除、权限变化，向量库和 BM25 索引应该怎么保持一致？

- 追问：删除一个 `doc_id` 时，为什么向量索引和关键词索引都要删除？
- 追问：权限变化是否一定需要重建 embedding？什么时候只更新 metadata 就够？

### Q12. 多模态扩展方向

当前项目支持多格式文本摄取，但还不是真正的多模态 RAG。你会如何扩展支持扫描 PDF、图片、表格和图表？

- 追问：OCR、layout parser、表格结构化、多模态 embedding、原文坐标回溯分别应该放在哪一层？
- 追问：表格问答为什么不能简单把表格转成一段纯文本？

---

## 三、检索策略与融合排序（7 题）

### Q13. 双路检索的互补性

这个项目为什么同时做 Chroma 向量检索和 BM25 关键词检索？在什么场景下其中一路会完全失效？

- 追问：产品编号、制度条款、专有名词、模糊语义查询分别更依赖哪一路召回？
- 追问：BM25 的 token 化用了 `jieba` + n-gram 扩展，为什么不只用 jieba？（单字 token 对专有名词和型号匹配不够，2/3-gram 补充精确匹配能力）

### Q14. RRF 融合算法原理

RRF（Reciprocal Rank Fusion）的公式是 `score = 1 / (k + rank + 1)`。请解释为什么 RRF 比简单的分数归一化求和更适合混合检索场景？

- 追问：向量检索的余弦相似度（0~1）和 BM25 的 TF-IDF 分数（0~几十）分布完全不同，RRF 如何消除尺度差异？
- 追问：如果一个 chunk 同时出现在向量检索和 BM25 检索的 top-1 位置，它的 RRF 分数是多少？（`2/61 ≈ 0.0328`）
- 追问：`RRF_K=60` 调大或调小对结果有什么影响？
- 追问：如果向量结果和 BM25 结果质量差异很大，RRF 的局限是什么？

### Q15. ACL 过采样策略

`VectorStoreManager.similarity_search` 在有 `user_context` 时为什么要 `search_k = k * 4`？

- 追问：这种后过滤方式有什么性能和召回风险？如果 ACL 过滤率很高（如 90% 文档不可访问），4 倍够吗？
- 追问：生产系统更应该如何利用 ChromaDB 的 metadata `where` filter 做前置租户和 ACL 过滤？

### Q16. Embedding 模型切换风险

当前本地 embedding 走 `HuggingFaceEmbeddings`，远端走 `OpenAIEmbeddings`。模型切换时最容易出什么问题？

- 追问：为什么不同 embedding 模型的索引不能随意混用？（维度不同、语义空间不同、余弦相似度不可比）
- 追问：collection 命名、版本记录和回滚策略应该怎么设计？

### Q17. 本地 Reranker 评分公式

`LocalReranker` 的评分公式是 `overlap * 1.5 + heading_overlap * 2.0 + rrf_score * 100`。三级信号加权的设计意图是什么？

- 追问：为什么 heading 命中权重比正文高？（标题代表文档主题分类，命中标题意味着整个 chunk 上下文高度相关）
- 追问：它在哪些场景会失效？换成 bge-reranker 或 cross-encoder 后，评估指标应如何变化？
- 追问：`RERANK_THRESHOLD = 3.0` 作为硬阈值过滤低分 chunk，设得太高会导致什么问题？

### Q18. 查询扩展的渐进策略

`query_variants` 机制在质量检查重试时生效，会生成三个查询变体。这种"查询扩展"技术的原理是什么？

- 追问：为什么只在第二次重试才启用？（第一次仅翻倍 top_k 成本较低，不够再启用查询扩展——渐进式升级）
- 追问：当前的 `_query_variants` 是规则式的（正则去标点 + 拼接固定后缀）。如果用 LLM 生成查询变体，会有哪些优劣？

### Q19. "检索不到"的排查方法论

如果用户说"为什么明明文档里有，系统检索不到"，你会如何排查？

- 追问：你会按文档加载、分块、embedding、BM25、RRF、rerank、权限过滤中的什么顺序定位？
- 追问：哪些日志或 trace 对排查最有价值？审计日志中的 `retrieved` 和 `reranked` 事件能提供什么线索？

---

## 四、权限、安全与治理（7 题）

### Q20. PII 三道防线

系统的 PII 脱敏分成了三道防线：`ask()` 入口的 `mask_pii`、`retrieval_guardrail` 的 `mask_document`、`output_guardrail` 的 `mask_pii`。请解释每道防线保护的是什么，为什么需要三道？

- 追问：**入口脱敏**发生在 `ask()` 方法内（图外）而不是图的第一个节点，关键原因是什么？（Checkpoint 隔离——PII 原文永远不会被写入 LangGraph 的 Checkpoint 持久化存储）
- 追问：为什么 `retrieved_docs.metadata`、`source_map.source`、`doc_id`、`heading_path`、`snippet` 都可能是泄漏面？如果文件名里包含邮箱或手机号，系统哪些位置可能泄漏？
- 追问：`mask_value` 递归处理 dict/list/tuple 中的字符串值，为什么不直接序列化整个结构用正则替换？

### Q21. 节点级脱敏 vs 输出级脱敏

为什么 PII 清洗要发生在"节点返回 state 之前"，而不是只在最终输出前做一次？

- 追问：LangGraph `MemorySaver` checkpoint 会把哪些中间状态持久化？
- 追问：这对企业合规、审计和数据删除权（GDPR Right to Erasure）意味着什么？

### Q22. Prompt 注入防御

`GuardrailManager.detect_injection` 使用正则模式检测 Prompt 注入。这些模式覆盖了哪些攻击向量？有什么明显的绕过方式？

- 追问：当前模式覆盖中英文常见注入特征（"ignore above instructions"、"忽略以上指令"、"system prompt"、"你现在是"、"bypass safety"）。绕过方式包括同义词替换、Unicode 混淆（零宽字符）、分段注入。
- 追问：输入拦截、检索内容清洗、生成约束、输出过滤分别能防什么，不能防什么？如果检索文档本身含有恶意 prompt，应该在哪些节点防御？

### Q23. ACL 权限模型

`AccessFilter` 用 `tenant_id + acl_tags` 做最小权限过滤。它的"宽松匹配"策略是什么？

- 追问：`acl_tags` 为空时默认允许、包含 `"public"` 直接允许、非 public 才做角色交集检查——为什么不能只在最终引用列表里隐藏无权限来源？
- 追问：检索、重排、生成、引用列表必须遵守同一套权限过滤，这句话具体意味着什么？
- 追问：如果要接入真实企业权限系统（用户/组织/部门/角色/用户组/文档密级/临时授权），你会如何扩展 `UserContext`？权限变更后旧会话和旧 checkpoint 应该如何处理？

### Q24. ACL 标签排序的一致性

`normalize_acl_tags` 会对标签做排序去重（`sorted(set(clean_tags))`）。为什么排序是必要的？

- 追问：ChromaDB 的 metadata 只支持简单类型（string/int/float/bool），不支持 list。这就是 `acl_tags` 被序列化为逗号分隔字符串的原因吗？
- 追问：如果不排序，`"hr,public"` 和 `"public,hr"` 会被 ChromaDB 视为不同的标签字符串，导致 metadata 过滤失效。

### Q25. 审计日志的设计边界

审计日志应该记录什么，不应该记录什么？如何同时满足排障可观测性和敏感数据最小化？

- 追问：当前记录了 `guardrail_blocked`、`guardrail_checked`、`intent_resolved`、`retrieved`、`reranked`、`citation_checked`、`quality_checked` 七类事件。审计日志里的 `payload_json` 是否可能包含 PII？
- 追问：当前实现用 SQLite 自增 ID + 时间戳，但没有任何防篡改措施（无签名、无 append-only 保护）。要满足 SOC2/GDPR 合规还需要哪些能力？

### Q26. 环境变量配置模式

`config.py` 中所有参数通过 `os.getenv("ENTERPRISE_RAG_XXX", default)` 注入。这种环境变量覆盖模式在生产部署中有什么优势和隐患？

- 追问：优势——12-Factor App 原则，无需改代码调整不同环境参数。隐患——环境变量名冲突、缺少类型校验、运行时修改需重启、敏感值可能被进程列表暴露。
- 追问：如果要实现运行时动态调整 `CHUNK_SIZE` 或 `RRF_K`，你会怎么设计？

---

## 五、LangGraph 状态管理与工作流编排（5 题）

### Q27. Checkpointer 会话隔离

`workflow.compile(checkpointer=MemorySaver())` 配合 `config = {"configurable": {"thread_id": session_id}}` 实现多会话并发。请解释这个隔离机制。

- 追问：`MemorySaver` 是基于内存字典的，`thread_id` 就是字典的 key。如果两个请求同时用同一个 `session_id` 调用 `ask()`，会发生什么？（Checkpoint 竞态条件）
- 追问：`MemorySaver` 在长时间运行的服务中有什么内存泄漏风险？生产环境应该替换成什么？（`SqliteSaver` 或 `PostgresSaver`）

### Q28. 状态更新机制

在 `quality_checker` 触发重试时，状态图中的 `retrieved_docs`、`reranked_docs`、`answer` 等字段会发生什么？LangGraph 的状态更新是覆盖还是合并？

- 追问：LangGraph 是**字段级覆盖**——节点返回 dict 的每个 key 覆盖 State 中对应 key，未返回的 key 保持不变。重试时旧中间结果不会保留。
- 追问：如果需要在重试时保留上一轮检索结果做对比分析，架构需要怎么调整？
- 追问：`retry_count` 的累加是在 `quality_checker` 中发生的，为什么不在 `hybrid_retriever` 节点中累加？

### Q29. ConversationStore vs Checkpoint

`ConversationStore`（SQLite 会话存储）和 LangGraph checkpoint 的职责有什么不同？

- 追问：一个负责用户可见会话历史（`/history` 命令），一个负责图执行状态（内部状态快照）。这种区分为什么重要？
- 追问：如果两者都保存原始敏感信息，会带来什么合规风险？

### Q30. 自适应重试策略

`quality_checker` 低分时扩大 `top_k`（翻倍但有上限 `min(top_k * 2, 20)`），第二次重试引入 `query_variants`。这个策略解决什么问题？

- 追问：什么时候重试会变成浪费成本甚至放大错误？（如果检索库里根本没有相关文档，重试只浪费 LLM 调用）
- 追问：重试策略应该根据哪些信号决定——引用失败、无召回、低 rerank 分、生成无引用，还是用户权限不足？
- 追问：重试时 `quality_checker` 直接跳回 `hybrid_retriever`，跳过了 `intent_resolver`，因为 query 不需要再改写。这个路由设计的依据是什么？

### Q31. thread_id 与多租户安全

`thread_id=session_id` 的作用是什么？如果多个用户共享 session_id，会出现什么安全和上下文污染问题？

- 追问：生产系统里 session、user、tenant、trace id 应该如何区分？
- 追问：`UserContext` 用 `frozen=True` 的 dataclass 有什么好处？（不可变性确保权限上下文在工作流执行过程中不被篡改）

---

## 六、引用、质量评估与可信回答（5 题）

### Q32. 引用验证的双重检查

`CitationVerifier` 的验证逻辑包含两个检查：引用 ID 存在性检查和"无引用事实回答"检查。后者的设计意图是什么？

- 追问：`if source_map and not used_ids and not unable_answer` —— 如果系统有参考文档、回答没有引用任何来源、且不是拒答，就判定不通过。防止 LLM "凭空编造"事实。
- 追问：只检查 `[S1]` 是否存在，为什么还不能证明答案真的被原文支撑？如果回答引用了正确来源但句子内容是编造的，当前系统能不能发现？
- 追问：如果回答引用了不存在的 `[S9]`，系统应该怎么处理——直接失败、重试生成、扩大检索，还是返回无法回答？

### Q33. 拒答也是高质量输出

为什么"根据现有资料无法回答"也是一种高质量输出？

- 追问：如何衡量 unsupported answer rate，而不是只看回答是否流畅？
- 追问：当前质量评分是规则式的（`score = 8` 或 `score = 4`），如果要引入 LLM-as-Judge 评分，你会怎么设计？

### Q34. 评估指标体系

当前评估用了 `Recall@K` 和 `MRR` 两个指标。它们分别衡量什么，为什么需要同时使用？

- 追问：`Recall@K` 衡量覆盖率（正确答案是否被检索到），`MRR` 衡量排序质量（正确答案排第几位）。单独用任一个都不完整。
- 追问：如果要评估企业级 RAG，还需要加入哪些指标？citation accuracy、groundedness、权限泄漏率、延迟、成本、用户反馈分别怎么量化？
- 追问：哪些指标适合自动化，哪些必须人工抽查？

### Q35. Recall 高但用户不信

如果评估集 Recall@5 很高，但用户仍反馈答案不可信，可能原因是什么？

- 追问：召回正确 chunk 是否等于生成正确答案？
- 追问：重排、prompt、引用校验、上下文压缩和权限过滤分别可能如何影响最终答案？

### Q36. 回归测试设计

如果要证明这个系统"安全且质量可控"，你会设计哪些回归测试？

- 追问：至少应覆盖 ACL 越权、metadata/source_map PII 泄漏、prompt 注入拦截、引用不存在、无证据拒答、重试路径和索引删除一致性。
- 追问：为什么安全测试不能只检查最终回答文本？（要检查 checkpoint 中间状态、审计日志 payload、会话历史记录中的所有敏感面）
- 追问：当前 `test_workflow_security.py` 已有 4 个安全测试用例，它们分别验证了什么？还缺少哪些场景？

---

## 七、性能优化与生产化扩展（4 题）

### Q37. 延迟来源与优化

企业级 RAG 的主要延迟来源有哪些？

- 追问：文档解析、embedding、向量检索、BM25、rerank、LLM 生成、引用校验分别如何优化？
- 追问：哪些步骤适合离线批处理，哪些必须在线实时执行？

### Q38. 规模瓶颈与基础设施替换

如果知识库规模从几百个 chunk 增长到几千万个 chunk，这个项目哪些地方会先撑不住？

- 追问：Chroma 本地文件、BM25 JSON 全量重建、SQLite 会话、同步 CLI 导入分别会遇到什么瓶颈？
- 追问：生产环境应该替换成哪些基础设施？（Milvus/Pinecone、Elasticsearch、PostgreSQL、异步任务队列）

### Q39. BM25 实现的性能问题

当前 `KeywordSearcher.search` 每次查询都对所有文档重新 token 化并构建 BM25 索引（`_SimpleBM25([tokenize(...) for doc in docs])`），而不是使用 `index_documents` 时已缓存的 `self._indexes`。这是 bug 还是有意设计？

- 追问：`index_documents` 方法中已经构建了 `_SimpleBM25` 实例并存入 `self._indexes`，但 `search` 没有使用它。大规模数据下的 O(n) 复杂度如何改进？
- 追问：如果要支持增量索引（只索引新增/修改的文档），当前架构需要哪些改动？

### Q40. 生产化路线图

如果要把这个教学项目升级成真实企业 RAG，你希望给出怎样的路线图？

- 追问：按优先级排序——
  1. Embedding 模型升级（影响检索质量）
  2. Reranker 升级为 Cross-Encoder（影响排序精度）
  3. Checkpointer 替换为 PostgresSaver（持久化可靠性）
  4. 向量数据库集群化（Milvus/Pinecone，扩展性和高可用）
  5. BM25 替换为 Elasticsearch（增量索引、分布式、并发安全）
  6. 审计日志增强（签名验证、ELK 集中收集、保留策略）
  7. Guardrail 升级（LLM-based 分类器 + 多层防御）
  8. LLM 回答生成增加 streaming、并发控制、token 预算管理
- 追问：模型网关、检索服务、索引任务队列、权限系统、评估流水线、可观测平台、人工反馈闭环分别应如何排期？
- 追问：哪些功能可以 MVP 后补，哪些必须上线前完成？
- 追问：如果预算有限只能改一项，你选哪项？为什么？

---

## 面试评分建议

### 强候选人特征

- 能把 RAG 拆成文档摄取、索引治理、混合检索、重排、生成、引用、评估、权限和审计的完整链路
- 能解释为什么企业级 RAG 的核心不是"接一个向量库"，而是**可控、可追溯、可评估、可治理**
- 能明确说明 `tenant_id`、`acl_tags`、`chunk_id`、`content_hash`、`source_map`、checkpoint 这些字段或机制的工程意义
- 能意识到敏感信息不只来自用户输入，也可能来自文档正文、metadata、文件路径、引用摘要和中间状态
- 能区分教学版实现和生产级实现，不会把 Chroma、SQLite、本地 BM25、本地 reranker 简单等同于完整企业方案
- 能深入源码细节：TypedDict 选型、延迟导入、状态覆盖机制、ACL 排序一致性、BM25 索引缓存 bug

### 弱候选人常见表现

- 只会解释 embedding、top-k、prompt，不理解索引生命周期和权限一致性
- 把引用标注当成可信性证明，无法说明引用校验和 groundedness 的区别
- 只关注最终输出过滤，忽略 checkpoint、审计日志和会话历史里的中间态泄漏
- 不能给出系统性排查路径，遇到"检索不到"只会调大 top-k
- 对 LangGraph 的理解停留在"流程图"，说不清状态、条件路由、重试和 checkpointer 的价值
