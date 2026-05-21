# Day 16 课程：综合项目 — AI 调研团队（上）🏆

经过 Day 14 和 Day 15 的学习，我们已经掌握了多 Agent 系统的两大核心模式（主管模式 + 协作模式）以及 LangGraph 的状态管理。现在，是时候把**所有学过的技术融合到一个真实项目**中了。

在接下来的两天（Day 16-17），我们将构建一个完整的 **AI 调研团队** —— 输入一个主题，自动完成调研、分析、报告撰写的全流程。今天的重点是**项目架构设计和各 Agent 模块的实现**。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：项目架构设计](#第一部分项目架构设计)
3. [第二部分：调研 Agent 实现](#第二部分调研-agent-实现)
4. [第三部分：分析 Agent 实现](#第三部分分析-agent-实现)
5. [第四部分：写作 Agent 实现](#第四部分写作-agent-实现)
6. [第五部分：LangGraph 工作流编排](#第五部分langgraph-工作流编排)
7. [核心原理深度解析](#核心原理深度解析)
8. [课后练习](#课后练习)

---

## 学习目标
- 掌握多 Agent 综合项目的**架构设计方法论**：如何拆分 Agent、设计状态、规划流程。
- 实现三个专业化 Agent：调研 Agent、分析 Agent、写作 Agent。
- 使用 LangGraph 编排完整的**协作工作流**（调研 → 分析 → 写作）。
- 理解 Agent 模块化设计的**工程最佳实践**。

---

## 第一部分：项目架构设计

### 1. 项目目标

构建一个 **AI 调研团队**，实现以下功能：

```
用户输入主题（如 "AI Agent 技术的发展现状与未来趋势"）
       │
       ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │🔍 调研Agent│──►│📊 分析Agent│──►│✍️ 写作Agent│──► 完整研究报告
  │ (搜集信息) │    │ (提炼洞察) │    │ (生成报告) │
  └──────────┘    └──────────┘    └──────────┘
```

**最终产出**：一篇结构完整、内容充实的研究报告，包含摘要、现状分析、深度洞察、挑战与机遇、结论与展望。

### 2. 项目目录结构

```
project_06_multi_agent/
├── 05_research_team/           # 综合项目目录
│   ├── agents/                 # Agent 模块（每个 Agent 独立一个文件）
│   │   ├── __init__.py         # 模块初始化
│   │   ├── researcher.py       # 调研 Agent：搜索收集信息
│   │   ├── analyst.py          # 分析 Agent：深度分析提炼
│   │   └── writer.py           # 写作 Agent：撰写最终报告
│   ├── workflow.py             # LangGraph 工作流定义
│   └── main.py                 # 项目入口
```

### 3. 为什么选择协作模式？

在 Day 15 中我们学过两种模式的对比，对于"调研 → 分析 → 写作"这个场景：

| 考量因素 | 分析 | 结论 |
|---------|------|------|
| 流程是否固定？ | 调研 → 分析 → 写作，顺序不变 | ✅ 适合协作模式 |
| 是否需要动态路由？ | 不需要 Supervisor 判断分配 | ✅ 协作模式更简单 |
| 是否需要重复执行？ | 基础版不需要退回重做 | ✅ 线性流水线即可 |
| Token 消耗考量 | 无需 Supervisor 的额外调用 | ✅ 协作模式更省 |

> **设计决策**：本项目使用**协作模式（Sequential Collaboration）**，三个 Agent 按固定顺序接力工作。

### 4. 共享状态设计

这是整个项目的**数据骨架**，决定了 Agent 之间如何传递信息：

```python
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

class ResearchTeamState(TypedDict):
    """AI 调研团队的共享状态。"""

    # 消息历史（自动累积，不会覆盖）
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # 用户输入
    topic: str              # 研究主题

    # 各 Agent 的输出（逐步填充）
    research_data: str      # 调研 Agent → 原始调研数据
    analysis_result: str    # 分析 Agent → 分析结果
    final_report: str       # 写作 Agent → 最终报告

    # 流程控制
    status: str             # 当前执行状态
```

**状态流转过程**：

```
初始状态                    调研后                     分析后                     写作后
─────────────────────────────────────────────────────────────────────────────────────
topic: "AI Agent"          topic: "AI Agent"          topic: "AI Agent"          topic: "AI Agent"
research_data: ""     →    research_data: "1.xx 2.xx" research_data: "1.xx 2.xx" research_data: "1.xx 2.xx"
analysis_result: ""        analysis_result: ""    →   analysis_result: "趋势..."  analysis_result: "趋势..."
final_report: ""           final_report: ""           final_report: ""       →   final_report: "# 报告..."
status: "started"          status: "researched"       status: "analyzed"         status: "completed"
```

### 5. 模块化设计原则

| 原则 | 说明 | 本项目的体现 |
|------|------|-------------|
| **单一职责** | 每个 Agent 只做一件事 | researcher 只搜集，analyst 只分析，writer 只写作 |
| **松耦合** | Agent 之间通过 State 通信，不直接调用彼此 | 每个 Agent 只读写 State，互不依赖 |
| **可独立测试** | 每个 Agent 可以单独运行测试 | 每个文件都有 `if __name__ == "__main__"` 测试代码 |
| **可复用** | Agent 可以在其他项目中使用 | `run_research()` 等函数可以独立调用 |

---

## 第二部分：调研 Agent 实现

### 1. 角色定位

调研 Agent 是团队中**第一个上场的成员**，它的职责是：
- 针对用户给定的研究主题，进行全面的信息收集
- 输出结构化的调研结果（关键发现 + 重要数据 + 典型案例）
- **只收集事实，不做分析**（分析是下一个 Agent 的事）

```
  用户主题                调研 Agent                       输出
  ─────────              ──────────                      ──────
  "AI Agent     →    🔍 收集关键信息              →   📋 6-8 个关键发现
   的发展趋势"        📊 搜集相关数据                   📈 重要数据指标
                      📌 寻找典型案例                   🔍 典型案例
```

### 2. 核心设计：System Prompt

调研 Agent 的 System Prompt 是它的"岗位说明书"，决定了它的行为模式：

```python
RESEARCHER_SYSTEM_PROMPT = """你是一个专业的信息调研专家（Researcher Agent）。

## 你的职责
你负责针对给定的研究主题，进行全面、深入的信息收集和调研。

## 工作要求
1. **全面性**：从多个角度收集信息，包括现状、趋势、案例、数据等
2. **准确性**：确保信息准确可靠，标注信息来源（如果有）
3. **结构化**：将收集到的信息按照清晰的结构组织
4. **客观性**：客观呈现信息，不添加个人分析（分析是分析 Agent 的工作）

## 输出格式
请按以下格式输出调研结果：

### 📋 调研主题
[主题名称]

### 📊 关键发现
1. [发现1]
2. [发现2]
...（至少列出 6-8 个关键发现）

### 📈 重要数据
- [相关统计数据或指标]

### 🔍 典型案例
- [案例1简述]
- [案例2简述]

### 📌 补充信息
- [其他值得关注的信息]
"""
```

**Prompt 设计要点**：
- 明确角色边界："只收集信息，不做分析"
- 指定输出格式：结构化的 Markdown 格式，方便下游 Agent 解析
- 设定质量标准：全面性、准确性、客观性

### 3. 代码实现

```python
"""调研 Agent - 负责信息搜索和收集。"""

import os  # 导入操作系统相关功能的模块
import sys  # 导入系统特定参数和函数的模块
from dotenv import load_dotenv  # 导入加载环境变量的工具函数
from langchain_core.language_models.chat_models import BaseChatModel  # 导入聊天模型基类
from langchain_core.messages import SystemMessage, HumanMessage  # 导入系统和人类消息类
from common.model_factory import create_model  # 导入项目统一的模型工厂创建函数

# 加载环境变量配置文件
load_dotenv()

def create_researcher_agent() -> BaseChatModel:
    """
    创建调研 Agent 的模型实例。

    本函数利用项目统一的公共模型工厂 create_model 来创建通义千问模型实例。

    输入参数:
        无

    输出返回值:
        BaseChatModel: 实例化后的聊天大模型对象，类型为 LangChain 模型基类
    """
    # 使用公共模型工厂创建模型，配置 provider 为 qwen，温度为 0.3 以保证事实准确性
    model_instance = create_model(
        provider="qwen",  # 指定模型提供商为通义千问
        model_name="qwen-plus",  # 指定具体的模型名称为 qwen-plus
        temperature=0.3,  # 设置较低的温度参数以减少“幻觉”并保证调研事实的一致性
    )
    # 返回创建好的大模型实例
    return model_instance

def run_research(topic: str) -> str:
    """
    执行调研任务。

    功能：传入调研主题，调用调研 Agent 执行信息收集，并返回 Markdown 格式的结果。

    输入参数:
        topic (str): 需要调研的原始主题

    输出返回值:
        str: 调研 Agent 收集并输出的结构化 Markdown 调研结果
    """
    # 实例化调研 Agent 的大模型对象
    model = create_researcher_agent()
    # 构造包含系统提示词和用户调研指令的消息列表
    messages = [
        # 传递包含岗位职责和格式约束的系统提示词
        SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
        # 传递用户指定的调研主题
        HumanMessage(content=f"请对以下主题进行全面调研：\n\n{topic}"),
    ]
    # 调用大模型的 invoke 方法执行推理并获取回复
    response = model.invoke(messages)
    # 返回大模型输出的文本内容
    return response.content
```

**关键设计决策**：

| 参数 | 值 | 理由 |
|------|----|------|
| `temperature` | 0.3 | 调研需要事实性和一致性，低温度减少"编造"风险 |
| 模型 | `qwen-plus` | 性价比高，知识面广，适合信息收集任务 |
| 输入 | 只有主题 | 调研 Agent 是流水线的第一环，只需要用户原始主题 |

> 📖 **代码实战**：查看 [researcher.py](file:///Users/huangyang/code/agent/project_06_multi_agent/05_research_team/agents/researcher.py)

---

## 第三部分：分析 Agent 实现

### 1. 角色定位

分析 Agent 是团队中的**第二个成员**，它的职责是：
- 接收调研 Agent 的原始数据
- 进行深度分析：识别趋势、提炼洞察、评估优劣
- 输出有深度的分析结果（而非简单的信息罗列）

```
  调研数据                分析 Agent                       输出
  ─────────              ──────────                      ──────
  "1. xxx         →    🎯 识别核心趋势              →   趋势分析
   2. xxx               💡 提炼关键洞察                   洞察列表
   3. xxx"              ⚖️ 评估优势与挑战                 SWOT 分析
                        🔮 给出前景判断                   前景预判
```

### 2. 核心设计：System Prompt

```python
ANALYST_SYSTEM_PROMPT = """你是一个资深的数据分析专家（Analyst Agent）。

## 你的职责
你负责对调研 Agent 收集的原始信息进行深度分析，提炼有价值的洞察。

## 工作要求
1. **深度分析**：不要停留在表面，要挖掘信息背后的规律和原因
2. **多维视角**：从技术、市场、用户、竞争等多个维度分析
3. **逻辑严谨**：分析要有因果链，结论要有依据支撑
4. **价值导向**：关注对读者最有价值的洞察

## 输出格式
### 🎯 核心趋势分析
[识别 3-4 个核心趋势，每个趋势给出分析]

### 💡 关键洞察
1. [洞察1：发现 + 意义]
2. [洞察2：发现 + 意义]
3. [洞察3：发现 + 意义]

### ⚖️ 优势与挑战
**优势/机遇：**
- [优势1]
- [优势2]

**挑战/风险：**
- [挑战1]
- [挑战2]

### 🔮 前景判断
[基于以上分析，给出你对该领域前景的判断]
"""
```

**与调研 Agent 的关键差异**：
- 调研 Agent 强调"**客观收集**"，分析 Agent 强调"**深度分析**"
- 调研 Agent 输出"事实"，分析 Agent 输出"洞察"
- 分析 Agent 的温度参数稍高（0.5），允许一定的创造性思考

### 3. 代码实现

```python
"""分析 Agent - 负责数据分析和洞察提炼。"""

def create_analyst_agent() -> BaseChatModel:
    """
    创建分析 Agent 的模型实例。

    本函数利用项目统一的公共模型工厂 create_model 来创建通义千问模型实例。

    输入参数:
        无

    输出返回值:
        BaseChatModel: 实例化后的聊天大模型对象，类型为 LangChain 模型基类
    """
    # 使用公共模型工厂创建模型，配置 provider 为 qwen，温度为 0.5 以平衡逻辑严谨性与创造性思考
    model_instance = create_model(
        provider="qwen",  # 指定模型提供商为通义千问
        model_name="qwen-plus",  # 指定具体的模型名称为 qwen-plus
        temperature=0.5,  # 设置中等温度以平衡严谨性和创造性
    )
    # 返回创建好的大模型实例
    return model_instance

def run_analysis(topic: str, research_data: str) -> str:
    """
    执行分析任务。

    功能：传入研究主题和原始调研数据，调用分析 Agent 进行深度提炼，返回 Markdown 格式的结果。

    输入参数:
        topic (str): 需要调研与分析的主题
        research_data (str): 调研 Agent 提供的原始调研数据文本

    输出返回值:
        str: 分析 Agent 输出的深度分析与洞察报告结果
    """
    # 实例化分析 Agent 的大模型对象
    model = create_analyst_agent()
    # 构造包含系统分析提示词和用户输入材料的消息列表
    messages = [
        # 传递包含深度分析指南和格式要求的系统提示词
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        # 传递包含研究主题和调研数据的用户输入消息
        HumanMessage(
            content=f"请对以下调研资料进行深度分析：\n\n"  # 拼接请求前缀
            f"**研究主题**：{topic}\n\n"  # 注入主题
            f"**调研数据**：\n{research_data}"  # 注入上游数据
        ),
    ]
    # 调用大模型的 invoke 方法执行分析计算并获取回复
    response = model.invoke(messages)
    # 返回分析大模型响应中的文本结果
    return response.content
```

**注意函数签名的差异**：
- `run_research(topic)` → 只需要主题
- `run_analysis(topic, research_data)` → 需要主题 + 上游调研数据

这体现了**流水线模式的数据依赖关系**。

> 📖 **代码实战**：查看 [analyst.py](file:///Users/huangyang/code/agent/project_06_multi_agent/05_research_team/agents/analyst.py)

---

## 第四部分：写作 Agent 实现

### 1. 角色定位

写作 Agent 是团队中的**最后一个成员**，负责整合所有前序 Agent 的成果：

```
  调研数据 + 分析结果          写作 Agent                     输出
  ────────────────           ──────────                    ──────
  📋 关键发现 6-8 条    →    📝 整合所有素材           →   📄 完整研究报告
  📊 数据指标                ✍️ 撰写连贯报告                 - 摘要
  🎯 趋势分析                📐 规范报告格式                 - 现状分析
  💡 关键洞察 3 条                                          - 深度洞察
  ⚖️ 优势与挑战                                            - 挑战与机遇
                                                           - 结论展望
```

### 2. 核心设计：System Prompt

```python
WRITER_SYSTEM_PROMPT = """你是一个专业的研究报告撰稿人（Writer Agent）。

## 你的职责
你负责将调研数据和分析结果整合成一篇高质量的研究报告。

## 工作要求
1. **结构完整**：报告要有清晰的章节结构
2. **内容准确**：严格基于提供的调研和分析材料，不编造信息
3. **语言专业**：使用专业但易懂的语言
4. **逻辑流畅**：段落之间要有自然的过渡和逻辑关联

## 输出格式
# 📋 [报告标题]

## 摘要
[2-3 句话概述核心内容和主要结论]

## 1. 引言
[介绍研究背景和目的]

## 2. 现状分析
[基于调研数据，描述当前状况]

## 3. 深度洞察
[基于分析结果，展开核心发现和趋势]

## 4. 挑战与机遇
[讨论面临的挑战和潜在机遇]

## 5. 结论与展望
[总结核心观点，展望未来发展]

---
*本报告由 AI 调研团队生成*
"""
```

### 3. 代码实现

```python
"""写作 Agent - 负责报告撰写。"""

def create_writer_agent() -> BaseChatModel:
    """
    创建写作 Agent 的模型实例。

    本函数利用项目统一的公共模型工厂 create_model 来创建通义千问模型实例。

    输入参数:
        无

    输出返回值:
        BaseChatModel: 实例化后的聊天大模型对象，类型为 LangChain 模型基类
    """
    # 使用公共模型工厂创建模型，配置 provider 为 qwen，温度为 0.7 以保持流畅文采和创造力
    model_instance = create_model(
        provider="qwen",  # 指定模型提供商为通义千问
        model_name="qwen-plus",  # 指定具体的模型名称为 qwen-plus
        temperature=0.7,  # 设置较高温度参数以提供更多的表达创造力
    )
    # 返回创建好的大模型实例
    return model_instance

def run_writing(topic: str, research_data: str, analysis_result: str) -> str:
    """
    执行报告撰写任务。

    功能：传入研究主题、原始调研数据和深度分析结果，调用写作 Agent 进行整合润色，并返回最终的研究报告。

    输入参数:
        topic (str): 需要调研与写作的主题名称
        research_data (str): 调研 Agent 提供的原始调研数据文本
        analysis_result (str): 分析 Agent 提供的深度提炼与洞察报告

    输出返回值:
        str: 写作 Agent 最终生成的完整高质量 Markdown 研究报告结果
    """
    # 实例化写作 Agent 的大模型对象
    model = create_writer_agent()
    # 构造包含系统写作提示词和前序工作流产出的用户输入材料的消息列表
    messages = [
        # 传递包含报告章节规范和行文质量要求的系统提示词
        SystemMessage(content=WRITER_SYSTEM_PROMPT),
        # 传递包含研究主题、调研数据以及分析结果的用户输入消息
        HumanMessage(
            content=f"请基于以下材料撰写一篇完整的研究报告：\n\n"  # 拼接请求前缀
            f"**研究主题**：{topic}\n\n"  # 注入主题
            f"**调研数据**：\n{research_data}\n\n"  # 注入上游原始调研事实
            f"**分析结果**：\n{analysis_result}"  # 注入上游深度分析洞察
        ),
    ]
    # 调用大模型的 invoke 方法执行文本写作计算并获取回复
    response = model.invoke(messages)
    # 返回写作大模型响应中的文本结果
    return response.content
```

### 4. 三个 Agent 的温度参数对比

温度参数 (`temperature`) 的选择体现了每个 Agent 不同的工作特性：

| Agent | temperature | 理由 |
|-------|-------------|------|
| 调研 Agent | 0.3（低） | 需要事实准确、结果一致，减少"幻觉" |
| 分析 Agent | 0.5（中） | 需要创造性思考，但也要逻辑严谨 |
| 写作 Agent | 0.7（高） | 需要文采和表达力，允许更多创造性 |

> 📖 **代码实战**：查看 [writer.py](file:///Users/huangyang/code/agent/project_06_multi_agent/05_research_team/agents/writer.py)

---

## 第五部分：LangGraph 工作流编排

### 1. 工作流架构

用 LangGraph 将三个 Agent 编排成一条协作流水线：

```
   START
     │
     ▼
  ┌──────────────┐     State.research_data 被填充
  │  researcher   │ ──────────────────────────────┐
  │  调研节点     │                                │
  └──────┬───────┘                                │
         │                                        ▼
  ┌──────▼───────┐     State.analysis_result 被填充
  │   analyst     │ ──────────────────────────────┐
  │   分析节点    │                                │
  └──────┬───────┘                                │
         │                                        ▼
  ┌──────▼───────┐     State.final_report 被填充
  │    writer     │ ──────────────────────────────┐
  │    写作节点   │                                │
  └──────┬───────┘                                │
         │                                        ▼
        END                                    完成！
```

### 2. 节点函数设计

每个节点函数的职责是：**从 State 读取输入 → 调用 Agent → 将输出写回 State**。

```python
from langchain_core.messages import AIMessage
from agents.researcher import run_research
from agents.analyst import run_analysis
from agents.writer import run_writing


def research_node(state: ResearchTeamState) -> dict:
    """调研节点：调用调研 Agent 收集信息。"""
    topic = state["topic"]                        # ← 从 State 读取主题
    research_result = run_research(topic)          # ← 调用 Agent
    return {
        "messages": [AIMessage(
            content=f"[调研结果]\n{research_result}",
            name="researcher",
        )],
        "research_data": research_result,          # ← 写入 State
        "status": "research_completed",
    }


def analysis_node(state: ResearchTeamState) -> dict:
    """分析节点：调用分析 Agent 进行深度分析。"""
    topic = state["topic"]                        # ← 从 State 读取
    research_data = state["research_data"]        # ← 读取上游调研结果
    analysis_result = run_analysis(topic, research_data)
    return {
        "messages": [AIMessage(
            content=f"[分析结果]\n{analysis_result}",
            name="analyst",
        )],
        "analysis_result": analysis_result,        # ← 写入 State
        "status": "analysis_completed",
    }


def writing_node(state: ResearchTeamState) -> dict:
    """写作节点：调用写作 Agent 生成最终报告。"""
    topic = state["topic"]
    research_data = state["research_data"]        # ← 读取调研结果
    analysis_result = state["analysis_result"]    # ← 读取分析结果
    final_report = run_writing(topic, research_data, analysis_result)
    return {
        "messages": [AIMessage(
            content=f"[最终报告]\n{final_report}",
            name="writer",
        )],
        "final_report": final_report,              # ← 写入 State
        "status": "report_completed",
    }
```

### 3. 构建状态图

```python
from langgraph.graph import StateGraph, END


def build_research_team_workflow() -> StateGraph:
    """构建 AI 调研团队的 LangGraph 工作流。"""

    # 创建状态图
    workflow = StateGraph(ResearchTeamState)

    # 添加三个 Agent 节点
    workflow.add_node("researcher", research_node)
    workflow.add_node("analyst", analysis_node)
    workflow.add_node("writer", writing_node)

    # 设置入口（从调研开始）
    workflow.set_entry_point("researcher")

    # 添加固定边（线性流水线）
    workflow.add_edge("researcher", "analyst")     # 调研 → 分析
    workflow.add_edge("analyst", "writer")         # 分析 → 写作
    workflow.add_edge("writer", END)               # 写作 → 结束

    # 编译并返回
    return workflow.compile()
```

**对比 Day 15 的 Supervisor 模式**：

```python
# Day 15 Supervisor 模式：使用条件边，动态路由
workflow.add_conditional_edges("supervisor", route_fn, {...})

# Day 16 协作模式：使用固定边，线性流水线
workflow.add_edge("researcher", "analyst")
workflow.add_edge("analyst", "writer")
workflow.add_edge("writer", END)
```

协作模式的代码更简洁，因为流程是固定的，不需要路由决策。

### 4. 主入口实现

```python
"""AI 调研团队 - 主入口。"""

from langchain_core.messages import HumanMessage
from workflow import build_research_team_workflow


def main():
    """AI 调研团队主函数。"""
    print("=" * 60)
    print("🏢 AI 调研团队 - Research Team")
    print("=" * 60)
    print("\n📝 团队成员：")
    print("  🔍 调研 Agent - 负责信息搜索和收集")
    print("  📊 分析 Agent - 负责深度分析和洞察提炼")
    print("  ✍️ 写作 Agent - 负责研究报告撰写")

    # 获取用户输入
    topic = input("\n🎯 请输入研究主题：").strip()
    if not topic:
        topic = "AI Agent 技术的发展现状与未来趋势"

    # 构建工作流
    workflow = build_research_team_workflow()

    # 执行工作流
    result = workflow.invoke({
        "messages": [HumanMessage(content=f"请对以下主题进行全面调研：{topic}")],
        "topic": topic,
        "research_data": "",
        "analysis_result": "",
        "final_report": "",
        "status": "started",
    })

    # 输出最终报告
    print("\n" + "=" * 60)
    print("📄 最终研究报告")
    print("=" * 60)
    print(result["final_report"])

    # 输出统计
    print(f"\n📊 统计：调研 {len(result['research_data'])} 字 → "
          f"分析 {len(result['analysis_result'])} 字 → "
          f"报告 {len(result['final_report'])} 字")
```

> 📖 **代码实战**：查看并运行 [workflow.py](file:///Users/huangyang/code/agent/project_06_multi_agent/05_research_team/workflow.py) 和 [main.py](file:///Users/huangyang/code/agent/project_06_multi_agent/05_research_team/main.py)

---

## 核心原理深度解析

### 1. 模块化 Agent 设计的本质

整个项目的架构可以用一句话概括：

> **每个 Agent = 一段专精的 System Prompt + 一个 LLM 调用 + 特定的输入输出接口**

```
┌─────────────────────────────────────────────────┐
│                  Agent 模块                      │
│                                                  │
│  ┌─────────────────────┐                        │
│  │  System Prompt       │ ← "你是一个调研专家..."  │
│  │  （角色说明书）       │                        │
│  └─────────┬───────────┘                        │
│            ▼                                     │
│  ┌─────────────────────┐                        │
│  │  LLM 调用            │ ← ChatOpenAI.invoke()  │
│  │  （核心引擎）         │                        │
│  └─────────┬───────────┘                        │
│            ▼                                     │
│  ┌─────────────────────┐                        │
│  │  输入/输出接口        │ ← run_research(topic)  │
│  │  （对外暴露的函数）   │    → str               │
│  └─────────────────────┘                        │
│                                                  │
└─────────────────────────────────────────────────┘
```

### 2. 为什么要把 Agent 放在单独的文件中？

| 做法 | 优点 | 缺点 |
|------|------|------|
| 全部写在一个文件里 | 简单 | 代码臃肿、难以维护、无法复用 |
| 每个 Agent 一个文件 ✅ | 清晰、可维护、可独立测试、可复用 | 文件稍多 |

在生产环境中，一个 Agent 可能有数百行代码（包括工具定义、错误处理、日志等），模块化是**必需的**。

### 3. State 设计的黄金法则

| 法则 | 说明 | 反例 |
|------|------|------|
| **只存必要数据** | State 不要存冗余信息 | 不要同时存 "research_data" 和 "research_summary" |
| **字段名要语义化** | 看名字就知道是什么 | 不要用 "data1"、"result2" |
| **明确读写方** | 记录每个字段由谁写、谁读 | 避免多个 Agent 写同一字段 |
| **消息用累积模式** | `Annotated[..., operator.add]` | 不要让消息互相覆盖 |

### 4. 本项目的技术栈回顾

这个项目整合了前 15 天学到的多项技术：

| 技术 | 学习日期 | 在本项目中的应用 |
|------|---------|-----------------|
| LangChain ChatOpenAI | Day 1-2 | 创建模型实例，调用 LLM |
| System Prompt 设计 | Day 2-3 | 为每个 Agent 设计专精的角色提示 |
| 消息类型管理 | Day 3-4 | SystemMessage / HumanMessage / AIMessage |
| LangGraph StateGraph | Day 7, 15 | 编排多 Agent 工作流 |
| 共享状态设计 | Day 14-15 | TypedDict 定义 State，Agent 间通信 |
| 协作模式 | Day 15 | 线性流水线（调研→分析→写作） |

---

## 课后练习

1. **独立运行各 Agent**：分别运行 `researcher.py`、`analyst.py`、`writer.py` 的测试代码（`if __name__ == "__main__"` 部分），验证每个 Agent 能独立工作。

2. **修改调研主题**：在 `main.py` 中尝试不同的研究主题（如"自动驾驶技术"、"量子计算"、"Web3"），观察输出质量的差异。

3. **Prompt 优化**：尝试修改某个 Agent 的 System Prompt，观察输出变化。例如，让调研 Agent 输出更多案例，或让写作 Agent 使用更通俗的语言。

4. **温度参数实验**：将写作 Agent 的温度从 0.7 改为 0.2，再改为 1.0，对比同一主题下生成报告的风格差异。

5. **Flake8 自检**：确保代码通过 `flake8 project_06_multi_agent/05_research_team/` 的检查。

---

## 🔮 明日预告

**Day 17：综合项目 — AI 调研团队（下）** 🎯

明天我们将在今天的基础上进行**增强和扩展**：
- 为 Agent 添加真实工具（如网络搜索工具），让调研 Agent 能搜索真实信息
- 添加质量审核环节（引入 Reviewer Agent 或反馈环）
- 添加执行日志和计时统计
- 将报告输出为文件（Markdown / TXT）
- 回顾整个 17 天的学习路径，总结核心知识点
