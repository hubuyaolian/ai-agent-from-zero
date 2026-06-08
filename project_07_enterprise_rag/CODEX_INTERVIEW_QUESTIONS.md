# Codex 生成的企业级 RAG 系统深度追问面试题

生成说明：本文档由 Codex 基于 `project_07_enterprise_rag` 当前项目结构和实现生成，用于考察候选人对企业级 RAG 系统架构、检索、治理、安全、LangGraph 工作流和质量保障的理解。

建议使用方式：让候选人先画出项目端到端链路，再按模块逐层追问。强候选人应能把文档治理、权限过滤、checkpoint 安全、引用可验证性、评估指标和生产化替代方案串成闭环。

## 一、企业级 RAG 架构设计

1. 这个项目为什么要拆成 `ingestion`、`retrieval`、`governance`、`graph`、`citation`、`evaluation` 这些模块，而不是写成一条线性 RAG pipeline？
   - 追问：如果要把它生产化，哪些模块边界最关键？
   - 追问：哪些教学版实现不能直接上生产？

2. 请完整描述一次用户提问从进入系统到返回答案的工作流。
   - 追问：`input_guardrail -> intent_resolver -> hybrid_retriever -> retrieval_guardrail -> reranker -> answer_generator -> citation_verifier -> quality_checker -> output_guardrail -> response_formatter` 每个节点分别解决什么风险？
   - 追问：哪些节点属于检索质量控制，哪些节点属于安全治理？

3. 基础 RAG 在企业场景下最容易失败在哪里？
   - 追问：单路向量检索、无权限过滤、无引用校验、无评估闭环分别会造成什么业务后果？
   - 追问：为什么“能回答”不等于“可信赖”？

4. 如果你负责这个项目的生产化改造，会优先改哪三处？
   - 追问：你会如何排序安全、性能、评估和可观测性的优先级？
   - 追问：哪些能力必须先有自动化测试，再允许上线？

## 二、文档摄取与索引治理

5. `DocumentLoaderFactory` 为什么要统一 PDF、DOCX、Markdown、TXT 的输出 metadata？
   - 追问：`doc_id`、`content_hash`、`version`、`source`、`page`、`tenant_id`、`acl_tags` 各自服务什么治理目标？
   - 追问：如果缺少 `content_hash`，文档更新检测和去重会遇到什么问题？

6. `HybridChunker` 为什么要做标题感知分块，而不是直接固定长度切分？
   - 追问：`heading_path`、`char_start`、`char_end` 对检索、引用、审计和原文高亮有什么价值？
   - 追问：过大 chunk 和过小 chunk 分别会怎样影响召回、重排和生成质量？

7. 稳定 `chunk_id` 在企业级 RAG 中有什么意义？
   - 追问：为什么只用 `source + chunk_index` 不够可靠？
   - 追问：如果文档中间插入一段文字，旧 chunk 的引用和评估集会发生什么变化？

8. 如果文档更新、删除、权限变化，向量库和 BM25 索引应该怎么保持一致？
   - 追问：删除一个 `doc_id` 时，为什么向量索引和关键词索引都要删除？
   - 追问：权限变化是否一定需要重建 embedding？什么时候只更新 metadata 就够？

9. 当前项目支持多格式文本摄取，但还不是真正的多模态 RAG。你会如何扩展扫描 PDF、图片、表格和图表？
   - 追问：OCR、layout parser、表格结构化、多模态 embedding、原文坐标回溯分别应该放在哪一层？
   - 追问：表格问答为什么不能简单把表格转成一段纯文本？

## 三、检索策略与向量存储

10. 这个项目为什么同时做 Chroma 向量检索和 BM25 关键词检索？
    - 追问：产品编号、制度条款、专有名词、模糊语义查询分别更依赖哪一路召回？
    - 追问：为什么只靠 embedding 容易漏掉精确匹配问题？

11. RRF 融合解决了什么问题？
    - 追问：为什么要按 `chunk_id` 去重？
    - 追问：如果向量结果和 BM25 结果质量差异很大，RRF 的局限是什么？

