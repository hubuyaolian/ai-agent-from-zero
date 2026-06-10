# Agent 框架选型课程项目计划书

## 1. 项目概述

本项目是 AI Agent 课程的第 10 个补充项目，目标是系统讲清当前主流 Agent 框架的定位、优势、适用场景和选型边界。

课程不做“框架排行榜”，也不把每个框架都安装演示一遍。更合理的目标是：学习者能根据项目需求判断应该优先评估哪类框架，并知道框架不能替代哪些生产工程边界。

框架信息截止日期：2026-06-10。课程给出的是当下选型方法和主流定位，具体 API、部署能力和生态成熟度必须以官方最新文档为准。

## 2. 教学目标

- 理解 Agent 框架的主要分类：状态图编排、原生运行时、企业开发套件、类型安全框架、多 Agent 对话、角色团队、RAG 数据层、企业中间件。
- 掌握 8 个核心框架的主线优势：LangGraph、OpenAI Agents SDK、Google ADK、PydanticAI、AutoGen、CrewAI、LlamaIndex Agents、Semantic Kernel。
- 理解 AgentScope、CAMEL、Haystack、Agno、Mastra、Strands Agents 的研究或新兴生态价值。
- 能把 project_07、project_08、project_09 的能力需求映射到合适框架。
- 能区分 Agent 框架、MCP 协议、观测平台、评估平台和模型网关。
- 能说清楚框架选型不能替代权限、审计、sandbox、checkpoint、eval、压测和成本治理。

## 3. 本期范围

| 模块 | 内容 |
|------|------|
| 框架地图 | 核心框架、研究框架、新兴框架的分类 |
| 选型维度 | 状态、工具、RAG、多 Agent、类型安全、部署、观测、沙箱、能力标签 |
| 项目映射 | project_07/08/09 与框架能力对应 |
| 可运行示例 | 终端入口脚本、按 capability tags 推荐框架 |
| 测试 | 验证核心选型规则 |

## 4. 非本期范围

- 不逐个安装所有框架。
- 不写真实 OpenAI、Google、AWS、Microsoft 云服务调用代码。
- 不承诺某个框架永远是“最优选择”。
- 不用 GitHub star 数或社交媒体热度代替工程判断。
- 不把 MCP、LangSmith、OpenTelemetry、Phoenix、Logfire 归类为 Agent 框架。

## 5. 两日课程计划

### Day 24：主流 Agent 框架横向比较

| 序号 | 内容 | 验收 |
|------|------|------|
| 24.1 | Agent 框架分类地图 | 能说出每类框架解决什么问题 |
| 24.2 | 8 个核心框架对比 | 能说明主要优势和不适用场景 |
| 24.3 | AgentScope / CAMEL 定位 | 能区分工业主流和研究主流 |
| 24.4 | MCP 与框架关系 | 能解释 MCP 是协议，不是 Agent 框架 |

### Day 25：选型方法论与项目映射

| 序号 | 内容 | 验收 |
|------|------|------|
| 25.1 | 选型决策树 | 能按需求维度做初选 |
| 25.2 | 能力标签定义 | 能解释 capability tags 的含义 |
| 25.3 | 框架组合风险 | 能指出状态、依赖、事件循环和调试链路成本 |
| 25.4 | 框架不能替代的边界 | 能指出安全、审计、评估、压测仍要自己设计 |
| 25.5 | 课程项目映射 | 能把 project_07/08/09 映射到合适框架 |
| 25.6 | 可运行示例 | `01_framework_comparison.py` 和测试通过 |

## 6. 交付物

| 文件 | 说明 |
|------|------|
| `DAY24.md` | 主流框架对比课程 |
| `DAY25.md` | 选型方法论课程 |
| `01_framework_comparison.py` | 终端框架对比和交互式选型演示 |
| `examples/framework_selection_matrix.py` | 框架能力标签与推荐逻辑 |
| `examples/agent_capability_mapper.py` | 课程项目到框架的映射 |
| `tests/test_framework_selection.py` | 选型规则测试 |

## 7. 验收标准

- 能清楚区分 LangGraph、OpenAI Agents SDK、Google ADK、PydanticAI、AutoGen、CrewAI、LlamaIndex Agents、Semantic Kernel 的定位。
- 能说明 AgentScope 和 CAMEL 为什么有代表性，但不应直接等同于工业第一梯队。
- 能给出 3 个以上具体场景的框架推荐，并说明理由。
- 可运行测试通过。
- 课程明确声明框架不能替代权限、审计、sandbox、checkpoint、质量评估和压测治理。

## 8. 当前技术判断

- LangGraph 是长程、有状态、可恢复 Agent 编排的重要主流路线。
- OpenAI Agents SDK 更适合 OpenAI 模型和工具生态下的原生 Agent runtime。
- Google ADK 更适合 Google Cloud / Gemini 企业生态。
- PydanticAI 的核心价值是类型安全、结构化输出、依赖注入和 eval。
- AutoGen 和 CrewAI 都适合多 Agent，但前者更偏对话/事件/研究原型，后者更偏角色团队和业务流程叙事。
- LlamaIndex Agents 和 Haystack 更贴近数据、检索、RAG pipeline。
- Semantic Kernel 更适合 Microsoft/.NET 和企业插件式集成。
- AgentScope、CAMEL 是多 Agent 研究与模拟的重要代表，可以讲，但不应替代工程主线。
