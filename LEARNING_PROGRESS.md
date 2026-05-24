# AI Agent 学习进度跟踪

> 最后更新：2025-05-24
> 学习方法：超级学习法（Ultralearning）
> 当前状态：**阶段1 进行中**

---

## 进度总览

| 阶段 | 名称 | 文件数 | 状态 | 完成数/总数 |
|------|------|--------|------|------------|
| 阶段1 | API基础与LangChain入门 | 7 | 🔄 进行中 | 2/7 |
| 阶段2 | 构建对话Agent | 7 | ⏳ 未开始 | 0/7 |
| 阶段3 | 工具调用Agent (Function Calling) | 7 | ⏳ 未开始 | 0/7 |
| 阶段4 | 记忆与RAG | 10 | ⏳ 未开始 | 0/10 |
| 阶段5 | 高级Agent模式 | 8 | ⏳ 未开始 | 0/8 |
| 阶段6 | 多Agent协作系统 | 11 | ⏳ 未开始 | 0/11 |
| 毕业一 | 企业级RAG | 0(待开发) | ⏳ 未开始 | 0/? |
| 毕业二 | 自动化流程Agent | 0(待开发) | ⏳ 未开始 | 0/? |
| 毕业三 | 多智能体协同开发 | 0(待开发) | ⏳ 未开始 | 0/? |

---

## 阶段1：API基础与LangChain入门

### 1-1: 01_raw_api_call.py (403行) ✅ 已完成
- **完成日期**: 2025-05-24
- **掌握要点**:
  - [x] LLM API = HTTP POST + JSON
  - [x] 请求三件套：Headers(认证) + Body(model/messages/temperature) + URL
  - [x] 响应路径：choices[0].message.content
  - [x] 多轮对话 = 客户端维护messages列表，每轮全量重发
  - [x] 三种角色：system(导演) / user(观众) / assistant(演员)
  - [x] 错误处理层级：Timeout→ConnectionError→HTTPError→KeyError→Exception
  - [x] temperature参数：0=确定 1=随机
- **检索练习成绩**: 3/3 全对
- **运行结果**: 三个演示全部通过

### 1-2: 02_langchain_models.py (370行) ✅ 已完成
- **完成日期**: 2025-05-24
- **掌握要点**:
  - [x] LangChain封装对比：手写40行 → LangChain 1行
  - [x] 工厂函数 create_model("deepseek") 一行切换模型
  - [x] 消息对象化：SystemMessage/HumanMessage/AIMessage（类型安全）
  - [x] invoke()返回值：result.content / result.response_metadata / result.usage_metadata
  - [x] 对比训练法：先手写理解原理，再看框架省了什么
- **检索练习成绩**: 待回答
- **运行结果**: 演示1~3通过（多模型对比演示超时）

### 1-3: 03_model_comparison.py (401行) ⏳ 未开始
### 1-4: 04_prompt_templates.py (522行) ⏳ 未开始
### 1-5: 05_output_parsers.py (530行) ⏳ 未开始
### 1-6: 06_lcel_chains.py (665行) ⏳ 未开始
### 1-7: 07_streaming.py (503行) ⏳ 未开始

---

## 阶段2：构建对话Agent

### 2-1: 01_simple_chatbot.py (269行) ⏳ 未开始
### 2-2: 02_chat_with_history.py (508行) ⏳ 未开始
### 2-3: 03_chat_with_persona.py (562行) ⏳ 未开始
### 2-4: 04_session_manager.py (460行) ⏳ 未开始
### 2-5: 05_context_window.py (469行) ⏳ 未开始
### 2-6: 06_chat_app.py (917行) ⏳ 未开始
### 2-config: config.py (179行) ⏳ 未开始

---

## 阶段3：工具调用Agent (Function Calling)

