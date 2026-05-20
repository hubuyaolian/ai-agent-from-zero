# Day 5 课程：Function Calling 原理 — 让 Agent 学会"使用工具" 🔧

从今天起，我们的 Agent 将迎来一次质的飞跃。

前 4 天，无论我们的 Agent 多么能说会道、多么有记忆力，它本质上只能做一件事：**生成文字**。它不能查天气、不能算数学、不能读文件、不能搜网页。

**Function Calling（函数调用 / 工具调用）**改变了一切。通过这个机制，大模型不再只是"嘴上说说"，它可以告诉你的代码："我需要调用这个函数，参数是这些"——然后由你的代码真正去执行，把结果反馈给大模型，大模型再基于执行结果组织最终回答。

这就是 Agent 从"聊天机器人"进化为"能做事的智能体"的关键转折点。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：Function Calling 底层原理](#第一部分function-calling-底层原理)
3. [第二部分：LangChain 工具系统 (@tool)](#第二部分langchain-工具系统-tool)
4. [第三部分：将工具绑定到模型 (bind_tools)](#第三部分将工具绑定到模型-bind_tools)
5. [核心原理深度解析](#核心原理深度解析)
6. [课后练习](#课后练习)

---

## 学习目标
- 彻底理解 Function Calling 的底层通信协议：大模型**不执行代码**，它只是输出一段结构化的 JSON 指令。
- 不借助任何框架，用纯 `requests` 手动实现一次完整的 Function Calling 闭环。
- 掌握 LangChain 的 `@tool` 装饰器，学会如何快速将 Python 函数变成大模型可调用的工具。
- 理解 `bind_tools()` 的底层原理——它是如何将工具的 JSON Schema 注入到 API 请求中的。

---

## 第一部分：Function Calling 底层原理

### 1. 一个关键认知：大模型不会执行任何代码

很多初学者以为"大模型调用工具"意味着大模型自己在服务器端运行了一段代码。**这是完全错误的。**

实际的交互流程如下：

```
 你的 Python 代码                      大模型服务器
      |                                    |
      |  1. 发送消息 + 工具定义列表           |
      | ---------------------------------> |
      |                                    |
      |  2. 返回: "我想调用 get_weather,     |
      |           参数是 {city: '北京'}"     |
      | <--------------------------------- |
      |                                    |
      |  3. 你的代码执行 get_weather("北京")  |
      |     得到结果: "晴天, 28°C"           |
      |                                    |
      |  4. 把执行结果作为新消息发回           |
      | ---------------------------------> |
      |                                    |
      |  5. 大模型基于结果生成自然语言回答     |
      |     "北京今天晴天，气温28度，..."      |
      | <--------------------------------- |
      |                                    |
```

> ⚠️ **核心要点**：大模型做的事情只有**"决策"**——决定该调用哪个函数、传什么参数。真正的**"执行"**永远发生在你的本地代码中。

### 2. 原始 API 中的 Function Calling 协议

当你在 HTTP 请求中附加工具定义时，请求体会多出一个 `tools` 字段：

```json
{
  "model": "deepseek-chat",
  "messages": [
    {"role": "user", "content": "北京今天天气怎么样？"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "获取指定城市的当前天气信息",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string",
              "description": "城市名称，如 '北京'、'上海'"
            }
          },
          "required": ["city"]
        }
      }
    }
  ]
}
```

大模型收到后会判断：用户的意图是否需要调用某个工具？如果需要，它不会返回普通的 `content` 文本，而是返回一个 `tool_calls` 数组：

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"city\": \"北京\"}"
            }
          }
        ]
      }
    }
  ]
}
```

注意 `arguments` 字段是一个**字符串化的 JSON**，你需要用 `json.loads()` 解析它才能拿到真正的参数字典。

### 3. 手动实现 Function Calling 闭环

不使用任何框架的完整流程伪代码：

```python
# 步骤 1：定义你的工具函数
def get_weather(city):
    """获取天气（模拟）"""
    return f"{city}今天晴天，28°C"

# 步骤 2：定义工具的 JSON Schema（告诉大模型有什么工具可用）
tools_schema = [...]  # 如上面的 JSON 定义

# 步骤 3：发送请求（附带 tools 定义）
response = requests.post(url, headers=headers, json={
    "model": "deepseek-chat",
    "messages": messages,
    "tools": tools_schema
})

# 步骤 4：检查返回值是否包含 tool_calls
data = response.json()
message = data["choices"][0]["message"]

