# AI Agent 从零到一：渐进式实战课程

> 从裸 HTTP API 调用到企业级 RAG、工作流 Agent、多 Agent 开发团队、主流 Agent 框架选型和生产化服务运维，27 天掌握 AI Agent 工程主线。

## 项目简介

本仓库是一个 **AI Agent 渐进式教学课程代码库**，共 11 个项目 / 27 天，从最底层的 HTTP API 请求开始，逐步过渡到 LangChain、LangGraph、RAG、多 Agent、企业治理、压测、框架选型和服务化运维。

课程分为两段：

- `project_01` 到 `project_06`：基础能力训练，每个文件基本都可独立运行，适合按 Day 顺序学习。
- `project_07` 到 `project_11`：企业级综合项目，按职责分包，重点训练架构设计、治理、安全、评估、选型判断和生产运维。

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| LLM 编排 | LangChain >= 0.3.0 | 模型调用、Prompt 模板、输出解析、LCEL 链 |
| Agent 编排 | LangGraph >= 0.2.0 | 状态机式 Agent 图编排 |
| 模型接口 | langchain-openai >= 0.2.0 | OpenAI 兼容接口，国产模型通用 |
| 模型接口 | langchain-google-genai >= 2.0.0 | Google Gemini 专用接口 |
| 向量数据库 | ChromaDB >= 0.5.0 | 本地向量存储和 RAG 检索 |
| 文档处理 | pypdf / python-docx / markdown | 多格式文档摄取 |
| 数据处理 | openpyxl / pandas | 表格处理、日报周报、业务流程自动化 |
| 数据校验 | Pydantic >= 2.0.0 | 结构化数据模型和输出约束 |
| 服务化 | FastAPI / Uvicorn | Agent API 服务、流式响应和健康检查 |
| 环境管理 | python-dotenv >= 1.0.0 | `.env` 文件管理 |
| 测试 | unittest / pytest | 毕业项目回归测试 |

### 支持的大模型

所有国产模型均通过 OpenAI 兼容接口统一调用，一行代码即可切换：

| 模型 | Provider 标识 | 推荐用途 |
|------|--------------|---------|
| DeepSeek | `deepseek` | 主力推荐，性价比高 |
| 通义千问 Qwen | `qwen` | 中文理解强 |
| 智谱 GLM | `glm` | 轻量任务和国产生态 |
| Kimi / Moonshot | `kimi` | 长上下文 |
| Google Gemini | `gemini` | 多模态能力 |

```python
from common.model_factory import create_model

model = create_model("deepseek", temperature=0.7)
result = model.invoke("你好")
```

## 课程路线

| 阶段 | 天数 | 项目 | 核心主题 |
|------|------|------|------|
| 阶段 1 | Day 1-2 | `project_01_basics` | 原始 API、LangChain 模型、Prompt、结构化输出、LCEL、Streaming |
| 阶段 2 | Day 3-4 | `project_02_chat_agent` | 对话 Agent、历史消息、角色设定、多会话、上下文窗口 |
| 阶段 3 | Day 5-7 | `project_03_tool_agent` | Function Calling、工具注册、Agent Loop、错误处理、LangGraph 工具 Agent |
| 阶段 4 | Day 8-10 | `project_04_memory_rag` | 短期记忆、长期记忆、Embedding、向量库、文档摄取、RAG Agent |
| 阶段 5 | Day 11-13 | `project_05_advanced` | ReAct、Planning、动态重规划、自我反思、Human-in-the-loop、Super Agent |
| 阶段 6 | Day 14-17 | `project_06_multi_agent` | 多 Agent 通信、Supervisor、协作模式、AI 调研团队 |
| 毕业项目 1 | Day 18-19 | `project_07_enterprise_rag` | 企业级 RAG、混合检索、ACL、审计、质量评估、吞吐量治理 |
| 毕业项目 2 | Day 20-21 | `project_08_workflow_agent` | 工作流 Agent、ToolRegistry、任务拆解、checkpoint、hooks、压力治理 |
| 毕业项目 3 | Day 22-23 | `project_09_dev_team` | 多 Agent 开发团队、消息总线、代码生成、自检闭环、沙箱与长任务治理 |
| 选型总结课 | Day 24-25 | `project_10_agent_frameworks` | 主流 Agent 框架横向比较、能力标签、项目映射、框架组合风险 |
| 生产运维课 | Day 26-27 | `project_11_agent_service_ops` | FastAPI 服务化、鉴权、限流、模型网关、成本治理、trace、metrics、eval、部署 |

