# AI Agent 学习课程前 3 天内容 Walkthrough 🎓

我们已经完成了前 3天详细的课程代码开发。这些代码以由浅入深的方式，为你剖析了从最底层的 API 网络请求，到使用 LangChain 框架进行模型调用、Prompt 管理、输出解析、流式渲染，最后实现带记忆和系统角色的命令行 Agent 全过程。

---

## 🛠️ 环境准备与基础配置

在开始运行任何课程代码之前，你需要进行以下两步准备：

1. **安装依赖**：
   在终端运行：
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**：
   复制项目根目录下的 `.env.example` 为 `.env`，并填入你真实的大模型 API Key：
   ```bash
   cp .env.example .env
   ```
   编辑 `.env` 文件填入至少一个 Key（推荐使用 **DeepSeek**，或者 **Qwen / Gemini** 等）：
   ```text
   DEEPSEEK_API_KEY=sk-xxxxxx
   ```

---

## 📁 课程内容结构与运行说明

### 🌟 公共模块 (common/)

- **[common/config.py](file:///Users/huangyang/code/agent/common/config.py)**：负责读取 `.env` 环境变量，统一管理国内模型（DeepSeek、Qwen、GLM、Kimi）和 Gemini 的 API 地址与名称。
- **[common/model_factory.py](file:///Users/huangyang/code/agent/common/model_factory.py)**：大模型实例的工厂类，屏蔽了各大厂商 SDK 接口不同的细节。使用工厂模式，通过一行代码 `create_model("deepseek")` 即可创建一个标准的聊天模型实例。

---

### 📅 Day 1：API 基础与 LangChain 模型入门

该阶段的重点是理解网络交互底层原理，并平滑过渡到 LangChain 模型调用。

#### 1. [01_raw_api_call.py](file:///Users/huangyang/code/agent/project_01_basics/01_raw_api_call.py)
* **内容**：不依赖任何第三方 AI 框架，仅使用 Python 标准 `requests` 库向 DeepSeek 的 OpenAI 兼容接口发送 HTTP POST 请求。
* **学习要点**：
  - 了解大模型接口的标准请求结构（Authorization Bearer Token、Content-Type）。
  - 熟悉 Payload Body 中的 messages 列表格式（system / user / assistant 角色）。
  - 手动管理对话上下文，通过 `messages.append` 实现一个多轮对话的死循环。
* **运行方法**：
  ```bash
  python project_01_basics/01_raw_api_call.py
  ```

#### 2. [02_langchain_models.py](file:///Users/huangyang/code/agent/project_01_basics/02_langchain_models.py)
* **内容**：使用 LangChain 的 `ChatOpenAI`（通过工厂模式）替代手动网络请求，并深入对比二者区别。
* **学习要点**：
  - 理解 LangChain 的三类基础消息对象：`SystemMessage`（系统设定）、`HumanMessage`（用户输入）、`AIMessage`（模型回答）。
  - 查看和解析 `model.invoke()` 返回的 `AIMessage` 结构，获取包含的 metadata。
* **运行方法**：
  ```bash
  python project_01_basics/02_langchain_models.py
  ```

#### 3. [03_model_comparison.py](file:///Users/huangyang/code/agent/project_01_basics/03_model_comparison.py)
* **内容**：让本地配置的多个大模型（如 DeepSeek 与 Gemini 等）同台竞技，回答同一组问题（涵盖问答、诗歌创意、逻辑谜题）。
* **学习要点**：
  - 学习如何通过 `list_available_providers()` 检测已配置的模型。
  - 对比不同大模型在生成速度（Token/s）、准确度、文学表达上的差异。
* **运行方法**：
  ```bash
  python project_01_basics/03_model_comparison.py
  ```

---

### 📅 Day 2：Prompt 工程 + Chain 组合 (LCEL)

该阶段的重点是学习如何将 prompt 模板化、如何让模型返回干净的结构化数据，以及如何使用管道操作符 `|` 构建应用链。

#### 4. [04_prompt_templates.py](file:///Users/huangyang/code/agent/project_01_basics/04_prompt_templates.py)
* **内容**：精讲 LangChain 中的 `PromptTemplate`（字符串模板）与 `ChatPromptTemplate`（聊天消息模板）。
* **学习要点**：
  - 掌握模板变量注入（`format`）。
  - 学习 `partial`（部分预填充变量，如时间或固定设定）。
  - 了解 `MessagesPlaceholder` 在占位历史消息时的核心作用。
* **运行方法**：
  ```bash
  python project_01_basics/04_prompt_templates.py
  ```

#### 5. [05_output_parsers.py](file:///Users/huangyang/code/agent/project_01_basics/05_output_parsers.py)
* **内容**：攻克“大模型不稳定返回纯文本”的痛点，学习将结果解析为纯字符串、JSON 字典，甚至严格的 Pydantic 模型对象。
* **学习要点**：
  - 掌握 `PydanticOutputParser` 与 Pydantic 数据类的绑定。
  - 理解解析器底层利用 System Prompt 自动要求模型以 JSON 格式输出的原理（`get_format_instructions()`）。
* **运行方法**：
  ```bash
  python project_01_basics/05_output_parsers.py
  ```

#### 6. [06_lcel_chains.py](file:///Users/huangyang/code/agent/project_01_basics/06_lcel_chains.py)
* **内容**：系统讲解 LangChain 独创的表达式语言 LCEL。
* **学习要点**：
  - 掌握 `prompt | model | parser` 的链式逻辑（重写 `__or__` 魔法方法实现的管道）。
  - 使用 `RunnablePassthrough` 在链式传递中透传或动态生成输入。
  - 使用 `RunnableLambda` 将自定义的纯 Python 业务逻辑函数无缝塞进链中。
  - 对比单次执行 `.invoke()` 与多输入并发批量执行 `.batch()` 的效率差异。
* **运行方法**：
  ```bash
  python project_01_basics/06_lcel_chains.py
  ```

#### 7. [07_streaming.py](file:///Users/huangyang/code/agent/project_01_basics/07_streaming.py)
* **内容**：演示如何让 AI 回答像打字机一样逐字吐出，告别长时间等待。
* **学习要点**：
  - 使用 `model.stream()` 和 `chain.stream()` 代替 `invoke`。
  - 异步处理的流式演示（`astream` 概念）。
  - 封装一个通用的打字效果打印函数 `stream_print`。
* **运行方法**：
  ```bash
  python project_01_basics/07_streaming.py
  ```

---

### 📅 Day 3：构建对话 Agent（从零理解 Agent）

进入 `project_02_chat_agent`。从这一天起，我们的代码将正式具备 Agent 的核心结构——感知（输入）、思考（LLM）与状态/记忆的维护。

#### 8. [project_02_chat_agent/config.py](file:///Users/huangyang/code/agent/project_02_chat_agent/config.py)
* **内容**：Day 3 项目的专属配置文件。定义了 Agent 运行的默认参数，并为 AI 预定义了 4 套各具特色的“面具提示词”（System Prompt）：
  1. 默认通用助手
  2. Python 编程导师
  3. 中英互译专家
  4. 苏格拉底式提问导师

#### 9. [01_simple_chatbot.py](file:///Users/huangyang/code/agent/project_02_chat_agent/01_simple_chatbot.py)
* **内容**：实现最简命令行对话控制台。
* **学习要点**：
  - 彻底搞懂无记忆状态下的对话局限（LLM 本身是没有服务器Session的，每次调用都是全新冷启动）。
  - 美化终端输入输出交互，支持输入 `clear` 清屏，`exit` 优雅退出。
* **运行方法**：
  ```bash
  python project_02_chat_agent/01_simple_chatbot.py
  ```

#### 10. [02_chat_with_history.py](file:///Users/huangyang/code/agent/project_02_chat_agent/02_chat_with_history.py)
* **内容**：为 Agent 注入“短期记忆”的能力。
* **学习要点**：
  - 实现自定义的 `ChatHistory` 类，自动保存每一轮的 `HumanMessage` 和 `AIMessage`。
  - 理解记忆的工程本质：每次对话时，将历史消息追加在一起，作为完整的 List 发送给模型。
  - 支持 `/history` 命令回看当前占用的上下文消息量，感受 Token 的随时间累积。
* **运行方法**：
  ```bash
  python project_02_chat_agent/02_chat_with_history.py
  ```

#### 11. [03_chat_with_persona.py](file:///Users/huangyang/code/agent/project_02_chat_agent/03_chat_with_persona.py)
* **内容**：打造个性化角色扮演 Agent。
* **学习要点**：
  - 通过注入首个 `SystemMessage` 的内容改变大模型的思考逻辑与人格倾向。
  - 允许在运行中通过交互菜单切换角色（通过输入 `/role` 命令）。
  - 了解角色切换时，自动清除旧历史以防止角色错乱和上下文污染。
* **运行方法**：
  ```bash
  python project_02_chat_agent/03_chat_with_persona.py
  ```

---

## 📌 代码质量与规范说明

所有生成的代码文件均严格按照你的要求进行开发，做到了：
- **每一行代码都添加了中文注释**：详细标注了每一步操作的意图，解释了为什么这样做。
- **杜绝高级/复杂语法**：没有使用三元运算符（单行 `if-else`），没有使用复杂的单行列表推导式，所有条件判断都是标准的多行缩进代码块，易于新手阅读。
- **完善的 Docstring**：每一个函数和类均拥有规范的 Docstring，清晰列出功能、参数类型、返回值。
