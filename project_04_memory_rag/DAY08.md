# Day 8 课程：长期记忆 — 让 Agent 跨会话记住你 💾

在 Day 3-4 中，我们为 Agent 实现了短期记忆（对话历史列表）。但这种记忆存在一个致命缺陷：**程序一关闭，所有记忆全部消失。**

今天我们要解决这个问题，让 Agent 具备**长期记忆 (Long-term Memory)** 能力——即使重启程序、甚至换一台电脑，Agent 依然能记住你是谁、你的偏好、你上次聊了什么。

---

## 目录
1. [学习目标](#学习目标)
2. [第一部分：短期记忆深化复习](#第一部分短期记忆深化复习)
3. [第二部分：长期记忆的设计与实现](#第二部分长期记忆的设计与实现)
4. [第三部分：集成记忆的完整 Agent](#第三部分集成记忆的完整-agent)
5. [核心原理深度解析](#核心原理深度解析)
6. [课后练习](#课后练习)

---

## 学习目标
- 深入理解短期记忆与长期记忆在工程上的区别。
- 掌握使用 SQLite 实现跨会话的持久化记忆存储。
- 学会设计"事实记忆"与"偏好记忆"的数据模型。
- 构建一个能跨会话记住用户信息的完整 Agent。

---

## 第一部分：短期记忆深化复习

### 1. 记忆分类体系

在 Agent 架构中，记忆可以分为三个层次：

```
Agent 记忆体系
├── 短期记忆 (Short-term / Working Memory)
│   ├── 本质：当前会话的消息列表 List[Message]
│   ├── 生命周期：程序运行期间
│   └── 作用：维持多轮对话的连贯性
│
├── 长期记忆 (Long-term Memory)
│   ├── 本质：持久化存储的结构化数据（SQLite / Redis / PostgreSQL）
│   ├── 生命周期：永久（直到主动删除）
│   └── 作用：跨会话记住用户身份、偏好、重要事实
│
└── 语义记忆 (Semantic Memory / Knowledge)
    ├── 本质：向量化的外部知识库（Embedding + 向量数据库）
    ├── 生命周期：永久
    └── 作用：让 Agent 基于私有文档回答问题（RAG）
```

今天我们聚焦于**长期记忆**，语义记忆（RAG）将在 Day 9-10 详细讲解。

### 2. 短期记忆的局限性回顾

| 局限 | 具体表现 |
|------|---------|
| 易失性 | 程序重启后所有对话历史清空 |
| 无法跨会话 | 上午和下午的对话完全独立，Agent 不知道你是同一个人 |
| Token 膨胀 | 长对话导致消息列表无限增长，可能超出上下文窗口 |
| 无结构化 | 记忆是原始的消息文本，无法高效地检索特定信息 |

> 📖 **代码实战**：查看并运行 [01_short_term_memory.py](file:///Users/huangyang/code/agent/project_04_memory_rag/01_short_term_memory.py)

---

## 第二部分：长期记忆的设计与实现

### 1. 长期记忆存什么？

与短期记忆（存原始消息列表）不同，长期记忆存储的是**经过提炼的结构化信息**：

| 记忆类型 | 示例 | 存储格式 |
|---------|------|---------|
| 用户身份 | "用户名字是张三" | `{"key": "user_name", "value": "张三"}` |
| 用户偏好 | "喜欢用 Python，偏好简洁风格" | `{"key": "coding_style", "value": "简洁"}` |
| 重要事实 | "用户正在学习 AI Agent 开发" | `{"key": "learning_topic", "value": "AI Agent"}` |
| 对话摘要 | "上次讨论了 LangChain 的 LCEL 链" | `{"key": "last_topic", "value": "LCEL"}` |

### 2. 使用 SQLite 实现持久化

我们选择 **SQLite** 作为长期记忆的存储引擎。它是 Python 内置的轻量级关系型数据库，无需安装任何额外软件，数据以单个 `.db` 文件保存在本地。

#### 数据库表设计

```sql
-- 用户记忆表：存储经过提炼的结构化记忆
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,           -- 用户标识
    memory_key TEXT NOT NULL,        -- 记忆键（如 "user_name"）
    memory_value TEXT NOT NULL,      -- 记忆值（如 "张三"）
    category TEXT DEFAULT 'general', -- 分类（identity/preference/fact）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 对话历史表：持久化保存完整的对话记录
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,        -- 会话 ID
    user_id TEXT NOT NULL,           -- 用户标识
    role TEXT NOT NULL,              -- 消息角色（system/user/assistant）
    content TEXT NOT NULL,           -- 消息内容
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### MemoryStore 类设计

```python
class MemoryStore:
    """长期记忆存储管理器。

    使用 SQLite 实现跨会话的持久化记忆存储。

    Attributes:
        db_path: SQLite 数据库文件路径。
    """

    def save_memory(self, user_id, key, value, category="general"):
        """保存一条记忆（如已存在则更新）。"""

    def get_memory(self, user_id, key):
        """获取指定键的记忆值。"""

    def get_all_memories(self, user_id):
        """获取用户的所有记忆。"""

    def delete_memory(self, user_id, key):
        """删除指定记忆。"""

    def search_memories(self, user_id, keyword):
        """按关键词搜索记忆。"""
```

### 3. 记忆的自动提取

让 Agent 自动从对话中提取值得记住的信息，是长期记忆系统的核心挑战。我们通过一条专门的"记忆提取 Prompt"来实现：

```python
MEMORY_EXTRACTION_PROMPT = """
分析以下对话内容，提取其中值得长期记忆的信息。

提取规则：
1. 用户的个人信息（姓名、职业、年龄等）
2. 用户的偏好（喜欢的编程语言、学习风格等）
3. 重要的事实（正在进行的项目、学习目标等）
4. 不要提取临时性的、无长期价值的信息

输出格式（JSON 数组）：
[
  {"key": "user_name", "value": "张三", "category": "identity"},
  {"key": "fav_language", "value": "Python", "category": "preference"}
]

如果没有值得记忆的信息，返回空数组 []。

对话内容：
{conversation}
"""
```

> 📖 **代码实战**：查看并运行 [02_long_term_memory.py](file:///Users/huangyang/code/agent/project_04_memory_rag/02_long_term_memory.py)

---

## 第三部分：集成记忆的完整 Agent

### 1. 架构设计

```
MemoryAgent
├── ShortTermMemory          # 当前会话的消息列表
├── LongTermMemory           # SQLite 持久化存储
│   ├── MemoryStore          # 结构化记忆的 CRUD
│   └── ChatHistoryStore     # 对话历史的持久化
├── MemoryExtractor          # 自动从对话中提取记忆
├── MemoryInjector           # 在每次对话开始时，将相关记忆注入 System Prompt
└── LLM                      # 大模型
```

### 2. 记忆注入流程

每次用户发送新消息时，Agent 在调用大模型之前，会先从长期记忆中检索相关信息，并将其注入到 System Prompt 中：

```
步骤 1: 用户发送 "帮我写一个排序算法"
           │
步骤 2: 从 SQLite 检索该用户的记忆
        → user_name: "张三"
        → fav_language: "Python"
        → coding_style: "简洁，多注释"
           │
步骤 3: 动态构建 System Prompt:
        "你是一个编程助手。
         当前用户信息：
         - 姓名：张三
         - 偏好语言：Python
         - 编码风格：简洁，多注释
         请根据用户偏好进行回答。"
           │
步骤 4: 将完整的 messages 列表发送给大模型
           │
步骤 5: 大模型回答后，触发记忆提取器分析本轮对话
        → 如有新的值得记忆的信息，写入 SQLite
```

### 3. 跨会话演示

```
=== 会话 1（上午 10:00）===
用户 > 你好，我叫张三，我正在学习 AI Agent 开发
🤖 AI > 你好张三！很高兴认识你，学习 AI Agent 开发是一个很好的方向...
💾 [记忆保存] user_name=张三, learning_topic=AI Agent

用户 > 我比较喜欢用 Python，代码风格偏好简洁
🤖 AI > 了解了！Python 确实很适合 AI 开发...
💾 [记忆保存] fav_language=Python, coding_style=简洁

=== 程序关闭并重启 ===

=== 会话 2（下午 15:00）===
用户 > 你好
🤖 AI > 张三你好！欢迎回来！上次我们聊到了 AI Agent 开发，今天要继续吗？
🧠 [记忆加载] user_name=张三, learning_topic=AI Agent
```

> 📖 **代码实战**：查看并运行 [03_memory_agent.py](file:///Users/huangyang/code/agent/project_04_memory_rag/03_memory_agent.py)

---

## 核心原理深度解析

### 长期记忆 vs. RAG 的区别

初学者容易混淆长期记忆和 RAG（检索增强生成），它们虽然都涉及"存储和检索"，但职责完全不同：

| 维度 | 长期记忆 (Long-term Memory) | RAG (检索增强生成) |
|------|---------------------------|-------------------|
| 存什么 | 用户的个人信息、偏好、历史行为 | 外部文档、知识库、FAQ |
| 数据来源 | 从对话中自动提取 | 人工导入或爬取 |
| 检索方式 | 按 Key 精确查询 | 按语义相似度模糊检索 |
| 存储技术 | 关系型数据库（SQLite） | 向量数据库（ChromaDB） |
| 更新频率 | 每次对话后可能更新 | 通常批量更新 |
| 用途 | 个性化回答、记住用户 | 基于私有知识回答问题 |

### 记忆提取的两种策略

| 策略 | 实现方式 | 优点 | 缺点 |
|------|---------|------|------|
| 显式提取 | 每轮对话后用额外的 LLM 调用分析并提取 | 准确率高 | 额外消耗 Token 和时间 |
| 隐式提取 | 用规则/正则匹配关键短语（如"我叫..."） | 零额外成本 | 只能覆盖预定义的模式 |

在学习阶段，我们使用**显式提取**来确保体验效果。在生产环境中，通常采用混合方案：先用规则快速匹配，匹配不到时再回退到 LLM 提取。

---

## 课后练习

1. **记忆管理命令**：为 Agent 添加 `/memories` 命令，显示当前用户的所有长期记忆；添加 `/forget <key>` 命令，允许用户主动删除某条记忆。

2. **记忆冲突处理**：当新提取的记忆与已有记忆冲突时（例如用户说"我改名叫李四了"），如何智能地更新而不是重复存储？实现一个冲突检测与合并机制。

3. **对话历史持久化**：将 `ChatHistoryStore` 与 Day 4 的 `SessionManager` 结合，实现"程序重启后恢复上次的对话历史"功能。

4. **Flake8 自检**：确保代码通过 `flake8 project_04_memory_rag/` 的检查。
