# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# AI Agent 渐进式学习课程（6 阶段 + 3 个毕业项目）

> 仓库根：`/Users/huangyang/code/agent`
> 文档：[README.md](README.md) · [LEARNING_PLAN.md](LEARNING_PLAN.md)

## 仓库速览

这是一个**多阶段 AI Agent 教学代码库**，9 个子项目按学习路径编号，每个项目都是可独立运行的 Python 工程。所有项目**共享根目录的 `common/` 公共模块**（模型工厂 + 全局配置）和 `requirements.txt`。

| 子项目 | 内容 | 入口 |
|--------|------|------|
| `project_01_basics/` | API 原始调用 → LangChain 入门（Day 1-2） | `01_raw_api_call.py` |
| `project_02_chat_agent/` | 对话 Agent + 消息历史管理（Day 3-4） | `06_chat_app.py` |
| `project_03_tool_agent/` | Function Calling + LangGraph 工具 Agent（Day 5-7） | `07_tool_agent_complete.py` |
| `project_04_memory_rag/` | 长期记忆 + ChromaDB + RAG（Day 8-10） | `10_knowledge_base_app.py` |
| `project_05_advanced/` | ReAct / Plan-Execute / Human-in-the-loop / Super Agent（Day 11-13） | `08_super_agent.py` |
| `project_06_multi_agent/` | 多 Agent 协作 + AI 调研团队（Day 14-17） | `05_research_team/main.py` |
| `project_07_enterprise_rag/` | **毕业项目一**：企业级 RAG 知识库（Day 18-19） | `main.py` |
| `project_08_workflow_agent/` | **毕业项目二**：业务流程自动化 Agent（Day 20-21） | `main.py` |
| `project_09_dev_team/` | **毕业项目三**：多智能体开发助手（Day 22-23） | `main.py` |

每个子项目有自己的 `DAYxx.md` 学习笔记和 `config.py`，可独立运行。

## 常用命令

### 环境准备
```bash
# 创建虚拟环境（推荐 Python 3.10+）
python -m venv .venv && source .venv/bin/activate

# 安装依赖（统一一份）
pip install -r requirements.txt

# 配置 API Key（至少配置一个）
cp .env.example .env
# 编辑 .env，至少填一个：DEEPSEEK_API_KEY / QWEN_API_KEY / GLM_API_KEY / KIMI_API_KEY / GEMINI_API_KEY
```

### 运行任意阶段代码
```bash
# 关键：必须在仓库根目录运行，或设置 PYTHONPATH 让项目找到 common/
cd /Users/huangyang/code/agent
python project_01_basics/01_raw_api_call.py
python project_07_enterprise_rag/main.py
```

### 代码质量
```bash
# Lint（项目使用 .flake8，忽略 E402/W503，行长上限 100）
flake8 project_xx/

# 毕业项目 07/08/09 自带 pytest 测试
cd project_07_enterprise_rag && pytest tests/ -v
cd project_08_workflow_agent && pytest tests/ -v
cd project_09_dev_team && pytest tests/ -v
```

## 核心架构

### 1. 模型工厂（`common/model_factory.py`）

所有 LLM 调用统一走 `create_model(provider, **kwargs)`，**通过切换 provider 字符串就能换模型**，无需改业务代码：

```python
from common.model_factory import create_model

model = create_model("deepseek", temperature=0.7)  # 换 qwen / glm / kimi / gemini
result = model.invoke("你好")
```

**支持的 provider**（在 `common/config.py` 的 `MODEL_CONFIGS` 字典中维护）：
- 国产模型走 `ChatOpenAI(base_url=...)` 兼容接口：`deepseek` / `qwen` / `glm` / `kimi` / `minimax` / `xiaomi mimo`
- Gemini 单独走 `ChatGoogleGenerativeAI`

修改默认模型 / 新增 provider：编辑 `common/config.py` 中 `MODEL_CONFIGS` 字典。

### 2. 毕业项目的统一架构（项目 07/08/09）

