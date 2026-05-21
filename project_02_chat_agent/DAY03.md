# Day 3 课程：构建对话 Agent（从零理解 Agent 核心循环与短期记忆）🤖

今天我们将正式踏入 **AI Agent (智能体)** 的开发大门。在前两天，我们编写的都是“单次触发、即用即走”的链式应用。从今天起，我们的程序将具备 Agent 的三大核心要素：**感知能力（Perception）**、**思考引擎（Brain/LLM）** 和 **状态维护（State/Memory）**。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：什么是 Agent 的核心循环？](#第一部分什么是-agent-的核心循环)
3. [第二部分：最简无状态对话循环 (Simple Chatbot)](#第二部分最简无状态对话循环-simple-chatbot)
4. [第三部分：短期记忆的工程实现 (Chat History)](#第三部分短期记忆的工程实现-chat-history)
5. [第四部分：System Prompt 塑造 Agent 人格 (Persona)](#第四部分system-prompt-塑造-agent-人格-persona)
6. [第五部分：LCEL 与对话 Agent 的关系](#第五部分lcel-与对话-agent-的关系)
7. [课后练习](#课后练习)

---

## 学习目标
- 深刻理解 Agent 的核心工作循环：`感知 -> 思考 -> 行动 -> 状态更新`。
- 掌握在命令行下构建交互式对话循环（`while True`）的工程技巧。
- 理解大模型“有记忆回答”在底层的代码实现机制，手写管理短期消息上下文。
- 明确 LCEL 与对话交互循环的定位差异，理解在多轮状态交互下如何选用合适的开发模式。
- 学会通过精心设计的 `SystemMessage` 赋予 Agent 特定的专业人格与行为边界。
- 掌握在多轮对话中动态切换 Agent 角色并进行上下文清理的开发流程。

---

## 第一部分：什么是 Agent 的核心循环？

一个最基础的对话 Agent，其运转逻辑可以通过下面的闭环来表示：

```
      +-----------------------------------------+
      |                                         |
      v                                         |
[ 1. 感知输入 ] (接收用户 Prompt)                |
      |                                         |
      v                                         |
[ 2. 思考决策 ] (大模型根据 Prompt & 记忆进行推理)  |
      |                                         |
      v                                         |
[ 3. 执行行动 ] (打印回答 / 执行外部工具)          |
      |                                         |
      v                                         |
[ 4. 状态更新 ] (将对话存入记忆，回到步骤 1)      |
      |                                         |
      +-----------------------------------------+
```

与普通程序的顺序执行不同，Agent 往往处于一个**持续监听和主动循环**的状态中。
在终端里，这个循环最直截了当的工程载体就是一个 `while True` 控制台交互循环。

---

## 第二部分：最简无状态对话循环 (Simple Chatbot)

要理解有记忆的 Agent，首先要从“无记忆”的反面教材开始。

在 [01_simple_chatbot.py](file:///Users/huangyang/code/agent/project_02_chat_agent/01_simple_chatbot.py) 中，我们构建了一个最简单的交互控制台：
- 使用 `input("用户 > ")` 持续监听用户输入。
- 过滤特殊命令（如 `exit` / `quit` 退出程序，`clear` 清屏）。
- 直接将当前用户的这一句话发给大模型，并打印回复。

### 无状态的局限性
当你运行这个程序并跟它对话时，你会发现：
- 你说：“我叫张三。” -> AI 说：“你好，张三！”
- 接着问：“我叫什么名字？” -> AI 说：“对不起，我不知道你叫什么名字。”

这是因为**每次 `while` 循环调用大模型，都是一次独立的、没有任何前置上下文的网络请求。**

---

## 第三部分：短期记忆的工程实现 (Chat History)

为了给 Agent 注入“记忆”，我们需要在客户端的运行状态中，使用一个容器把每一次的对话内容保存下来。

### 1. 记忆的工程本质
当用户提问第 $N$ 次时，我们发送给大模型的实际内容是：
`[ 历史用户消息 1, 历史AI回复 1, 历史用户消息 2, 历史AI回复 2, ..., 当前用户消息 N ]`

### 2. `ChatHistory` 类的设计与封装
我们在 [02_chat_with_history.py](file:///Users/huangyang/code/agent/project_02_chat_agent/02_chat_with_history.py) 中，封装了一个面向对象的 `ChatHistory` 管理器，其核心职责包括：
- `add_user_message(content)`：接收用户文本，将其转换为 `HumanMessage` 对象存入列表。
- `add_ai_message(content)`：接收大模型文本，将其转换为 `AIMessage` 对象存入列表。
- `get_messages()`：返回包含所有消息的完整列表，如果设置了 `system_prompt`，则将其作为列表的第一个元素（`SystemMessage`）。
- `clear()`：清空历史，只保留可选的系统设定。

### 3. Token 膨胀的隐患
有了短期记忆后，大模型能非常聪明地结合上下文聊天。但这也带来了一个重大的代价：**随着对话轮数的增加，发送给大模型的 Token 数量呈线性上涨**。
这意味着：
1. **费用成本**急剧上升。
2. 很容易超出大模型的 **Context Window (上下文窗口上限)**，导致模型报错或者开始“遗忘”最早的对话。
*(注：我们将在后续阶段学习如何通过滑动窗口截断、摘要压缩等技术解决此问题。)*

> 📖 **代码实战**：查看并运行 [02_chat_with_history.py](file:///Users/huangyang/code/agent/project_02_chat_agent/02_chat_with_history.py)

---

## 第四部分：System Prompt 塑造 Agent 人格 (Persona)

通过给大模型发送的第一条消息（`SystemMessage`），我们可以设定大模型的底层逻辑、说话语气、专业背景以及“不准做什么”的负面约束。这在工程上被称为**塑造 Persona (人格/面具)**。

### 1. 好的 System Prompt 要素
一个合格的 Agent 系统提示词应该包括：
1. **身份定位**（Role）：例如“你是一位资深的 Python 编程导师”。
2. **行为准则**（Rules）：例如“不要直接给出完整代码，而是指出错误行并给出提示”。
3. **输出风格**（Style）：例如“语气严肃、有耐心，多用代码块格式化输出”。
4. **限制边界**（Constraints）：例如“如果用户问及非编程问题，请礼貌地拒绝回答”。

### 2. 多角色动态切换与上下文清理
在 [03_chat_with_persona.py](file:///Users/huangyang/code/agent/project_02_chat_agent/03_chat_with_persona.py) 中，我们定义了四种角色，并支持用户在终端中输入 `/role` 命令动态切换 Agent 角色。

> ⚠️ **关键设计细节**：
> 当用户中途切换角色时，我们**必须清空历史记忆（调用 `history.clear()`）**。
> 否则，前一个角色的对话记录（比如心理咨询师的安慰话语）会混入新角色（比如严厉的编程导师）的上下文里，导致大模型产生“角色精神分裂”和行为失常。

> 📖 **代码实战**：查看并运行 [03_chat_with_persona.py](file:///Users/huangyang/code/agent/project_02_chat_agent/03_chat_with_persona.py)

---

## 第五部分：LCEL 与对话 Agent 的关系

在 Day 2 中，我们重点学习了 LangChain 的核心概念 **LCEL (LangChain 表达语言)**，采用 `chain = prompt | model | parser` 这种极简的管道式语法来组装应用。但是，你可能会好奇：**为什么在 Day 3 的对话 Agent 中，我们没有使用 LCEL，而是手写了 `while True` 循环和 `history.get_messages()` 呢？**

这是出于以下工程和设计上的权衡：

### 1. 为什么对话场景不直接使用简单的 LCEL？
- **多轮交互的复杂状态**：普通的 LCEL 管道是**单次执行、无状态**的。它非常运营于类似于“输入 -> 翻译 -> 结构化输出”这样的单向单次流，但在面对“用户输入 -> 获取历史 -> 模型判断 -> 打印输出 -> 存入历史”这种需要**持续交互和状态变更**的循环中，简单的 `|` 管道很难优雅地维护客户端内存中的状态变更（例如动态清除历史、切换角色）。
- **流程的可控性**：在终端对话中，我们需要对用户的输入进行拦截处理（例如 `/role` 命令、`/clear` 命令、`exit` 退出信号）。这些命令控制逻辑如果强行塞进 LCEL 管道，会使管道变得异常臃肿，反而失去了 LCEL 简洁明了的优势。

### 2. 在对话场景中，如何正确使用 LCEL？
虽然我们不直接用 LCEL 编写交互循环，但我们可以在 LCEL 中引入 **带有记忆的 Runnable**。
LangChain 提供了 `RunnableWithMessageHistory` 来包装一个 LCEL 链，使其自动管理记忆。例如：

```python
# 示例代码：使用 LCEL + 记忆包装器（概念演示）
from langchain_core.runnables.history import RunnableWithMessageHistory

# 1. 定义基础的 LCEL 链
chain = prompt | model

# 2. 用记忆包装器封装基础链，使其具备自动读取/存入历史消息的能力
conversational_chain = RunnableWithMessageHistory(
    chain,
    get_session_history=lambda session_id: memory_store[session_id],
    input_messages_key="input",
    history_messages_key="history"
)
```

> 💡 **架构选择**：
> 在现阶段，为了让大家**深刻理解短期记忆在内存和 API 请求底层的流转细节**，我们选择手写 `ChatHistory` 管理器和 `while` 循环。这种“透明白盒”的方式更有利于初学者建立稳同的 Agent 底层心智模型。当进入更复杂的图结构编排（如 Day 7 开始的 LangGraph）时，我们将会使用更高级的编排图框架来自动接管这些底层的循环和状态。

---

## 课后练习
1. **添加记忆大小监视器**：修改 `02_chat_with_history.py`，在每一次 AI 回答完毕后，实时在屏幕右下角或提示符处打印当前对话中 `HumanMessage` 和 `AIMessage` 的总计 Token 估算值。
2. **实现一个“限时记忆” Agent**：尝试修改 `ChatHistory` 类，使其只保留最近 5 轮（即最后 10 条消息）的对话上下文。当超过 10 条时，自动丢弃最旧的消息（提示：使用 `collections.deque` 或列表切片）。
3. **设计你的专属 Agent 人格**：编写一个新的 System Prompt（例如：“小说大纲策划师”或“SQL 注入漏洞检测专家”），并加入到 `config.py` 的 preset 中进行测试。
