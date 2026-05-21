# AI Agent 从零到一 — 渐进式实战课程

> 从裸 HTTP API 调用到 LangGraph 多 Agent 协作系统，17 天掌握 AI Agent 开发全链路

## 项目简介

本仓库是一个 **AI Agent 渐进式教学课程代码库**，共 6 个阶段 / 17 天，从最底层的 HTTP API 请求开始，逐步过渡到使用 LangChain + LangGraph 框架构建完整的智能体系统。每一课都有可独立运行的代码、详尽的中文注释和学习笔记。

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| LLM 编排 | LangChain >= 0.3.0 | 模型调用、Prompt 模板、输出解析、LCEL 链 |
| Agent 编排 | LangGraph >= 0.2.0 | 状态机式 Agent 图编排 |
| 模型接口 | langchain-openai >= 0.2.0 | OpenAI 兼容接口（国产模型通用） |
| 模型接口 | langchain-google-genai >= 2.0.0 | Google Gemini 专用接口 |
| 向量数据库 | ChromaDB >= 0.5.0 | 本地向量存储（RAG） |
| 数据校验 | Pydantic >= 2.0.0 | 结构化数据模型 |
| HTTP 请求 | requests >= 2.31.0 | 原始 API 调用 |
| 环境管理 | python-dotenv >= 1.0.0 | .env 文件管理 |

### 支持的大模型

所有国产模型均通过 OpenAI 兼容接口（`ChatOpenAI` + 自定义 `base_url`）统一调用，一行代码即可切换：

| 模型 | Provider 标识 | 推荐用途 |
|------|--------------|---------|
| DeepSeek | `deepseek` | **主力推荐**，性价比高 |
| 通义千问 Qwen | `qwen` | 中文理解强 |
| 智谱 GLM | `glm` | 轻硬兼顾 |
| Kimi / Moonshot | `kimi` | 长上下文 |
| Google Gemini | `gemini` | 多模态能力 |

```python
from common.model_factory import create_model

model = create_model("deepseek")   # 切换只需改一个参数
result = model.invoke("你好")
```

## 课程路线

### 阶段 1：API 基础与 LangChain 入门（Day 1-2）

| 文件 | 内容 |
|------|------|
| `01_raw_api_call.py` | 原始 HTTP API 调用，理解底层原理 |
| `02_langchain_models.py` | LangChain 模型调用与多模型切换 |
| `03_model_comparison.py` | 多模型输出对比 |
| `04_prompt_templates.py` | PromptTemplate / ChatPromptTemplate |
| `05_output_parsers.py` | JSON / Pydantic 结构化输出解析 |
| `06_lcel_chains.py` | LCEL 链式调用 `prompt \| model \| parser` |
| `07_streaming.py` | 流式输出 |

### 阶段 2：对话 Agent（Day 3-4）

| 文件 | 内容 |
|------|------|
| `01_simple_chatbot.py` | 最简命令行对话循环 |
| `02_chat_with_history.py` | 带消息历史的短期记忆 |
| `03_chat_with_persona.py` | 角色扮演 Agent（4 种人设） |
| `04_session_manager.py` | 多会话管理 |
| `05_context_window.py` | Token 窗口管理（防溢出） |
| `06_chat_app.py` | 综合命令行聊天应用 |

### 阶段 3：工具调用 Agent — Function Calling（Day 5-7）

| 文件 | 内容 |
|------|------|
| `01_function_calling_raw.py` | 手写 Function Calling 完整生命周期 |
| `02_langchain_tools.py` | `@tool` 装饰器快速创建工具 |
| `03_tool_binding.py` | 工具绑定到模型 |
| `04_agent_loop.py` | Agent 工具调用循环 |
| `05_error_handling.py` | 错误处理与重试 |
| `06_langgraph_agent.py` | LangGraph 状态机式工具 Agent |
| `07_tool_agent_complete.py` | 完整版多工具命令行 Agent |

内置工具集：
- **安全计算器** — AST 抽象语法树安全求值，不直接 eval
- **网络搜索** — 模拟搜索接口
- **文件读写** — 本地文件操作
- **系统信息** — 运行环境信息
- **代码执行** — Python 沙箱执行

### 阶段 4：记忆与 RAG（Day 8-10）

| 文件 | 内容 |
|------|------|
| `01_short_term_memory.py` | 短期记忆（运行期间消息列表） |
| `02_long_term_memory.py` | 长期记忆（SQLite 持久化） |
| `03_memory_agent.py` | 集成记忆的 Agent |
| `04_embedding_basics.py` | Embedding 原理（文本 → 向量 → 相似度） |
| `05_vector_store.py` | ChromaDB 向量库增删改查 |
| `06_document_loader.py` | 文档加载（PDF/Markdown/TXT） |
| `07_text_splitter.py` | 文本分块策略 |
| `08_simple_rag.py` | 完整 RAG 管道 |
| `09_rag_agent.py` | RAG 作为 Agent 工具 |
| `10_knowledge_base_app.py` | 个人知识库问答应用 |

### 阶段 5：高级 Agent 模式（Day 11-13）

