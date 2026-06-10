# Day 25 课程：Agent 框架选型方法论

Day 24 解决“有哪些框架”。Day 25 解决“我的项目该先评估谁”。

框架选型不是填表格打分，而是把业务约束翻译成工程能力，再找最匹配的框架组合。

---

## 学习目标

- 能从需求中提取 Agent 框架能力标签。
- 能用决策树做初步选型。
- 能把 project_07/08/09 映射到不同框架。
- 能指出框架不能替代的生产工程边界。

---

## 一、先问 8 个问题

| 问题 | 如果答案是“是” | 优先评估 |
|------|----------------|----------|
| 是否需要长程状态、条件分支、checkpoint？ | 需要可恢复工作流 | LangGraph |
| 是否深度使用 OpenAI 模型、handoff、guardrails、sandbox？ | 需要原生 runtime | OpenAI Agents SDK |
| 是否在 Google Cloud / Gemini 生态？ | 需要企业部署和运维 | Google ADK |
| 是否要求输出强结构化、可校验、可测试？ | 需要 schema 和 eval | PydanticAI |
| 是否是多 Agent 对话和代码执行实验？ | 需要对话协作 | AutoGen |
| 是否是角色团队式业务自动化？ | 需要直观团队模型 | CrewAI |
| 是否 RAG、检索、数据连接是系统核心？ | 需要数据层能力 | LlamaIndex Agents / Haystack |
| 是否在 Microsoft / .NET 企业生态？ | 需要插件和企业 API 集成 | Semantic Kernel |

如果多个答案都是“是”，不要强行只选一个框架。真实系统经常组合使用：LangGraph 管流程，LlamaIndex 管检索，PydanticAI 管结构化输出，MCP 管工具接入。

---

## 二、能力标签怎么理解

`examples/framework_selection_matrix.py` 使用 capability tags 做教学演示。标签不是行业标准，而是课程内部为了把“需求”翻译成“工程能力”设计的词汇。

常用标签定义：

| 标签 | 含义 |
|------|------|
| `state_graph` | 用显式状态、节点和边编排 Agent 工作流 |
| `checkpoint` | 能保存中间状态，支持暂停、恢复或回放 |
| `human_in_loop` | 支持人工审批、人工中断或人工反馈 |
| `long_running` | 适合长时间、多步骤、可恢复任务 |
| `workflow` | 支持流程、状态或任务编排 |
| `rag_heavy` | RAG、检索、索引或数据问答是系统核心 |
| `data_connectors` | 提供较强的数据源连接和加载能力 |
| `retrieval` | 提供检索、召回或搜索能力 |
| `indexing` | 支持索引构建、维护或检索优化 |
| `query_engine` | 提供 query engine 或类似数据问答抽象 |
| `openai_native` | 贴近 OpenAI 模型和工具运行时 |
| `handoff` | 支持 Agent 之间的任务移交 |
| `guardrails` | 提供安全护栏、输入输出限制或运行时策略 |
| `tracing` | 支持调用链追踪和运行过程记录 |
| `sandbox` | 支持或适合沙箱执行、隔离工具调用 |
| `typed_output` | 用类型或 schema 约束模型输出 |
| `structured_output` | 强调结构化输出和程序可解析结果 |
| `dependency_injection` | 支持依赖注入，便于测试和业务对象管理 |
| `eval` | 支持或强调评估集、质量度量和持续评估 |
| `multi_agent` | 支持多个 Agent 协作 |
| `research_multi_agent` | 适合多 Agent 研究、仿真或原型实验 |
| `code_execution` | 支持或适合代码执行、测试和代码类工具调用 |
| `role_team` | 以角色团队和任务分工组织 Agent |
| `delegation` | 支持任务委派、角色分工或 Agent 协作分派 |
| `business_automation` | 面向业务流程自动化和重复运营任务 |
| `message_passing` | 以消息传递作为 Agent 协作核心机制 |
| `role_playing` | 以角色扮演方式组织 Agent 协作 |
| `simulation` | 适合模拟、仿真或探索性任务 |
| `enterprise_deploy` | 关注企业部署、运行时、权限或运维 |
| `observability` | 强调 trace、日志、指标或可观测性 |
| `mcp` | 支持或适合接入 Model Context Protocol |
| `plugin` | 支持插件、函数或工具封装 |
| `api_orchestration` | 编排企业 API、函数或插件调用 |
| `python` | 适合 Python 技术栈 |
| `typescript` | 适合 TypeScript 技术栈 |
| `enterprise_dotnet` | 适合 Microsoft / .NET 企业软件环境 |
| `google_cloud` | 适合 Google Cloud 生态 |
| `agent_platform` | 提供 Agent 应用运行平台、会话、权限或管理能力 |
| `audit` | 支持或强调运行记录、审计日志和操作追踪 |
| `rbac` | 强调角色权限或访问控制 |