三个毕业项目**结构高度一致**，都采用"按职责分包 + LangGraph 状态机"模式：

```
project_xx/
├── config.py          # 项目级配置（路径、阈值、重试次数等，env 可覆盖）
├── main.py            # CLI 入口
├── graph/             # LangGraph 状态机（state.py 定义状态，workflow.py 组装图）
├── <业务模块>/         # ingestion/retrieval/citation/memory/... 按职责分包
├── governance/        # 审计/合规/治理
├── tests/             # pytest 测试
└── runtime_data/ 或 data/   # 运行时产物（已 gitignore）
```

**模式要点**：
- `config.py` 中所有可调参数都通过 `os.getenv("PROJECT_XX_XXX", default)` 注入，可被环境变量覆盖
- 每个项目都定义了 LangGraph 6 节点工作流，节点职责清晰：plan → execute → validate → report（或类似变体）
- 质量闭环：LLM 自评 + 最多 N 次重试（N 在 config.py 中配）
- 审计/治理逻辑独立放在 `governance/`

### 3. 学习阶段项目的"裸跑"特性

阶段 1-6（`project_01` ~ `project_06`）是**单文件可执行的教学脚本**，每个 `.py` 独立、互相不强依赖。每文件顶部都有大量中文注释解释原理。修改 prompt / 切换模型 / 调参 → 直接观察输出变化是核心学习方式。

### 4. 工具与沙箱（`project_03_tool_agent/tools/`）

教学项目内置了一组安全工具实现可参考：
- `calculator.py` — AST 抽象语法树安全求值（**不直接用 `eval`**）
- `code_executor.py` — Python 沙箱执行
- `web_search.py` / `file_ops.py` / `system_info.py`

毕业项目 08 的 `tools/` 实现了完整的 `ToolRegistry`（注册/分组/校验/权限/降级替代），是面试高频考点。

## 重要约定

### 中文优先
- 所有代码注释、文档、commit message 用中文
- 与用户对话也用中文回复

### 关键约束
- **`.env` 永不可提交**（已在 `.gitignore`），任何 API Key 走 `os.getenv` 读取
- **不要硬编码 API Key** 到代码里
- 教学项目可能含 `eval`/`exec` 演示代码（如 `code_executor.py`），**毕业项目 09 已通过 `BANNED_CODE_PATTERNS` 列表禁止**这些不安全模式生成

### PYTHONPATH 问题
所有项目用 `from common.xxx import ...` 导入公共模块，**必须在仓库根目录执行 `python` 命令**。如果 IDE/Pylance 报错找不到 `common`，设置工作目录为仓库根。

## 文档索引

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目介绍 + 快速开始 |
| [LEARNING_PLAN.md](LEARNING_PLAN.md) | 17 天完整学习计划（6 阶段 + 3 毕业项目） |
| [LEARNING_PROGRESS.md](LEARNING_PROGRESS.md) | 个人学习进度记录 |
| [LEARNING_SKILLS.md](LEARNING_SKILLS.md) | 学习掌握的技能清单 |
| `project_xx/DAYxx.md` | 每课学习笔记（原理讲解 + 代码导读） |
| `project_xx/PROJECT_PLAN.md` | 毕业项目架构设计文档 |
| `.env.example` | 环境变量模板（`cp .env.example .env` 后填 Key） |

## 添加新阶段/新模型

- **新增 LLM provider**：在 `common/config.py` 的 `MODEL_CONFIGS` 中加一个条目，然后在 `.env` 添加对应的 `XXX_API_KEY` 环境变量。
- **新增教学项目**：参照 `project_01_basics` 单文件结构；如果内容超过 3-4 个文件，建议参考毕业项目 07/08/09 的分包模式。
- **新增毕业项目**：参考 `project_07_enterprise_rag/PROJECT_PLAN.md` 写架构设计，遵循 `config.py + main.py + graph/ + <modules>/ + governance/ + tests/` 结构。
