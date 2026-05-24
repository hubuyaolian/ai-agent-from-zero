# Day 20 课程：自动化业务流程 Agent — 工具注册、任务拆解与统一调度 🏭

在前 19 天的课程中，我们掌握了 Agent 的核心能力：对话、工具调用、记忆、RAG 检索、ReAct 推理、任务规划、自我反思。但这些能力大多在"交互式对话"场景下使用——用户发一条消息，Agent 回复一次。

企业中存在大量**重复性固定工作**：每日数据汇总、周报生成、台账更新、日志巡检、消息推送。这些任务不需要人类"对话"，而是需要 Agent **自主拆解、自主调用工具、自主完成全流程**，甚至**定时自动执行**。

今天的课程将从一个全新的视角重新审视工具调用——从"对话中的工具"升级为"企业级工具注册中心"，从"单次 ReAct 循环"升级为"多步骤复杂流程的全自动执行链"。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：从交互式 Agent 到自动化流程 Agent](#第一部分从交互式-agent-到自动化流程-agent)
3. [第二部分：统一工具注册机制](#第二部分统一工具注册机制)
4. [第三部分：智能任务拆解与规划](#第三部分智能任务拆解与规划)
5. [核心原理深度解析](#核心原理深度解析)
6. [课后练习](#课后练习)

---

## 学习目标
- 理解交互式 Agent 与自动化流程 Agent 的架构差异。
- 掌握统一工具注册机制（ToolRegistry）：注册、校验、权限、分组。
- 掌握 LLM 驱动的任务拆解：将复杂指令分解为可执行子任务链。
- 理解执行计划（ExecutionPlan）的数据结构与流转机制。
- 实现文件处理、Excel 读写、数据清洗、消息推送等核心工具。

---

## 第一部分：从交互式 Agent 到自动化流程 Agent

### 1. 交互式 vs. 自动化的本质区别

| 维度 | 交互式 Agent (Day 5-7) | 自动化流程 Agent (Day 20-21) |
|------|----------------------|--------------------------|
| 触发方式 | 用户主动发消息 | 定时调度 / 事件触发 / 指令触发 |
| 执行模式 | 一问一答，用户确认后再继续 | 全自动执行，无需人工干预 |
| 任务复杂度 | 单次 1-3 步操作 | 多步骤长链路（5-15 步） |
| 容错要求 | 失败了可以问用户 | 必须自主重试、自主纠错 |
| 工具数量 | 3-5 个通用工具 | 10+ 个业务专用工具 |
| 输出形式 | 自然语言回复 | 结构化产物（报表、文件、消息） |

### 2. 企业日常重复性工作全景

```
企业日常重复性工作分类：

📊 数据类
├── 每日销售数据汇总
├── 周度业绩报表生成
├── 月度财务台账更新
└── 异常数据筛查与告警

📁 文件类
├── 日志文件定期归档
├── 过期文件清理
├── 文档格式批量转换
└── 模板文件自动填充

🔔 通知类
├── 每日站会提醒
├── 任务截止预警
├── 审批催办消息
└── 系统巡检结果推送

🔍 巡检类
├── 服务可用性检查
├── 磁盘/内存用量监控
├── 数据库慢查询排查
└── 安全日志审计
```

这些任务的共同特征：**流程固定、重复执行、规则明确**——正是 Agent 自动化的最佳切入点。

### 3. 自动化流程 Agent 的整体架构

```
┌──────────────────────────────────────────────────────────────┐
│              自动化业务流程调度 Agent 架构                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──── 调度层 ────┐                                          │
│  │ CronScheduler  │  定时调度（每天/每周/每月）                │
│  │ EventTrigger   │  事件触发（文件更新/消息到达）              │
│  │ ManualTrigger  │  手动触发（CLI 指令 / API 调用）           │
│  └───────┬────────┘                                          │
│          │ 触发执行                                           │
│          ▼                                                   │
│  ┌──── 规划层 ────┐                                          │
│  │ TaskPlanner    │  LLM 拆解复杂指令 → 子任务列表              │
│  │ ExecutionPlan  │  有序执行计划（含依赖关系）                  │
│  └───────┬────────┘                                          │
│          │ 按计划执行                                         │
│          ▼                                                   │
│  ┌──── 执行层 ────┐      ┌──── 工具层 ────┐                  │
│  │ WorkflowEngine │─────►│ ToolRegistry   │                  │
│  │ (LangGraph)    │      │ (统一注册中心)  │                  │
│  │                │      │                │                  │
│  │ planner_node   │      │ file_tools     │ 文件处理          │
│  │ executor_node  │      │ excel_tools    │ Excel 读写        │
│  │ validator_node │      │ data_tools     │ 数据清洗          │
│  │ reporter_node  │      │ text_tools     │ 文本处理          │
│  └───────┬────────┘      │ notify_tools   │ 消息推送          │
│          │               │ schedule_tools │ 定时任务          │
│          ▼               └────────────────┘                  │
│  ┌──── 容错层 ────┐                                          │
│  │ RetryHandler   │  自动重试（指数退避）                      │
│  │ ErrorLogger    │  异常日志记录                              │
│  │ FallbackRouter │  降级路由（工具 B 替代工具 A）             │
│  └────────────────┘                                          │
│                                                              │
│  ┌──── 产物层 ────┐                                          │
│  │ 报表文件        │  .xlsx / .csv / .pdf                     │
│  │ 汇总台账        │  SQLite / JSON                           │
│  │ 通知消息        │  企业微信 / 邮件 / 钉钉                   │
│  │ 执行日志        │  任务执行记录 + 异常追踪                   │
│  └────────────────┘                                          │
└──────────────────────────────────────────────────────────────┘
```

### 4. 目录结构设计

```
project_08_workflow_agent/
├── config.py                    # 项目配置
├── main.py                      # CLI 入口
├── tools/                       # 工具集
│   ├── __init__.py              # ALL_TOOLS 导出
│   ├── registry.py              # ToolRegistry 统一注册机制
│   ├── file_tools.py            # 文件处理（读/写/归档/清理）
│   ├── excel_tools.py           # Excel 读写（openpyxl）
│   ├── data_tools.py            # 数据清洗/统计/转换
│   ├── text_tools.py            # 文本提取/格式化
│   ├── notify_tools.py          # 消息推送（模拟企业微信/邮件）
│   └── schedule_tools.py        # 定时任务注册/查询
├── planner/                     # 任务规划
│   ├── __init__.py
│   └── task_planner.py          # TaskPlanner 任务拆解
├── executor/                    # 执行引擎
│   ├── __init__.py
│   └── workflow_engine.py       # LangGraph 执行引擎
├── reports/                     # 报表自动化
│   ├── __init__.py
│   └── report_generator.py      # 报表生成器
├── scheduler/                   # 定时调度
│   ├── __init__.py
│   └── task_scheduler.py        # 定时/触发调度器
├── error_handler/               # 异常处理
│   ├── __init__.py
│   └── retry.py                 # 容错重试机制
├── graph/                       # LangGraph 工作流
│   ├── __init__.py
│   ├── state.py                 # WorkflowState
│   └── workflow.py              # 多节点状态图
├── data/                        # 数据目录
│   ├── templates/               # 报表模板
│   └── output/                  # 输出产物
├── DAY20.md
├── DAY21.md
└── requirements.txt
```

---

## 第二部分：统一工具注册机制

### 1. 为什么需要 ToolRegistry？

在 Day 5-7 中，工具通过 `@tool` 装饰器定义，用 `ALL_TOOLS` 列表统一管理。这在工具少（3-5 个）时够用，但企业场景下工具数量可能达到 10-20 个，需要更系统化的管理：

| 痛点 | Day 5-7 方案 | ToolRegistry 方案 |
|------|-------------|------------------|
| 工具发现 | 手动维护 ALL_TOOLS 列表 | 自动注册，按名/分组查找 |
| 参数校验 | 依赖 LLM 生成的参数 | 注册时定义 schema + 运行时校验 |
| 权限控制 | 无 | 按工具组设置执行权限 |
| 工具分组 | 无 | 文件组/数据组/通知组/调度组 |
| 降级替换 | 不支持 | 注册替代工具，失败自动切换 |
| 执行日志 | 无 | 每次调用自动记录参数/结果/耗时 |

### 2. ToolRegistry 的设计

```python
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from langchain_core.tools import BaseTool


@dataclass
class ToolMeta:
    """工具元信息。"""
    name: str                          # 工具名
    group: str                         # 分组 (file/data/notify/schedule/text)
    description: str                   # 功能描述
    sensitive: bool = False            # 是否敏感（需要审批）
    fallback: Optional[str] = None     # 降级替代工具名
    rate_limit: int = 0                # 调用频率限制（次/分钟，0=不限）


class ToolRegistry:
    """统一工具注册中心。"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._metas: Dict[str, ToolMeta] = {}
        self._call_log: List[dict] = []

    def register(self, tool: BaseTool, group: str, sensitive: bool = False,
                 fallback: str = None, rate_limit: int = 0):
        """注册一个工具。"""
        meta = ToolMeta(
            name=tool.name,
            group=group,
            description=tool.description,
            sensitive=sensitive,
            fallback=fallback,
            rate_limit=rate_limit,
        )
        self._tools[tool.name] = tool
        self._metas[tool.name] = meta

    def get(self, name: str) -> Optional[BaseTool]:
        """按名称获取工具。"""
        return self._tools.get(name)

    def get_meta(self, name: str) -> Optional[ToolMeta]:
        """获取工具元信息。"""
        return self._metas.get(name)

    def list_by_group(self, group: str) -> List[BaseTool]:
        """按分组列出工具。"""
        return [
            self._tools[name]
            for name, meta in self._metas.items()
            if meta.group == group
        ]

    def list_all(self) -> List[BaseTool]:
        """列出所有已注册工具。"""
        return list(self._tools.values())

    def get_fallback(self, name: str) -> Optional[BaseTool]:
        """获取降级替代工具。"""
        meta = self._metas.get(name)
        if meta and meta.fallback:
            return self._tools.get(meta.fallback)
        return None

    def log_call(self, tool_name: str, args: dict, result: str,
                 success: bool, duration_ms: float):
        """记录工具调用日志。"""
        self._call_log.append({
            "tool": tool_name,
            "args": args,
            "result_preview": result[:200],
            "success": success,
            "duration_ms": duration_ms,
        })
```

### 3. 工具分组与注册

将工具按业务领域分组注册：

```python
def create_registry() -> ToolRegistry:
    """创建并初始化工具注册中心。"""
    registry = ToolRegistry()

    # ---- 文件处理组 ----
    registry.register(read_file, group="file")
    registry.register(write_file, group="file")
    registry.register(archive_files, group="file")
    registry.register(clean_expired, group="file", sensitive=True)

    # ---- Excel 处理组 ----
    registry.register(read_excel, group="data")
    registry.register(write_excel, group="data", sensitive=True)
    registry.register(merge_excel, group="data")
    registry.register(calc_statistics, group="data")

    # ---- 数据清洗组 ----
    registry.register(clean_data, group="data")
    registry.register(filter_rows, group="data")
    registry.register(transform_format, group="data")

    # ---- 文本处理组 ----
    registry.register(extract_text, group="text")
    registry.register(summarize_text, group="text")

    # ---- 消息推送组 ----
    registry.register(send_notification, group="notify", sensitive=True)
    registry.register(send_email, group="notify", sensitive=True)

    # ---- 定时任务组 ----
    registry.register(schedule_task, group="schedule", sensitive=True)
    registry.register(list_scheduled, group="schedule")

    return registry
```

### 4. 核心工具实现

#### 文件处理工具 (file_tools.py)

```python
@tool
def read_file(filepath: str) -> str:
    """读取指定文件的全部内容。

    Args:
        filepath: 文件的绝对或相对路径。

    Returns:
        文件内容字符串。
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


@tool
def write_file(filepath: str, content: str) -> str:
    """将内容写入指定文件。

    Args:
        filepath: 目标文件路径。
        content: 要写入的内容。

    Returns:
        操作结果描述。
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return f"文件写入成功: {filepath}"


@tool
def archive_files(source_dir: str, archive_dir: str, pattern: str = "*") -> str:
    """将源目录中匹配的文件归档到目标目录。

    Args:
        source_dir: 源文件目录。
        archive_dir: 归档目标目录。
        pattern: 文件匹配模式，默认 "*"。

    Returns:
        归档结果描述。
    """
    import shutil
    import glob
    os.makedirs(archive_dir, exist_ok=True)
    files = glob.glob(os.path.join(source_dir, pattern))
    for f in files:
        shutil.move(f, archive_dir)
    return f"已归档 {len(files)} 个文件到 {archive_dir}"


@tool
def clean_expired(directory: str, days: int = 30) -> str:
    """清理目录中超过指定天数的过期文件。

    Args:
        directory: 目标目录。
        days: 文件过期天数，默认 30 天。

    Returns:
        清理结果描述。
    """
    import time
    now = time.time()
    count = 0
    for f in os.listdir(directory):
        path = os.path.join(directory, f)
        if os.path.isfile(path):
            if now - os.path.getmtime(path) > days * 86400:
                os.remove(path)
                count += 1
    return f"已清理 {count} 个超过 {days} 天的过期文件"
```

#### Excel 处理工具 (excel_tools.py)

```python
@tool
def read_excel(filepath: str, sheet_name: str = None) -> str:
    """读取 Excel 文件内容，返回结构化摘要。

    Args:
        filepath: Excel 文件路径（.xlsx）。
        sheet_name: 工作表名称，默认读取第一个。

    Returns:
        包含列名、行数、前 5 行数据的摘要。
    """
    from openpyxl import load_workbook
    wb = load_workbook(filepath, read_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return "Excel 文件为空"
    headers = [str(c) for c in rows[0]]
    preview = rows[1:6]
    summary = f"工作表: {ws.title}\n列名: {headers}\n总行数: {len(rows) - 1}\n前5行:\n"
    for row in preview:
        summary += f"  {list(row)}\n"
    wb.close()
    return summary


@tool
def write_excel(filepath: str, headers: list, rows: list,
                sheet_name: str = "Sheet1") -> str:
    """将数据写入 Excel 文件。

    Args:
        filepath: 目标文件路径。
        headers: 列名列表。
        rows: 数据行列表（每行为值列表）。
        sheet_name: 工作表名称，默认 Sheet1。

    Returns:
        操作结果描述。
    """
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for row in rows:
        ws.append(row)
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    wb.save(filepath)
    return f"Excel 写入成功: {filepath} ({len(rows)} 行数据)"


@tool
def calc_statistics(filepath: str, column: str) -> str:
    """对 Excel 指定列计算统计指标（均值/最大/最小/计数）。

    Args:
        filepath: Excel 文件路径。
        column: 目标列名。

    Returns:
        统计结果描述。
    """
    from openpyxl import load_workbook
    wb = load_workbook(filepath, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(c) for c in rows[0]]
    col_idx = headers.index(column) if column in headers else -1
    if col_idx == -1:
        return f"未找到列: {column}"
    values = []
    for row in rows[1:]:
        try:
            values.append(float(row[col_idx]))
        except (TypeError, ValueError):
            continue
    if not values:
        return f"列 {column} 无有效数值"
    result = (
        f"列 {column} 统计:\n"
        f"  计数: {len(values)}\n"
        f"  均值: {sum(values) / len(values):.2f}\n"
        f"  最大: {max(values)}\n"
        f"  最小: {min(values)}\n"
        f"  总和: {sum(values):.2f}"
    )
    wb.close()
    return result
```

#### 消息推送工具 (notify_tools.py)

```python
@tool
def send_notification(title: str, content: str, channel: str = "wechat") -> str:
    """发送通知消息（模拟企业微信/钉钉推送）。

    Args:
        title: 通知标题。
        content: 通知内容。
        channel: 推送渠道 (wechat/email/dingtalk)，默认 wechat。

    Returns:
        发送结果描述。
    """
    # 学习阶段使用模拟推送，生产环境对接实际 API
    channel_names = {"wechat": "企业微信", "email": "邮件", "dingtalk": "钉钉"}
    ch = channel_names.get(channel, channel)
    # 模拟写入通知记录文件
    log_path = os.path.join("data", "output", "notifications.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{channel}] {title}: {content}\n")
    return f"✅ 通知已通过 {ch} 发送: {title}"
```

---

## 第三部分：智能任务拆解与规划

### 1. 从 ReAct 到 TaskPlanner

Day 11 的 ReAct 是"边想边做"——每一步决策都是局部的。Day 12 的 Planning 是"先规划后执行"——先制定全局计划再逐步执行。Day 20 的 TaskPlanner 将 Planning 模式与工具注册中心结合：

```
Day 11 ReAct:          Day 12 Planning:        Day 20 TaskPlanner:
思考 → 行动 → 观察     规划 → 逐步执行          拆解 → 校验 → 执行 → 验证
(局部决策)             (静态计划)               (动态校验+工具约束)
```

TaskPlanner 的独特之处：
1. **工具约束感知**：拆解时就知道有哪些工具可用，不会规划出"无法执行"的步骤
2. **参数校验**：每个步骤的参数在执行前就校验合法性
3. **依赖分析**：步骤间有明确的数据依赖关系（步骤 3 依赖步骤 1 的输出）

### 2. ExecutionPlan 数据结构

```python
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Step:
    """执行计划中的单个步骤。"""
    id: int                            # 步骤编号
    tool_name: str                     # 调用的工具名
    args: dict                         # 工具参数
    description: str                   # 步骤描述
    depends_on: List[int] = field(default_factory=list)  # 依赖的前置步骤 ID
    status: str = "pending"            # pending / running / done / failed / skipped
    result: Optional[str] = None       # 执行结果
    retry_count: int = 0               # 已重试次数


@dataclass
class ExecutionPlan:
    """完整的执行计划。"""
    goal: str                          # 用户原始目标
    steps: List[Step] = field(default_factory=list)
    current_step: int = 0              # 当前执行到第几步
    status: str = "created"            # created / running / done / failed
    created_at: str = ""               # 创建时间
```

### 3. TaskPlanner — LLM 驱动的任务拆解

```python
TASK_PLANNER_PROMPT = """
你是一个业务流程自动化专家。请将用户的指令拆解为可执行的步骤列表。

可用工具列表:
{tool_descriptions}

拆解规则:
1. 每个步骤必须使用上面列出的工具之一
2. 步骤参数必须符合工具的参数定义
3. 有依赖关系的步骤必须标注 depends_on
4. 步骤顺序必须满足依赖关系
5. 尽量减少步骤数量，避免冗余

用户指令: {instruction}

输出 JSON 格式:
{{
  "steps": [
    {{
      "id": 1,
      "tool_name": "工具名",
      "args": {{"参数名": "参数值"}},
      "description": "步骤描述",
      "depends_on": []
    }}
  ]
}}
"""
```

**拆解示例**：

```
用户指令: "读取今天的销售数据，汇总统计，生成日报，推送给管理层"

TaskPlanner 拆解结果:
┌─────┬──────────────┬────────────────────────────┬────────────┐
│ ID  │ 工具          │ 参数                       │ 依赖       │
├─────┼──────────────┼────────────────────────────┼────────────┤
│ 1   │ read_excel   │ filepath: "data/sales.xlsx"│ —          │
│ 2   │ calc_statistics│ filepath: "...", column: │ [1]        │
│     │              │ "金额"                      │            │
│ 3   │ write_excel  │ filepath: "reports/日报..." │ [2]        │
│     │              │ headers: [...], rows: [...] │            │
│ 4   │ send_notification│ title: "销售日报",      │ [3]        │
│     │              │ content: "详见附件"          │            │
└─────┴──────────────┴────────────────────────────┴────────────┘
```

### 4. 依赖解析与拓扑排序

步骤之间可能有依赖关系（步骤 3 依赖步骤 2 的输出）。TaskPlanner 使用拓扑排序确保步骤按正确的顺序执行：

```python
def resolve_execution_order(steps: List[Step]) -> List[Step]:
    """根据依赖关系进行拓扑排序，返回可执行的步骤顺序。"""
    # 构建依赖图
    in_degree = {s.id: len(s.depends_on) for s in steps}
    id_to_step = {s.id: s for s in steps}
    dependents = {s.id: [] for s in steps}
    for s in steps:
        for dep in s.depends_on:
            dependents[dep].append(s.id)

    # Kahn 算法拓扑排序
    queue = [sid for sid, deg in in_degree.items() if deg == 0]
    ordered = []
    while queue:
        sid = queue.pop(0)
        ordered.append(id_to_step[sid])
        for dep_id in dependents[sid]:
            in_degree[dep_id] -= 1
            if in_degree[dep_id] == 0:
                queue.append(dep_id)

    if len(ordered) != len(steps):
        raise ValueError("步骤依赖关系存在循环引用！")

    return ordered
```

### 5. 参数模板与动态填充

步骤的参数可能依赖前置步骤的输出。例如"生成日报"需要"统计结果"作为内容：

```python
# 参数模板语法: {{step_id.field}}
# 例如: {{2.result}} 表示步骤 2 的执行结果

def fill_step_args(step: Step, completed_steps: dict) -> dict:
    """填充步骤参数中的动态引用。"""
    filled = {}
    for key, value in step.args.items():
        if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
            ref = value[2:-2].strip()  # "2.result"
            step_id, field = ref.split(".", 1)
            ref_step = completed_steps.get(int(step_id))
            if ref_step:
                filled[key] = getattr(ref_step, field, value)
            else:
                filled[key] = value
        else:
            filled[key] = value
    return filled
```

---

## 核心原理深度解析

### ToolRegistry 与 Day 5 @tool 装饰器的关系

Day 5 的 `@tool` 装饰器解决的是"如何定义一个工具"的问题——它将 Python 函数转换为 LangChain 的 `BaseTool` 对象。

Day 20 的 `ToolRegistry` 解决的是"如何管理大量工具"的问题——它在 `@tool` 之上增加了注册、分组、校验、权限、降级、日志等企业级管理能力。

```
@tool 定义工具（函数 → BaseTool）
       │
       ▼
ToolRegistry 管理工具（注册/分组/校验/权限/降级/日志）
       │
       ▼
TaskPlanner 使用工具（感知可用工具集 → 生成合法执行计划）
       │
       ▼
WorkflowEngine 执行工具（按计划调用 → 容错重试 → 记录日志）
```

### 任务拆解的"工具约束感知"

TaskPlanner 与普通 LLM 规划的关键区别在于：**它知道有哪些工具可用**，因此生成的计划一定是"可执行的"。

普通 LLM 规划可能会生成：
```
Step 2: "在数据库中查询销售数据"  ← 没有数据库查询工具！
Step 3: "调用 Python 脚本分析"    ← 没有代码执行工具！
```

ToolPlanner 的 Prompt 中包含了完整的工具列表和参数定义，LLM 只能在这些工具范围内规划，确保每个步骤都可执行。

### 执行计划的依赖图本质

步骤间的依赖关系本质上是一个**有向无环图 (DAG)**。拓扑排序保证：
1. 被依赖的步骤先执行
2. 无依赖的步骤可以并行执行（Day 21 优化方向）
3. 循环依赖会被检测并报错

```
Step 1 (read_excel) ──────┬──────► Step 3 (write_excel)
                          │
Step 2 (calc_statistics) ─┘        Step 4 (send_notification) ◄── Step 3

拓扑排序结果: [1, 2, 3, 4] 或 [2, 1, 3, 4]（1 和 2 无依赖可并行）
```

---

## 课后练习

1. **ToolRegistry 功能扩展**：为 ToolRegistry 添加 `rate_limit` 频率限制功能——当某工具在 1 分钟内被调用超过指定次数时，自动排队等待。

2. **工具分组展示**：实现 `/tools` CLI 命令，按分组（文件/数据/文本/通知/调度）展示所有已注册工具及其描述。

3. **拆解质量对比**：分别使用"不提供工具列表"和"提供完整工具列表 + 参数定义"两种 Prompt，让 LLM 对同一个复杂指令进行拆解，对比生成的计划是否都可用。

4. **依赖图可视化**：使用 `graphviz` 或 Mermaid 将 ExecutionPlan 的步骤依赖关系导出为可视化图表。

5. **Flake8 自检**：确保代码通过 `flake8 project_08_workflow_agent/` 的检查。
