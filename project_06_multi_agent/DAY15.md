# Day 15 课程：LangGraph 多 Agent 实战 — 主管模式与协作模式 🏗️

在 Day 14 中，我们学习了多 Agent 系统的三大架构模式（主从、协作、辩论）和通信机制。今天我们用 LangGraph 来**实际构建**这些多 Agent 系统。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：主管模式 (Supervisor Pattern)](#第一部分主管模式-supervisor-pattern)
3. [第二部分：协作模式 (Collaborative Pattern)](#第二部分协作模式-collaborative-pattern)
4. [核心原理深度解析](#核心原理深度解析)
5. [课后练习](#课后练习)

---

## 学习目标
- 用 LangGraph 构建完整的 Supervisor 多 Agent 系统。
- 用 LangGraph 构建完整的协作流水线多 Agent 系统。
- 理解 Supervisor Agent 的路由决策逻辑。
- 掌握多 Agent 场景下的状态管理和错误处理。

---

## 第一部分：主管模式 (Supervisor Pattern)

### 1. 架构概览

主管模式中有两类 Agent：
- **Supervisor（主管）**：不直接干活，负责分析用户请求、决定分配给哪个 Worker、汇总最终结果。
- **Workers（工人）**：每个 Worker 专精一个领域，只负责自己擅长的任务。

### 2. LangGraph 实现

```python
from langgraph.graph import StateGraph, END
from typing import Literal

# ---- 定义 Supervisor 的路由逻辑 ----
def supervisor_node(state: MultiAgentState):
    """主管节点：分析任务，决定分配给谁。"""

    supervisor_prompt = """你是一个团队主管。根据用户请求，决定应该交给哪个团队成员处理。

    可用的团队成员：
    - researcher: 负责信息搜索和资料收集
    - coder: 负责编写和调试代码
    - writer: 负责撰写文档和报告

    如果任务已经完成，回答 "FINISH"。

    用户请求: {request}
    已完成的工作: {completed_work}

    请回答应该交给谁 (researcher/coder/writer/FINISH):
    """
    # 调用 LLM 进行路由决策
    decision = supervisor_chain.invoke(state)
    return {"next_agent": decision}

# ---- 定义路由函数 ----
def route_to_agent(state: MultiAgentState) -> str:
    """根据 Supervisor 的决策路由到对应节点。"""
    return state["next_agent"]

# ---- 构建图 ----
graph = StateGraph(MultiAgentState)

# 添加所有节点
graph.add_node("supervisor", supervisor_node)
graph.add_node("researcher", researcher_node)
graph.add_node("coder", coder_node)
graph.add_node("writer", writer_node)

# 设置入口
graph.set_entry_point("supervisor")

# Supervisor 根据决策路由到不同 Worker
graph.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {
        "researcher": "researcher",
        "coder": "coder",
        "writer": "writer",
        "FINISH": END
    }
)

# 所有 Worker 完成后回到 Supervisor
graph.add_edge("researcher", "supervisor")
graph.add_edge("coder", "supervisor")
graph.add_edge("writer", "supervisor")

# 编译
app = graph.compile()
```

### 3. 执行示例

```
用户: "帮我调研 FastAPI 和 Flask 的区别，然后写一个 FastAPI 的示例代码"

[Supervisor] 任务需要先调研再编码。分配给 researcher。
[Researcher] 搜索 FastAPI vs Flask 的对比资料...
             → FastAPI 异步、类型提示、自动文档；Flask 轻量、灵活...
[Supervisor] 调研完成。现在需要写代码。分配给 coder。
[Coder]      基于调研结果编写 FastAPI 示例代码...
             → 生成了一个带路由、Pydantic 模型的 FastAPI 应用
[Supervisor] 代码完成。任务全部完成。→ FINISH

最终输出: 调研报告 + 示例代码
```

### 4. Supervisor 的路由策略

| 策略 | 实现 | 优缺点 |
|------|------|--------|
| LLM 路由 | 让大模型分析任务并决定分配 | 灵活但不稳定 |
| 结构化输出路由 | 强制 LLM 输出 JSON `{"next": "researcher"}` | 可靠，推荐 |
| 规则路由 | 关键词匹配（如含"搜索"→ researcher） | 最稳定但不灵活 |

> 📖 **代码实战**：查看并运行 [03_supervisor_pattern.py](file:///Users/huangyang/code/agent/project_06_multi_agent/03_supervisor_pattern.py)

---

## 第二部分：协作模式 (Collaborative Pattern)

### 1. 流水线架构

协作模式中，Agent 按固定顺序依次处理，每个 Agent 的输出自动成为下一个 Agent 的输入：

```
         ┌────────────┐     ┌────────────┐     ┌────────────┐
用户 ───►│  Agent A   │────►│  Agent B   │────►│  Agent C   │───► 输出
  输入    │ (阶段 1)   │     │ (阶段 2)   │     │ (阶段 3)   │
         └────────────┘     └────────────┘     └────────────┘
```

### 2. LangGraph 实现

```python
# 定义线性流水线
graph = StateGraph(PipelineState)

graph.add_node("researcher", researcher_node)  # 阶段 1：调研
graph.add_node("analyst", analyst_node)        # 阶段 2：分析
graph.add_node("writer", writer_node)          # 阶段 3：撰写

# 线性连接
graph.set_entry_point("researcher")
graph.add_edge("researcher", "analyst")
graph.add_edge("analyst", "writer")
graph.add_edge("writer", END)

app = graph.compile()
```

### 3. 协作模式的进阶：带反馈环

有时流水线中的后续 Agent 发现前面阶段的产出不符合要求，需要退回重做：

```
  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │ 调研Agent │────►│ 审核Agent │────►│ 写作Agent │
  └──────────┘     └──┬───────┘     └──────────┘
        ▲             │
        │         不合格
        └─────────────┘
              (退回重新调研)
```

```python
def review_router(state):
    """审核路由：通过或退回。"""
    if state["review_result"] == "PASS":
        return "writer"
    else:
        return "researcher"  # 退回重做

graph.add_conditional_edges(
    "analyst",
    review_router,
    {"writer": "writer", "researcher": "researcher"}
)
```

### 4. 执行示例

```
用户: "帮我写一份关于 AI Agent 发展趋势的分析报告"

[Researcher] 搜索 AI Agent 最新发展动态...
             → 收集到 10 条相关资料

[Analyst]    分析收集到的资料，提炼 5 个关键趋势...
             → 1. 多模态 Agent  2. 多 Agent 协作  3. ...

[Writer]     基于分析结果撰写完整报告...
             → 《AI Agent 发展趋势分析报告》
                一、引言 ...
                二、五大关键趋势 ...
                三、未来展望 ...
```

> 📖 **代码实战**：查看并运行 [04_collaborative_agents.py](file:///Users/huangyang/code/agent/project_06_multi_agent/04_collaborative_agents.py)

---

## 核心原理深度解析

### 主管模式 vs. 协作模式的选择

| 维度 | 主管模式 | 协作模式 |
|------|---------|---------|
| 任务类型 | 可分解为独立子任务 | 有阶段性流程 |
| 执行顺序 | 动态（Supervisor 决定） | 固定（编码时确定） |
| 灵活性 | ⭐⭐⭐ 高 | ⭐⭐ 中 |
| 可预测性 | ⭐⭐ 中 | ⭐⭐⭐ 高 |
| Supervisor 开销 | 有（额外的 LLM 调用） | 无 |
| 适用场景 | 客服分流、任务调度 | 内容生产、数据处理 |

### 多 Agent 系统的常见陷阱

| 陷阱 | 描述 | 解决方案 |
|------|------|---------|
| 无限循环 | Supervisor 反复将任务分配给同一个 Worker | 设置 `max_iterations` 安全阀 |
| 信息丢失 | Worker 的关键输出没有传递到 State 中 | 设计完善的 State Schema |
| 角色混淆 | Agent 的 System Prompt 不够精确 | 用精准的 Prompt 严格限定职责边界 |
| 上下文膨胀 | 多 Agent 通信导致消息列表迅速膨胀 | 每个 Agent 只传递摘要 |

---

## 课后练习

1. **扩展 Supervisor**：为主管模式添加第四个 Worker Agent——"Reviewer"（审核员），在 Writer 完成后由 Reviewer 检查质量，不合格则退回 Writer 修改。

2. **动态团队**：修改 Supervisor，让它不仅决定分配给哪个 Worker，还能决定**同时**分配给多个 Worker 并行执行。

3. **协作流水线日志**：为协作模式添加详细的执行日志，记录每个 Agent 的输入、输出、耗时，方便分析瓶颈。

4. **Flake8 自检**：确保代码通过 `flake8 project_06_multi_agent/` 的检查。
