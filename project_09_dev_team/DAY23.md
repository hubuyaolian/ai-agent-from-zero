# Day 23 课程：多智能体协同开发助手 — 工作流编排与受控交付 🔧

在 Day 22 中，我们完成了多智能体系统的两大基础：**四角色智能体架构**（规划/开发/测试/文档）和**消息通信机制**（MessageBus + 任务分配）。今天我们将这些组件组装为一台完整的"软件开发流水线"——用 LangGraph 思想编排一个包含反馈循环的多 Agent 工作流，实现从需求输入到项目交付的受控闭环。

> 技术状态说明（2026）：LangGraph 的 multi-agent、自定义 workflow 和 supervisor/subagents 模式仍然是主流路线之一；OpenAI Agents SDK 也明确支持 agents-as-tools、handoffs、guardrails、sessions、tracing、MCP 与 sandbox；AutoGen 和 CrewAI 也在继续维护 teams/flows。课程路线不落后，但“全自动开发并交付”必须加边界：结构化输出、路径白名单、测试沙箱、最大修复轮次、人工审批和交付前质量门禁。长程开发 Agent 的关键不只是能连续工作更久，而是能在长时间运行中保持状态可恢复、工具可控、成本可预算、失败可追踪。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：LangGraph 多 Agent 工作流编排](#第一部分langgraph-多-agent-工作流编排)
3. [第二部分：代码受控生成与自检](#第二部分代码受控生成与自检)
4. [第三部分：项目自动化交付闭环](#第三部分项目自动化交付闭环)
5. [第四部分：2026 前沿扩展：长程开发 Agent 的工程边界](#第四部分2026-前沿扩展长程开发-agent-的工程边界)
6. [核心原理深度解析](#核心原理深度解析)
7. [课后练习](#课后练习)

---

## 学习目标
- 掌握 LangGraph 编排多 Agent 工作流的设计（含反馈循环）。
- 理解"写代码 → 查代码 → 改代码"的自检闭环机制。
- 掌握 DevTeamState 的状态管理与流转。
- 实现从需求输入到项目交付的受控闭环。
- 构建完整的多智能体协同开发 CLI 应用。
- 理解长程开发 Agent 的 checkpoint、sandbox、人工中断、成本预算和可观测性边界。

---

## 第一部分：LangGraph 多 Agent 工作流编排

### 1. DevTeamState — 团队工作流状态

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class DevTeamState(TypedDict):
    """多智能体协同开发工作流状态。"""
    messages: Annotated[list, add_messages]  # 全局对话消息
    requirement: str                         # 用户原始需求
    plan: dict                               # 规划 Agent 输出的开发计划
    task_queue: list                         # 待执行的任务队列
    current_task: dict                       # 当前正在执行的任务
    code_artifacts: dict                     # 代码产物 {文件路径: 内容}
    artifact_manifest: list                  # 结构化产物清单
    test_report: dict                        # 测试报告
    bug_list: list                           # 测试发现的 Bug 列表
    fix_count: int                           # 修复轮次计数
    doc_artifacts: dict                      # 文档产物 {文件路径: 内容}
    approval_required: bool                  # 是否需要人工审批
    quality_gate: dict                       # 交付质量门禁结果
    stage: str                               # 当前阶段: planning/developing/testing/fixing/documenting/done
    message_bus: list                        # Agent 间消息记录
```

### 2. 6 节点工作流图

```
START
  │
  ▼
┌─────────────────┐
│ planner_node    │  规划Agent：需求分析 → 任务拆解 → 架构设计
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ developer_node  │  开发Agent：按任务编写代码
└────────┬────────┘
         │
         ▼
┌─────────────────┐     发现 Bug
│ tester_node     │──────────────────► developer_node
│                 │     (修复循环,       (fix 模式)
│                 │      最多 3 轮)
└────────┬────────┘
         │ 测试通过
         ▼
┌─────────────────┐
│ fixer_node      │  开发Agent（修复模式）：处理测试反馈的 Bug
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ docwriter_node  │  文档Agent：代码注释 + API 文档 + README
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ deliver_node    │  交付节点：汇总产物 + 生成项目报告
└────────┬────────┘
         │
         ▼
        END
```

### 3. 条件边：测试后的路由决策

测试节点后有三条可能的路径：

```python
def route_after_test(state: DevTeamState) -> str:
    """测试节点后的路由决策。"""
    bugs = state.get("bug_list", [])
    fix_count = state.get("fix_count", 0)

    if not bugs:
        # 无 Bug → 进入文档阶段
        return "document"

    if fix_count >= MAX_FIX_ROUNDS:
        # 修复轮次耗尽 → 强制进入文档阶段（附带未修复 Bug 说明）
        return "document_with_issues"

    # 有 Bug 且修复轮次未耗尽 → 进入修复阶段
    return "fix"
```

```
tester_node ──┬── 无 Bug ──────────────► docwriter_node
              │
              ├── 有 Bug, fix_count < 3 ► fixer_node → developer_node(fix) → tester_node
              │
              └── 有 Bug, fix_count ≥ 3 ► docwriter_node (附带未修复问题清单)
```

### 4. 各节点实现

#### planner_node — 规划节点

```python
def planner_node(state: DevTeamState) -> dict:
    """规划 Agent：分析需求 → 拆解任务 → 输出开发计划。"""
    planner = create_agent("planner", model)

    response = planner.invoke({
        "messages": [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=REQUIREMENT_ANALYSIS_PROMPT.format(
                requirement=state["requirement"]
            )),
        ]
    })

    plan = parse_plan_response(response["messages"][-1].content)

    # 将任务清单转化为任务队列
    task_queue = plan.get("tasks", [])
    # 按依赖关系排序
    ordered_tasks = resolve_execution_order(task_queue)

    # 记录消息
    message_bus_send(
        sender="planner",
        receiver="developer",
        msg_type="task",
        content=f"开发计划已生成，共 {len(ordered_tasks)} 个任务",
        attachments={"plan": plan},
    )

    return {
        "plan": plan,
        "task_queue": ordered_tasks,
        "stage": "developing",
    }
```

#### developer_node — 开发节点

```python
def developer_node(state: DevTeamState) -> dict:
    """开发 Agent：按任务编写代码。"""
    developer = create_agent("developer", model)

    # 取出下一个任务
    task_queue = state.get("task_queue", [])
    if not task_queue:
        return {"stage": "testing"}

    current_task = task_queue[0]
    remaining_tasks = task_queue[1:]

    # 构造开发指令
    context = build_dev_context(state["plan"], current_task, state["code_artifacts"])

    response = developer.invoke({
        "messages": [
            SystemMessage(content=DEVELOPER_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"当前任务: {current_task['description']}\n\n"
                f"架构设计:\n{context}\n\n"
                f"请编写实现代码，输出完整的文件路径和文件内容。"
            )),
        ]
    })

    # 解析代码产物
    new_artifacts = parse_code_response(response["messages"][-1].content)
    all_artifacts = {**state.get("code_artifacts", {}), **new_artifacts}

    return {
        "task_queue": remaining_tasks,
        "current_task": current_task,
        "code_artifacts": all_artifacts,
        "stage": "developing" if remaining_tasks else "testing",
    }
```

#### tester_node — 测试节点

```python
def tester_node(state: DevTeamState) -> dict:
    """测试 Agent：审查代码 → 检测 Bug → 生成测试报告。"""
    tester = create_agent("tester", model)

    # 将所有代码产物拼给测试 Agent
    code_summary = format_code_artifacts(state["code_artifacts"])

    response = tester.invoke({
        "messages": [
            SystemMessage(content=TESTER_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"请审查以下代码，检测 Bug、安全风险和性能问题。\n\n"
                f"项目需求: {state['requirement']}\n\n"
                f"代码:\n{code_summary}"
            )),
        ]
    })

    # 解析测试报告
    test_result = parse_test_response(response["messages"][-1].content)
    bugs = test_result.get("bugs", [])

    # 按严重级别分类
    critical_bugs = [b for b in bugs if b["severity"] == "CRITICAL"]
    high_bugs = [b for b in bugs if b["severity"] == "HIGH"]
    other_bugs = [b for b in bugs if b["severity"] not in ("CRITICAL", "HIGH")]

    # 记录消息
    if bugs:
        message_bus_send(
            sender="tester",
            receiver="developer",
            msg_type="bug",
            content=f"发现 {len(bugs)} 个问题（{len(critical_bugs)} CRITICAL, {len(high_bugs)} HIGH）",
            attachments={"bugs": bugs},
        )

    return {
        "test_report": test_result,
        "bug_list": bugs,
        "stage": "fixing" if bugs else "documenting",
    }
```

#### fixer_node — 修复节点

```python
def fixer_node(state: DevTeamState) -> dict:
    """开发 Agent（修复模式）：根据测试反馈修复 Bug。"""
    developer = create_agent("developer", model)

    bugs = state.get("bug_list", [])
    bug_descriptions = format_bug_list(bugs)
    code_summary = format_code_artifacts(state["code_artifacts"])

    response = developer.invoke({
        "messages": [
            SystemMessage(content=DEVELOPER_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"测试发现以下问题，请逐一修复:\n\n"
                f"{bug_descriptions}\n\n"
                f"当前代码:\n{code_summary}\n\n"
                f"请输出修复后的完整文件路径和文件内容。"
            )),
        ]
    })

    # 解析修复后的代码
    fixed_artifacts = parse_code_response(response["messages"][-1].content)
    all_artifacts = {**state["code_artifacts"], **fixed_artifacts}

    return {
        "code_artifacts": all_artifacts,
        "bug_list": [],        # 清空 Bug 列表，等待重新测试
        "fix_count": state.get("fix_count", 0) + 1,
        "stage": "testing",    # 回到测试节点
    }
```

#### docwriter_node — 文档节点

```python
def docwriter_node(state: DevTeamState) -> dict:
    """文档 Agent：代码注释 + API 文档 + README。"""
    docwriter = create_agent("docwriter", model)

    code_summary = format_code_artifacts(state["code_artifacts"])

    response = docwriter.invoke({
        "messages": [
            SystemMessage(content=DOCWRITER_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"项目需求: {state['requirement']}\n\n"
                f"代码:\n{code_summary}\n\n"
                f"请生成以下文档:\n"
                f"1. README.md — 项目简介、安装步骤、使用方法\n"
                f"2. API.md — 接口文档\n"
                f"3. ARCHITECTURE.md — 架构说明\n"
            )),
        ]
    })

    doc_artifacts = parse_doc_response(response["messages"][-1].content)

    return {
        "doc_artifacts": doc_artifacts,
        "stage": "done",
    }
```

#### deliver_node — 交付节点

```python
def deliver_node(state: DevTeamState) -> dict:
    """交付节点：汇总所有产物，生成项目报告。"""
    gate = evaluate_quality_gate(state)
    if not gate["passed"]:
        return {
            "approval_required": True,
            "quality_gate": gate,
            "messages": [AIMessage(content="质量门禁未通过，等待人工确认或重新修复。")],
        }

    project_dir = safe_project_dir(state["requirement"])

    # 写入代码文件
    for filepath, content in state["code_artifacts"].items():
        safe_write_artifact(project_dir, filepath, content)

    # 写入文档文件
    for filepath, content in state["doc_artifacts"].items():
        safe_write_artifact(project_dir, filepath, content)

    # 生成项目报告
    report = generate_delivery_report(state)

    return {
        "quality_gate": gate,
        "messages": [AIMessage(content=report)],
    }
```

`evaluate_quality_gate` 至少应检查：是否存在 CRITICAL/HIGH 问题、测试命令是否通过、文件路径是否合法、是否有 README、是否超过最大修复轮次。`safe_write_artifact` 必须在安全工作区内解析路径，禁止目录穿越和绝对路径。

### 5. 图的编译

```python
def build_dev_team_workflow():
    """构建多智能体协同开发工作流。"""
    workflow = StateGraph(DevTeamState)

    # 添加节点
    workflow.add_node("planner_node", planner_node)
    workflow.add_node("developer_node", developer_node)
    workflow.add_node("tester_node", tester_node)
    workflow.add_node("fixer_node", fixer_node)
    workflow.add_node("docwriter_node", docwriter_node)
    workflow.add_node("deliver_node", deliver_node)

    # 设置入口
    workflow.set_entry_point("planner_node")

    # 顺序边
    workflow.add_edge("planner_node", "developer_node")
    workflow.add_edge("docwriter_node", "deliver_node")
    workflow.add_edge("deliver_node", END)

    # 开发循环：逐任务执行
    workflow.add_conditional_edges(
        "developer_node",
        lambda s: "next_task" if s.get("task_queue") else "to_test",
        {"next_task": "developer_node", "to_test": "tester_node"}
    )

    # 测试后路由：无Bug→文档，有Bug→修复→重新测试
    workflow.add_conditional_edges(
        "tester_node",
        route_after_test,
        {
            "document": "docwriter_node",
            "document_with_issues": "docwriter_node",
            "fix": "fixer_node",
        }
    )
    workflow.add_edge("fixer_node", "tester_node")

    # 编译
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
```

---

## 第二部分：代码受控生成与自检

### 1. "写 → 查 → 改" 自检闭环

这是多智能体开发系统的核心循环——开发 Agent 写代码，测试 Agent 查代码，如果发现 Bug 则回传给开发 Agent 修改：

```
┌───────────────────────────────────────────────────────────┐
│                    自检闭环                                │
│                                                           │
│   开发Agent          测试Agent          开发Agent          │
│   (写代码)           (查代码)           (改代码)          │
│                                                           │
│   ┌──────┐          ┌──────┐          ┌──────┐          │
│   │ 编写  │ ──────► │ 审查  │ ──────► │ 修复  │          │
│   │ 代码  │         │ 代码  │  Bug    │ Bug  │          │
│   └──────┘          └──┬───┘          └──┬───┘          │
│                        │                  │              │
│                        │ 无Bug            │              │
│                        ▼                  │              │
│                   ┌──────┐                │              │
│                   │ 通过  │ ◄─────────────┘              │
│                   └──────┘  (修复后重测)                  │
│                                                           │
│   最多 3 轮修复循环，超过则附带问题清单继续交付            │
└───────────────────────────────────────────────────────────┘
```

### 2. 测试 Agent 的审查维度

测试 Agent 从五个维度审查代码：

```
审查维度金字塔:

          ┌──────────┐
          │  安全性   │  CRITICAL: 硬编码密钥、SQL 注入、命令注入
          └─────┬────┘
        ┌───────┴───────┐
        │    正确性      │  HIGH: 逻辑错误、类型错误、未处理的异常
        └───────┬───────┘
      ┌─────────┴─────────┐
      │      健壮性        │  MEDIUM: 边界条件、空值处理、竞态条件
      └─────────┬─────────┘
    ┌───────────┴───────────┐
    │       可维护性         │  LOW: 魔术数字、过长函数、复杂条件嵌套
    └───────────┬───────────┘
  ┌─────────────┴─────────────┐
  │         性能               │  LOW: N+1 查询、不必要的复制、低效算法
  └───────────────────────────┘
```

### 3. Bug 反馈的标准化格式

测试 Agent 发现的问题以结构化格式反馈给开发 Agent：

```python
BUG_REPORT_FORMAT = """
发现 {count} 个问题:

{bugs}

修复要求:
- CRITICAL 和 HIGH 级别的问题必须修复
- MEDIUM 级别的问题建议修复
- LOW 级别的问题可以暂不处理
- 修复时请输出完整的修改后文件，不要只输出 diff
- 每个修复说明修改了什么以及为什么
"""
```

### 4. 代码产物的解析与持久化

开发 Agent 的输出必须被解析为结构化的文件列表。不要依赖自由文本中的任意路径，也不要直接把模型输出写入磁盘。

```
开发 Agent 的原始输出:
```python
# 文件: models.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class TodoItem:
    id: str
    title: str
    done: bool = False
    created_at: str = ""
```

```python
# 文件: storage.py
import json
import os

def load_tasks(filepath: str) -> list:
    ...
```
```

解析函数将上述输出拆分为 `{文件名: 文件内容}` 的字典：

```python
def parse_code_response(response_text: str) -> dict:
    """解析开发 Agent 的结构化代码产物。

    推荐让模型输出 JSON:
    {
      "files": [
        {"path": "todo_app/models.py", "content": "...", "type": "code"}
      ]
    }
    """
    payload = json.loads(response_text)
    artifacts = {}
    for item in payload.get("files", []):
        path = validate_artifact_path(item["path"])
        content = item.get("content", "")
        if not content.strip():
            raise ValueError(f"空文件内容: {path}")
        artifacts[path] = content
    return artifacts
```

`validate_artifact_path` 至少要做三件事：禁止绝对路径、禁止 `..` 目录穿越、只允许写入本项目的输出工作区。这样即使模型输出了 `/etc/passwd` 或 `../../secrets.env`，交付节点也会拒绝。

---

## 第三部分：项目自动化交付闭环

### 1. 完整交付流程

```
用户输入需求
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ 规划Agent                                                    │
│ ├── 需求分析: 核心功能 + 非功能需求                           │
│ ├── 模块设计: 目录结构 + 职责划分                             │
│ ├── 任务拆解: 6-10 个开发任务 + 依赖排序                      │
│ └── 接口规范: 函数签名 + 数据模型                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 开发Agent (逐任务循环)                                        │
│ ├── T1: models.py — 数据模型定义                              │
│ ├── T2: storage.py — 文件存储层                               │
│ ├── T3: commands.py — 命令处理层                              │
│ └── T4: main.py — CLI 入口                                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 测试Agent                                                    │
│ ├── 语法审查: 类型注解缺失、导入错误                           │
│ ├── 逻辑审查: 边界条件、异常处理                               │
│ ├── 安全扫描: 硬编码路径、eval 使用                            │
│ └── 输出: 2 HIGH + 3 MEDIUM 问题                             │
└─────────────────────────┬───────────────────────────────────┘
                          │ (有 Bug)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 开发Agent (修复模式, Round 1)                                 │
│ ├── 修复 HIGH-1: storage.py 添加文件不存在时的异常处理          │
│ ├── 修复 HIGH-2: commands.py 删除操作增加 ID 校验             │
│ └── 修复 MEDIUM-1: main.py 添加 Ctrl+C 优雅退出              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 测试Agent (Round 2)                                          │
│ └── 输出: 0 HIGH + 1 LOW (通过)                               │
└─────────────────────────┬───────────────────────────────────┘
                          │ (无 Bug)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 文档Agent                                                    │
│ ├── README.md — 项目简介、安装、使用                          │
│ ├── API.md — 接口文档                                        │
│ └── ARCHITECTURE.md — 架构说明                                │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 交付节点                                                     │
│ ├── 写入代码文件到 data/output/todo_app/                      │
│ ├── 写入文档文件到 data/output/todo_app/                      │
│ └── 生成交付报告                                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
                    ✅ 项目待确认/已交付
```

### 2. 交付报告示例

```
📋 项目交付报告
═══════════════════════════════════════

项目: 待办事项管理应用
需求: 支持增删改查，数据存到本地文件

── 架构设计 ──
todo_app/
├── main.py          # CLI 入口
├── models.py        # TodoItem 数据模型
├── storage.py       # JSON 文件存储层
└── commands.py      # 命令处理层

── 代码产物 ──
✅ models.py     (32 行)  — 数据模型定义
✅ storage.py    (48 行)  — 文件读写 + 异常处理
✅ commands.py   (67 行)  — 增删改查命令
✅ main.py       (55 行)  — CLI 交互循环

── 测试结果 ──
Round 1: 2 HIGH + 3 MEDIUM 问题
Round 2: 0 HIGH + 1 LOW 问题 ✅ 通过

── 文档产物 ──
✅ README.md         — 项目简介与使用指南
✅ API.md            — 接口文档
✅ ARCHITECTURE.md   — 架构说明

── Agent 协作统计 ──
规划Agent: 1 轮 (任务拆解 + 架构设计)
开发Agent: 5 轮 (4 个任务 + 1 轮修复)
测试Agent: 2 轮 (首轮审查 + 修复后复查)
文档Agent: 1 轮 (README + API + 架构文档)

── 产出路径 ──
📁 data/output/todo_app/
═══════════════════════════════════════
```

### 3. CLI 交互设计

```
🤝 多智能体协同开发助手
================================

👥 团队成员:
  🧠 规划Agent — 需求分析、任务拆解、架构设计
  💻 开发Agent — 代码编写、接口实现、Bug 修复
  🔍 测试Agent — 代码审查、BUG 检测、安全扫描
  📝 文档Agent — 注释、API 文档、项目文档

系统命令:
  /team                 查看团队状态
  /history              查看执行历史
  /artifacts            查看当前产出物
  /quit                 退出

请输入项目需求开始开发:
```

### 4. 交互式执行示例

```
👤 用户 > 做一个待办事项管理应用，支持增删改查，数据存到本地文件

🧠 规划Agent 正在分析需求...
  ✅ 需求分析: 4 个核心功能点
  ✅ 模块设计: 4 个文件
  ✅ 任务拆解: 4 个开发任务
  ✅ 接口规范: 7 个函数签名

💻 开发Agent 开始编码...
  ✅ [T1] models.py — TodoItem 数据模型 (32 行)
  ✅ [T2] storage.py — JSON 文件读写 (48 行)
  ✅ [T3] commands.py — 增删改查命令 (67 行)
  ✅ [T4] main.py — CLI 入口循环 (55 行)

🔍 测试Agent 正在审查代码...
  ⚠️ 发现 5 个问题:
    HIGH: storage.py — 文件不存在时未处理 FileNotFoundError
    HIGH: commands.py — 删除操作未校验 ID 存在性
    MEDIUM: main.py — 缺少 Ctrl+C 优雅退出
    MEDIUM: storage.py — JSON 解析错误未捕获
    LOW: commands.py — list_all 建议支持过滤参数

💻 开发Agent 修复中 (Round 1)...
  ✅ 修复 HIGH: storage.py 添加 FileNotFoundError 处理
  ✅ 修复 HIGH: commands.py 添加 ID 校验
  ✅ 修复 MEDIUM: main.py 添加信号处理
  ✅ 修复 MEDIUM: storage.py 添加 JSON 解析异常处理

🔍 测试Agent 复查中 (Round 2)...
  ✅ 所有 HIGH/MEDIUM 问题已修复，1 个 LOW 问题暂留

📝 文档Agent 正在编写文档...
  ✅ README.md — 项目简介、安装步骤、使用方法
  ✅ API.md — 4 个模块的接口文档
  ✅ ARCHITECTURE.md — 架构说明与模块关系

📦 项目交付完成！
  📁 产出路径: data/output/todo_app/
  📊 代码: 4 文件, 202 行
  📄 文档: 3 文件
  🔧 修复: 1 轮, 4 个问题已修复
```

---

## 第四部分：2026 前沿扩展：长程开发 Agent 的工程边界

长程开发 Agent 指的是能跨越较长时间、多个步骤和多个工具持续工作的 Agent。它可能先读需求，再规划任务、检索文档、生成代码、运行测试、修复问题、写文档、等待人工审批，最后交付项目。这个方向在 2026 年很热，但工程上最容易出事故的也是这里。

### 1. 长程不等于放任自动化

一个短程 Agent 出错，通常只是一条回答不好；一个长程 Agent 出错，可能会连续执行几十个动作。风险包括：

- 无限循环：反复生成、测试、修复，消耗大量 token 和时间。
- 状态污染：上一轮错误计划或错误测试报告影响后续步骤。
- 副作用扩大：错误写文件、错误发送通知、错误提交代码。
- 上下文遗失：运行很久后忘记原始需求、约束和人工反馈。
- 责任不清：不知道是 Planner、Developer、Tester、工具还是人类审批环节导致失败。

所以长程 Agent 的核心不是“让模型多做几步”，而是让每一步都可暂停、可检查、可恢复、可审计。

### 2. 长程开发 Agent 必须有五类边界

| 边界 | 目的 | 本项目对应能力 |
|------|------|----------------|
| 状态边界 | 记录当前阶段、产物、测试报告和修复轮次 | `DevTeamState`、`run_id`、`fix_count` |
| 工具边界 | 限制读写、执行、网络和外部系统访问 | `validate_artifact_path`、白名单 unittest |
| 成本边界 | 限制最大轮次、最大 token、最大运行时间 | `MAX_FIX_ROUNDS` |
| 人工边界 | 高风险动作前暂停确认 | 计划确认、diff review、最终交付审批 |
| 观测边界 | 追踪每个 Agent 的输入、输出、耗时和错误 | `MessageBus.history()`、`ARTIFACTS_INDEX.json`、`DELIVERY_REPORT.md` |

生产系统还应补充真正的 checkpoint/resume。比如 Developer 生成代码后暂停等待人类 review，用户批准后从同一个 run 继续测试，而不是重新开始整个工作流。

### 3. Hooks 是长程 Agent 的运行时刹车

长程 Agent 运行时间越长，越不能只靠一开始的 System Prompt 约束。实际工程里，需要把关键节点做成 hooks，让运行时在每一步都能重新检查权限、预算、状态和风险。

在开发 Agent 场景中，常见 hooks 可以这样设计：

| Hook | 检查内容 | 失败时怎么处理 |
|------|----------|----------------|
| UserPromptSubmit | 用户需求是否含越权、危险命令或敏感数据 | 拒绝、脱敏、要求补充确认 |
| SessionStart / SubagentStart | 当前 run 的角色、工具、预算、工作目录是否正确 | 禁止启动或降级为只读模式 |
| PreToolUse | 文件路径、命令、网络、依赖安装、MCP 工具是否越界 | 阻止工具执行，写入审计 |
| PermissionRequest | 写文件、删文件、提交代码、发通知、导出数据是否需要人审 | 保存 checkpoint，等待人工决定 |
| PostToolUse | 工具结果是否异常、是否泄露敏感信息、是否需要补偿 | 追加反馈、触发修复、停止流程 |
| Stop / SubagentStop | 是否要保存摘要、成本、产物索引和下一步恢复点 | 生成 trace 和 checkpoint |

这和本项目现有边界是一致的：`MAX_FIX_ROUNDS` 是成本 hook，`validate_artifact_path()` 是写文件前 hook，`MessageBus.history()` 是审计 hook，测试失败后的修复循环是 post-test hook。课程没有把它们做成通用 HookManager，是为了先让学生看懂显式流程；生产版可以再把这些散点抽象成统一生命周期机制。

### 4. Sandbox 是长程开发 Agent 的底线

本项目的 `TesterAgent` 只运行白名单 `unittest`，并把生成项目写到临时目录。这是教学版的最低安全边界。生产版如果允许 Agent 运行命令、安装依赖、访问网络或修改真实仓库，就必须使用更强隔离：

- 容器或微虚拟机隔离工作目录。
- CPU、内存、磁盘、运行时间限制。
- 网络默认关闭，按需白名单开放。
- 凭证代理，不把真实密钥交给模型。
- 文件系统 ACL，禁止访问宿主机敏感路径。
- 每轮运行保留快照，便于 diff、回滚和复盘。

OpenAI Agents SDK 等新框架开始把 sandbox、files、tools、tracing 这些能力放进运行时，这是因为长程 Agent 的可靠性越来越依赖执行环境，而不是只依赖 prompt。

### 5. 本项目如何扩展到长程模式

如果要把本课升级为更接近真实开发助手，可以按这个顺序扩展：

1. `DevTeamResult` 增加更完整的 trace：每个节点开始/结束时间、输入摘要、输出摘要、错误。
2. `DeliveryManager` 交付前生成 diff，并支持人工确认。
3. 引入 checkpoint：保存 `plan`、`code_artifacts`、`test_report`、`fix_count`、`stage`。
4. 增加 `resume(run_id, decision)`：支持人工批准、驳回、补充反馈。
5. 把测试运行迁移到容器沙箱。
6. 为每类需求建立基准任务集，评估成功率、修复轮次、成本和人工介入率。

做到这些之前，不应把系统描述为“全自动软件工程师”。更准确的定位是：受控的开发工作流助手。

---

## 核心原理深度解析

### 多 Agent 系统的可扩展性

当前的四角色架构是针对"软件开发"场景设计的。但多 Agent 的编排模式是通用的——只需替换 System Prompt 和工具集，就能适配不同的业务场景：

| 场景 | 规划Agent | 执行Agent | 审查Agent | 输出Agent |
|------|----------|----------|----------|----------|
| 软件开发 | 架构师 | 开发工程师 | 测试工程师 | 技术文档 |
| 内容创作 | 主编 | 写手 | 编辑 | 排版 |
| 数据分析 | 数据架构师 | 数据工程师 | 质量分析师 | 报告撰写 |
| 法律审核 | 案情分析 | 条文检索 | 合规审查 | 法律意见书 |

核心模式不变：**拆解 → 执行 → 审查 → 修正 → 输出**。

### 反馈循环的最大轮次设计

为什么限制修复轮次为 3？

```
Round 1: 修复大部分问题（通常解决 70-80%）
Round 2: 修复剩余问题和 Round 1 引入的新问题
Round 3: 边际收益极低，大部分是 LOW 级别问题

超过 3 轮的原因通常是：
1. 架构设计有根本性缺陷 → 应该让规划 Agent 重新设计
2. LLM 对某个问题反复"修复-引入新问题" → 人工介入
3. 问题本身就是主观判断（如"代码风格"） → 不值得继续
```

3 轮是一个经验性的平衡点：既给了足够的纠错空间，又避免了无限循环。

### 代码产物解析的挑战

LLM 输出的代码不像 API 调用那样有严格的 JSON Schema。我们需要从自然语言中提取代码文件：

| 挑战 | 解决方案 |
|------|---------|
| LLM 输出格式不固定 | 在 Prompt 中明确要求"用 `# 文件: xxx.py` 标记" |
| 代码块嵌套 markdown | 正则匹配去除 ` ```python ``` ` 标记 |
| 单次输出多个文件 | 按文件标记分割 |
| 代码不完整（截断） | 检查花括号/缩进是否匹配，不完整则要求续写 |
| 文件路径不规范 | 统一为相对路径，去除特殊字符 |

### 多 Agent 与微服务架构的类比

多 Agent 系统的架构思想与微服务架构高度相似：

| 微服务概念 | 多 Agent 对应 |
|-----------|-------------|
| 服务实例 | Agent 实例 |
| API 接口 | System Prompt + 工具集 |
| 服务间通信 | MessageBus |
| API Gateway | LangGraph 工作流 |
| 服务发现 | ToolRegistry |
| 熔断降级 | 修复轮次限制 + 降级策略 |
| 链路追踪 | MessageBus 历史记录 |
| CI/CD | 自检闭环（写→查→改） |

理解这个类比有助于将微服务的最佳实践迁移到多 Agent 系统中。

---

## 课后练习

1. **完整项目实战**：输入一个中等复杂度的需求（如"Markdown 笔记管理应用，支持创建/搜索/标签/导出"），运行完整的开发流程，检查最终交付的代码是否可运行。

2. **修复轮次实验**：故意给开发 Agent 一个"有根本性架构缺陷"的任务，观察修复循环是否能发现并修正架构问题。如果 3 轮修复后问题依然存在，分析原因。

3. **Agent 通信追踪**：在一次完整的开发流程后，读取 MessageBus 的历史记录，统计各 Agent 之间的消息数量和类型，画出通信频率图。

4. **角色增减实验**：尝试去掉测试 Agent（直接从开发跳到文档），对比有无测试环节的代码质量差异。再尝试增加一个"性能优化 Agent"，观察对代码质量的影响。

5. **需求复杂度梯度**：分别输入简单需求（"计算器 CLI"）、中等需求（"待办事项应用"）、复杂需求（"Markdown 博客生成器"），观察规划 Agent 的任务拆解数量和开发 Agent 的代码行数是否随复杂度合理增长。

6. **Flake8 自检**：确保代码通过 `flake8 project_09_dev_team/` 的检查。
