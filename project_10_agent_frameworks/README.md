# Project 10：主流 Agent 框架选型课

本项目用于横向比较当前主流 Agent 框架，帮助学习者理解不同框架的核心优势、适用场景和工程边界。

它不是框架排行榜，也不追求把每个框架都安装一遍。课程重点是建立选型方法：先看业务问题需要什么能力，再判断哪类框架更合适。

框架信息截止日期：2026-06-10。Agent 框架迭代很快，学习和生产选型时必须再查官方最新文档。

## 课程定位

前面项目已经覆盖了三类真实 Agent 形态：

- `project_07_enterprise_rag`：企业级 RAG。
- `project_08_workflow_agent`：自动化业务流程 Agent。
- `project_09_dev_team`：多 Agent 协同开发助手。

`project_10_agent_frameworks` 用这些项目作为参照，回答一个更实际的问题：如果进入生产系统，应该优先评估哪些 Agent 框架，为什么。

## 课程结构

| 文件 | 内容 |
|------|------|
| `PROJECT_PLAN.md` | 项目计划、范围和验收标准 |
| `DAY24.md` | 主流 Agent 框架横向比较 |
| `DAY25.md` | 选型方法论、决策树和课程项目映射 |
| `01_framework_comparison.py` | 终端运行的框架对比和选型演示 |
| `examples/framework_selection_matrix.py` | 按能力标签推荐框架 |
| `examples/agent_capability_mapper.py` | 把 project_07/08/09 映射到框架 |
| `tests/test_framework_selection.py` | 选型规则测试 |

## 覆盖框架

核心必讲：

- LangGraph
- OpenAI Agents SDK
- Google ADK
- PydanticAI
- AutoGen
- CrewAI
- LlamaIndex Agents
- Semantic Kernel

研究和新兴方向：

- AgentScope
- CAMEL
- Haystack
- Agno
- Mastra
- Strands Agents

## 运行测试

必须在仓库根目录执行：

```bash
conda run -n agent_env python -m unittest discover project_10_agent_frameworks/tests -v
```

## 运行演示

```bash
python project_10_agent_frameworks/01_framework_comparison.py
python project_10_agent_frameworks/01_framework_comparison.py --scenario rag
python project_10_agent_frameworks/01_framework_comparison.py --interactive
```

## 学习重点

- 不把“框架热度”当成唯一标准。
- 不把 MCP、观测平台、评估平台误认为 Agent 框架。
- 不认为换框架就能替代权限、审计、checkpoint、sandbox、质量评估和压测治理。
- 能把框架能力映射回真实项目需求。
- 能理解框架组合的集成成本，例如状态序列化、事件循环、依赖版本和调试链路。
