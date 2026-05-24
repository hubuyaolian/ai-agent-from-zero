# Day 21 课程：自动化业务流程 Agent — 执行引擎、容错重试与定时调度 ⚙️

在 Day 20 中，我们完成了自动化流程 Agent 的两大基础能力：**统一工具注册机制**（ToolRegistry）和**智能任务拆解**（TaskPlanner）。现在我们有了"工具库"和"计划书"，还缺一个"执行引擎"把计划变成现实。

今天的课程将实现三个核心能力：

1. **执行引擎**：用 LangGraph 编排"拆解 → 执行 → 校验 → 报告"的完整工作流，支持质量检查和自我纠错。
2. **容错重试**：工具调用失败时的指数退避重试、降级替代、异常日志。
3. **定时调度**：Cron 定时执行 + 事件触发，让 Agent 真正"无人值守"运行。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：LangGraph 执行引擎](#第一部分langgraph-执行引擎)
3. [第二部分：异常自主判断与容错重试](#第二部分异常自主判断与容错重试)
4. [第三部分：报表自动化实战](#第三部分报表自动化实战)
5. [第四部分：定时调度与触发式任务](#第四部分定时调度与触发式任务)
6. [第五部分：完整 CLI 应用](#第五部分完整-cli-应用)
7. [核心原理深度解析](#核心原理深度解析)
8. [课后练习](#课后练习)

---

## 学习目标
- 掌握 LangGraph 编排多步骤执行引擎的设计。
- 理解指数退避重试、降级路由和异常日志的实现。
- 实现日报/周报全自动生成流程。
- 掌握 Cron 定时调度与事件触发的实现。
- 构建完整的企业级业务流程自动化 CLI 应用。

---

## 第一部分：LangGraph 执行引擎

### 1. WorkflowState — 工作流状态定义

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class WorkflowState(TypedDict):
    """业务流程自动化工作流状态。"""
    messages: Annotated[list, add_messages]  # 对话消息
    instruction: str                         # 用户原始指令
    plan: dict                               # ExecutionPlan（步骤列表）
    current_step_index: int                  # 当前执行到的步骤索引
    step_results: list                       # 各步骤执行结果
    execution_log: list                      # 执行日志
    retry_count: int                         # 全局重试计数
    status: str                              # 整体状态: planning/executing/validating/done/failed
```

### 2. 4 节点执行图

```
START
  │
  ▼
┌──────────────┐
│ plan_node    │  LLM 拆解指令 → ExecutionPlan
└──────┬───────┘
       │
       ▼
┌──────────────┐     步骤执行完成？
│ execute_node │──────────────────────────► validate_node
│ (逐步骤执行) │                              │
└──────┬───────┘                              │
       │ 还有下一步骤                          │
       │ (回环执行)                            ▼
       │                              ┌──────────────┐
       └──────────────────────────────│ validate_node│
                                      │  (校验结果)   │
                                      └──────┬───────┘
                                             │
                                     ┌───────┴───────┐
                                     │               │
                              校验通过 ▼        校验失败 ▼
                            ┌──────────┐   ┌──────────────┐
                            │ report_  │   │ plan_node    │
                            │ node     │   │ (重新拆解)    │
                            └────┬─────┘   └──────┬───────┘
                                 │                │
                                 ▼                │ (最多重试 2 次)
                                END               │
                                                  └──► (回环)
```

### 3. 各节点实现

#### plan_node — 任务拆解节点

```python
def plan_node(state: WorkflowState) -> dict:
    """任务拆解：LLM 分析指令 → 生成 ExecutionPlan。"""
    # 从 ToolRegistry 获取可用工具描述
    tool_descriptions = format_tools_for_prompt(registry.list_all())

    # 调用 LLM 拆解
    plan_json = model.invoke(
        TASK_PLANNER_PROMPT.format(
            tool_descriptions=tool_descriptions,
            instruction=state["instruction"]
        )
    )

    # 解析为 ExecutionPlan
    plan = parse_plan(plan_json.content)

    return {
        "plan": plan,
        "current_step_index": 0,
        "step_results": [],
        "status": "executing",
    }
```

#### execute_node — 逐步骤执行节点

```python
def execute_node(state: WorkflowState) -> dict:
    """执行当前步骤：调用工具 → 记录结果 → 推进到下一步。"""
    steps = state["plan"]["steps"]
    idx = state["current_step_index"]

    if idx >= len(steps):
        return {"status": "validating"}

    step = steps[idx]
    tool = registry.get(step["tool_name"])
    if not tool:
        result = f"错误：工具 '{step['tool_name']}' 未注册"
        state["step_results"].append(result)
        state["execution_log"].append({
            "step": step["id"], "tool": step["tool_name"],
            "status": "failed", "error": "工具未注册"
        })
        return {
            "current_step_index": idx + 1,
            "step_results": state["step_results"],
            "execution_log": state["execution_log"],
        }

    # 填充动态参数
    filled_args = fill_step_args(step, state["step_results"])

    try:
        # 调用工具
        result = tool.invoke(filled_args)
        state["step_results"].append(result)
        state["execution_log"].append({
            "step": step["id"], "tool": step["tool_name"],
            "status": "success", "result_preview": str(result)[:200],
        })
    except Exception as e:
        # 容错处理（第二部分详解）
        result = handle_tool_error(step, e, state)
        state["step_results"].append(result)

    return {
        "current_step_index": idx + 1,
        "step_results": state["step_results"],
        "execution_log": state["execution_log"],
    }
```

#### validate_node — 校验节点

```python
VALIDATE_PROMPT = """
你是一个流程执行校验专家。请评估以下执行结果是否完成了用户的目标。

用户目标: {instruction}
执行步骤及结果: {results}

校验维度:
1. 完整性：是否所有必要步骤都执行了？
2. 正确性：步骤结果是否符合预期？
3. 目标达成：用户的目标是否完成？

输出:
SCORE: <1-10>
NEEDS_REPLAN: <YES/NO>
REASON: <简短说明>
"""

def validate_node(state: WorkflowState) -> dict:
    """校验执行结果是否达成目标。"""
    results_text = format_step_results(state["step_results"])
    evaluation = model.invoke(
        VALIDATE_PROMPT.format(
            instruction=state["instruction"],
            results=results_text,
        )
    )
    score = parse_score(evaluation.content)
    needs_replan = score < 6 and state["retry_count"] < MAX_RETRY

    if needs_replan:
        return {"status": "planning", "retry_count": state["retry_count"] + 1}

    return {"status": "done"}
```

#### report_node — 报告节点

```python
def report_node(state: WorkflowState) -> dict:
    """生成执行报告：汇总步骤结果 + 日志 → 格式化输出。"""
    report_lines = [f"📋 执行报告: {state['instruction']}\n"]
    for log in state["execution_log"]:
        status_icon = "✅" if log["status"] == "success" else "❌"
        report_lines.append(
            f"  {status_icon} Step {log['step']}: {log['tool']} — {log['status']}"
        )
    report = "\n".join(report_lines)
    return {"messages": [AIMessage(content=report)]}
```

### 4. 条件边路由

```python
def route_after_execute(state: WorkflowState) -> str:
    """执行节点后的路由判断。"""
    if state["status"] == "validating":
        return "validate"
    return "continue"  # 继续执行下一步

def route_after_validate(state: WorkflowState) -> str:
    """校验节点后的路由判断。"""
    if state["status"] == "planning":
        return "replan"
    return "report"

workflow.add_conditional_edges(
    "execute_node", route_after_execute,
    {"validate": "validate_node", "continue": "execute_node"}
)
workflow.add_conditional_edges(
    "validate_node", route_after_validate,
    {"replan": "plan_node", "report": "report_node"}
)
```

---

## 第二部分：异常自主判断与容错重试

### 1. 工具调用失败的常见场景

| 异常类型 | 示例 | 处理策略 |
|---------|------|---------|
| 文件不存在 | 读取的 Excel 文件路径错误 | 检查路径 → 提示 LLM 修正参数 |
| 格式错误 | 期望数字但列中含文本 | 跳过无效行 → 继续处理有效数据 |
| 权限不足 | 写入受保护目录 | 切换到可写目录 |
| 网络超时 | 消息推送 API 超时 | 指数退避重试 |
| 工具未注册 | LLM 规划了不存在的工具 | 降级到替代工具 |
| 参数缺失 | 必填参数为空 | 用默认值补全或跳过步骤 |

### 2. RetryHandler — 指数退避重试

```python
import time

class RetryHandler:
    """工具调用容错重试处理器。"""

    def __init__(self, max_retries=3, base_delay=1.0, max_delay=30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def execute_with_retry(self, tool, args: dict) -> str:
        """带指数退避重试的工具调用。"""
        for attempt in range(self.max_retries + 1):
            try:
                return tool.invoke(args)
            except Exception as e:
                if attempt >= self.max_retries:
                    return f"工具执行失败（已重试 {self.max_retries} 次）: {e}"
                delay = min(
                    self.base_delay * (2 ** attempt),
                    self.max_delay
                )
                time.sleep(delay)
        return "工具执行失败"

    def execute_with_fallback(self, tool_name: str, args: dict,
                              registry: ToolRegistry) -> str:
        """带降级替代的工具调用。"""
        tool = registry.get(tool_name)
        if tool is None:
            # 尝试降级替代
            fallback = registry.get_fallback(tool_name)
            if fallback:
                return f"[降级] {tool_name} → {fallback.name}: " + \
                       fallback.invoke(args)
            return f"工具 '{tool_name}' 未注册且无替代方案"

        result = self.execute_with_retry(tool, args)
        if "失败" in result:
            fallback = registry.get_fallback(tool_name)
            if fallback:
                return f"[主工具失败，降级执行] " + fallback.invoke(args)
        return result
```

**指数退避图示**：

```
重试次数:    0        1          2           3
等待时间:   1s      2s         4s          8s
            │       │          │           │
调用: ──X───┘───X──┘─────X───┘──────✓────┘
      失败    失败       失败        成功

公式: delay = min(base_delay × 2^attempt, max_delay)
```

### 3. ErrorLogger — 异常日志持久化

```python
import json
from datetime import datetime

class ErrorLogger:
    """异常日志记录器。"""

    def __init__(self, log_dir="data/output/logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def log(self, task_name: str, step_id: int, tool_name: str,
            error: str, action: str, detail: dict = None):
        """记录一条异常日志。"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task_name,
            "step_id": step_id,
            "tool": tool_name,
            "error": error,
            "action": action,  # retry / fallback / skip / abort
            "detail": detail or {},
        }
        log_file = os.path.join(
            self.log_dir,
            f"error_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_today_errors(self) -> list:
        """获取今天的所有异常日志。"""
        log_file = os.path.join(
            self.log_dir,
            f"error_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )
        if not os.path.exists(log_file):
            return []
        with open(log_file, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f]
```

---

## 第三部分：报表自动化实战

### 1. 日报全自动生成流程

这是最典型的企业自动化场景——将每天人工 1-2 小时的数据整理工作压缩为 Agent 30 秒自动完成：

```
用户指令: "生成今天的销售日报"

Agent 执行链路:
┌─────────────────────────────────────────────────────────────┐
│ Step 1: read_excel                                           │
│   输入: data/sales/daily_sales_2024-01-15.xlsx              │
│   输出: 读取到 256 行销售数据，列: 日期/产品/数量/金额/区域  │
├─────────────────────────────────────────────────────────────┤
│ Step 2: calc_statistics                                      │
│   输入: 同文件, 列="金额"                                    │
│   输出: 总额 ¥1,256,800 / 均值 ¥4,909 / 最大 ¥28,500       │
├─────────────────────────────────────────────────────────────┤
│ Step 3: calc_statistics                                      │
│   输入: 同文件, 列="数量"                                    │
│   输出: 总量 1,893 件 / 均值 7.4 件 / 最大 120 件           │
├─────────────────────────────────────────────────────────────┤
│ Step 4: write_excel                                          │
│   输入: reports/日报_2024-01-15.xlsx                         │
│   输出: 写入汇总表 (日期/总金额/总数量/均值/最大单笔)         │
├─────────────────────────────────────────────────────────────┤
│ Step 5: send_notification                                    │
│   输入: title="销售日报 2024-01-15"                          │
│         content="今日销售总额 ¥1,256,800，共 1,893 件..."     │
│   输出: ✅ 通知已通过企业微信发送                              │
└─────────────────────────────────────────────────────────────┘

⏱️ 总耗时: ~25 秒   (人工操作约 1-2 小时)
```

### 2. ReportGenerator — 报表生成器封装

```python
class ReportGenerator:
    """报表自动化生成器。"""

    def __init__(self, registry: ToolRegistry, model):
        self.registry = registry
        self.model = model

    def generate_daily_report(self, data_path: str, output_path: str,
                              notify: bool = True) -> str:
        """生成日报：读取数据 → 统计汇总 → 写入报表 → 推送通知。"""
        results = []

        # Step 1: 读取数据
        read_tool = self.registry.get("read_excel")
        data_summary = read_tool.invoke({"filepath": data_path})
        results.append(f"数据读取: {data_summary}")

        # Step 2: 统计汇总（自动识别数值列）
        stats_tool = self.registry.get("calc_statistics")
        # 让 LLM 从数据摘要中识别需要统计的列
        columns_prompt = f"从以下数据摘要中识别所有数值列名:\n{data_summary}\n只输出列名，逗号分隔。"
        columns_resp = self.model.invoke(columns_prompt)
        numeric_columns = [c.strip() for c in columns_resp.content.split(",")]

        stats_results = []
        for col in numeric_columns:
            stat = stats_tool.invoke({"filepath": data_path, "column": col})
            stats_results.append(stat)
        results.append("统计完成: " + "; ".join(stats_results))

        # Step 3: 写入报表
        write_tool = self.registry.get("write_excel")
        # 将统计结果转为表格数据
        headers, rows = self._stats_to_table(stats_results)
        write_result = write_tool.invoke({
            "filepath": output_path,
            "headers": headers,
            "rows": rows,
            "sheet_name": "汇总",
        })
        results.append(write_result)

        # Step 4: 推送通知
        if notify:
            notify_tool = self.registry.get("send_notification")
            notify_result = notify_tool.invoke({
                "title": f"日报已生成: {os.path.basename(output_path)}",
                "content": "\n".join(stats_results),
            })
            results.append(notify_result)

        return "\n".join(results)
```

### 3. 周报自动化

周报与日报的区别在于数据范围（7 天）和统计维度（同比/环比）：

```python
def generate_weekly_report(self, data_dir: str, output_path: str) -> str:
    """生成周报：合并 7 天数据 → 周度统计 → 环比计算 → 写入报表。"""
    # Step 1: 合并本周数据
    merge_tool = self.registry.get("merge_excel")
    merge_result = merge_tool.invoke({
        "source_dir": data_dir,
        "output_path": "data/temp_weekly.xlsx",
    })

    # Step 2: 统计本周数据
    # ... (类似日报统计)

    # Step 3: 读取上周数据并计算环比
    # ... (对比上周报表)

    # Step 4: 写入周报
    # ... (包含本周统计 + 环比变化)
```

---

## 第四部分：定时调度与触发式任务

### 1. 双模式调度架构

```
调度模式一: Cron 定时调度
┌─────────────────────────────┐
│ CronScheduler               │
│                             │
│ "0 9 * * 1-5"  → 生成日报   │  每个工作日 9:00
│ "0 17 * * 5"   → 生成周报   │  每周五 17:00
│ "0 0 1 * *"    → 月度归档   │  每月 1 号 0:00
│ "0 2 * * *"    → 日志清理   │  每天凌晨 2:00
└─────────────────────────────┘

调度模式二: 事件触发
┌─────────────────────────────┐
│ EventTrigger                │
│                             │
│ 文件更新 → 自动处理新数据    │  data/in/ 出现新文件
│ 消息指令 → 执行指定流程      │  收到 "run:report" 指令
│ 定时检查 → 异常数据告警      │  每 10 分钟检查一次
└─────────────────────────────┘
```

### 2. TaskScheduler — 定时调度器

```python
import schedule
import threading

class TaskScheduler:
    """任务调度器，支持 Cron 定时和事件触发。"""

    def __init__(self, workflow_engine):
        self.engine = workflow_engine
        self._scheduled_tasks = {}  # task_name → schedule.Job
        self._running = False

    def add_cron_task(self, name: str, cron_expr: str, instruction: str):
        """添加 Cron 定时任务。

        Args:
            name: 任务名称。
            cron_expr: Cron 表达式（简化版，仅支持 schedule 库格式）。
            instruction: 执行的指令。
        """
        # 解析简化的 cron 表达式
        # 示例: "daily 09:00" / "weekly mon 17:00" / "monthly 1 00:00"
        parts = cron_expr.split()
        if parts[0] == "daily":
            time_str = parts[1]
            job = schedule.every().day.at(time_str).do(
                self._run_task, name=name, instruction=instruction
            )
        elif parts[0] == "weekly":
            day_name = parts[1]  # mon/tue/wed/thu/fri/sat/sun
            time_str = parts[2]
            day_map = {
                "mon": schedule.every().monday,
                "tue": schedule.every().tuesday,
                "wed": schedule.every().wednesday,
                "thu": schedule.every().thursday,
                "fri": schedule.every().friday,
                "sat": schedule.every().saturday,
                "sun": schedule.every().sunday,
            }
            job = day_map[day_name].at(time_str).do(
                self._run_task, name=name, instruction=instruction
            )
        elif parts[0] == "monthly":
            # 月度任务（简化处理）
            job = schedule.every(30).days.do(
                self._run_task, name=name, instruction=instruction
            )
        else:
            raise ValueError(f"不支持的 cron 表达式: {cron_expr}")

        self._scheduled_tasks[name] = {
            "job": job,
            "instruction": instruction,
            "cron_expr": cron_expr,
        }

    def remove_task(self, name: str):
        """移除定时任务。"""
        if name in self._scheduled_tasks:
            schedule.cancel_job(self._scheduled_tasks[name]["job"])
            del self._scheduled_tasks[name]

    def list_tasks(self) -> list:
        """列出所有已注册的定时任务。"""
        return [
            {"name": name, "cron": info["cron_expr"],
             "instruction": info["instruction"]}
            for name, info in self._scheduled_tasks.items()
        ]

    def start(self):
        """启动调度循环（后台线程）。"""
        self._running = True
        thread = threading.Thread(target=self._schedule_loop, daemon=True)
        thread.start()

    def stop(self):
        """停止调度循环。"""
        self._running = False

    def _schedule_loop(self):
        """调度主循环。"""
        while self._running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

    def _run_task(self, name: str, instruction: str):
        """执行一个定时任务。"""
        print(f"⏰ 定时任务触发: {name}")
        try:
            result = self.engine.run(instruction)
            print(f"✅ 定时任务完成: {name}")
        except Exception as e:
            print(f"❌ 定时任务失败: {name} — {e}")
```

### 3. 事件触发器

```python
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class FileTriggerHandler(FileSystemEventHandler):
    """文件更新事件触发器。"""

    def __init__(self, workflow_engine, instruction_template: str):
        self.engine = workflow_engine
        self.instruction_template = instruction_template

    def on_created(self, event):
        """当新文件创建时触发。"""
        if event.is_directory:
            return
        filepath = event.src_path
        instruction = self.instruction_template.format(filepath=filepath)
        print(f"📂 文件触发: {filepath}")
        try:
            self.engine.run(instruction)
        except Exception as e:
            print(f"❌ 文件触发任务失败: {e}")


class EventTrigger:
    """事件触发管理器。"""

    def __init__(self, workflow_engine):
        self.engine = workflow_engine
        self._observers = []

    def watch_directory(self, dir_path: str, instruction_template: str):
        """监控目录，新文件创建时触发任务。

        Args:
            dir_path: 监控的目录路径。
            instruction_template: 指令模板，{filepath} 会被替换为实际文件路径。
        """
        handler = FileTriggerHandler(self.engine, instruction_template)
        observer = Observer()
        observer.schedule(handler, dir_path, recursive=False)
        observer.start()
        self._observers.append(observer)

    def stop_all(self):
        """停止所有监控。"""
        for obs in self._observers:
            obs.stop()
            obs.join()
```

---

## 第五部分：完整 CLI 应用

### 1. CLI 命令设计

```
🏭 自动化业务流程调度 Agent
================================

任务执行:
  直接输入指令           让 Agent 自动拆解并执行
  /run <指令>           同上（显式触发）
  /report daily         生成今日日报
  /report weekly        生成本周周报

任务调度:
  /schedule add <名称> <cron> <指令>   添加定时任务
  /schedule list                       列出所有定时任务
  /schedule remove <名称>              移除定时任务

工具管理:
  /tools                列出所有可用工具（按分组）
  /tools <组名>         列出指定分组的工具

执行历史:
  /history              查看最近执行记录
  /errors               查看今日异常日志

系统:
  /quit                 退出应用
```

### 2. 交互式执行示例

```
🏭 自动化业务流程调度 Agent
================================

👤 用户 > 读取今天的销售数据，统计汇总，生成日报，推送给管理层

📋 任务拆解中...
  Step 1: read_excel(filepath="data/sales/daily_sales.xlsx")
  Step 2: calc_statistics(filepath="data/sales/daily_sales.xlsx", column="金额")
  Step 3: calc_statistics(filepath="data/sales/daily_sales.xlsx", column="数量")
  Step 4: write_excel(filepath="reports/日报_2024-01-15.xlsx", ...)
  Step 5: send_notification(title="销售日报 2024-01-15", ...)

⚙️ 执行中...
  ✅ Step 1: read_excel — 读取 256 行数据
  ✅ Step 2: calc_statistics — 金额统计: 总额 ¥1,256,800
  ✅ Step 3: calc_statistics — 数量统计: 总量 1,893 件
  ✅ Step 4: write_excel — 日报写入成功
  ✅ Step 5: send_notification — 企业微信推送成功

🔍 校验结果: 8/10 — 目标已达成
📋 执行报告: 5/5 步骤成功，耗时 25 秒
```

### 3. 定时调度示例

```
👤 用户 > /schedule add daily_report "daily 09:00" "读取今天销售数据，统计汇总，生成日报，推送管理层"
✅ 定时任务已添加: daily_report (每天 09:00)

👤 用户 > /schedule list
📅 已注册的定时任务:
  1. daily_report    | 每天 09:00 | 读取今天销售数据，统计汇总...
  2. weekly_report   | 每周五 17:00 | 生成本周周报并推送...
  3. log_cleanup     | 每天 02:00 | 清理 30 天前的日志文件...
```

### 4. 异常处理示例

```
👤 用户 > /run 读取 data/missing.xlsx 的数据

📋 任务拆解中...
  Step 1: read_excel(filepath="data/missing.xlsx")

⚙️ 执行中...
  ❌ Step 1: read_excel — 文件不存在: data/missing.xlsx
  🔄 重试 1/3... (等待 1s)
  ❌ Step 1: read_excel — 文件不存在: data/missing.xlsx
  🔄 重试 2/3... (等待 2s)
  ❌ Step 1: read_excel — 文件不存在: data/missing.xlsx
  🔄 重试 3/3... (等待 4s)
  ❌ Step 1: read_excel — 重试耗尽，尝试降级替代...
  ⚠️ 无降级替代工具

🔍 校验结果: 2/10 — 目标未达成
📋 执行报告: 0/1 步骤成功，3 次重试失败
💡 建议: 请确认文件路径是否正确
```

---

## 核心原理深度解析

### 从 Day 12 Planning 到 Day 21 执行引擎的演进

| 维度 | Day 12 Planning Agent | Day 21 执行引擎 |
|------|---------------------|----------------|
| 规划方式 | LLM 自由规划 | 工具约束感知规划 |
| 执行单位 | 通用 ReAct 步骤 | 具名工具调用 |
| 容错机制 | Replanning（重新规划） | 指数退避重试 + 降级替代 |
| 参数处理 | LLM 自由生成 | Schema 校验 + 动态填充 |
| 执行日志 | 无 | 全链路日志持久化 |
| 调度能力 | 无 | Cron + 事件触发 |

### 指数退避的数学原理

为什么不用固定间隔重试？考虑两种策略对比：

```
固定间隔重试（间隔 2s）:
时刻: 0s  2s  4s  6s  8s
请求: X   X   X   X   X    ← 5 次请求集中在 8 秒内
                               如果是服务过载，会加剧问题

指数退避重试（base=1s）:
时刻: 0s  1s  3s  7s  15s
请求: X   X   X   X   X    ← 请求间隔逐渐增大
                               给服务恢复的时间窗口
```

指数退避的直觉：**失败越多次，越应该"等一等再试"**。因为连续失败往往意味着系统暂时不可用（网络波动、服务过载），立即重试只会加重负担。

### Cron 表达式与 schedule 库的映射

标准 Cron 表达式（5 字段）与 Python `schedule` 库的对应关系：

| Cron | 含义 | schedule 写法 |
|------|------|--------------|
| `0 9 * * 1-5` | 工作日 9:00 | `schedule.every().monday.at("09:00")` 等 |
| `0 17 * * 5` | 每周五 17:00 | `schedule.every().friday.at("17:00")` |
| `0 0 1 * *` | 每月 1 号 | `schedule.every(30).days` (近似) |
| `*/10 * * * *` | 每 10 分钟 | `schedule.every(10).minutes` |

我们使用简化版 cron（`daily/weekly/monthly + 时间`），降低学习门槛，同时覆盖最常见的业务调度场景。

### 企业级自动化的"三道防线"

```
第一道防线: 工具层容错
├── 参数校验（执行前检查参数合法性）
├── 指数退避重试（网络/超时类错误）
└── 降级替代（工具 A 失败 → 工具 B）

第二道防线: 流程层校验
├── 执行后校验（LLM 评估结果是否达标）
├── 重新规划（校验不通过 → 重新拆解执行）
└── 最大重试限制（防止无限循环）

第三道防线: 调度层监控
├── 执行日志持久化（记录每次调用的参数/结果/耗时）
├── 异常告警（连续失败 N 次后推送告警）
└── 人工兜底（极端情况下暂停调度，等待人工介入）
```

---

## 课后练习

1. **日报自动化实战**：准备一份模拟的 Excel 销售数据，运行日报生成流程，验证从数据读取到推送通知的完整链路。

2. **容错机制测试**：故意设置错误的文件路径（不存在的文件），观察 RetryHandler 的指数退避重试行为和最终降级处理。

3. **定时调度实验**：注册一个"每分钟执行一次"的定时任务（输出当前时间），观察 5 分钟内的调度执行情况。

4. **降级替代设计**：为 `read_excel` 工具注册一个降级替代（如 `read_csv`），当 Excel 文件读取失败时自动切换到 CSV 格式。

5. **事件触发实验**：配置目录监控，当新文件放入目录时自动触发数据处理流程。手动创建一个测试文件验证触发效果。

6. **Flake8 自检**：确保代码通过 `flake8 project_08_workflow_agent/` 的检查。
