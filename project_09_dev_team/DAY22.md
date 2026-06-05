# Day 22 课程：多智能体协同开发助手 — 角色分工与消息通信 🤝

在前 21 天中，我们构建的所有 Agent 都是"单兵作战"——一个 Agent 独自完成推理、调用工具、生成回答。但在真实的软件开发场景中，没有人能独自完成所有事情：需求分析、架构设计、编码实现、测试排错、文档编写，每一项都需要不同的专业能力。

单智能体面对完整项目开发时，会遇到三个根本性瓶颈：

1. **角色混乱**：让同一个 LLM 既做架构设计又写代码又测 Bug，不同角色的思维方式和输出格式截然不同，LLM 容易在角色切换中丢失上下文。
2. **上下文爆炸**：复杂项目的完整上下文（需求文档 + 架构设计 + 代码 + 测试用例）远超 LLM 的上下文窗口，单 Agent 无法同时持有所有信息。
3. **无法并行**：单 Agent 只能串行处理任务，而实际项目中架构设计和文档编写可以并行，测试可以在编码完成后立即开始。

**多智能体协同**正是为解决这些问题而生的。每个 Agent 扮演一个专业角色，拥有独立的 System Prompt 和工具集，通过消息传递协同完成复杂任务。

> 技术状态说明（2026）：多 Agent 开发团队并不落后，LangGraph、OpenAI Agents SDK、AutoGen、CrewAI 都仍在围绕 subagents、handoffs、teams、flows 等模式演进。但当前最佳实践已经从“让多个 Agent 全自动写完项目”转向“代码编排 + 专家 Agent + 结构化产物 + 沙箱执行 + 人工审批 + 可观测评估”。因此本课不能承诺无边界全自动交付生产代码，而应把目标设为**受控的本地开发闭环**。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：从单 Agent 到多 Agent 协同](#第一部分从单-agent-到多-agent-协同)
3. [第二部分：四角色智能体架构设计](#第二部分四角色智能体架构设计)
4. [第三部分：Agent 间消息通信与任务流转](#第三部分agent-间消息通信与任务流转)
5. [核心原理深度解析](#核心原理深度解析)
6. [课后练习](#课后练习)

---

## 学习目标
- 理解单 Agent 的三大瓶颈与多 Agent 协同的优势。
- 掌握四角色智能体的职责划分、System Prompt 设计和工具配置。
- 掌握多 Agent 消息队列、任务下发、结果回传机制。
- 理解 LangGraph 中多 Agent 编排的两种模式：线性流水线 vs. 主管调度。
- 实现规划 Agent 的需求结构化拆解能力。
- 理解角色隔离、工具最小权限、产物 schema 校验和安全工作区的重要性。

---

## 第一部分：从单 Agent 到多 Agent 协同

### 1. 单 Agent 的三大瓶颈

#### 瓶颈一：角色混乱

```
单 Agent 的角色切换:

[需求分析模式] "我需要拆解这个需求..."
    ↓ 切换上下文
[编码模式] "我来写这段代码..."
    ↓ 再次切换
[测试模式] "让我检查这段代码有没有 Bug..."
    ↓ 又切换
[文档模式] "我来写 API 文档..."

每次切换都丢失一部分上下文，最终输出质量逐级下降。
```

#### 瓶颈二：上下文爆炸

```
单 Agent 的上下文窗口:

需求文档 (2000 tokens) + 架构设计 (3000 tokens)
+ 代码实现 (5000 tokens) + 测试报告 (2000 tokens)
+ 历史消息 (3000 tokens) = 15,000 tokens

简单项目勉强装下，中等项目直接溢出。
```

#### 瓶颈三：无法并行

```
单 Agent（串行）:
需求分析 → 架构设计 → 编码 → 测试 → 文档
   5min     8min     15min   10min   5min   = 43min

多 Agent（部分并行）:
规划Agent: 需求分析 → 架构设计 ─────────────────┐
                                            │
开发Agent:          ────── 编码 ←───────────┤
                                            │
测试Agent:          ────────────── 测试 ←───┤
                                            │
文档Agent:          ─────────────────── 文档 ←┘
                                              = 28min
```

### 2. 多 Agent 协同的核心优势

| 维度 | 单 Agent | 多 Agent 协同 |
|------|---------|-------------|
| 角色专注度 | 频繁切换，每个角色都做不精 | 每个角色有专属 Prompt，专注做一件事 |
| 上下文管理 | 全量共享，容易溢出 | 按需传递，每个 Agent 只看相关信息 |
| 并行能力 | 只能串行 | 无依赖的任务可并行 |
| 容错能力 | 一个环节出错影响全局 | 单 Agent 出错可被其他 Agent 修正 |
| 可扩展性 | 增加能力需要修改全局 Prompt | 新增角色只需加一个 Agent |

### 3. Day 16-17 多 Agent 与 Day 22 多 Agent 的区别

| 维度 | Day 16-17 调研团队 | Day 22-23 开发团队 |
|------|-------------------|-------------------|
| Agent 数量 | 3 个（调研/分析/写作） | 4 个（规划/开发/测试/文档） |
| 任务类型 | 信息收集与整理 | 软件开发全流程 |
| 输出产物 | 一份调研报告 | 代码 + 测试 + 文档（多产物） |
| 交互模式 | 线性流水线 | 流水线 + 反馈循环（测试→开发→修复） |
| 反馈机制 | 无（单向流转） | 有（测试发现 Bug → 回传开发 Agent 修复） |
| 工具集 | 搜索工具 | 代码生成/审查/执行/文件写入 |

---

## 第二部分：四角色智能体架构设计

### 1. 四大核心角色

```
┌─────────────────────────────────────────────────────────┐
│              多智能体协同开发系统                          │
│                                                         │
│  ┌──────────┐    ┌──────────┐                          │
│  │ 规划Agent │    │ 开发Agent │                          │
│  │ Planner   │    │ Developer │                          │
│  │           │    │           │                          │
│  │ 需求分析   │    │ 代码编写   │                          │
│  │ 任务拆解   │    │ 接口实现   │                          │
│  │ 架构设计   │    │ 逻辑开发   │                          │
│  │ 整体统筹   │    │ Bug 修复  │                          │
│  └─────┬────┘    └─────┬────┘                          │
│        │               │                               │
│        ▼               ▼                               │
│  ┌──────────┐    ┌──────────┐                          │
│  │ 测试Agent │    │ 文档Agent │                          │
│  │ Tester    │    │ DocWriter │                          │
│  │           │    │           │                          │
│  │ 代码审查   │    │ 代码注释   │                          │
│  │ BUG 检测  │    │ API 文档  │                          │
│  │ 性能检查   │    │ 开发文档   │                          │
│  │ 安全扫描   │    │ 项目复盘   │                          │
│  └──────────┘    └──────────┘                          │
└─────────────────────────────────────────────────────────┘
```

### 2. 各角色的 System Prompt 设计

#### 规划 Agent (Planner)

```python
PLANNER_SYSTEM_PROMPT = """你是一位资深的软件架构师和项目经理。

你的职责：
1. 分析用户的需求描述，理解核心目标
2. 将模糊需求拆解为结构化的功能点清单
3. 设计模块划分和接口规范
4. 规划开发步骤和执行顺序
5. 协调其他 Agent 的工作流程

输出规范：
- 任务拆解使用 JSON 格式，包含模块名、功能点、优先级、依赖关系
- 架构设计使用目录结构 + 接口列表
- 每个任务必须包含明确的输入/输出/验收标准

思维原则：
- 先理解需求，再设计方案，最后拆解任务
- 模块之间保持低耦合、高内聚
- 优先实现核心功能，非核心功能标注为可选
"""
```

#### 开发 Agent (Developer)

```python
DEVELOPER_SYSTEM_PROMPT = """你是一位高级全栈开发工程师。

你的职责：
1. 根据架构设计编写代码实现
2. 遵循模块划分和接口规范
3. 编写清晰、安全、可维护的代码
4. 根据测试反馈修复 Bug

编码规范：
- 代码必须有类型注解
- 函数长度不超过 50 行
- 使用有意义的变量和函数命名
- 关键逻辑添加注释说明 WHY（为什么这样做）
- 不使用 eval()、exec() 等危险函数
- 所有外部输入必须校验

修复 Bug 时：
- 先分析错误原因，再修复
- 修复后说明修改了什么、为什么这样修改
- 如果是架构问题，反馈给规划 Agent
"""
```

#### 测试 Agent (Tester)

```python
TESTER_SYSTEM_PROMPT = """你是一位严谨的测试工程师和代码审查专家。

你的职责：
1. 审查代码的语法正确性
2. 检查逻辑漏洞和边界异常
3. 扫描安全风险（硬编码密钥、SQL 注入、XSS 等）
4. 检查性能问题（N+1 查询、无限循环、内存泄漏）
5. 生成修复建议

审查维度：
- 正确性：代码是否能正确实现功能？
- 安全性：是否存在安全漏洞？
- 健壮性：边界情况是否处理？
- 可维护性：代码是否清晰易读？
- 性能：是否存在性能瓶颈？

输出格式：
对于每个问题，输出：
- 严重级别: CRITICAL / HIGH / MEDIUM / LOW
- 位置: 文件名:行号
- 描述: 问题描述
- 建议: 修复方案
"""
```

#### 文档 Agent (DocWriter)

```python
DOCWRITER_SYSTEM_PROMPT = """你是一位专业的技术文档工程师。

你的职责：
1. 为代码添加注释和 docstring
2. 编写 API 接口文档
3. 编写开发文档（架构说明、模块说明）
4. 生成项目 README
5. 编写项目复盘总结

文档规范：
- API 文档包含：接口路径、请求方法、参数说明、返回格式、示例
- 模块说明包含：职责、依赖、接口列表
- README 包含：项目简介、安装步骤、使用方法、目录结构
- 所有文档使用中文

写作原则：
- 面向读者，而非面向自己
- 先说结论，再说细节
- 代码示例优于纯文字描述
"""
```

### 3. 各角色的工具配置

不同角色拥有不同的工具集，确保每个 Agent 只能做自己职责范围内的事：

| 角色 | 工具集 | 说明 |
|------|--------|------|
| 规划 Agent | `list_files`, `read_file`, `emit_plan` | 只读代码 + 输出结构化计划 |
| 开发 Agent | `read_file`, `emit_artifact` | 不能直接写磁盘，只能提交代码产物 |
| 测试 Agent | `read_file`, `run_tests` | 只读代码 + 在沙箱工作区运行白名单测试 |
| 文档 Agent | `read_file`, `emit_artifact` | 读代码 + 提交文档产物 |
| 交付节点 | `safe_write_artifacts` | 唯一允许落盘的节点，负责路径校验和覆盖策略 |

```python
# 工具配置示例
AGENT_TOOLS = {
    "planner": [list_files, read_file, emit_plan],
    "developer": [read_file, emit_artifact],
    "tester": [read_file, run_tests],
    "docwriter": [read_file, emit_artifact],
}

def create_agent(role: str, model) -> Runnable:
    """创建指定角色的 Agent。"""
    prompts = {
        "planner": PLANNER_SYSTEM_PROMPT,
        "developer": DEVELOPER_SYSTEM_PROMPT,
        "tester": TESTER_SYSTEM_PROMPT,
        "docwriter": DOCWRITER_SYSTEM_PROMPT,
    }
    tools = AGENT_TOOLS[role]
    model_with_tools = model.bind_tools(tools)
    # 返回 LangGraph 的 create_react_agent
    return create_react_agent(
        model=model_with_tools,
        tools=tools,
        prompt=prompts[role],
    )
```

这个变化很关键：Agent 不直接写任意文件，也不直接执行任意命令。Planner、Developer、DocWriter 只产出结构化对象；真正写入磁盘由交付节点统一做路径校验、文件覆盖判断和审计。Tester 只能在项目输出目录下执行白名单测试命令，不能获得通用 shell。

---

## 第三部分：Agent 间消息通信与任务流转

### 1. 消息传递机制设计

多 Agent 系统的核心挑战是**Agent 之间如何通信**。我们设计一个基于 LangGraph 共享状态的消息传递机制：

```
Agent 通信模型:

┌─────────────┐     task_message      ┌─────────────┐
│ 规划Agent    │ ───────────────────► │ 开发Agent    │
│             │                       │             │
│ 输出: 架构   │ ◄─────────────────── │ 输出: 代码   │
│     任务列表 │      result_message   │     实现文件 │
└─────────────┘                       └──────┬──────┘
                                             │
                                             │ task_message
                                             ▼
                                      ┌─────────────┐
                                      │ 测试Agent    │
                                      │             │
                                      │ 输出: 测试   │
                                      │     报告    │
                                      └──────┬──────┘
                                             │
                              ┌───────────────┼───────────────┐
                              │ bug_message   │               │ doc_request
                              ▼               │               ▼
                       ┌─────────────┐       │        ┌─────────────┐
                       │ 开发Agent    │       │        │ 文档Agent    │
                       │ (修复Bug)   │       │        │ (写文档)    │
                       └─────────────┘       │        └─────────────┘
                                             │
                                    (修复后重新测试)
```

### 2. Message 数据结构

```python
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class AgentMessage:
    """Agent 间传递的消息。"""
    message_id: str                       # 消息 ID
    correlation_id: str                   # 同一项目/任务的关联 ID
    sender: str                          # 发送方 Agent 角色
    receiver: str                        # 接收方 Agent 角色
    msg_type: str                        # 消息类型: task / result / bug / feedback
    content: str                         # 消息正文
    attachments: dict = field(default_factory=dict)  # 附带数据（代码/文件路径等）
    priority: str = "normal"             # high / normal / low
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskAssignment:
    """任务下发结构。"""
    task_id: str                         # 任务 ID
    target_agent: str                    # 目标 Agent 角色
    description: str                     # 任务描述
    input_data: dict = field(default_factory=dict)  # 输入数据
    acceptance_criteria: str = ""        # 验收标准
    priority: str = "normal"             # 优先级: high / normal / low


@dataclass
class TaskResult:
    """任务结果回传结构。"""
    task_id: str                         # 对应的任务 ID
    agent: str                           # 完成任务的 Agent
    status: str                          # done / failed / needs_revision
    output: str                          # 输出内容
    artifacts: list = field(default_factory=list)  # 产出文件列表
    issues: list = field(default_factory=list)     # 发现的问题
```

### 3. MessageBus — 消息总线

```python
class MessageBus:
    """Agent 间消息总线，基于共享状态的消息传递。"""

    def __init__(self):
        self._queue: list[AgentMessage] = []
        self._history: list[AgentMessage] = []

    def send(self, message: AgentMessage):
        """发送消息。"""
        self._queue.append(message)
        self._queue.sort(key=lambda m: {"high": 0, "normal": 1, "low": 2}.get(m.priority, 1))
        self._history.append(message)

    def receive(self, receiver: str) -> list[AgentMessage]:
        """接收指定 Agent 的所有待处理消息。"""
        messages = [
            m for m in self._queue if m.receiver == receiver
        ]
        # 从队列中移除已读消息
        self._queue = [
            m for m in self._queue if m.receiver != receiver
        ]
        return messages

    def broadcast(self, sender: str, msg_type: str, content: str):
        """广播消息给所有 Agent。"""
        for role in ["planner", "developer", "tester", "docwriter"]:
            if role != sender:
                self.send(AgentMessage(
                    message_id=f"{sender}-{role}-{len(self._history) + 1}",
                    correlation_id="project-run",
                    sender=sender,
                    receiver=role,
                    msg_type=msg_type,
                    content=content,
                ))

    def get_history(self, agent: str = None) -> list[AgentMessage]:
        """获取消息历史。"""
        if agent:
            return [
                m for m in self._history
                if m.sender == agent or m.receiver == agent
            ]
        return self._history
```

### 4. 规划 Agent 的需求结构化拆解

规划 Agent 是整个系统的"大脑"，负责将模糊的自然语言需求转化为结构化的开发任务：

```
用户输入（模糊需求）:
"做一个待办事项管理应用，支持增删改查，数据存到本地文件"

规划 Agent 输出:

📋 需求分析:
核心功能: 待办事项的增删改查 (CRUD)
数据持久化: 本地 JSON 文件
非功能需求: 命令行交互界面

🏗️ 模块设计:
todo_app/
├── main.py          # CLI 入口
├── models.py        # 数据模型 (TodoItem)
├── storage.py       # 文件存储层
└── commands.py      # 命令处理层

📝 任务清单:
┌────┬──────────────┬──────────────────────────┬──────┬────────┐
│ ID │ 模块          │ 任务描述                  │ 优先级│ 依赖   │
├────┼──────────────┼──────────────────────────┼──────┼────────┤
│ T1 │ models       │ 定义 TodoItem 数据模型     │ 高   │ —      │
│ T2 │ storage      │ 实现 JSON 文件读写         │ 高   │ T1     │
│ T3 │ commands     │ 实现增删改查命令            │ 高   │ T2     │
│ T4 │ main         │ 实现 CLI 交互循环           │ 中   │ T3     │
│ T5 │ —            │ 编写单元测试               │ 中   │ T1-T4  │
│ T6 │ —            │ 编写 README 和 API 文档    │ 低   │ T1-T4  │
└────┴──────────────┴──────────────────────────┴──────┴────────┘

🔗 接口规范:
- TodoItem: {id: str, title: str, done: bool, created_at: str}
- Storage.load() -> List[TodoItem]
- Storage.save(items: List[TodoItem]) -> None
- Commands.add(title: str) -> TodoItem
- Commands.delete(id: str) -> bool
- Commands.list_all() -> List[TodoItem]
- Commands.toggle(id: str) -> TodoItem
```

### 5. TaskPlanner 的 Prompt 设计

```python
REQUIREMENT_ANALYSIS_PROMPT = """你是一位资深软件架构师。请分析以下需求，输出结构化的开发计划。

需求描述:
{requirement}

请按以下格式输出:

1. 需求分析: 核心功能点列表 + 非功能需求
2. 模块设计: 目录结构 + 模块职责说明
3. 任务清单: 每个任务包含 ID/模块/描述/优先级/依赖
4. 接口规范: 每个模块对外暴露的函数/类签名
5. 数据模型: 核心数据结构定义

注意事项:
- 每个任务必须是单一职责的，可独立开发
- 任务粒度适中（每个任务 30-100 行代码）
- 依赖关系必须明确（被依赖的任务优先开发）
- 接口规范必须包含参数类型和返回类型
"""
```

---

## 核心原理深度解析

### 多 Agent 系统的三种编排模式

```
模式一: 线性流水线 (Day 16-17 调研团队)

规划 → 开发 → 测试 → 文档
  │      │      │      │
  └──────┴──────┴──────┘  单向流转，无反馈

模式二: 主管调度 (Day 14 Supervisor Pattern)

        ┌─── 规划Agent ───┐
        │                  │
主管 ───┼─── 开发Agent ───┤─── 主管
Agent   │                  │   (汇总)
        ┌─── 测试Agent ───┤
        │                  │
        └─── 文档Agent ───┘

模式三: 流水线 + 反馈循环 (Day 22-23 开发团队)

规划 → 开发 → 测试 ──┐
              ▲      │ (Bug 反馈)
              └── 开发 (修复) ── 测试 ── 文档
```

Day 22-23 选择**模式三**，因为软件开发天然存在"编码 → 测试 → 修复"的反馈循环，这是模式一和模式二无法表达的。

### Agent 角色隔离的价值

每个 Agent 有独立的 System Prompt 和工具集，这不仅是"专业分工"，更是一种**安全边界**：

| 安全考量 | 说明 |
|---------|------|
| 工具隔离 | 测试 Agent 不能写入代码，防止测试修改被测对象 |
| 视角隔离 | 开发 Agent 不看需求原文，只看架构设计，避免"按需求直译" |
| 权限隔离 | 文档 Agent 不能执行代码，防止文档生成触发危险操作 |
| 认知隔离 | 每个 Agent 的上下文窗口只装载自己需要的信息 |

### 消息传递 vs. 共享内存

多 Agent 通信有两种基本模式：

| 模式 | 实现 | 优点 | 缺点 |
|------|------|------|------|
| 消息传递 | AgentMessage 队列 | 松耦合、可追踪、支持异步 | 需要序列化/反序列化 |
| 共享内存 | LangGraph State | 简单直接、自动同步 | 紧耦合、状态冲突风险 |

我们采用**混合模式**：LangGraph 的 `WorkflowState` 作为共享内存（存储全局进度和最终产物），`MessageBus` 作为消息传递层（存储 Agent 间的任务分配和结果回传）。这样既利用了 LangGraph 的状态管理能力，又保持了 Agent 间的松耦合。

---

## 课后练习

1. **角色 Prompt 调优**：对四个 Agent 的 System Prompt 分别进行 A/B 测试——同一个需求，使用"详细版 Prompt"和"简洁版 Prompt"，对比最终代码质量差异。

2. **工具隔离验证**：故意让测试 Agent 尝试调用 `write_file` 工具（它不应该拥有），验证工具隔离是否生效。如果测试 Agent 试图写入文件，说明工具配置有泄漏。

3. **消息总线扩展**：为 MessageBus 添加"消息优先级"功能——高优先级消息（如 CRITICAL Bug 报告）优先处理，低优先级消息（如文档更新请求）排队等待。

4. **需求拆解实验**：准备 3 个不同复杂度的需求描述（简单/中等/复杂），让规划 Agent 分别拆解，对比拆解结果的质量和步骤数量。

5. **Flake8 自检**：确保代码通过 `flake8 project_09_dev_team/` 的检查。
