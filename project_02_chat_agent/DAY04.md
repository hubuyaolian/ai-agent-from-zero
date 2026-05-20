# Day 4 课程：对话管理进阶 — 多会话、Token 窗口与综合聊天应用 🧠

在 Day 3 中，我们实现了一个带有短期记忆和角色切换的命令行 Agent。但那个 Agent 仍然存在几个工程层面的硬伤：

1. **只有一个会话**：所有对话都混在同一条历史消息链里，无法区分不同的用户或不同的话题。
2. **历史消息无限膨胀**：随着对话轮数增长，发送给大模型的 Token 数量无限制地线性上升，迟早会突破 Context Window（上下文窗口）上限，导致报错或"遗忘"。
3. **功能零散**：之前每个脚本独立演示，缺少一个将所有功能整合在一起的完整应用。

今天我们要彻底解决这三个问题。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：多会话管理 (Session Manager)](#第一部分多会话管理-session-manager)
3. [第二部分：Token 窗口管理 (Context Window)](#第二部分token-窗口管理-context-window)
4. [第三部分：综合命令行聊天应用 (Chat App)](#第三部分综合命令行聊天应用-chat-app)
5. [核心原理深度解析](#核心原理深度解析)
6. [课后练习](#课后练习)

---

## 学习目标
- 掌握多会话（Session）的隔离与管理：不同用户 / 不同话题拥有独立的对话历史。
- 深入理解 Token 窗口溢出的原因，学会三种主流的截断与压缩策略。
- 从零搭建一个功能完整、交互友好的终端聊天应用，整合前几天学习的所有能力。

---

## 第一部分：多会话管理 (Session Manager)

### 1. 为什么需要多会话？

回忆 Day 3 的 `ChatHistory` 类——它在内存中只有一个消息列表。这意味着：
- 如果你的应用同时服务多个用户（例如 Web 端的 API 后端），所有人的对话会混在一起。
- 即使是单用户场景，当你想开启一个全新的话题（例如从"讨论 Python"切换到"制定旅行计划"），旧话题的上下文会干扰新话题的回答质量。

### 2. 工程方案：Session ID 隔离

核心思路很简单：**用一个字典（`dict`），以 Session ID 为键，以独立的 `ChatHistory` 实例为值。**

```
SessionManager
├── sessions: Dict[str, ChatHistory]
│   ├── "user_001" -> ChatHistory(messages=[...用户1的对话...])
│   ├── "user_002" -> ChatHistory(messages=[...用户2的对话...])
│   └── "topic_python" -> ChatHistory(messages=[...Python话题...])
└── methods:
    ├── create_session(session_id, system_prompt) -> 创建新会话
    ├── get_session(session_id) -> 获取指定会话
    ├── delete_session(session_id) -> 删除指定会话
    ├── list_sessions() -> 列出所有活跃会话
    └── switch_session(session_id) -> 切换当前活跃会话
```

### 3. Session ID 的生成策略
在工程实践中，Session ID 的生成方式取决于应用场景：
- **单用户多话题**：可以用时间戳或自增序号，例如 `session_20260520_001`。
- **多用户场景**：通常用 UUID（`uuid.uuid4()`）保证全局唯一性。
- **Web 应用**：Session ID 往往绑定在用户的 Cookie 或 JWT Token 中。

> 📖 **代码实战**：查看并运行 [04_session_manager.py](file:///Users/huangyang/code/agent/project_02_chat_agent/04_session_manager.py)

---

## 第二部分：Token 窗口管理 (Context Window)

### 1. 什么是 Context Window？

每一个大模型都有一个**最大上下文窗口**（即一次请求中能处理的最大 Token 总数）。一旦你发送的消息 Token 数超过这个限制，模型要么直接报错，要么静默截断掉最早的内容（取决于具体实现）。

常见模型的 Context Window 大小：

| 模型 | 上下文窗口 |
|------|-----------|
| DeepSeek Chat | 64K tokens |
| Qwen Plus | 128K tokens |
| GPT-4o | 128K tokens |
| Gemini 2.5 Flash | 1M tokens |
| Kimi (moonshot-v1-8k) | 8K tokens |

### 2. Token 计算方式
一个中文汉字大约占 1.5 - 2 个 Token，一个英文单词大约占 1 - 1.5 个 Token。

精确计算 Token 数量可以使用 `tiktoken` 库（OpenAI 官方分词工具）：
```python
import tiktoken

# 获取编码器（cl100k_base 是 GPT-4/ChatGPT 系列模型使用的编码器）
encoder = tiktoken.get_encoding("cl100k_base")

# 将文本编码为 Token 列表
tokens = encoder.encode("你好，我是 AI 助手。")
print(f"Token 数量: {len(tokens)}")   # 约 8 个 Token
print(f"Token 列表: {tokens}")        # [57668, 35946, ...]
```

### 3. 三种主流的截断与压缩策略

#### 策略一：滑动窗口截断 (Sliding Window)
保留最近 N 轮的对话（例如最近 10 轮 = 20 条消息），丢弃更早的对话。

**优点**：实现最简单，性能开销为零。
**缺点**：早期的重要信息（例如用户的姓名、核心需求）会被彻底丢失。

```
滑动前: [sys, H1, A1, H2, A2, H3, A3, H4, A4, H5, A5, H6, A6]
                ^^^^^^^^^^^^^^^^^^^^                              <- 被丢弃
滑动后: [sys, H4, A4, H5, A5, H6, A6]
```

#### 策略二：摘要压缩 (Summary Compression)
当消息历史超过阈值时，调用一次额外的 LLM 请求，将旧的对话总结成一段简短的摘要（Summary），用这段摘要替换掉全部的旧消息。

**优点**：关键信息（如用户姓名、偏好）可以被保留在摘要中。
**缺点**：每次压缩都需要额外调用一次 LLM，增加了 Token 消耗和延迟。

```
压缩前: [sys, H1, A1, H2, A2, ..., H10, A10, H11_new]
压缩后: [sys, Summary("用户张三，讨论了Python基础..."), H10, A10, H11_new]
```

#### 策略三：Token 硬限制 (Token Budget)
精确计算当前所有消息的 Token 总数。如果总数超过预设的预算上限（例如模型最大窗口的 80%），则从最旧的消息开始逐条删除，直到低于预算。

**优点**：精确控制，不会浪费也不会溢出。
**缺点**：需要引入 `tiktoken` 等 Token 编码工具，增加一定的代码复杂度。

> 📖 **代码实战**：查看并运行 [05_context_window.py](file:///Users/huangyang/code/agent/project_02_chat_agent/05_context_window.py)

---

## 第三部分：综合命令行聊天应用 (Chat App)

这是 Day 4 的终极实战：将我们在 Day 3 和 Day 4 中学到的所有能力，整合成一个功能丰富、交互友好的命令行聊天应用。

### 1. 功能清单

| 功能 | 命令 | 说明 |
|------|------|------|
| 正常对话 | 直接输入文字 | 带上下文记忆的智能对话 |
| 新建会话 | `/new [名称]` | 创建一个新的对话会话 |
| 切换会话 | `/switch <ID>` | 切换到指定的会话 |
| 列出会话 | `/sessions` | 显示所有活跃的会话列表 |
| 删除会话 | `/delete <ID>` | 删除指定的会话 |
| 切换角色 | `/role` | 选择预设的 AI 角色 |
| 查看历史 | `/history` | 显示当前会话的消息记录与 Token 统计 |
| 清空历史 | `/clear` | 清空当前会话的对话历史 |
| 切换模型 | `/model` | 切换底层大模型提供商 |
| 帮助信息 | `/help` | 显示所有可用命令 |
| 退出 | `/quit` 或 `exit` | 退出应用 |

### 2. 架构设计

```
ChatApp (主控类)
├── SessionManager     # 会话管理器（管理多个独立对话）
├── TokenManager       # Token 窗口管理器（防溢出）
├── PersonaManager     # 角色管理器（System Prompt 切换）
├── ModelFactory       # 模型工厂（动态切换底层模型）
└── run()              # 主循环入口
    ├── 解析用户输入
    ├── 识别斜杠命令 vs 普通对话
    ├── 路由到对应的处理函数
    └── 格式化输出 AI 回答
```

### 3. 用户交互体验优化
- **彩色终端**：使用 ANSI 转义码区分用户输入、AI 回答、系统提示。
- **状态栏**：在每次交互后显示当前会话名称、角色、消息数量、Token 估算。
- **错误容忍**：所有 LLM 调用都包裹在 try/except 中，网络超时或模型限流不会导致程序崩溃。

> 📖 **代码实战**：查看并运行 [06_chat_app.py](file:///Users/huangyang/code/agent/project_02_chat_agent/06_chat_app.py)

---

## 核心原理深度解析

### 为什么 LLM 本身没有"记忆"？

这是一个在学习 Agent 开发时需要反复巩固的核心认知：

```
                    ┌─────────────────────────────────────────┐
                    │          大模型服务器 (Stateless)          │
                    │                                         │
  请求 1:           │  f(messages_1) -> response_1             │
  [H1]              │                                         │
                    │  ↕ 没有任何关联 ↕                         │
                    │                                         │
  请求 2:           │  f(messages_2) -> response_2             │
  [H2]              │                                         │
                    └─────────────────────────────────────────┘
```

大模型的每一次推理调用都是一个**纯函数 (Pure Function)**：相同的输入一定产出一致的概率分布。它不会在自己的服务器上保存你上一次的对话内容。

所以，"记忆"从来就不是大模型的能力，**而是你作为开发者在客户端代码中赋予它的附加功能**。

### Token 窗口 vs. 费用的权衡

| 策略 | Token 效率 | 信息保真度 | 额外费用 | 代码复杂度 |
|------|-----------|-----------|---------|-----------|
| 滑动窗口 | ⭐⭐⭐ | ⭐ | 无 | ⭐ |
| 摘要压缩 | ⭐⭐ | ⭐⭐⭐ | 有（额外 LLM 调用） | ⭐⭐⭐ |
| Token 硬限制 | ⭐⭐⭐ | ⭐⭐ | 无 | ⭐⭐ |
| 混合策略 | ⭐⭐⭐ | ⭐⭐⭐ | 少量 | ⭐⭐⭐ |

在生产环境中，推荐的方案通常是**混合策略**：
1. 首先用 Token 硬限制作为最后的安全网，确保永远不会溢出。
2. 在 Token 消耗达到阈值的 60%-70% 时，触发摘要压缩来保留关键上下文。
3. 如果模型提供了超大窗口（如 Gemini 的 1M Token），可以只用简单的滑动窗口，不必过度工程化。

---

## 课后练习

1. **多会话数据持久化**：目前 `SessionManager` 中的会话数据全部存在内存中，程序一关闭就丢失了。尝试使用 `json` 模块或 `sqlite3`，将每个 Session 的消息历史保存到本地文件或数据库中，使其在程序重启后仍然可用。

2. **Token 压缩可视化实验**：修改 `05_context_window.py`，打印每一次压缩前后的 Token 变化量和保留的摘要内容，直观感受摘要压缩保留了哪些信息、丢弃了哪些信息。

3. **实现会话导出功能**：为 `06_chat_app.py` 添加一个 `/export` 命令，将当前会话的所有对话历史导出为格式整洁的 Markdown 文件（带时间戳、角色标注），方便后续复查。

4. **Flake8 自检**：确保你修改后的代码，能够通过 `flake8 project_02_chat_agent/` 的检查。
