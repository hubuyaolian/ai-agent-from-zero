# Day 20 课程：自动化业务流程 Agent — 工具注册、任务拆解与统一调度 🏭

在前 19 天的课程中，我们掌握了 Agent 的核心能力：对话、工具调用、记忆、RAG 检索、ReAct 推理、任务规划、自我反思。但这些能力大多在"交互式对话"场景下使用——用户发一条消息，Agent 回复一次。

企业中存在大量**重复性固定工作**：每日数据汇总、周报生成、台账更新、日志巡检、消息推送。这些任务不需要人类"对话"，而是需要 Agent **按预设边界拆解任务、调用工具、生成产物**，甚至**定时自动执行**。

今天的课程将从一个全新的视角重新审视工具调用——从"对话中的工具"升级为"企业级工具注册中心"，从"单次 ReAct 循环"升级为"多步骤复杂流程的可审计执行链"。

> 技术状态说明（2026）：LangGraph 仍是长时间、有状态 Agent 工作流的主流编排选择之一，不落后。但企业自动化不能只靠内存状态和简单重试。当前最佳实践强调 durable execution、checkpoint、trace、幂等副作用、审批中断、结构化计划校验和可恢复任务。Python `schedule` 库只适合本地教学和简单定时任务，生产调度应评估 APScheduler、Celery Beat、Prefect、Temporal 等方案。工具接入层也在协议化：MCP 已成为 Agent 连接外部工具和数据源的重要标准；Google ADK、PydanticAI、OpenAI Agents SDK 等框架则把工具、结构化输出、追踪和部署能力进一步产品化。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：从交互式 Agent 到自动化流程 Agent](#第一部分从交互式-agent-到自动化流程-agent)
3. [第二部分：统一工具注册机制](#第二部分统一工具注册机制)
4. [第三部分：智能任务拆解与规划](#第三部分智能任务拆解与规划)
5. [第四部分：2026 前沿扩展：MCP 与 Agent 框架生态](#第四部分2026-前沿扩展mcp-与-agent-框架生态)
6. [核心原理深度解析](#核心原理深度解析)
7. [课后练习](#课后练习)

---

## 学习目标
- 理解交互式 Agent 与自动化流程 Agent 的架构差异。
- 掌握统一工具注册机制（ToolRegistry）：注册、校验、权限、分组。
- 掌握 LLM 驱动的任务拆解：将复杂指令分解为可执行子任务链。
- 理解执行计划（ExecutionPlan）的数据结构与流转机制。
- 实现文件处理、CSV 读取统计、报表生成、消息推送等核心工具；Excel 读写作为可选扩展，不作为两日项目的硬依赖。
- 理解 MCP 与 ToolRegistry 的职责差异，以及 ADK、PydanticAI 等新框架和本项目的关系。

---

## 第一部分：从交互式 Agent 到自动化流程 Agent

### 1. 交互式 vs. 自动化的本质区别

| 维度 | 交互式 Agent (Day 5-7) | 自动化流程 Agent (Day 20-21) |
|------|----------------------|--------------------------|
| 触发方式 | 用户主动发消息 | 定时调度 / 事件触发 / 指令触发 |
| 执行模式 | 一问一答，用户确认后再继续 | 低风险任务可无人值守，敏感操作需审批或 dry-run |
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

这些任务的共同特征：**流程固定、重复执行、规则明确**——正是 Agent 自动化的最佳切入点。反过来，权限不清、结果不可验证、需要强业务判断的流程不适合直接全自动执行，应先做人机协同。

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
│  │ TaskPlanner    │  LLM/规则拆解指令 → 结构化子任务列表        │
│  │ ExecutionPlan  │  有序执行计划（含依赖关系）                  │
│  └───────┬────────┘                                          │
│          │ 按计划执行                                         │
│          ▼                                                   │
│  ┌──── 执行层 ────┐      ┌──── 工具层 ────┐                  │
│  │ WorkflowEngine │─────►│ ToolRegistry   │                  │
│  │ (LangGraph)    │      │ (统一注册中心)  │                  │
│  │                │      │                │                  │
│  │ planner_node   │      │ file_tools     │ 文件处理          │
│  │ executor_node  │      │ data_tools     │ CSV/统计          │
│  │ validator_node │      │ report_tools   │ 报表生成          │
│  │ reporter_node  │      │ text_tools     │ 文本处理          │
│  └───────┬────────┘      │ notify_tools   │ 消息推送          │
│          │               │ schedule_tools │ 定时任务          │
│          ▼               └────────────────┘                  │
│  ┌──── 容错层 ────┐                                          │
│  │ RetryHandler   │  自动重试（指数退避+jitter）                │
│  │ ErrorLogger    │  异常日志记录                              │
│  │ FallbackRouter │  降级路由（工具 B 替代工具 A）             │
│  │ ApprovalGate   │  敏感工具审批 / dry-run                    │
│  └────────────────┘                                          │
│                                                              │
│  ┌──── 产物层 ────┐                                          │
│  │ 报表文件        │  .csv / .xlsx(可选) / .pdf(可选)          │
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
│   ├── data_tools.py            # CSV 读取/统计/转换
│   ├── notify_tools.py          # 消息推送（模拟企业微信/邮件）
├── planner/                     # 任务规划
│   ├── __init__.py
│   ├── models.py                # Step / ExecutionPlan
│   ├── plan_validator.py        # 计划校验与拓扑排序
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
├── governance/                  # 权限、审批与审计
│   ├── __init__.py
│   ├── policy.py                # UserContext / ToolPolicy
│   └── audit_log.py             # JSONL 执行审计
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
| 权限控制 | 无 | 按工具组/工具名/用户角色执行权限 |
| 工具分组 | 无 | 文件组/数据组/通知组/调度组 |
| 降级替换 | 不支持 | 注册替代工具，失败自动切换 |
| 执行日志 | 无 | 每次调用自动记录参数/结果/耗时 |
| 审批与 dry-run | 无 | 敏感工具默认先生成计划，不直接执行 |

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
    args_schema: dict = field(default_factory=dict)  # 参数 JSON Schema
    sensitive: bool = False            # 是否敏感（需要审批或 dry-run）
    allowed_roles: List[str] = field(default_factory=lambda: ["user"])
    fallback: Optional[str] = None     # 降级替代工具名
    rate_limit: int = 0                # 调用频率限制（次/分钟，0=不限）
    idempotent: bool = True            # 重试是否安全
    timeout_seconds: int = 30          # 工具超时时间


class ToolRegistry:
    """统一工具注册中心。"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._metas: Dict[str, ToolMeta] = {}
        self._call_log: List[dict] = []

    def register(self, tool: BaseTool, group: str, sensitive: bool = False,
                 fallback: str = None, rate_limit: int = 0,
                 allowed_roles: List[str] = None, idempotent: bool = True):
        """注册一个工具。"""
        meta = ToolMeta(
            name=tool.name,
            group=group,
            description=tool.description,
            args_schema=tool.args_schema.schema() if tool.args_schema else {},
            sensitive=sensitive,
            allowed_roles=allowed_roles or ["user"],
            fallback=fallback,
            rate_limit=rate_limit,
            idempotent=idempotent,
        )
        self._tools[tool.name] = tool
        self._metas[tool.name] = meta

    def validate_args(self, name: str, args: dict) -> tuple[bool, str]:
        """执行前校验参数。教学版做必填字段检查，生产版应使用 Pydantic/JSON Schema。"""
        meta = self._metas[name]
        required = meta.args_schema.get("required", [])
        missing = [field for field in required if field not in args]
        if missing:
            return False, f"缺少必填参数: {missing}"
        return True, ""

    def can_execute(self, name: str, user_roles: List[str]) -> bool:
        """检查当前用户角色是否允许执行工具。"""
        meta = self._metas[name]
        return bool(set(meta.allowed_roles) & set(user_roles))

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
            "args_preview": str(args)[:200],
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
    registry.register(write_file, group="file", sensitive=True, idempotent=True)
    registry.register(archive_files, group="file", sensitive=True, idempotent=False)
    registry.register(clean_expired, group="file", sensitive=True, idempotent=False)

    # ---- CSV / 数据处理组 ----
    registry.register(read_csv_summary, group="data")
    registry.register(calc_csv_statistics, group="data")
    registry.register(generate_daily_report, group="report", sensitive=True, idempotent=True)

    # ---- 消息推送组 ----
    registry.register(send_notification, group="notify", sensitive=True, idempotent=False)
    registry.register(send_email, group="notify", sensitive=True, idempotent=False)

    return registry
```

### 4. 核心工具实现

#### 文件处理工具 (file_tools.py)

文件工具是自动化 Agent 中风险最高的一类。教学版必须限制在项目 `data/` 和 `reports/` 目录内，生产系统还应使用对象存储权限、操作审计和审批流。不要让 LLM 直接读写任意绝对路径。

```python
SAFE_ROOTS = ["data", "reports"]

def resolve_safe_path(filepath: str) -> str:
    """将路径限制在允许目录内，防止路径穿越和误删。"""
    path = os.path.abspath(filepath)
    allowed = [os.path.abspath(root) for root in SAFE_ROOTS]
    if not any(path.startswith(root + os.sep) or path == root for root in allowed):
        raise PermissionError(f"路径不在允许目录内: {filepath}")
    return path


@tool
def read_file(filepath: str) -> str:
    """读取指定文件的全部内容。

    Args:
        filepath: 文件的绝对或相对路径。

    Returns:
        文件内容字符串。
    """
    filepath = resolve_safe_path(filepath)
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
    filepath = resolve_safe_path(filepath)
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
    source_dir = resolve_safe_path(source_dir)
    archive_dir = resolve_safe_path(archive_dir)
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
    directory = resolve_safe_path(directory)
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

#### CSV 数据工具 (data_tools.py)

```python
@tool
def read_csv_summary(filepath: str, preview_rows: int = 5) -> str:
    """读取 CSV 文件内容，返回结构化摘要。

    Args:
        filepath: CSV 文件路径。
        preview_rows: 预览行数。

    Returns:
        包含列名、行数、前 5 行数据的摘要。
    """
    import csv
    filepath = resolve_safe_path(filepath)
    with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []
    return f"列名: {headers}\n总行数: {len(rows)}\n预览: {rows[:preview_rows]}"


@tool
def calc_csv_statistics(filepath: str, column: str | None = None) -> str:
    """对 CSV 数值列计算统计指标（均值/最大/最小/计数）。

    Args:
        filepath: CSV 文件路径。
        column: 目标列名；为空则自动扫描所有数值列。

    Returns:
        统计结果描述。
    """
    import csv
    filepath = resolve_safe_path(filepath)
    with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []
    candidate_columns = [column] if column else headers
    lines = []
    for col in candidate_columns:
        values = []
        for row in rows:
            try:
                values.append(float(str(row.get(col, "")).replace(",", "")))
            except ValueError:
                continue
        if values:
            lines.append(
                f"{col}: count={len(values)}, sum={sum(values):.2f}, "
                f"avg={sum(values) / len(values):.2f}, min={min(values)}, max={max(values)}"
            )
    return "\n".join(lines) if lines else "未找到可统计的数值列"
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
1. **工具约束感知**：拆解时知道有哪些工具可用，但生成结果仍必须二次校验
2. **参数校验**：每个步骤的参数在执行前就校验合法性
3. **依赖分析**：步骤间有明确的数据依赖关系（步骤 3 依赖步骤 1 的输出）
4. **审批感知**：敏感工具默认进入 pending_approval 或 dry-run，而不是直接执行

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
    requires_approval: bool = False    # 是否需要人工审批
    idempotency_key: str = ""          # 幂等键，避免重复副作用


@dataclass
class ExecutionPlan:
    """完整的执行计划。"""
    goal: str                          # 用户原始目标
    steps: List[Step] = field(default_factory=list)
    current_step: int = 0              # 当前执行到第几步
    status: str = "created"            # created / running / done / failed
    created_at: str = ""               # 创建时间
    plan_hash: str = ""                # 计划 hash，用于审计和复现
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
5. 涉及写文件、删除、归档、通知、调度的步骤必须标记 requires_approval=true
6. 每个产生副作用的步骤必须提供 idempotency_key
7. 尽量减少步骤数量，避免冗余

用户指令: {instruction}

输出 JSON 格式:
{{
  "steps": [
    {{
      "id": 1,
      "tool_name": "工具名",
      "args": {{"参数名": "参数值"}},
      "description": "步骤描述",
      "depends_on": [],
      "requires_approval": false,
      "idempotency_key": "稳定幂等键"
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
│ 1   │ read_csv_summary│ filepath: "data/sales.csv"│ —        │
│ 2   │ calc_csv_statistics│ filepath: "data/sales.csv"│ [1]   │
│ 3   │ generate_daily_report│ data_path/output_path │ [2]      │
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

## 第四部分：2026 前沿扩展：MCP 与 Agent 框架生态

本项目的 `ToolRegistry` 是一个本地教学版工具治理中心：注册工具、声明参数、标记敏感操作、控制角色、记录调用日志。到了生产系统，工具不一定都写在同一个 Python 进程里，可能分布在内部 API、SaaS、数据库、文件系统、消息平台和工作流平台中。这时需要把“工具接入协议”和“工具治理策略”分开看。

### 1. MCP 与 ToolRegistry 的区别

MCP（Model Context Protocol）解决的是“AI 应用如何用统一协议连接外部工具和上下文”。它可以把文件系统、GitHub、数据库、搜索服务、内部系统封装成 MCP server；Agent 或应用作为 MCP client 连接这些 server，并按协议发现工具、读取资源、获取 prompt 或调用能力。

ToolRegistry 解决的是本项目内部的“哪些工具可用、谁能调用、是否敏感、能否重试、如何审计”。两者关系可以这样理解：

```
MCP Server / API / 本地函数
          ↓ 暴露工具能力
ToolRegistry 或工具网关
          ↓ 加权限、审批、幂等、限流、审计
WorkflowEngine
          ↓ 按 ExecutionPlan 调用
业务产物 / 通知 / 报表
```

因此，MCP 不能替代 `ToolRegistry` 的治理职责。即使工具来自 MCP server，也仍然需要：

- tool filtering：只暴露当前工作流允许的工具。
- approval policy：敏感工具必须审批或 dry-run。
- idempotency：通知、归档、删除这类副作用不能盲目重试。
- tracing：记录每次工具发现、调用、失败、降级和恢复。
- secret isolation：MCP server 和 Agent 都不应直接暴露企业凭证。

### 2. MCP Server 设计时要问的问题

如果把本项目的工具改造成 MCP server，至少要回答：

| 问题 | 工程含义 |
|------|----------|
| 暴露哪些工具 | 不要把所有内部 API 一次性暴露给 Agent |
| 参数 schema 如何定义 | 结构化、可校验、可版本化 |
| 调用在哪里执行 | 本地 stdio、远程 HTTP、托管 connector 的安全边界不同 |
| 是否需要审批 | 删除、写文件、发通知、外发数据默认敏感 |
| 如何审计 | 记录调用者、参数摘要、结果摘要、耗时、错误、trace id |
| 如何限流 | 防止循环调用或高成本工具被误触发 |

这和本课 `ToolMeta` 中的 `required_args`、`sensitive`、`allowed_roles`、`idempotent`、`rate_limit`、`timeout_seconds` 是同一组治理问题，只是 MCP 把工具接入标准化了。

仓库中提供了一个可选示例：`project_08_workflow_agent/examples/mcp_tool_adapter_demo.py`。它用简化版 MCP tool descriptor 演示如何把外部工具描述注册进 `ToolRegistry`，并继续由 `ToolRegistry` 控制权限、敏感工具、参数校验和审计日志。

### 3. 新 Agent 框架生态怎么看

2025-2026 年出现了更多“带工程约束”的 Agent 框架。它们和本项目不是对立关系，而是提供了不同层级的能力：

| 框架/方向 | 关注点 | 与本项目的对应关系 |
|-----------|--------|--------------------|
| OpenAI Agents SDK | tools、handoffs、sessions、tracing、MCP、sandbox | 可替换部分 Runner / 工具调用 / 追踪能力 |
| Google ADK | 企业级 Agent 构建、调试、部署，多语言生态 | 可作为生产部署和企业集成框架参考 |
| PydanticAI | 类型安全、结构化输出、依赖注入、eval、observability | 可强化 `ExecutionPlan`、Step 输出和工具 schema |
| LangGraph | 有状态图、条件路由、checkpoint、人类审批 | 可替换本地顺序 `WorkflowEngine` |
| Temporal / Prefect | durable execution、任务重试、调度、补偿 | 可承接长时间业务流程的可靠执行 |

学习时不要陷入“哪个框架最好”的问题。更重要的是判断：你的系统需要的是类型安全、工具协议、状态图、durable execution、沙箱、还是部署控制台。框架只是承载这些工程边界的工具。

### 4. 长程流程 Agent 的新增风险

企业流程 Agent 一旦从“几步工具调用”变成“长时间运行的自动化流程”，风险会显著增加：

- 状态膨胀：中间结果、审批状态、工具输出都可能变大且含敏感信息。
- 副作用难回滚：文件移动、消息发送、外部系统写入不是简单重跑就能恢复。
- 成本失控：循环规划、重复检索、重复通知会放大 API 和基础设施成本。
- 责任归因困难：失败可能来自 planner、validator、tool、retry、approval、scheduler 任一环节。

本项目用 `ExecutionPlan`、`PlanValidator`、`ToolRegistry`、`RetryHandler`、`CheckpointStore` 和 `AuditLog` 建立的是最小工程骨架。生产系统可以换框架，但这些边界不能省。

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

TaskPlanner 与普通 LLM 规划的关键区别在于：**它知道有哪些工具可用**，因此更容易生成可执行计划。但这不是安全保证，LLM 仍可能输出错误 JSON、错误参数或不合理依赖，所以必须经过 `PlanValidator` 校验。

普通 LLM 规划可能会生成：
```
Step 2: "在数据库中查询销售数据"  ← 没有数据库查询工具！
Step 3: "调用 Python 脚本分析"    ← 没有代码执行工具！
```

ToolPlanner 的 Prompt 中包含了完整的工具列表和参数定义，但真正的可执行性来自运行时校验：

```python
class PlanValidator:
    """校验工具是否存在、参数是否完整、依赖是否成环、敏感步骤是否审批。"""

    def validate(self, plan: ExecutionPlan, registry: ToolRegistry) -> list[str]:
        errors = []
        tool_names = {tool.name for tool in registry.list_all()}
        step_ids = {step.id for step in plan.steps}
        for step in plan.steps:
            if step.tool_name not in tool_names:
                errors.append(f"未知工具: {step.tool_name}")
            for dep in step.depends_on:
                if dep not in step_ids:
                    errors.append(f"步骤 {step.id} 依赖不存在的步骤 {dep}")
            ok, reason = registry.validate_args(step.tool_name, step.args)
            if not ok:
                errors.append(f"步骤 {step.id} 参数错误: {reason}")
        resolve_execution_order(plan.steps)  # 如果成环会抛错
        return errors
```

### 执行计划的依赖图本质

步骤间的依赖关系本质上是一个**有向无环图 (DAG)**。拓扑排序保证：
1. 被依赖的步骤先执行
2. 无依赖的步骤可以并行执行（Day 21 优化方向）
3. 循环依赖会被检测并报错

```
Step 1 (read_csv_summary) ───┬────► Step 3 (generate_daily_report)
                             │
Step 2 (calc_csv_statistics) ─┘     Step 4 (send_notification) ◄── Step 3

拓扑排序结果: [1, 2, 3, 4] 或 [2, 1, 3, 4]（1 和 2 无依赖可并行）
```

---

## 课后练习

1. **ToolRegistry 功能扩展**：为 ToolRegistry 添加 `rate_limit` 频率限制功能——当某工具在 1 分钟内被调用超过指定次数时，自动排队等待。

2. **工具分组展示**：实现 `/tools` CLI 命令，按分组（文件/数据/文本/通知/调度）展示所有已注册工具及其描述。

3. **拆解质量对比**：分别使用"不提供工具列表"和"提供完整工具列表 + 参数定义"两种 Prompt，让 LLM 对同一个复杂指令进行拆解，对比生成的计划是否都可用。

4. **依赖图可视化**：使用 `graphviz` 或 Mermaid 将 ExecutionPlan 的步骤依赖关系导出为可视化图表。

5. **Flake8 自检**：确保代码通过 `flake8 project_08_workflow_agent/` 的检查。
