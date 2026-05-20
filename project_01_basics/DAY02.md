# Day 2 课程：Prompt 工程、结构化输出与 LCEL 链式调用 ⚙️

在第一天掌握了大模型的调用和基本通信原理后，今天我们将进入大模型应用开发的核心篇章。我们将学习如何精细化控制大模型的输入（Prompt）、如何约束大模型的输出格式（Parser），以及如何像搭积木一样将它们串联成复杂的业务流（LCEL）。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：Prompt 模板化 (Prompt Templates)](#第一部分prompt-模板化-prompt-templates)
3. [第二部分：结构化输出解析 (Output Parsers)](#第二部分结构化输出解析-output-parsers)
4. [第三部分：LCEL 链式调用表达式 (Runnable)](#第三部分lcel-链式调用表达式-runnable)
5. [第四部分：流式交互原理与实现 (Streaming)](#第四部分流式交互原理与实现-streaming)
6. [课后练习](#课后练习)

---

## 学习目标
- 深入掌握 `PromptTemplate` 和 `ChatPromptTemplate` 的构建与参数动态填充。
- 熟练使用 `MessagesPlaceholder` 进行历史对话占位。
- 掌握让大模型输出干净、合规的 JSON 或 Pydantic 结构化数据的方法。
- 彻底搞懂 LCEL 的“管道符（`|`）”原理，学会使用 `RunnablePassthrough` 和 `RunnableLambda`。
- 掌握流式（Streaming）接口的调用和前端打字机效果的封装。

---

## 第一部分：Prompt 模板化 (Prompt Templates)

在第一天中，我们都是手写死字符串发给大模型。但在实际应用中，Prompt 往往需要包含**固定模板**和**动态变量**（比如用户的输入、当前的时间等）。

LangChain 提供了高度封装的模板工具：

### 1. `PromptTemplate`（针对普通文本字符串）
主要用于非对话型任务，底层类似于 Python 的 `str.format()` 封装：
```python
template = "请帮我把下面这段话翻译成{language}：\n{text}"
prompt = PromptTemplate.from_template(template)
formatted = prompt.format(language="英文", text="你好")
# 输出: "请帮我把下面这段话翻译成英文：\n你好"
```

### 2. `ChatPromptTemplate`（针对对话流）
对于 Agent 开发，我们更常用 `ChatPromptTemplate`。它可以组合多条不同角色（System, Human, AI）的消息：
```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个名叫{name}的专业翻译官。"),
    ("human", "请翻译这段话：{text}")
])
```

### 3. 高级用法
- **`partial` (部分预填充)**：如果某个变量在启动时就已经确定（例如当前日期），我们可以使用 `partial` 先锁定它，避免每次调用都重复传入。
- **`MessagesPlaceholder` (消息占位符)**：这是后续实现**对话记忆（Chat History）**的基石。它会在模板中占一个坑，后面可以动态塞入一个 `List[BaseMessage]` 历史列表。

> 📖 **代码实战**：查看并运行 [04_prompt_templates.py](file:///Users/huangyang/code/agent/project_01_basics/04_prompt_templates.py)

---

## 第二部分：结构化输出解析 (Output Parsers)

大模型默认返回的是没有格式保障的纯文本。如果我们想开发一个“图书分类 Agent”，需要它返回 JSON 格式如 `{"category": "科技", "tags": ["AI"]}`，直接让它输出，经常会夹杂解释性文字（如“好的，这是你要的JSON：...”），导致程序无法直接用 `json.loads` 解析。

LangChain 的 `OutputParser` 正是为解决这一痛点而生：

```
+--------+   格式化提示词    +-------+   纯文本结果    +--------+   结构化对象
| Parser | --------------> |  LLM  | --------------> | Parser | --------------> Python Dict / Pydantic
+--------+ (Format Instruct) +-------+ (含各种杂质)   +--------+ (提取和校验)
```

### 1. 常用解析器
- **`StrOutputParser`**：最简单的解析器，只做一件事——把 `AIMessage` 中的 `content` 纯文本提取出来，过滤掉其他元数据。
- **`JsonOutputParser`**：利用 Prompt 提示大模型必须返回 JSON，并在收到响应后，自动将字符串反序列化为 Python 字典 (`dict`)。
- **`PydanticOutputParser`**：最严格的解析器。我们需要定义一个 Pydantic 模型类（声明各字段的类型与描述），解析器会自动提取出完全符合该数据结构的 Python 类实例，如果格式不符还会抛出校验异常。

### 2. 原理：Format Instructions
解析器之所以能约束大模型输出，是因为它内部提供了 `parser.get_format_instructions()` 函数。这个函数会生成一段非常严格的系统提示词（告诉 LLM 应该用什么 JSON 结构，不能输出多余字符等），我们需要将这段提示词拼接到最终的 Prompt 中发给大模型。

> 📖 **代码实战**：查看并运行 [05_output_parsers.py](file:///Users/huangyang/code/agent/project_01_basics/05_output_parsers.py)

---

## 第三部分：LCEL 链式调用表达式 (Runnable)

在 LangChain 0.2/0.3 中，**LCEL (LangChain Expression Language)** 是构建链和 Agent 的标准方式。它最直观的特点是使用管道符 `|` 来拼装组件。

### 1. 管道符背后的魔法
当你写下 `chain = prompt | model | parser` 时，这并不是魔法，而是 Python 中**操作符重载**的应用。
LangChain 组件都继承自 `Runnable` 基类，重写了 `__or__` 和 `__ror__` 魔法方法：
```python
# 这两行代码在 Python 底层是完全等价的：
chain = prompt | model | parser
chain = parser.__ror__(model.__ror__(prompt))
```

### 2. LCEL 的优势
1. **统一的接口**：所有 LCEL 链都天然支持 `.invoke()` (同步单次调用)、`.batch()` (并发批量调用) 和 `.stream()` (流式调用)。
2. **异步支持**：每个方法都有对应的异步版本（如 `.ainvoke()`, `.abatch()`, `.astream()`）。
3. **内置并行化**：如果链中有可以并行的步骤，LCEL 会自动启用线程池并发执行，极大提高接口吞吐率。

### 3. Runnable 家族的核心成员
- **`RunnablePassthrough`**：透传组件。用于在链的输入端将数据原封不动地传下去，或者用于动态组装字典输入。
- **`RunnableLambda`**：自定义逻辑函数包装器。你可以把任何纯 Python 函数用它包装，这样就能无缝拼接到 `|` 管道中。

> 📖 **代码实战**：查看并运行 [06_lcel_chains.py](file:///Users/huangyang/code/agent/project_01_basics/06_lcel_chains.py)

---

## 第四部分：流式交互原理与实现 (Streaming)

大模型生成回答需要时间（通常需要几秒到十几秒）。如果等到所有文本都生成完再一次性返回，用户体验会非常糟糕。

### 1. 原理：服务器发送事件 (SSE)
大模型 API 支持流式输出，底层使用的是 HTTP 的 **SSE (Server-Sent Events)** 协议。
服务器不用一次性给出全部 Body，而是以 `text/event-stream` 的格式，源源不断地向客户端推送微小的字符块（Chunk），直到传输结束。

### 2. LangChain 中的流式处理
在 LCEL 链中，你可以直接调用 `.stream()` 代替 `.invoke()`：
```python
# 链的流式调用
for chunk in chain.stream({"input": "请写一首关于春天的诗"}):
    # 这里的 chunk 已经是被 StrOutputParser 解析出来的单字/单词字符串
    print(chunk, end="", flush=True)
```
我们还可以在代码里封装一个通用的 `stream_print` 函数，在终端中模拟像打字机一样丝滑的输出效果，并收集最终的完整文本以备后续业务处理。

> 📖 **代码实战**：查看并运行 [07_streaming.py](file:///Users/huangyang/code/agent/project_01_basics/07_streaming.py)

---

## 课后练习
1. **组合挑战**：结合今天学习的内容，自己构建一条链：
   - 输入：一篇打乱格式和夹带空格的用户输入。
   - 步骤一：通过 `RunnableLambda` 清除输入两端的空格。
   - 步骤二：使用 `ChatPromptTemplate` 提取文章中的关键实体（人名、地名）。
   - 步骤三：使用 `JsonOutputParser` 让模型返回结构化 JSON 实体字典。
2. **并发测试**：使用 `chain.batch()` 并发调用 3 个不同的 Prompt，打印并对比它们与单次调用 3 次的总时间耗时。
3. **Flake8 自检**：确保你修改后的代码，能够通过 `flake8` 的检查。
