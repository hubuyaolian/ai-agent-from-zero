# Day 14 课程：多 Agent 基础 — 从"独狼"到"团队" 👥

前 13 天，我们构建的都是**单体 Agent**——一个大模型实例包揽所有任务。但现实中的复杂任务往往超出单个 Agent 的能力范围。就像一家公司不可能只靠一个人运转，复杂的 AI 系统也需要**多个专业化的 Agent 协同工作**。

今天我们将进入 Agent 开发的最后阶段：**多 Agent 系统 (Multi-Agent System)**。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：多 Agent 架构模式](#第一部分多-agent-架构模式)
3. [第二部分：Agent 之间的消息传递](#第二部分agent-之间的消息传递)
4. [核心原理深度解析](#核心原理深度解析)
5. [课后练习](#课后练习)

---

## 学习目标
- 理解多 Agent 系统的三大架构模式：主从模式、协作模式、辩论模式。
- 掌握 Agent 之间的消息传递与状态共享机制。
- 理解"为什么需要多个 Agent"——专业化分工的优势。

---

## 第一部分：多 Agent 架构模式

### 1. 为什么需要多 Agent？

| 单 Agent 的局限 | 多 Agent 的优势 |
|----------------|----------------|
| System Prompt 过长（又要当程序员、又要当写手、又要当分析师） | 每个 Agent 有精准的 Prompt，专精一个领域 |
| 工具太多，模型选择困难 | 每个 Agent 只配备自己领域的工具 |
| 上下文窗口紧张 | 每个 Agent 独立管理自己的上下文 |
| 单点故障 | 一个 Agent 失败不影响其他 Agent |

### 2. 三大架构模式

#### 模式一：主从模式 (Supervisor Pattern) 👨‍💼

一个"主管 (Supervisor)" Agent 负责接收用户请求、分析任务、分配给专业的"工人 (Worker)" Agent 执行。

```
                     用户
                      │
                      ▼
              ┌──────────────┐
              │  Supervisor  │  (负责任务分配和结果汇总)
              │  主管 Agent   │
              └──┬─────┬──┬──┘
                 │     │  │
          ┌──────┘     │  └──────┐
          ▼            ▼         ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ 搜索专家  │ │ 分析专家  │ │ 写作专家  │
    │ Agent    │ │ Agent    │ │ Agent    │
    └──────────┘ └──────────┘ └──────────┘
```

**适用场景**：任务可以明确分类，需要中央协调。

#### 模式二：协作模式 (Collaborative / Pipeline Pattern) 🤝

多个 Agent 按照流水线接力完成任务，前一个 Agent 的输出作为下一个 Agent 的输入。

```
    用户输入
       │
       ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ 调研 Agent │──►│ 分析 Agent │──►│ 写作 Agent │──► 最终输出
  │ (搜集信息) │    │ (提炼要点) │    │ (生成报告) │
  └──────────┘    └──────────┘    └──────────┘
```

**适用场景**：任务有明确的阶段性流程，每个阶段需要不同的专业能力。

#### 模式三：辩论模式 (Debate Pattern) 🗣️

多个 Agent 对同一个问题给出各自的观点，通过多轮辩论或投票达成共识，提高回答质量。

```
  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ Agent A  │   │ Agent B  │   │ Agent C  │
  │ (乐观派) │   │ (悲观派) │   │ (中立派) │
  └────┬─────┘   └────┬─────┘   └────┬─────┘
       │              │              │
       └──────┬───────┘              │
              │                      │
              ▼                      │
       ┌────────────┐               │
       │  裁判 Agent │◄──────────────┘
       │ (综合判断)  │
       └────────────┘
```

**适用场景**：需要多角度分析、降低偏见、提高决策质量。

> 📖 **代码实战**：查看并运行 [01_multi_agent_concepts.py](file:///Users/huangyang/code/agent/project_06_multi_agent/01_multi_agent_concepts.py)

---

## 第二部分：Agent 之间的消息传递

### 1. 共享状态 vs. 消息传递

多 Agent 之间的通信有两种基本方式：

| 方式 | 实现 | 优点 | 缺点 |
|------|------|------|------|
| 共享状态 | 所有 Agent 读写同一个 State 对象 | 简单直接 | 容易产生状态冲突 |
| 消息传递 | Agent 之间通过消息队列通信 | 解耦、可扩展 | 实现较复杂 |

在 LangGraph 中，默认使用**共享状态**模式——所有节点（Agent）共享同一个 `State` 对象。

### 2. 多 Agent 的 State 设计

```python
from typing import Annotated, List
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class MultiAgentState(TypedDict):
    """多 Agent 系统的共享状态。"""

    # 完整的对话消息历史
    messages: Annotated[list, add_messages]

    # 当前应该由哪个 Agent 处理
    next_agent: str

    # 各 Agent 的中间结果
    research_result: str    # 调研 Agent 的输出
    analysis_result: str    # 分析 Agent 的输出
    final_report: str       # 写作 Agent 的输出
```

### 3. Agent 之间的信息流转

```python
def research_agent(state: MultiAgentState):
    """调研 Agent：负责搜集信息。"""
    # 使用搜索工具搜集资料
    result = research_chain.invoke(state["messages"])
    return {
        "research_result": result,
        "messages": [AIMessage(content=f"[调研完成] {result}")]
    }

def analysis_agent(state: MultiAgentState):
    """分析 Agent：基于调研结果进行分析。"""
    # 读取调研 Agent 的结果
    research = state["research_result"]
    result = analysis_chain.invoke(research)
    return {
        "analysis_result": result,
        "messages": [AIMessage(content=f"[分析完成] {result}")]
    }
```

> 📖 **代码实战**：查看并运行 [02_agent_communication.py](file:///Users/huangyang/code/agent/project_06_multi_agent/02_agent_communication.py)

---

## 核心原理深度解析

### 多 Agent 的本质

多 Agent 系统听起来很复杂，但其本质非常简单：

> **多 Agent = 多个不同 System Prompt 的 LLM 调用 + 编排逻辑**

每个 "Agent" 其实就是：
1. 一段特定的 System Prompt（定义它的角色和专长）
2. 一组特定的工具（只给它需要的工具）
3. 可能有独立的上下文管理

"多 Agent 协作"实质上就是**用代码编排多次 LLM 调用的顺序和数据流**。

### 何时使用多 Agent vs. 单 Agent

| 场景 | 推荐方案 |
|------|---------|
| 简单问答、单一工具 | 单 Agent |
| 需要 2-3 种不同专业能力 | 单 Agent + 多工具 |
| 需要 4+ 种专业能力 | 多 Agent |
| 任务有明确的阶段划分 | 多 Agent（协作模式） |
| 需要多角度分析 | 多 Agent（辩论模式） |
| 团队级别的复杂工作流 | 多 Agent（主从模式） |

---

## 课后练习

1. **角色设计**：为一个"代码审查"场景设计 3 个 Agent：开发者（编写代码）、审查员（检查质量）、测试员（编写测试用例）。为每个 Agent 设计精准的 System Prompt。

2. **通信实验**：实现两个 Agent 之间的简单对话——Agent A 提出观点，Agent B 进行反驳，来回 3 轮后由你作为人类裁判评判谁更有道理。

3. **Flake8 自检**：确保代码通过 `flake8 project_06_multi_agent/` 的检查。