## 重点项目说明

### project_07：企业级 RAG 智能知识库

企业级 RAG 不只是在向量库里查几段文本。这个项目覆盖文档摄取、混合分块、向量检索、BM25、RRF 融合、LLM 重排、来源追踪、租户 ACL、PII 保护、审计日志、RAG 质量评估和吞吐量治理。

核心工作流：

```text
意图解析 -> 混合检索 -> 重排 -> 生成 -> 质量检查 -> 格式化输出
```

### project_08：自动化业务流程调度 Agent

这个项目把 Agent 放到企业流程里：统一工具注册、权限校验、任务拆解、依赖排序、执行引擎、重试降级、checkpoint、人类审批、hooks、日报周报生成和压力治理。

核心工作流：

```text
plan -> execute -> validate -> report
```

### project_09：多智能体协同开发助手

这个项目训练多 Agent 工程协作：规划、开发、测试、文档四类角色通过消息总线协作，形成“写代码 -> 查代码 -> 改代码 -> 生成交付报告”的闭环，同时强调 sandbox、审计、长任务、压力和交付边界。

核心工作流：

```text
planner -> developer -> tester -> fixer -> docwriter -> deliver
```

### project_10：主流 Agent 框架选型课

这个项目不是框架排行榜，而是选型方法课。它把 LangGraph、OpenAI Agents SDK、Google ADK、PydanticAI、AutoGen、CrewAI、LlamaIndex Agents、Semantic Kernel 等框架按能力标签映射到真实工程需求，并明确 MCP、观测平台、评估平台和模型网关不等同于 Agent 框架。

### project_11：Agent 生产化服务与运维

这个项目把前面的 Agent 能力封装成真实 FastAPI 服务，覆盖 `/chat`、`/stream`、`/health`、`/metrics`、`/eval/smoke`，并补上 API Key 鉴权、令牌桶限流、全局异常映射、模型网关、fallback、预算控制、trace、metrics、冒烟评估和 Docker 部署说明。`/stream` 是 SSE 协议演示，不伪装成真实 token-by-token 模型流；成本、指标和 trace 使用内存实现，文档明确说明生产环境应接入数据库、Redis、Prometheus 或 OpenTelemetry。

## 项目结构

```text
agent/
├── common/                         # 公共模块
│   ├── config.py                   # 全局模型配置
│   └── model_factory.py            # 模型工厂，一行代码切换 provider
├── project_01_basics/              # Day 1-2：API 与 LangChain 入门
├── project_02_chat_agent/          # Day 3-4：对话 Agent
├── project_03_tool_agent/          # Day 5-7：工具调用 Agent
├── project_04_memory_rag/          # Day 8-10：记忆与 RAG
├── project_05_advanced/            # Day 11-13：高级 Agent 模式
├── project_06_multi_agent/         # Day 14-17：多 Agent 协作
├── project_07_enterprise_rag/      # Day 18-19：企业级 RAG
├── project_08_workflow_agent/      # Day 20-21：自动化业务流程 Agent
├── project_09_dev_team/            # Day 22-23：多智能体开发团队
├── project_10_agent_frameworks/    # Day 24-25：Agent 框架选型
├── project_11_agent_service_ops/   # Day 26-27：Agent 服务化与生产运维
├── requirements.txt                # Python 依赖
├── .env.example                    # 环境变量模板
├── LEARNING_PLAN.md                # 完整学习计划
└── walkthrough.md                  # 前 3 天详细 Walkthrough
```

## 快速开始

### 1. 环境准备

```bash
git clone <repo-url>
cd agent

conda create -n agent_env python=3.10
conda activate agent_env

pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env

# 编辑 .env，至少配置一个模型 Key
# DEEPSEEK_API_KEY=sk-your-key-here
```

### 3. 运行课程代码

必须在仓库根目录执行，确保 `common/` 能被正确导入。