完整标签定义以 `list_capability_definitions()` 返回值为准。增加新标签时，必须同时补定义和测试，避免选型规则变成黑盒。

评分公式是教学用启发式：

```python
score = len(matched) * 10 - len(missing) * 2
```

默认还会给 `engineering` tier 加 3 分，因为这门课优先面向工程落地，而不是纯研究模拟。如果要中性比较研究框架，可以调用 `recommend_frameworks(tags, tier_weight=0)`。

---

## 三、选型决策树

```text
问题是否以 RAG / 数据检索为核心？
├── 是：优先 LlamaIndex Agents / Haystack
│   └── 如果还需要复杂状态和审批：叠加 LangGraph
└── 否：
    是否需要长程状态、checkpoint、human-in-the-loop？
    ├── 是：优先 LangGraph
    └── 否：
        是否深度绑定 OpenAI runtime、handoff、guardrails、sandbox？
        ├── 是：优先 OpenAI Agents SDK
        └── 否：
            是否强依赖结构化输出和类型安全？
            ├── 是：优先 PydanticAI
            └── 否：
                是否是多角色协作？
                ├── 偏对话/研究/代码执行：AutoGen
                ├── 偏角色团队/业务流程：CrewAI
                └── 偏企业插件/API 编排：Semantic Kernel
```

---

## 四、把课程项目映射到框架

### project_07_enterprise_rag

核心能力：

- RAG 检索。
- 数据连接和索引。
- 混合检索、rerank、引用校验。
- LangGraph 质量闭环。

推荐组合：

- LlamaIndex Agents：负责数据连接、索引、retriever、query engine。
- LangGraph：负责多轮状态、质量检查、重试和人工介入。
- PydanticAI：负责结构化评估结果和引用校验输出。

### project_08_workflow_agent

核心能力：

- 任务规划。
- 工具注册和治理。
- 审批、checkpoint、resume。
- 重试、限流、熔断、审计。

推荐组合：

- LangGraph：负责状态图、审批中断和恢复。
- OpenAI Agents SDK：负责 handoff、guardrails、tracing、MCP 和 sandbox。
- Google ADK：如果目标是企业部署和云上运维，可作为生产化路线。

### project_09_dev_team

核心能力：

- 多 Agent 角色协作。
- Planner / Developer / Tester / DocWriter。
- 代码生成、测试、修复循环。
- sandbox、质量门禁、人工确认。

推荐组合：

- AutoGen：适合多 Agent 对话和代码执行实验。
- CrewAI：适合角色团队和任务委派叙事。
- LangGraph：适合把协作过程收敛成可恢复状态机。
- OpenAI Agents SDK：适合接 handoff、sandbox、tracing 和 guardrails。

---

## 五、框架组合的集成成本

组合框架很常见，但组合不等于把优点简单相加。常见风险包括：