if message.get("tool_calls"):
    # 步骤 5：解析工具调用请求
    tool_call = message["tool_calls"][0]
    func_name = tool_call["function"]["name"]
    func_args = json.loads(tool_call["function"]["arguments"])

    # 步骤 6：执行对应的本地函数
    result = get_weather(**func_args)

    # 步骤 7：将执行结果作为 tool 角色的消息追加到历史
    messages.append(message)  # 先追加 assistant 的 tool_calls 消息
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "content": str(result)
    })

    # 步骤 8：再次请求大模型，让它根据工具结果生成最终回答
    final_response = requests.post(url, headers=headers, json={
        "model": "deepseek-chat",
        "messages": messages
    })
```

> 📖 **代码实战**：查看并运行 [01_function_calling_raw.py](file:///Users/huangyang/code/agent/project_03_tool_agent/01_function_calling_raw.py)

---

## 第二部分：LangChain 工具系统 (@tool)

在上一部分中，我们需要手动编写冗长的 JSON Schema 来描述每个工具。这在工具数量较多时会非常痛苦且容易出错。

LangChain 的 `@tool` 装饰器通过**自动反射（Reflection）**解决了这个问题：它会自动读取你函数的**名称、Docstring、参数类型注解**，自动生成对应的 JSON Schema。

### 1. 基本用法

```python
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """获取指定城市的当前天气信息。

    Args:
        city: 城市名称，如 '北京'、'上海'。

    Returns:
        包含天气信息的字符串。
    """
    # 实际项目中这里会调用真实的天气 API
    return f"{city}今天晴天，气温28°C"
```

仅仅这么几行代码，LangChain 就能自动生成如下 JSON Schema：
```json
{
  "name": "get_weather",
  "description": "获取指定城市的当前天气信息。",
  "parameters": {
    "type": "object",
    "properties": {
      "city": {"type": "string", "description": "城市名称，如 '北京'、'上海'。"}
    },
    "required": ["city"]
  }
}
```

### 2. @tool 的自动推断规则

| Python 源码元素 | 映射到 JSON Schema 中的字段 |
|----------------|---------------------------|
| 函数名 `get_weather` | `"name": "get_weather"` |
| Docstring 第一行 | `"description": "获取指定城市..."` |
| 参数名 `city` | `properties` 中的键名 |
| 类型注解 `str` | `"type": "string"` |
| Docstring 中 Args 下 `city:` 的描述 | 对应 property 的 `"description"` |

### 3. 支持复杂参数类型

`@tool` 也支持更复杂的参数（如 Pydantic 模型、可选参数、枚举值等）：

```python
from typing import Optional

@tool
def search_products(
    keyword: str,
    category: Optional[str] = None,
    max_price: float = 1000.0
) -> str:
    """搜索商品。

    Args:
        keyword: 搜索关键词。
        category: 商品分类（可选）。
        max_price: 最高价格限制，默认 1000 元。

    Returns:
        搜索结果的字符串描述。
    """
    return f"搜索 '{keyword}' 在 {category or '全部分类'} 中，价格不超过 {max_price} 元"
```

> 📖 **代码实战**：查看并运行 [02_langchain_tools.py](file:///Users/huangyang/code/agent/project_03_tool_agent/02_langchain_tools.py)

---

## 第三部分：将工具绑定到模型 (bind_tools)

有了工具定义后，还需要将它们**绑定**到模型上，这样模型在推理时才知道有哪些工具可供调用。

### 1. bind_tools() 的用法

```python
from common.model_factory import create_model

# 创建模型实例
model = create_model("deepseek")

# 将工具列表绑定到模型
model_with_tools = model.bind_tools([get_weather, search_products])

# 调用（LangChain 会自动将工具 Schema 附加到 API 请求中）
response = model_with_tools.invoke("北京今天天气怎么样？")
```

### 2. bind_tools() 底层做了什么？

`bind_tools()` 的底层操作非常直接：

```
bind_tools([tool_1, tool_2])
    ↓
1. 遍历每个 tool，调用 tool.get_schema() 获取 JSON Schema
    ↓
2. 将所有 Schema 组装成 tools 数组
    ↓
3. 返回一个新的模型副本，在该副本中，
   每次 invoke() 请求时都会自动附带 tools 参数
```

本质上，它就是帮你在每次 HTTP 请求中自动附加了 `"tools": [...]` 字段，和我们在第一部分中手写 JSON 完全一样，只是自动化了。

### 3. 解析模型返回的 tool_calls

当模型决定调用工具时，LangChain 返回的 `AIMessage` 对象中会包含一个 `tool_calls` 属性：

```python
response = model_with_tools.invoke("北京天气怎么样？")