12. `VectorStoreManager.similarity_search` 在有 `user_context` 时为什么要扩大 `search_k` 再做过滤？
    - 追问：这种后过滤方式有什么性能和召回风险？
    - 追问：生产系统更应该如何利用 metadata filter 做租户和 ACL 过滤？

13. 当前本地 embedding 走 HuggingFaceEmbeddings，远端 embedding 走 OpenAI 兼容接口。模型切换时最容易出什么问题？
    - 追问：为什么不同 embedding 模型的索引不能随意混用？
    - 追问：collection 命名、版本记录和回滚策略应该怎么设计？

14. 当前 `LocalReranker` 用 token overlap、标题 overlap、RRF score 做本地重排。
    - 追问：它在哪些场景会失效？
    - 追问：换成 bge-reranker、Qwen reranker 或 cross-encoder 后，评估指标应如何变化？

15. 如果用户说“为什么明明文档里有，系统检索不到”，你会如何排查？
    - 追问：你会按文档加载、分块、embedding、BM25、RRF、rerank、权限过滤中的什么顺序定位？
    - 追问：哪些日志或 trace 对排查最有价值？

## 四、权限、安全与治理

16. `AccessFilter` 只用 `tenant_id + acl_tags` 做最小权限过滤，这个设计的优点和不足是什么？
    - 追问：为什么不能只在最终引用列表里隐藏无权限来源？
    - 追问：检索、重排、生成、引用列表必须遵守同一套权限过滤，这句话具体意味着什么？

17. 这个项目里 PII 脱敏为什么不能只处理用户 query？
    - 追问：为什么 `retrieved_docs.metadata`、`source_map.source`、`doc_id`、`heading_path`、`snippet` 都可能是泄漏面？
    - 追问：如果文件名里包含邮箱或手机号，系统哪些位置可能泄漏？

18. 为什么 PII 清洗要发生在“节点返回 state 之前”，而不是只在最终输出前做一次？
    - 追问：LangGraph `MemorySaver` checkpoint 会把哪些中间状态持久化？
    - 追问：这对企业合规、审计和数据删除权意味着什么？

19. Prompt 注入检测放在 `input_guardrail`，输出脱敏放在 `output_guardrail`，两者职责有什么区别？
    - 追问：如果检索文档本身含有恶意 prompt，应该在哪些节点防御？
    - 追问：输入拦截、检索内容清洗、生成约束、输出过滤分别能防什么，不能防什么？

20. 审计日志应该记录什么，不应该记录什么？
    - 追问：如何同时满足排障可观测性和敏感数据最小化？
    - 追问：审计日志里记录原始 query、改写 query、chunk_id、质量分、失败原因分别有什么风险和价值？

## 五、LangChain 与 LangGraph 工作流编排

21. 为什么这里适合用 LangGraph `StateGraph`，而不是普通函数顺序调用？
    - 追问：条件路由、重试循环、checkpoint、会话隔离分别体现在哪里？
    - 追问：如果未来加入人工审批或异步索引任务，LangGraph 能带来什么扩展性？

22. `EnterpriseRAGState` 里为什么要显式保存 `query`、`rewritten_query`、`retrieved_docs`、`reranked_docs`、`source_map`、`citation_check`、`quality_score`？
    - 追问：这些状态分别对调试、重试、审计和最终输出有什么作用？
    - 追问：哪些字段最容易带来 checkpoint 敏感信息风险？

23. `thread_id=session_id` 的作用是什么？
    - 追问：如果多个用户共享 session_id，会出现什么安全和上下文污染问题？
    - 追问：生产系统里 session、user、tenant、trace id 应该如何区分？

24. `quality_checker` 低分时扩大 `top_k`，第二次重试引入 `query_variants`，这个策略解决什么问题？
    - 追问：什么时候重试会变成浪费成本甚至放大错误？
    - 追问：重试策略应该根据哪些信号决定：引用失败、无召回、低 rerank 分、生成无引用，还是用户权限不足？

25. `ConversationStore` 和 LangGraph checkpoint 的职责有什么不同？
    - 追问：一个负责用户可见会话历史，一个负责图执行状态，这种区分为什么重要？
    - 追问：如果两者都保存原始敏感信息，会带来什么合规风险？

## 六、引用、质量评估与可信回答

