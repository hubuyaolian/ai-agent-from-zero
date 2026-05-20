# Day 1 课程：API 基础与 LangChain 模型入门 🎓

本章是 AI Agent 学习的第一步。我们将从最底层的网络通信原理出发，理解大模型 API 的请求与响应结构，然后过渡到 LangChain 框架对这些接口的抽象，最后通过横向评测对比不同大模型（国内模型与 Gemini）的表现。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：原始 API 调用 (Raw API Call)](#第一部分原始-api-调用-raw-api-call)
3. [第二部分：LangChain 聊天模型 (Chat Models)](#第二部分langchain-聊天模型-chat-models)
4. [第三部分：多模型对比 (Model Comparison)](#第三部分多模型对比-model-comparison)
5. [常见问题与避坑指南](#常见问题与避坑指南)
6. [课后练习](#课后练习)

---

## 学习目标
- 掌握大模型接口的标准请求与响应 JSON 结构。
- 理解大模型“无状态（Stateless）”的本质，以及多轮对话在客户端是如何维持的。
- 熟练使用 LangChain 统一封装的 `ChatOpenAI` 接口调用不同模型。
- 理解 `SystemMessage`、`HumanMessage`、`AIMessage` 的含义和使用场景。
- 掌握如何对不同模型进行响应速度（Token/s）和质量的横向对比。

---

## 第一部分：原始 API 调用 (Raw API Call)

大模型 API 的底层并不是什么神秘的技术，它本质上就是一个标准的 **HTTP POST 接口**。

我们以调用 **DeepSeek** 为例，当不用任何框架时，其网络交互流程如下：

```
+------------+                  POST /chat/completions                  +------------+
|            | -------------------------------------------------------> |            |
|   Python   |  Headers: {"Authorization": "Bearer sk-xxx", ...}        |  DeepSeek  |
|   Client   |  Body:    {"model": "deepseek-chat", "messages": [...]}  |   Server   |
|            | <------------------------------------------------------- |            |
+------------+              Response: {"choices": [...]}                +------------+
```

### 1. 请求结构解析
发送给大模型 API 的 HTTP 请求由三部分组成：

- **URL (请求地址)**: 
  对于兼容 OpenAI 格式的接口，地址通常以 `/v1/chat/completions` 或 `/chat/completions` 结尾。例如：
  - DeepSeek: `https://api.deepseek.com/chat/completions`
  - 阿里云百炼: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`

- **Headers (请求头)**:
  - `Content-Type`: 必须为 `application/json`。
  - `Authorization`: 携带 API Key，格式为 `Bearer your_api_key_here`。

- **Body (请求体 - JSON)**:
  - `model`: 指定要调用的模型名称（如 `deepseek-chat`, `qwen-plus`）。
  - `messages`: 对话消息数组。每个消息都是一个字典，包含 `role` 和 `content`：
    - `system`: 系统设定，用于定义 AI 的角色、语气和规则。
    - `user`: 用户发送的内容。
    - `assistant`: AI 生成的历史回答。
  - `temperature`: 控制随机性，范围通常在 `0` 到 `2` 之间。越接近 `0` 回答越严谨，越接近 `1` 回答越有创意。

### 2. 响应结构解析
模型返回的也是一个 JSON，核心数据嵌套在 `choices` 中：
```json
{
  "id": "chatcmpl-xxxxxx",
  "object": "chat.completion",
  "created": 1716223200,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！我是你的 AI 助手。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 8,
    "total_tokens": 23
  }
}
```
我们提取回答时，需要通过 `data["choices"][0]["message"]["content"]` 获取。

### 3. 多轮对话的底层原理
大模型是**无状态（Stateless）**的。这意味着，它不会在服务器端保存你之前跟它说过的话。

为了实现“记住上下文”的多轮对话，我们必须在**客户端（你的 Python 代码中）**手动维护一个 `messages` 列表。每次用户发送新消息时：
1. 将用户的新消息 append 到 `messages` 列表。
2. 将**整个历史消息列表**作为 Body 发送给大模型。
3. 收到大模型的回答后，将 AI 的回答也 append 到 `messages` 列表，为下一次对话做准备。

> 📖 **代码实战**：查看并运行项目中的 [01_raw_api_call.py](file:///Users/huangyang/code/agent/project_01_basics/01_raw_api_call.py)

---

## 第二部分：LangChain 聊天模型 (Chat Models)

如果我们需要调用好几个不同的大模型，手写 HTTP 请求会变得非常繁琐（每个厂商的 SDK、传参方式都可能不一样）。

**LangChain 的最大价值之一，就是提供了标准统一的接口抽象。**

### 1. LangChain 核心抽象
- **模型类 (`ChatOpenAI`)**：由于国内大部分模型都兼容 OpenAI 的 API 格式，我们可以统一使用 `ChatOpenAI` 来实例化它们，只需传入不同的 `base_url`、`api_key` 和 `model`。
- **消息类 (`BaseMessage`)**：LangChain 将消息抽象成了专门的类，相比于 Python 字典，它们能提供更强的类型安全和元数据管理：
  - `SystemMessage` 对应 `{"role": "system"}`
  - `HumanMessage` 对应 `{"role": "user"}`
  - `AIMessage` 对应 `{"role": "assistant"}`

### 2. 工厂模式的应用
在我们的项目中，我们在 `common/model_factory.py` 里封装了 `create_model` 函数。要切换模型，你不需要修改任何复杂的网络参数，只需传入提供商名称：

```python
from common.model_factory import create_model

# 实例化 DeepSeek
model_ds = create_model("deepseek")

# 一行代码切换到 通义千问
model_qw = create_model("qwen")

# 甚至切换到 Google Gemini
model_gm = create_model("gemini")
```

### 3. 调用与返回值
调用模型只需要调用其 `.invoke()` 方法：
```python
response = model.invoke([
    SystemMessage(content="你是一个幽默的助手"),
    HumanMessage(content="为什么冰淇淋是甜的？")
])
```
`.invoke()` 的返回值是一个 `AIMessage` 对象。你可以通过：
- `response.content` 获取文本回答。
- `response.response_metadata` 获取原始的 HTTP 响应元数据（如日志 ID、结束原因等）。
- `response.usage_metadata` 获取结构化的 Token 使用统计（输入、输出、总计）。

> 📖 **代码实战**：查看并运行项目中的 [02_langchain_models.py](file:///Users/huangyang/code/agent/project_01_basics/02_langchain_models.py)

---

## 第三部分：多模型对比 (Model Comparison)

在实际开发 Agent 时，我们经常需要评估**哪一个模型最适合作为我们的“大脑”**。对比的维度通常有：
1. **生成质量**：逻辑推理能力如何？角色扮演是否拟真？
2. **响应速度**：生成首字的时间以及生成速度（Token/s）快不快？
3. **价格成本**：Token 消耗是否划算？

在第三部分的课程代码中，我们设计了三个典型的测试场景：
- **知识问答**（考查模型的事实检索与清晰表述能力）
- **创意写作**（考查模型的文学素养与格式限制能力）
- **逻辑推理**（考查模型的深层逻辑分析能力）

通过 Python 的 `time` 模块和 `usage_metadata`，我们可以在终端里输出直观的“速度排行榜”：

```
============================================================
模型速度与表现排行榜 (按生成速度从快到慢):
============================================================
1. QWEN: 0.85 秒 (62.3 Token/s)
2. DEEPSEEK: 1.22 秒 (41.5 Token/s)
3. GEMINI: 1.54 秒 (32.1 Token/s)
============================================================
```

> 📖 **代码实战**：查看并运行项目中的 [03_model_comparison.py](file:///Users/huangyang/code/agent/project_01_basics/03_model_comparison.py)

---

## 常见问题与避坑指南

### 1. 为什么运行代码报错：`ValueError: API key not found`？
**原因**：没有正确加载 `.env` 环境变量，或者 `.env` 中没有定义对应的 KEY。
**解决**：
- 确认你已经把 `.env.example` 复制为了 `.env`。
- 确认你在 `.env` 填入了正确的 Key 且没有多余的空格。
- 在代码最上方检查是否执行了 `load_dotenv()`。

### 2. 国内模型调用老是超时或报错 401 Unauthorized？
**原因**：国内各厂商的兼容协议可能会有些许差异，或者你的 `base_url` 填错了（比如把通义千问的兼容地址写成了官方 Dashscope 非兼容地址）。
**解决**：仔细对比项目 [common/config.py](file:///Users/huangyang/code/agent/common/config.py) 中的 `base_url` 定义，确保与官方文档的 OpenAI 兼容端点一致。

---

## 课后练习
1. **修改 01 文件**：尝试为原始 API 调用中的 `messages` 添加一条 `SystemMessage`（例如设定它为“只用古文回答的算命先生”），观察在没有框架的情况下，它是如何限制 AI 回答的。
2. **修改 03 文件**：添加一个你需要经常解决的业务场景问题，对比你配置的这几个大模型，看看哪一个的回答最符合你的预期。
3. **Flake8 自检**：在终端里运行 `flake8 project_01_basics/`，确保你在修改代码后，没有遗留任何格式规范的警告。