| 风险 | 例子 | 应对 |
|------|------|------|
| 状态序列化不一致 | LangGraph checkpoint 保存的状态和某个框架 session 状态格式不同 | 明确唯一状态源，跨框架只传结构化快照 |
| 事件循环竞争 | 一个框架用 async runtime，另一个工具层也管理事件循环 | 在边界层统一 async 调度，不在业务节点里嵌套运行循环 |
| 依赖版本冲突 | 不同框架依赖的 LLM SDK、Pydantic、http client 版本不一致 | 锁定依赖版本，先做最小集成 spike |
| 调试链路断裂 | trace 分散在多个框架和工具服务里 | 统一 trace_id / run_id / tool_call_id |
| 工具治理重复 | 两个框架都能注册工具，但权限策略不一致 | 把权限、审批、审计放到统一工具网关或 ToolRegistry |
| 错误处理语义不同 | A 框架把失败当 retryable，B 框架直接抛异常 | 定义统一错误类型和重试策略 |
| 成本统计不完整 | RAG、LLM、工具调用分别记账 | 在入口层统一记录 token、耗时、工具次数和用户/租户 |

课程建议：先选一个主编排框架，再接一个明确职责的辅助框架。比如 `LangGraph + LlamaIndex` 是清晰组合：前者管流程状态，后者管数据检索。不要让两个框架同时争夺“谁是主 runtime”。

---

## 六、框架不能替代什么

无论选哪个框架，下面这些能力都必须明确设计：

| 工程边界 | 为什么不能省 |
|----------|--------------|
| 权限 | 框架不会自动知道谁能读写哪些企业数据 |
| 审计 | 生产事故需要追踪每一步工具调用和决策 |
| Sandbox | 代码执行、文件写入、网络访问必须隔离 |
| Checkpoint | 长程任务必须可暂停、恢复、回放 |
| Eval | 框架跑通不代表回答可靠 |
| 压测 | demo 成功不代表高并发稳定 |
| 成本预算 | 多轮规划、检索、工具调用会放大成本 |
| 人工介入 | 高风险动作需要审批和回退 |

框架能降低实现成本，但不能替你做安全和治理判断。

---

## 七、可运行示例

`examples/framework_selection_matrix.py` 用 capability tags 做简单推荐。

示例：

```python
from project_10_agent_frameworks.examples.framework_selection_matrix import recommend_frameworks

recommendations = recommend_frameworks(
    {"state_graph", "checkpoint", "human_in_loop", "long_running"}
)
print(recommendations[0].framework.name)
# LangGraph
```

`examples/agent_capability_mapper.py` 把前面课程项目映射到框架：

```python
from project_10_agent_frameworks.examples.agent_capability_mapper import (
    map_project_to_frameworks,
)

mapping = map_project_to_frameworks("project_07_enterprise_rag")
print(mapping.recommendations[0].framework.name)
# LlamaIndex Agents
```

运行测试：

```bash
conda run -n agent_env python -m unittest discover project_10_agent_frameworks/tests -v
```

---

## 八、面试追问方向

1. 为什么 LangGraph 适合长程 Agent，而不是简单聊天机器人？
2. OpenAI Agents SDK 的 handoff 和 CrewAI 的 role delegation 有什么区别？
3. PydanticAI 解决的是模型能力问题，还是工程约束问题？
4. AutoGen 和 CAMEL 都能做多 Agent，为什么一个更偏工程原型，一个更偏研究模拟？
5. LlamaIndex Agents 和 LangGraph 能如何组合？
6. 为什么 MCP 不能替代 ToolRegistry 或权限系统？
7. 如果一个项目既要 RAG，又要审批，又要类型安全，你会怎么组合框架？

---

## 课后练习

1. 为一个“企业合同问答 + 审批流”项目做框架选型。
2. 为一个“自动生成周报并发送消息”的项目做框架选型。
3. 为一个“代码生成、测试、修复”的项目做框架选型。
4. 修改 `framework_selection_matrix.py`，给 Mastra 添加一个 TypeScript 产品 Agent 场景。
5. 写一段说明：为什么框架选型必须和权限、审计、压测一起讨论。