26. `SourceTracker` 和 `CitationVerifier` 分别负责什么？
    - 追问：只检查 `[S1]` 是否存在，为什么还不能证明答案真的被原文支撑？
    - 追问：如果回答引用了正确来源，但句子内容是编造的，当前系统能不能发现？

27. 为什么“根据现有资料无法回答”也是一种高质量输出？
    - 追问：如何衡量 unsupported answer rate，而不是只看回答是否流畅？
    - 追问：企业知识库问答为什么宁可拒答，也不能编造？

28. 当前评估里有 `Recall@K` 和 `MRR`。如果要评估企业级 RAG，还需要加入哪些指标？
    - 追问：citation accuracy、groundedness、权限泄漏率、延迟、成本、用户反馈分别怎么量化？
    - 追问：哪些指标适合自动化，哪些必须人工抽查？

29. 如果 `CitationVerifier` 发现回答引用了不存在的 `[S9]`，系统应该怎么处理？
    - 追问：应该直接失败、重试生成、扩大检索，还是返回无法回答？
    - 追问：不同处理方式对用户体验和成本有什么影响？

30. 如果评估集 Recall@5 很高，但用户仍反馈答案不可信，可能原因是什么？
    - 追问：召回正确 chunk 是否等于生成正确答案？
    - 追问：重排、prompt、引用校验、上下文压缩和权限过滤分别可能如何影响最终答案？

## 七、性能优化与生产化扩展

31. 企业级 RAG 的主要延迟来源有哪些？
    - 追问：文档解析、embedding、向量检索、BM25、rerank、LLM 生成、引用校验分别如何优化？
    - 追问：哪些步骤适合离线批处理，哪些必须在线实时执行？

32. 如果知识库规模从几百个 chunk 增长到几千万个 chunk，这个项目哪些地方会先撑不住？
    - 追问：Chroma、本地 BM25 JSON、SQLite 会话、同步 CLI 导入分别会遇到什么瓶颈？
    - 追问：生产环境应该替换成哪些基础设施？

33. 如果要接入真实企业权限系统，你会如何扩展 `UserContext`？
    - 追问：用户、组织、部门、角色、用户组、文档密级、临时授权应该如何表达？
    - 追问：权限变更后旧会话和旧 checkpoint 里的内容应该如何处理？

34. 如果要证明这个系统“安全且质量可控”，你会设计哪些回归测试？
    - 追问：至少应覆盖 ACL 越权、metadata/source_map PII 泄漏、prompt 注入拦截、引用不存在、无证据拒答、重试路径和索引删除一致性。
    - 追问：为什么安全测试不能只检查最终回答文本？

35. 如果候选人要把这个教学项目升级成真实企业 RAG，你希望他给出怎样的路线图？
    - 追问：模型网关、检索服务、索引任务队列、权限系统、评估流水线、可观测平台、人工反馈闭环分别应如何排期？
    - 追问：哪些功能可以 MVP 后补，哪些必须上线前完成？

## 面试评分建议

强候选人通常具备这些特征：

- 能把 RAG 拆成文档摄取、索引治理、混合检索、重排、生成、引用、评估、权限和审计的完整链路。
- 能解释为什么企业级 RAG 的核心不是“接一个向量库”，而是可控、可追溯、可评估、可治理。
- 能明确说明 `tenant_id`、`acl_tags`、`chunk_id`、`content_hash`、`source_map`、checkpoint 这些字段或机制的工程意义。
- 能意识到敏感信息不只来自用户输入，也可能来自文档正文、metadata、文件路径、引用摘要和中间状态。
- 能区分教学版实现和生产级实现，不会把 Chroma、SQLite、本地 BM25、本地 reranker 简单等同于完整企业方案。

弱候选人常见表现：

- 只会解释 embedding、top-k、prompt，不理解索引生命周期和权限一致性。
- 把引用标注当成可信性证明，无法说明引用校验和 groundedness 的区别。
- 只关注最终输出过滤，忽略 checkpoint、审计日志和会话历史里的中间态泄漏。
- 不能给出系统性排查路径，遇到“检索不到”只会调大 top-k。
- 对 LangGraph 的理解停留在“流程图”，说不清状态、条件路由、重试和 checkpointer 的价值。