### 3-1: 01_function_calling_raw.py (271行) ⏳ 未开始
### 3-2: 02_langchain_tools.py (175行) ⏳ 未开始
### 3-3: 03_tool_binding.py (214行) ⏳ 未开始
### 3-4: 04_agent_loop.py (173行) ⏳ 未开始
### 3-5: 05_error_handling.py (206行) ⏳ 未开始
### 3-6: 06_langgraph_agent.py (232行) ⏳ 未开始
### 3-7: 07_tool_agent_complete.py (540行) ⏳ 未开始
### 3-tools: tools/ (5个工具文件) ⏳ 未开始

---

## 阶段4：记忆与RAG

### 4-1: 01_short_term_memory.py (117行) ⏳ 未开始
### 4-2: 02_long_term_memory.py (359行) ⏳ 未开始
### 4-3: 03_memory_agent.py (267行) ⏳ 未开始
### 4-4: 04_embedding_basics.py (125行) ⏳ 未开始
### 4-5: 05_vector_store.py (152行) ⏳ 未开始
### 4-6: 06_document_loader.py (155行) ⏳ 未开始
### 4-7: 07_text_splitter.py (140行) ⏳ 未开始
### 4-8: 08_simple_rag.py (241行) ⏳ 未开始
### 4-9: 09_rag_agent.py (371行) ⏳ 未开始
### 4-10: 10_knowledge_base_app.py (532行) ⏳ 未开始

---

## 阶段5：高级Agent模式

### 5-1: 01_react_concept.py (227行) ⏳ 未开始
### 5-2: 02_langgraph_react.py (180行) ⏳ 未开始
### 5-3: 03_react_with_tools.py (245行) ⏳ 未开始
### 5-4: 04_plan_and_execute.py (342行) ⏳ 未开始
### 5-5: 05_dynamic_replanning.py (420行) ⏳ 未开始
### 5-6: 06_self_reflection.py (278行) ⏳ 未开始
### 5-7: 07_human_in_the_loop.py (407行) ⏳ 未开始
### 5-8: 08_super_agent.py (713行) ⏳ 未开始

---

## 阶段6：多Agent协作系统

### 6-1: 01_multi_agent_concepts.py (148行) ⏳ 未开始
### 6-2: 02_agent_communication.py (239行) ⏳ 未开始
### 6-3: 03_supervisor_pattern.py (425行) ⏳ 未开始
### 6-4: 04_collaborative_agents.py (240行) ⏳ 未开始
### 6-5: 05_research_team/ (6个文件) ⏳ 未开始

---

## 毕业项目

### 毕业一: project_07_enterprise_rag/ ⏳ 未开始（代码待开发）
### 毕业二: project_08_workflow_agent/ ⏳ 未开始（代码待开发）
### 毕业三: project_09_dev_team/ ⏳ 未开始（代码待开发）

---

## 各阶段教学策略（按需参考）

### 阶段1：API基础与LangChain入门（1-1 到 1-7）
**策略：对比训练法** — 每个概念都有手写版和框架版

| 文件 | 教学重点 | 核心问题 | 比喻/直觉 |
|------|---------|---------|----------|
| 1-1 raw_api_call | HTTP底层原理 | API请求的本质是什么？ | API = 快递：你填单子发出去，收到包裹 |
| 1-2 langchain_models | 框架封装 | LangChain帮你省了什么？ | 手写 = 自己做饭，LangChain = 外卖 |
| 1-3 model_comparison | 多模型对比 | 不同模型风格差异？ | 同一问题问不同人 |
| 1-4 prompt_templates | 变量注入 | 怎么让Prompt可复用？ | 模板 = 填空题，变量 = 空格处 |
| 1-5 output_parsers | 结构化输出 | 怎么让模型输出JSON？ | 解析器 = 翻译官，把自然语言翻成结构化数据 |
| 1-6 lcel_chains | LCEL管道 | prompt \| model \| parser 怎么理解？ | 管道 = 工厂流水线，上一个工序的输出=下一个的输入 |
| 1-7 streaming | 流式输出 | 怎么实现打字机效果？ | 流式 = 水龙头滴水，非流式 = 一桶水倒出 |