```bash
# Day 1：原始 API 调用
python project_01_basics/01_raw_api_call.py

# Day 4：综合聊天应用
python project_02_chat_agent/06_chat_app.py

# Day 7：完整工具 Agent
python project_03_tool_agent/07_tool_agent_complete.py

# Day 10：个人知识库问答
python project_04_memory_rag/10_knowledge_base_app.py

# Day 13：Super Agent
python project_05_advanced/08_super_agent.py

# Day 17：AI 调研团队
python project_06_multi_agent/05_research_team/main.py

# Day 19：企业级 RAG
python project_07_enterprise_rag/main.py

# Day 21：工作流 Agent
python project_08_workflow_agent/main.py

# Day 23：多智能体开发团队
python project_09_dev_team/main.py

# Day 24-25：Agent 框架选型演示
python project_10_agent_frameworks/01_framework_comparison.py

# Day 26-27：Agent 生产化服务
python project_11_agent_service_ops/main.py
```

### 4. 运行回归测试

```bash
python -m unittest discover project_07_enterprise_rag/tests -v
python -m unittest discover project_08_workflow_agent/tests -v
python -m unittest discover project_09_dev_team/tests -v
python -m unittest discover project_10_agent_frameworks/tests -v
python -m unittest discover project_11_agent_service_ops/tests -v
```

## 核心设计

### 模型工厂模式

所有模型通过工厂统一创建，国产模型走 `ChatOpenAI(base_url=...)` 兼容接口：

```python
from common.model_factory import create_model

model = create_model("deepseek", temperature=0.7)
result = model.invoke("解释量子计算")
```

### Function Calling 生命周期

```text
请求附带 tools schema -> 模型返回 tool_calls -> 本地执行工具函数 -> 结果反馈 -> 模型生成最终回答
```

### LangGraph 状态机编排

```python
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("researcher", researcher_node)
workflow.add_conditional_edges("supervisor", route_fn)
app = workflow.compile()
```

### 企业级 Agent 工程边界

课程后半段反复强调：框架不能替代生产工程能力。企业级 Agent 需要单独设计：

- 权限、租户隔离和访问控制
- 审计日志、trace、运行记录和失败分析
- checkpoint、人工审批和可恢复执行
- sandbox、敏感操作隔离和安全扫描
- eval、压测、吞吐量、成本和降级策略
- API 服务化、流式响应、鉴权、限流、健康检查和发布后冒烟评估
- 模型网关、全局异常处理、成本持久化、指标导出和 trace 采集
- 框架组合时的状态序列化、依赖冲突和调试链路

## 学习建议

1. **按 Day 顺序推进**：`project_01` 到 `project_06` 是基础能力递进，`project_07` 到 `project_11` 是企业项目、选型和生产运维收束。
2. **先跑再改**：每个脚本先用默认参数跑通，再改 Prompt、模型、工具和配置。
3. **关注边界**：不要只看 LLM 回答，要观察状态、工具调用、日志、重试和失败路径。
4. **毕业项目重点读结构**：`project_07/08/09` 更接近真实工程，要重点看 `graph/`、`governance/`、`tests/`。
5. **选型课不要背结论**：`project_10` 的重点是“需求 -> 能力标签 -> 框架匹配”，不是记排行榜。

## 文档索引

| 文档 | 说明 |
|------|------|
| [LEARNING_PLAN.md](LEARNING_PLAN.md) | 完整学习计划大纲（11 个项目 / 27 天） |
| [LEARNING_PROGRESS.md](LEARNING_PROGRESS.md) | 学习进度记录 |
| [LEARNING_SKILLS.md](LEARNING_SKILLS.md) | 学习技能与方法总结 |
| [walkthrough.md](walkthrough.md) | 前 3 天详细 Walkthrough |
| `project_XX/DAYXX.md` | 每日学习笔记 |
| `project_07_enterprise_rag/PROJECT_PLAN.md` | 企业级 RAG 项目计划和验收标准 |
| `project_08_workflow_agent/PROJECT_PLAN.md` | 工作流 Agent 项目计划和验收标准 |
| `project_09_dev_team/PROJECT_PLAN.md` | 多智能体开发团队项目计划和验收标准 |
| `project_10_agent_frameworks/PROJECT_PLAN.md` | 主流 Agent 框架选型项目计划和验收标准 |
| `project_11_agent_service_ops/PROJECT_PLAN.md` | Agent 生产化服务与运维项目计划和验收标准 |

## 当前课程边界

本课程已经覆盖 Agent 工程主线和最小生产化服务闭环。后续如果继续扩展，最自然的方向是把 project_11 进一步升级为完整平台课，例如多租户控制台、队列化异步任务、OpenTelemetry 接入、Prometheus 看板、Kubernetes 部署和灰度发布。

## 许可证

本项目仅供学习参考使用。
