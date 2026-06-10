# Day 24 课程：主流 Agent 框架横向比较

前面 23 天我们已经从底层 API、工具调用、RAG、LangGraph 工作流、多 Agent 协作一路搭到企业级项目。现在需要补一课：真实工程里不会每次都从零手写 Agent loop，而是会评估成熟框架。

但框架选型最容易犯两个错误：

1. 只看热度，不看项目需求。
2. 以为换了框架就自动拥有安全、审计、评估、压测和生产可靠性。

本课的目标不是背框架名字，而是建立一张框架地图。

---

## 学习目标

- 能区分 Agent 框架的主要类型。
- 能说清 8 个核心框架的优势和适用场景。
- 能判断 AgentScope、CAMEL 这类研究型框架的价值和边界。
- 能解释 MCP、观测平台、评估平台为什么不等同于 Agent 框架。

---

## 一、Agent 框架先按工程问题分类

| 类型 | 代表框架 | 解决的核心问题 |
|------|----------|----------------|
| 状态图编排 | LangGraph | 长程状态、条件分支、checkpoint、人工介入 |
| 原生 Agent runtime | OpenAI Agents SDK | handoff、guardrails、sessions、tracing、MCP、sandbox |
| 企业开发套件 | Google ADK | 开发、调试、部署、观测、评估和企业生态 |
| 类型安全 Agent | PydanticAI | 结构化输出、依赖注入、eval、类型校验 |
| 多 Agent 对话 | AutoGen | 多 Agent 对话、事件驱动、代码执行实验 |
| 角色团队 Agent | CrewAI | 角色、任务、团队、流程控制 |
| RAG 数据层 Agent | LlamaIndex Agents | 数据连接、索引、检索、query engine |
| 企业中间件 | Semantic Kernel | 插件、函数、企业 API、Microsoft/.NET 生态 |

这几类不是互斥的。一个生产系统可以同时使用 LangGraph 编排流程、LlamaIndex 负责检索、PydanticAI 校验结构化输出，再用 MCP 接外部工具。

---

## 二、核心必讲框架

### 1. LangGraph

核心概念：状态图（State Graph）。

主要优势：

- 状态、节点、边、条件分支都很明确。
- 适合 checkpoint、resume、human-in-the-loop。
- 很适合长程 Agent、RAG 工作流、审批流程和质量闭环。

适合：

- `project_07_enterprise_rag` 的 RAG pipeline。
- `project_08_workflow_agent` 的计划、审批、执行、恢复。
- 需要可恢复状态和人工中断的复杂系统。

不适合：

- 只做一次简单问答或一次工具调用的小功能。

### 2. OpenAI Agents SDK

核心概念：OpenAI 生态原生 Agent runtime。

主要优势：

- Agent、handoff、guardrails、sessions、tracing 等能力集中。
- 支持 MCP 和 sandbox 这类生产 Agent 常见能力。
- 适合直接使用 OpenAI 模型和工具生态。

适合：

- 多 Agent handoff。
- 带 guardrails 和 tracing 的工具型 Agent。
- 代码执行、文件、沙箱类工作流。

不适合：

- 团队希望完全抽象掉模型供应商差异的场景。

### 3. Google ADK

核心概念：企业级 Agent 开发套件。

主要优势：

- 关注开发、调试、部署、运行和评估全链路。
- 适合 Gemini 和 Google Cloud 生态。
- 企业集成和部署视角更完整。

适合：

- 已经在 Google Cloud / Gemini 技术栈上的团队。
- 需要企业级部署、运维和观测的 Agent 项目。

不适合：

- 只想用最少代码理解 Agent 基础原理的入门阶段。

### 4. PydanticAI

核心概念：类型安全 Agent。

主要优势：

- Pydantic schema 对结构化输出约束强。
- 依赖注入适合测试和业务工程。
- eval、hooks、durable execution 等能力贴近生产质量控制。

适合：

- 金融、客服、审批、表单、订单等强结构化业务。
- 需要把 LLM 输出转成可校验对象的系统。

不适合：

- 以多 Agent 社会模拟和开放式对话实验为主的研究项目。

### 5. AutoGen

核心概念：可对话 Agent 与多 Agent 协作。

主要优势：

- 多 Agent 对话模型成熟。
- 适合研究原型、代码执行和协作实验。
- Core 层适合事件驱动和分布式扩展。