### 阶段2：构建对话Agent（2-1 到 2-6）
**策略：渐进构建法** — 从最简chatbot逐步增加功能

| 文件 | 教学重点 | 核心问题 | 比喻/直觉 |
|------|---------|---------|----------|
| 2-1 simple_chatbot | 最小对话循环 | Agent最简形态？ | while True: 问→答 |
| 2-2 chat_with_history | 消息历史 | 怎么让Agent"记住"？ | 记忆 = 聊天记录本，每次翻开看 |
| 2-3 chat_with_persona | 角色扮演 | 怎么让Agent有人设？ | system prompt = 剧本，Agent = 演员 |
| 2-4 session_manager | 多会话管理 | 多用户同时聊天？ | 会话 = 包间，管理 = 领班 |
| 2-5 context_window | Token窗口 | 对话太长怎么办？ | 滑动窗口 = 望远镜，只看最近N条 |
| 2-6 chat_app | 综合应用 | 所有功能串起来 | 集大成 = 装满零件的机器人 |

**关键直觉**：这个阶段的"记忆"只是**内存中的列表**，重启就没了。阶段4才做持久化。

### 阶段3：工具调用Agent（3-1 到 3-7）⭐ 最核心
**策略：底层优先法** — 先手写Function Calling全生命周期

| 文件 | 教学重点 | 核心问题 | 比喻/直觉 |
|------|---------|---------|----------|
| 3-1 function_calling_raw | Function Calling底层 | 模型怎么"动手"？ | 模型=大脑(只思考)，工具=手(执行)，Function Calling=神经连接 |
| 3-2 langchain_tools | @tool装饰器 | 怎么快速创建工具？ | @tool = 自动说明书生成器 |
| 3-3 tool_binding | bind_tools | 怎么告诉模型有哪些工具？ | 绑定 = 把工具清单递给大脑 |
| 3-4 agent_loop | Agent循环 | Agent怎么决定用哪个工具？ | 循环 = 想→做→看→想→做→看...直到完成 |
| 3-5 error_handling | 错误处理 | 工具调用失败怎么办？ | 重试 = 跌倒了爬起来 |
| 3-6 langgraph_agent | LangGraph状态机 | 怎么用图结构编排Agent？ | 状态机 = 地铁线路图，节点=站，边=轨道 |
| 3-7 tool_agent_complete | 完整Agent | 所有能力集成 | 集大成 = 全副武装的Agent |

**重点精讲 3-1**：手写Function Calling是整个课程最关键的一步：
```
用户提问 → 模型看到tools列表 → 模型输出tool_calls(JSON) 
→ 代码解析JSON → 执行函数 → 结果作为新消息发回 
→ 模型看到结果 → 生成最终回答
```

### 阶段4：记忆与RAG（4-1 到 4-10）
**策略：原理先行法** — 先理解Embedding原理，再建RAG管道

| 文件 | 教学重点 | 核心问题 | 比喻/直觉 |
|------|---------|---------|----------|
| 4-1 short_term_memory | 短期记忆 | 复习阶段2的记忆机制 | 内存 = 草稿纸，关机就没了 |
| 4-2 long_term_memory | 长期记忆 | 怎么持久化？ | SQLite = 笔记本，永久保存 |
| 4-3 memory_agent | 记忆Agent | Agent怎么用记忆？ | 记忆Agent = 有记性的助手 |
| 4-4 embedding_basics | Embedding原理 | 文本怎么变向量？ | Embedding = 万物翻译器，把文字翻成坐标 |
| 4-5 vector_store | 向量库 | 怎么存和查向量？ | ChromaDB = 图书馆，向量 = 书的坐标 |
| 4-6 document_loader | 文档加载 | 怎么读各种文件？ | 加载器 = 扫描仪，把纸质文档变电子版 |
| 4-7 text_splitter | 文本分块 | 长文档怎么切？ | 分块 = 切蛋糕，要切得均匀又不断层 |
| 4-8 simple_rag | 完整RAG | RAG管道长什么样？ | RAG = 先查资料再回答，开卷考试 |
| 4-9 rag_agent | RAG Agent | RAG作为工具？ | RAG Agent = 带参考书的助手 |
| 4-10 knowledge_base_app | 综合应用 | 个人知识库 | 集大成 = 你的私人图书馆+管理员 |