| 文件 | 内容 |
|------|------|
| `01_react_concept.py` | ReAct 原理解密（手写 Thought → Action → Observation） |
| `02_langgraph_react.py` | LangGraph ReAct Agent |
| `03_react_with_tools.py` | ReAct + 工具集 |
| `04_plan_and_execute.py` | Plan-and-Execute 规划模式 |
| `05_dynamic_replanning.py` | 动态重新规划 |
| `06_self_reflection.py` | 自我反思与纠错 |
| `07_human_in_the_loop.py` | 人类介入（Human-in-the-loop） |
| `08_super_agent.py` | **集大成 Super Agent**（713 行） |

**Super Agent 架构**：任务复杂度自动研判 → 简单任务 ReAct 直接回答 / 复杂任务规划执行 → 安全审批中断（人类介入）→ 自我反思质检 → 最多 3 次重修

### 阶段 6：多 Agent 协作系统（Day 14-17）

| 文件 | 内容 |
|------|------|
| `01_multi_agent_concepts.py` | 多 Agent 架构模式（主从/对等/辩论） |
| `02_agent_communication.py` | Agent 消息传递 |
| `03_supervisor_pattern.py` | **主管模式**（Supervisor 动态路由分派） |
| `04_collaborative_agents.py` | 协作模式（接力完成） |
| `05_research_team/` | **AI 调研团队**（综合项目） |

**AI 调研团队流水线**：Researcher（搜集事实）→ Analyst（提炼洞察）→ Writer（编排报告）→ 文件落盘

## 项目结构

```
agent/
├── common/                    # 公共模块
│   ├── config.py              #   全局模型配置（5 种模型 base_url / api_key）
│   └── model_factory.py       #   模型工厂（一行代码切换模型）
├── project_01_basics/         # 阶段 1：API 与框架入门（Day 1-2）
├── project_02_chat_agent/     # 阶段 2：对话 Agent（Day 3-4）
├── project_03_tool_agent/     # 阶段 3：工具调用 Agent（Day 5-7）
│   └── tools/                 #   内置工具集
├── project_04_memory_rag/     # 阶段 4：记忆与 RAG（Day 8-10）
├── project_05_advanced/       # 阶段 5：高级 Agent 模式（Day 11-13）
├── project_06_multi_agent/    # 阶段 6：多 Agent 协作（Day 14-17）
│   └── 05_research_team/      #   AI 调研团队综合项目
├── requirements.txt           # Python 依赖
├── .env.example               # 环境变量模板
├── LEARNING_PLAN.md           # 完整学习计划大纲
└── walkthrough.md             # 前 3 天详细 Walkthrough
```

## 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone <repo-url>
cd agent

# 创建并激活 conda 虚拟环境
conda create -n agent_env python=3.10
conda activate agent_env

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入你的 API Key（至少配置一个模型）
# DEEPSEEK_API_KEY=sk-your-key-here
```

### 3. 运行课程代码

每个 `.py` 文件均可独立运行：

```bash
# 阶段 1：从原始 API 调用开始
python project_01_basics/01_raw_api_call.py

# 阶段 2：体验对话 Agent
python project_02_chat_agent/06_chat_app.py

# 阶段 3：工具调用 Agent
python project_03_tool_agent/07_tool_agent_complete.py

# 阶段 4：RAG 知识库
python project_04_memory_rag/10_knowledge_base_app.py

# 阶段 5：Super Agent
python project_05_advanced/08_super_agent.py

# 阶段 6：AI 调研团队
python project_06_multi_agent/05_research_team/main.py
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

```
请求附带 tools schema → 模型返回 tool_calls → 本地执行工具函数 → 结果反馈 → 模型生成最终回答
```

### LangGraph 状态机编排

```python
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("researcher", researcher_node)
workflow.add_conditional_edges("supervisor", route_fn)
app = workflow.compile()
```

### Super Agent 决策流

```
Planner(规划) → [简单: ReAct直接回答 | 复杂: Executor→SafetyCheck→Reflector]
                                    ↓
                            人类审批中断挂起
                                    ↓
                            自我反思纠错（最多3次）
```

## 学习建议

1. **按顺序学习**：阶段之间有严格的依赖关系，建议从 Day 1 开始依次推进
2. **先读文档**：每个阶段目录下有 `DAYXX.md` 学习笔记，建议先读再跑代码
3. **动手修改**：改 Prompt、换模型、调参数，观察输出变化
4. **对比理解**：阶段 3 的 `01_function_calling_raw.py`（手写）vs `06_langgraph_agent.py`（框架），对比理解框架抽象的价值
5. **综合实战**：最后的 AI 调研团队（阶段 6）是所有知识的综合运用

## 文档索引

| 文档 | 说明 |
|------|------|
| [LEARNING_PLAN.md](LEARNING_PLAN.md) | 完整学习计划大纲（6 阶段 / 17 天） |
| [walkthrough.md](walkthrough.md) | 前 3 天详细 Walkthrough |
| `project_XX/DAYXX.md` | 每日学习笔记 |

## 许可证

本项目仅供学习参考使用。
