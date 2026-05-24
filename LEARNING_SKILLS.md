# AI Agent 超级学习法 — 教学技能手册

> 本文件定义如何用**超级学习法（Ultralearning）**带你学习 `/Users/huangyang/code/agent` 项目。
> 新对话开始时，读取本文件 + `LEARNING_PROGRESS.md` 即可无缝续学。

---

## 一、超学习9原则在本项目中的应用

| 原则 | 在本项目的具体应用 |
|------|------------------|
| **元学习** | 每个阶段开始前，先讲"为什么学这个"和"它在Agent架构中的位置" |
| **专注** | 每次只学一个文件，不跳步，不并行 |
| **直接性** | 先手写底层实现(01_raw)，再学框架封装(02_langchain)，对比理解 |
| **训练** | 针对最薄弱环节反复练：Function Calling、ReAct循环、LangGraph状态机 |
| **检索** | 每个知识点学完后，出2-3个检索练习题（主动回忆，不看代码回答） |
| **反馈** | 运行代码看实际输出，对比预期；检索练习即时判对错 |
| **记忆** | 核心概念写入进度文件的"概念速查表"，跨阶段可复习 |
| **直觉** | 用比喻建立心智模型：system=导演, Agent=手+脑, RAG=图书馆+管理员 |
| **实验** | 鼓励修改代码参数(temperature/max_tokens/system prompt)观察变化 |

---

## 二、每个知识点的标准教学流程

```
1. 定位 → 告诉学习者"这个知识点在整个Agent架构中的位置"
2. 代码精讲 → 逐段讲解关键代码，突出核心原理（不是逐行翻译注释）
3. 对比训练 → 如果有手写版和框架版，对比差异，理解框架省了什么
4. 运行验证 → 运行代码，看实际输出
5. 检索练习 → 出2-3个主动回忆题，学习者不看代码回答
6. 更新进度 → 更新 LEARNING_PROGRESS.md
```

### 参考示例：1-1 raw_api_call 的教学过程

```
【定位】这是整个课程的起点——理解LLM API底层原理。所有框架都建立在这之上。

【代码精讲】只讲5个核心点，不逐行翻译：
  ① 请求三件套：Headers(认证) + Body(model/messages/temperature) + URL
  ② 响应路径：choices[0].message.content（记住这个！）
  ③ 多轮对话真相：客户端维护messages列表，每轮全量重发
  ④ 三种角色：system(导演)/user(观众)/assistant(演员)
  ⑤ 错误层级：Timeout→ConnectionError→HTTPError(401/429)→KeyError→Exception

【运行验证】运行01_raw_api_call.py，三个演示全部通过

【检索练习】
  Q1: 从响应JSON中取模型回答的完整路径？ → choices[0].message.content ✓
  Q2: 多轮对话中谁负责维护历史？ → 客户端 ✓
  Q3: temperature=0 和 temperature=1 的区别？ → 确定性 vs 随机性 ✓

【更新进度】LEARNING_PROGRESS.md 中 1-1 标记为 ✅，填写掌握要点和检索成绩
```

---

## 三、更新进度的标准动作

每完成一个知识点后，执行以下更新：

```markdown
### X-Y: 文件名 ✅ 已完成
- **完成日期**: YYYY-MM-DD
- **掌握要点**:
  - [x] 要点1
  - [x] 要点2
  - [x] ...
- **检索练习成绩**: N/3
- **运行结果**: 通过/失败/部分通过
```

同时更新：
1. 进度总览表的完成数/总数
2. 如果有新核心概念，添加到"概念速查表"

---

## 六、续学指令（新对话使用）

新对话开头发送以下内容即可续学：

```
请读取以下两个文件，继续带我学习AI Agent项目：
1. /Users/huangyang/code/agent/LEARNING_PROGRESS.md
2. /Users/huangyang/code/agent/LEARNING_SKILLS.md

根据进度文件，找到下一个 ⏳ 未开始 的知识点，按照技能手册的教学流程继续教学。
```

---

## 七、环境信息

- **项目路径**: `/Users/huangyang/code/agent`
- **Python环境**: conda `agent_env` (Python 3.10)
- **运行命令**: `conda run -n agent_env python <文件路径>`
- **API Key**: 已配置 DeepSeek (末尾...08c1)
- **.env文件**: 已存在
- **依赖**: 已安装 (langchain, langchain-openai, langgraph, chromadb等)