**关键直觉**：RAG本质 = **开卷考试**，先找到相关资料，再基于资料回答。

### 阶段5：高级Agent模式（5-1 到 5-8）
**策略：模式对比法** — ReAct vs Plan-and-Execute vs Self-Reflection

| 文件 | 教学重点 | 核心问题 | 比喻/直觉 |
|------|---------|---------|----------|
| 5-1 react_concept | ReAct原理 | Thought→Action→Observation？ | ReAct = 边想边做，像解数学题打草稿 |
| 5-2 langgraph_react | LangGraph ReAct | 框架封装的ReAct？ | create_react_agent = 生产线 |
| 5-3 react_with_tools | ReAct+工具 | ReAct Agent实战 | 全副武装的思考者 |
| 5-4 plan_and_execute | 规划模式 | 先规划再执行？ | 规划 = 先画图纸再施工 |
| 5-5 dynamic_replanning | 动态重规划 | 计划赶不上变化？ | 重规划 = 施工中发现问题改图纸 |
| 5-6 self_reflection | 自我反思 | Agent怎么质检？ | 反思 = 写完作业自己检查一遍 |
| 5-7 human_in_the_loop | 人类介入 | 关键决策要人确认？ | 介入 = 自动驾驶偶尔要人接管 |
| 5-8 super_agent | 综合Agent | 全能力集成 | Super Agent = 钢铁侠 |

### 阶段6：多Agent协作（6-1 到 6-5）
**策略：架构演进法** — 单Agent → 主管模式 → 协作模式 → 团队

| 文件 | 教学重点 | 核心问题 | 比喻/直觉 |
|------|---------|---------|----------|
| 6-1 multi_agent_concepts | 架构模式 | 主从/对等/辩论？ | 架构 = 团队组织形式 |
| 6-2 agent_communication | 消息传递 | Agent怎么通信？ | 通信 = 传纸条/微信群 |
| 6-3 supervisor_pattern | 主管模式 | 一个Agent分配任务？ | 主管 = 部门经理 |
| 6-4 collaborative_agents | 协作模式 | 接力完成？ | 协作 = 接力赛 |
| 6-5 research_team | 综合项目 | AI调研团队 | 团队 = 调研员→分析师→作家 |

### 毕业项目教学策略
1. **先读DAY文档**：每个毕业项目都有DAY18~DAY23.md设计文档
2. **一起写代码**：不是直接给答案，而是引导学习者自己设计
3. **架构优先**：先画节点图(StateGraph)，再填节点实现
4. **增量验证**：每实现一个节点就运行测试

---

## 学习笔记

### 核心概念速查

| 概念 | 一句话解释 | 首次出现在 |
|------|-----------|-----------|
| LLM API | HTTP POST发JSON，返回JSON | 1-1 |
| choices[0].message.content | 从响应中取模型回答的通用路径 | 1-1 |
| 多轮对话 | 客户端维护messages列表，每轮全量重发 | 1-1 |
| system/user/assistant | 导演/观众/演员三种角色 | 1-1 |
| ChatOpenAI | LangChain封装的模型调用类 | 1-2 |
| create_model() | 工厂函数，一行切换模型 | 1-2 |
| SystemMessage/HumanMessage/AIMessage | 类型安全的消息对象 | 1-2 |