适合：

- 研究型多 Agent。
- 代码生成、测试、审查类协作原型。
- 多角色对话实验。

不适合：

- 只需要严格 DAG 和审批恢复的业务流程。

### 6. CrewAI

核心概念：角色团队（Crews）和流程（Flows）。

主要优势：

- 角色、任务、团队概念直观。
- 适合内容生产、研究团队、运营自动化。
- 业务叙事清晰，上手快。

适合：

- “研究员 + 分析师 + 写作者 + 审稿人”这类角色分工。
- 运营、营销、内容生产类 Agent 团队。

不适合：

- 对底层状态、checkpoint、条件边要求极细的系统。

### 7. LlamaIndex Agents

核心概念：数据和检索驱动的 Agent。

主要优势：

- 数据连接、索引、retriever、query engine 生态强。
- RAG 和 Agent 衔接自然。
- 适合文档、知识库、数据库问答。

适合：

- `project_07_enterprise_rag` 这类知识库问答。
- 数据密集型 Agent。
- 需要多数据源检索和工具调用结合的应用。

不适合：

- 与数据检索关系不大的纯流程自动化。

### 8. Semantic Kernel

核心概念：企业中间件式 AI SDK。

主要优势：

- 插件、函数、planner 等概念适合接企业 API。
- C# / Python / Java 覆盖企业常见技术栈。
- 适合 Microsoft 和 .NET 生态。

适合：

- Microsoft / Azure / .NET 企业系统。
- 需要把大量内部 API 封装成插件的场景。

不适合：

- 以多 Agent 研究模拟为主的项目。

---

## 三、研究型与新兴框架

### AgentScope

AgentScope 适合讲消息传递、大规模多 Agent 应用和分布式部署。它有代表性，但更偏研究、平台和仿真场景，不应直接等同于企业流程 Agent 的第一选择。

### CAMEL

CAMEL 的代表性在 role-playing、agent society、模拟专家协作和合成数据。它适合探索性任务和多 Agent 研究，但不应被包装成强治理、强审计的生产流程框架。

### Haystack

Haystack 更偏 RAG、pipeline 和 context engineering。它适合和 LlamaIndex 对比，用来讲生产 RAG pipeline 的另一条路线。

### Agno

Agno 代表 Agent platform 方向，强调 SDK、runtime、AgentOS、会话、审计、RBAC 等平台能力。可以作为新兴生态观察。

### Mastra

Mastra 是 TypeScript / Node 生态代表，适合产品型 Agent、Web 应用和前后端一体工程。

### Strands Agents

Strands Agents 值得作为 AWS 生态观察项。课程主线可以先不展开，但可以提醒学习者关注云厂商 Agent SDK 的演进。

---

## 四、MCP 和观测评估不是 Agent 框架

MCP 是工具和上下文接入协议。它解决“Agent 如何发现和调用外部工具/资源”，不直接解决状态编排、质量评估、审批和审计。

LangSmith、OpenTelemetry、Phoenix、Logfire 等更偏观测和评估。它们可以和 Agent 框架一起使用，但不能替代 Agent runtime。

模型网关也不是 Agent 框架。模型网关解决模型访问、配额、审计、路由和成本控制。

---

## 五、课后练习

1. 选 3 个你熟悉的业务场景，分别判断最适合哪类框架。
2. 解释为什么 AgentScope 和 CAMEL 有代表性，但不应该作为企业工程默认第一选择。
3. 用一句话区分 LangGraph、AutoGen、CrewAI。
4. 说明 MCP 在 OpenAI Agents SDK、LangGraph、LlamaIndex 中分别可能承担什么角色。
5. 阅读 `examples/framework_selection_matrix.py`，给一个新场景添加 capability tags。

---

## 参考入口

- LangGraph: https://docs.langchain.com/oss/python/langgraph/overview
- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/
- Google ADK: https://adk.dev/
- PydanticAI: https://pydantic.dev/docs/ai/overview/
- AutoGen: https://microsoft.github.io/autogen/stable/
- CrewAI: https://docs.crewai.com/
- LlamaIndex Agents: https://docs.llamaindex.ai/
- Semantic Kernel: https://learn.microsoft.com/semantic-kernel/
- AgentScope: https://github.com/modelscope/agentscope
- CAMEL: https://docs.camel-ai.org/
