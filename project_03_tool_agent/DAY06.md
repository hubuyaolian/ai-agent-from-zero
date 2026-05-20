# Day 6 课程：丰富工具集与 Agent 工具调用循环 🔄

在 Day 5 中，我们理解了 Function Calling 的底层协议，并学会了用 `@tool` 快速定义工具、用 `bind_tools()` 将工具绑定到模型。但那时候我们的"闭环"还是手动拼凑的——手动判断 `tool_calls`、手动执行、手动拼回消息列表。

今天我们要解决两个关键问题：
1. **工具集的丰富与工程化组织**：一个真正有用的 Agent 需要具备多种工具能力（搜索、文件操作、代码执行、系统查询等），如何将这些工具干净地组织起来？
2. **自动化的 Agent Loop（智能体循环）**：如何让 Agent 自主地、循环地调用工具，直到它认为任务已经完成为止？

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：构建丰富的工具集](#第一部分构建丰富的工具集)
3. [第二部分：Agent 工具调用循环 (Agent Loop)](#第二部分agent-工具调用循环-agent-loop)
4. [第三部分：错误处理与重试机制](#第三部分错误处理与重试机制)
5. [核心原理深度解析](#核心原理深度解析)
6. [课后练习](#课后练习)

---

## 学习目标
- 学会按功能域组织工具代码（`tools/` 目录分模块管理）。
- 掌握 Agent Loop 的完整实现：感知 → 推理 → 工具调用 → 结果反馈 → 再推理 → ... → 最终回答。
- 理解工具调用中的异常处理策略：超时、参数错误、工具执行失败等场景的容错机制。
- 理解"多轮工具调用"的本质——大模型可能需要连续调用多个工具才能完成一个复杂任务。

---

## 第一部分：构建丰富的工具集

### 1. 工具的工程化组织

当工具数量增多后，把所有工具都写在一个文件里会变得非常混乱。推荐按**功能域**将工具拆分到 `tools/` 目录下的独立模块中：

```
project_03_tool_agent/
├── tools/
│   ├── __init__.py            # 统一导出所有工具
│   ├── calculator.py          # 数学计算工具
│   ├── web_search.py          # 网络搜索工具（模拟）
│   ├── file_ops.py            # 文件读写工具
│   ├── system_info.py         # 系统信息工具
│   └── code_executor.py       # Python 代码执行工具（沙箱）
├── 04_agent_loop.py           # 完整的 Agent 循环
└── 05_error_handling.py       # 错误处理与重试
```

在 `tools/__init__.py` 中统一导出，方便主程序一行导入所有工具：
```python
from tools.calculator import calculate
from tools.web_search import web_search
from tools.file_ops import read_file, write_file, list_directory
from tools.system_info import get_system_time, get_system_info
from tools.code_executor import execute_python

# 统一的工具列表，方便一次性绑定到模型
ALL_TOOLS = [
    calculate,
    web_search,
    read_file, write_file, list_directory,
    get_system_time, get_system_info,
    execute_python,
]
```

### 2. 各工具设计详解

#### 📐 计算器工具 (`calculator.py`)
- **功能**：接收一个数学表达式字符串，返回精确计算结果。
- **为什么需要**：大模型做数学运算经常出错（例如会算错多位数乘法），把精确计算委托给 Python 可以确保 100% 正确。
- **安全考量**：使用 Python 内置的 `ast.literal_eval` 或受限的 `eval` 执行表达式，避免恶意代码注入。

#### 🔍 网络搜索工具 (`web_search.py`)
- **功能**：模拟搜索引擎，根据关键词返回相关信息。
- **为什么需要**：大模型的知识存在截止日期（Knowledge Cutoff），无法回答实时问题（如今天的新闻、当前股价等）。
- **学习阶段策略**：先用模拟数据演示调用流程，后续可以替换为真实的搜索 API（如 Tavily、SerpAPI 等）。

#### 📁 文件操作工具 (`file_ops.py`)
- **功能**：支持读文件、写文件、列出目录内容。
- **为什么需要**：让 Agent 能够与本地文件系统交互，例如"帮我读取 config.json 的内容"或"把这段代码写入 output.py"。
- **安全考量**：限制可操作的路径范围，防止 Agent 误删系统关键文件。

#### ⏰ 系统信息工具 (`system_info.py`)
- **功能**：获取当前时间、操作系统信息、CPU/内存使用率等。
- **为什么需要**：这些是大模型无法自行获取的实时运行环境信息。

#### 🐍 代码执行工具 (`code_executor.py`)
- **功能**：接收一段 Python 代码字符串，在受限沙箱中执行并返回输出结果。
- **为什么需要**：让 Agent 具备"写代码并运行"的能力，是实现编程助手的基础。
- **安全考量**：设置执行超时（如 5 秒）、禁用危险模块（`os.system`、`subprocess` 等）、限制内存使用。

> 📖 **代码实战**：查看 `tools/` 目录下的各工具模块

---

## 第二部分：Agent 工具调用循环 (Agent Loop)

### 1. 核心问题：为什么需要"循环"？

在 Day 5 中，我们的 Function Calling 只有一轮：用户提问 → 模型调用一次工具 → 返回结果 → 结束。

但在现实中，很多任务需要**多轮工具调用**才能完成。例如：

> 用户："帮我查一下北京今天的天气，然后写一首跟天气有关的诗，最后把诗保存到 poem.txt 里。"

这个请求需要 Agent 连续执行三步：
1. 调用 `get_weather("北京")` 获取天气信息
2. 基于天气信息生成一首诗（这一步模型自己完成，不需要工具）
3. 调用 `write_file("poem.txt", poem_content)` 保存文件

### 2. Agent Loop 的完整伪代码

```python
def agent_loop(user_input, model, tools, max_iterations=10):
    """
    Agent 工具调用的核心循环。

    Args:
        user_input: 用户输入的文本。
        model: 绑定了工具的模型实例。
        tools: 工具名称到函数的映射字典。
        max_iterations: 最大迭代次数（安全阀）。

    Returns:
        最终的文本回答。
    """
    messages = [HumanMessage(content=user_input)]

    for i in range(max_iterations):
        # 调用模型
        response = model.invoke(messages)
        messages.append(response)

        # 检查是否有 tool_calls
        if not response.tool_calls:
            # 没有工具调用 → 模型已经给出最终回答
            return response.content

        # 有工具调用 → 逐个执行
        for tool_call in response.tool_calls:
            # 查找并执行工具
            tool_func = tools[tool_call["name"]]
            result = tool_func.invoke(tool_call["args"])

            # 将执行结果封装为 ToolMessage
            tool_msg = ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"]
            )
            messages.append(tool_msg)

        # 回到循环顶部，带着工具结果再次调用模型

    return "达到最大迭代次数，Agent 停止。"
```

### 3. max_iterations 安全阀

`max_iterations` 是一个至关重要的安全机制。没有它，Agent 可能会陷入**无限循环**——例如模型反复调用同一个工具却无法得到满意结果。

在生产环境中，通常设置 `max_iterations = 10 ~ 25`，超过则强制终止并返回错误提示。

### 4. Agent Loop 流程图

```
                    用户输入
                      │
                      ▼
              ┌──────────────┐
              │  调用大模型    │◄──────────────────┐
              └──────┬───────┘                    │
                     │                            │
                     ▼                            │
            ┌────────────────┐                    │
            │ 有 tool_calls? │                    │
            └───┬────────┬───┘                    │
                │        │                        │
            YES │        │ NO                     │
                ▼        ▼                        │
        ┌─────────┐  ┌──────────┐                 │
        │ 执行工具 │  │ 返回回答  │                 │
        └────┬────┘  └──────────┘                 │
             │                                    │
             ▼                                    │
    ┌─────────────────┐                           │
    │ 追加 ToolMessage │──────────────────────────┘
    └─────────────────┘
```

> 📖 **代码实战**：查看并运行 [04_agent_loop.py](file:///Users/huangyang/code/agent/project_03_tool_agent/04_agent_loop.py)

---

## 第三部分：错误处理与重试机制

### 1. 工具执行中的常见错误

| 错误类型 | 示例场景 | 影响 |
|---------|---------|------|
| 参数类型错误 | 模型传了字符串 "123" 给需要 int 的参数 | 工具函数抛出 TypeError |
| 参数值非法 | 模型传了不存在的城市名 | 工具返回空结果或报错 |
| 执行超时 | 网络搜索 API 响应过慢 | 程序阻塞 |
| 权限不足 | 文件操作工具尝试访问受保护目录 | PermissionError |
| 工具不存在 | 模型幻觉出一个不存在的工具名 | KeyError |

### 2. 错误处理的三层防御策略

#### 第一层：工具函数内部防御
每个工具函数自身应该包含完整的 try-except，并返回结构化的错误信息（而非抛出异常）：

```python
@tool
def read_file(filepath: str) -> str:
    """读取指定路径的文件内容。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"错误：文件 '{filepath}' 不存在。"
    except PermissionError:
        return f"错误：没有权限读取文件 '{filepath}'。"
```

#### 第二层：Agent Loop 中的异常捕获
在循环中包裹工具执行的 try-except，即使工具执行崩溃，也将错误信息作为 `ToolMessage` 反馈给大模型，让它有机会自我修正：

```python
try:
    result = tool_func.invoke(tool_call["args"])
except Exception as e:
    result = f"工具执行出错: {type(e).__name__}: {str(e)}"

# 无论成功还是失败，都把结果反馈给大模型
tool_msg = ToolMessage(content=str(result), tool_call_id=tool_call["id"])
```

#### 第三层：全局超时与熔断
为整个 Agent Loop 设置总超时时间（如 60 秒），防止单次用户请求消耗过长时间。

### 3. 大模型的自我纠错能力

当工具返回错误信息时，优秀的大模型（如 DeepSeek、GPT-4）往往能够**自主纠正**。例如：
1. 模型调用 `read_file("/data/config.yaml")`，得到"文件不存在"。
2. 模型自动换一个路径 `read_file("/etc/config.yaml")` 再试。
3. 或者模型先调用 `list_directory("/data/")` 查看目录内容，找到正确的文件名后再调用 `read_file()`。

这种"试错 → 反馈 → 重试"的行为，正是 Agent 智能性的体现。

> 📖 **代码实战**：查看并运行 [05_error_handling.py](file:///Users/huangyang/code/agent/project_03_tool_agent/05_error_handling.py)

---

## 核心原理深度解析

### Agent Loop vs. 普通 Chain 的本质区别

| 维度 | Chain（链） | Agent Loop（智能体循环） |
|------|-----------|----------------------|
| 执行路径 | 固定的、线性的 | 动态的、由模型自主决定 |
| 步骤数量 | 编码时确定 | 运行时不确定 |
| 工具选择 | 编码时指定 | 模型自主选择 |
| 错误恢复 | 直接崩溃 | 反馈给模型，尝试自我修正 |
| 适用场景 | 流程固定的任务 | 开放性、探索性任务 |

### 消息类型的完整家族

经过 Day 5 和 Day 6 的学习，我们接触到了 LangChain 中所有核心的消息类型：

```
BaseMessage (基类)
├── SystemMessage     # 系统设定（角色定义）    → role: "system"
├── HumanMessage      # 用户输入              → role: "user"
├── AIMessage         # 模型回答/工具调用决策    → role: "assistant"
│   └── .tool_calls   # 工具调用指令数组
└── ToolMessage       # 工具执行结果           → role: "tool"
    └── .tool_call_id # 关联的 tool_call ID
```

这些消息类型在 API 请求中对应不同的 `role`，大模型正是根据 `role` 来判断每条消息的语义角色的。

---

## 课后练习

1. **扩展工具集**：为你的 Agent 添加一个"翻译工具"——接收原文和目标语言，调用另一个大模型实例进行翻译并返回结果。注意这里的"工具内部再调用大模型"是完全合法的工程做法。

2. **多轮调用实验**：设计一个需要 Agent 连续调用 3 个以上工具才能完成的复杂任务，观察 Agent Loop 中消息列表的增长过程，体会"推理-执行-反馈"循环的节奏。

3. **错误自纠实验**：故意让一个工具返回错误信息（如"文件不存在"），观察大模型是否能自动调整参数重试或者换用其他工具来达成目标。

4. **Flake8 自检**：确保代码通过 `flake8 project_03_tool_agent/` 的检查。