# 检查模型是否决定调用工具
if response.tool_calls:
    for tool_call in response.tool_calls:
        print(f"工具名称: {tool_call['name']}")
        print(f"调用参数: {tool_call['args']}")
        print(f"调用 ID:  {tool_call['id']}")
else:
    # 模型认为不需要调用工具，直接返回文本回答
    print(f"直接回答: {response.content}")
```

### 4. 完整的 Tool Calling 闭环（LangChain 版）

```python
from langchain_core.messages import HumanMessage, ToolMessage

# 1. 用户提问
messages = [HumanMessage(content="北京今天天气怎么样？")]

# 2. 模型推理（可能返回 tool_calls）
response = model_with_tools.invoke(messages)
messages.append(response)

# 3. 如果有 tool_calls，执行工具并反馈结果
if response.tool_calls:
    for tool_call in response.tool_calls:
        # 执行工具（根据工具名查找并调用）
        result = execute_tool(tool_call["name"], tool_call["args"])

        # 用 ToolMessage 封装执行结果
        tool_msg = ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        )
        messages.append(tool_msg)

    # 4. 将工具结果发回大模型，生成最终自然语言回答
    final_response = model_with_tools.invoke(messages)
    print(final_response.content)
```

> 📖 **代码实战**：查看并运行 [03_tool_binding.py](file:///Users/huangyang/code/agent/project_03_tool_agent/03_tool_binding.py)

---

## 核心原理深度解析

### Function Calling 的两种模式

大模型在收到带 `tools` 定义的请求后，有两种行为模式：

| 模式 | 行为 | 示例场景 |
|------|------|---------|
| **不调用工具** | 大模型认为自己可以直接回答，返回普通文本 `content` | 用户问："什么是 Python？" |
| **调用工具** | 大模型认为需要外部信息/操作，返回 `tool_calls` | 用户问："北京今天天气怎么样？" |

大模型会**自主判断**是否需要使用工具。这个判断依据的是：
1. **用户问题的语义**：是否涉及需要实时数据、外部操作等模型自身知识无法覆盖的内容。
2. **工具的 description**：工具的描述文字写得越清晰准确，大模型匹配的成功率就越高。

### 多工具并行调用

当一个用户请求涉及多个独立的工具调用时（例如"帮我查北京和上海的天气"），大模型可能在一次响应中返回**多个** `tool_calls`：

```json
{
  "tool_calls": [
    {"id": "call_001", "function": {"name": "get_weather", "arguments": "{\"city\": \"北京\"}"}},
    {"id": "call_002", "function": {"name": "get_weather", "arguments": "{\"city\": \"上海\"}"}}
  ]
}
```

此时你的代码可以**并行执行**这两个工具调用，然后将两个 `ToolMessage` 都追加到消息历史中，一次性发回给大模型。

### 工具描述的重要性

`@tool` 装饰器自动提取函数的 Docstring 作为工具描述。这段描述直接决定了大模型能否正确识别和选择工具：

| 描述质量 | 示例 | 模型行为 |
|---------|------|---------|
| ❌ 差 | `"处理数据"` | 大模型不知道什么时候该用这个工具 |
| ⚠️ 一般 | `"获取天气"` | 基本能匹配，但边界情况可能出错 |
| ✅ 好 | `"获取指定中国城市的当前天气信息，包括温度、湿度和天气状况。输入城市名称如'北京'。"` | 大模型能精确匹配，参数也更准确 |

> **经验法则**：把工具描述当作给一个实习生的工作说明书来写——越详细越好，要包含"什么情况下用"、"输入什么"、"输出什么"。

---

## 课后练习

1. **手写一个计算器工具**：在 `01_function_calling_raw.py` 中，增加一个 `calculate` 工具（支持加减乘除），使用纯 `requests` 手动处理 Function Calling 的完整流程。让用户可以问"123 乘以 456 等于多少？"并获得精确的数学结果。

2. **工具描述 A/B 测试**：为同一个工具（例如 `get_weather`）编写两个不同质量的描述（一个含糊、一个详细），分别绑定到模型上，发送同样的 10 个用户问题，统计大模型正确调用该工具的命中率差异。

3. **多工具并行**：创建 3 个独立的工具（如查天气、查汇率、查时间），然后向大模型发送一句话包含三个需求的提问（如"北京天气怎么样？现在几点了？1美元兑多少人民币？"），观察大模型是否返回了 3 个并行的 `tool_calls`。

4. **Flake8 自检**：确保代码通过 `flake8 project_03_tool_agent/` 的检查。
