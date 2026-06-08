# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## 项目概述

AI Agent 渐进式教学代码库，9 个子项目按学习路径编号（project_01 ~ project_09），从裸 HTTP API 调用到 LangGraph 多 Agent 协作系统。所有项目共享 `common/` 公共模块和根目录 `requirements.txt`。

- **阶段 1-6**（project_01 ~ project_06）：单文件可执行教学脚本，每文件独立、互相不强依赖
- **毕业项目 07/08/09**：按职责分包 + LangGraph 状态机的完整工程

## 常用命令

```bash
# 环境准备（推荐 Python 3.10+）
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 填入至少一个 API Key

# 运行任意脚本（必须在仓库根目录执行，确保 common/ 可被导入）
python project_01_basics/01_raw_api_call.py
python project_07_enterprise_rag/main.py

# Lint
flake8 project_xx/

# 毕业项目的 pytest 测试
cd project_07_enterprise_rag && pytest tests/ -v
cd project_08_workflow_agent && pytest tests/ -v
cd project_09_dev_team && pytest tests/ -v
```

## 核心架构

### 模型工厂（common/）

所有 LLM 调用统一走 `create_model(provider, **kwargs)`，切换 provider 字符串即可换模型：

```python
from common.model_factory import create_model
model = create_model("deepseek", temperature=0.7)
```

- `common/config.py`：`MODEL_CONFIGS` 字典维护所有 provider 的 base_url / api_key / default_model，API Key 从 `.env` 环境变量读取
- `common/model_factory.py`：工厂函数，国产模型走 `ChatOpenAI(base_url=...)` 兼容接口，Gemini 走 `ChatGoogleGenerativeAI`
- 新增 provider：在 `MODEL_CONFIGS` 加条目 + `.env` 加对应 `XXX_API_KEY`

### 毕业项目统一架构（project_07 / 08 / 09）

三个毕业项目结构高度一致：

```
project_xx/
├── config.py          # 项目级配置，参数通过 os.getenv("PROJECT_XX_XXX", default) 注入
├── main.py            # CLI 入口
├── graph/             # LangGraph 状态机（state.py + workflow.py）
├── <业务模块>/         # 按职责分包（ingestion/retrieval/planner/agents/...）
├── governance/        # 审计/合规/治理
├── tests/             # pytest 测试
└── runtime_data/ 或 data/   # 运行时产物（已 gitignore）
```

模式要点：
- LangGraph 状态机编排节点工作流，节点职责清晰
- 质量闭环：LLM 自评 + 最多 N 次重试（N 在 config.py 中配置）
- 审计/治理逻辑独立放在 `governance/`

### PYTHONPATH 关键约束

所有项目用 `from common.xxx import ...` 导入公共模块，**必须在仓库根目录执行 python 命令**。

## 重要约定

- **中文优先**：代码注释、文档、commit message 用中文
- **`.env` 永不可提交**（已在 .gitignore），API Key 一律走 `os.getenv` 读取，不硬编码
- **Flake8 配置**（.flake8）：忽略 E402/W503，行长上限 100，排除 .venv/__pycache__/.git 等
- 教学项目（project_03）可能含 `eval`/`exec` 演示代码；毕业项目 09 通过 `BANNED_CODE_PATTERNS` 列表禁止不安全模式
- 工具实现参考：`project_03_tool_agent/tools/calculator.py` 使用 AST 安全求值（不直接 eval）；`project_08_workflow_agent/tools/` 实现了完整的 `ToolRegistry`（注册/分组/校验/权限/降级替代）
