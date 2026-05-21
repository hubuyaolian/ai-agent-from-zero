"""
Day 8 - 课程 2：长期记忆数据库的 CRUD 操作与大模型自动记忆提取。

学习目标：
    1. 掌握如何使用 SQLite 实现跨会话长期记忆的结构化保存。
    2. 掌握使用大模型 (LLM) 对对话记录进行结构化 JSON 事实与偏好提取。
    3. 实现将提取的信息自动持久化到本地 SQLite 数据库中。
"""

# 导入系统模块
import sys
# 导入系统路径模块
import os
# 导入 SQLite 模块
import sqlite3

# 取得当前脚本所在的绝对路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将项目根目录置入搜索路径首位
sys.path.insert(0, os.path.join(CURRENT_DIR, '..'))

# 从公共模块中导入模型构建工厂函数
from common.model_factory import create_model  # noqa: E402
# 从 LangChain 导入提示词模板类
from langchain_core.prompts import ChatPromptTemplate  # noqa: E402
# 从 LangChain 导入 JSON 输出解析器
from langchain_core.output_parsers import JsonOutputParser  # noqa: E402


class MemoryStore:
    """
    基于 SQLite 的长期记忆持久化存储管理器。
    """

    def __init__(self, db_path: str = None):
        """
        初始化 MemoryStore 并创建所需的数据库表。

        Args:
            db_path: 数据库文件的相对或绝对路径，默认在当前目录下创建 memories.db。
        """
        # 如果未传入数据库路径
        if db_path is None:
            # 默认建立在 project_04_memory_rag 文件夹下
            self.db_path = os.path.join(CURRENT_DIR, "memories.db")
        # 传入了路径
        else:
            # 使用指定路径
            self.db_path = db_path

        # 初始化数据库连接并创建表结构
        self._init_db()

    def _init_db(self):
        """
        在 SQLite 数据库中创建 memories 记忆信息表。
        """
        # 打开数据库连接
        conn = sqlite3.connect(self.db_path)
        # 获取游标
        cursor = conn.cursor()
        # 执行建表 SQL 语句，存储用户的关键事实和偏好信息
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                memory_key TEXT NOT NULL,
                memory_value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, memory_key)
            )
            """
        )
        # 提交数据库事务
        conn.commit()
        # 关闭连接
        conn.close()

    def save_memory(self, user_id: str, key: str, value: str, category: str = "general"):
        """
        存储或更新一条用户记忆（键值对）。

        Args:
            user_id: 用户的唯一标识 ID。
            key: 记忆键。
            value: 记忆值。
            category: 记忆分类（如 'identity'、'preference' 等）。
        """
        # 建立连接
        conn = sqlite3.connect(self.db_path)
        # 获取游标
        cursor = conn.cursor()
        # 覆盖更新相同 user_id 和 memory_key 的记录
        cursor.execute(
            """
            INSERT OR REPLACE INTO memories (
                user_id, memory_key, memory_value, category, updated_at
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (user_id, key.strip(), value.strip(), category.strip())
        )
        # 提交事务
        conn.commit()
        # 关闭连接
        conn.close()

    def get_memory(self, user_id: str, key: str) -> str:
        """
        根据指定键获取对应用户的一条长期记忆。

        Args:
            user_id: 用户唯一标识。
            key: 目标记忆键。

        Returns:
            若找到则返回记忆内容字符串；若不存在则返回 None。
        """
        # 建立连接
        conn = sqlite3.connect(self.db_path)
        # 获取游标
        cursor = conn.cursor()
        # 查询指定键值
        cursor.execute(
            "SELECT memory_value FROM memories WHERE user_id = ? AND memory_key = ?",
            (user_id, key)
        )
        # 提取单行记录
        row = cursor.fetchone()
        # 关闭连接
        conn.close()

        # 如果查询到了数据
        if row is not None:
            # 返回第一列内容
            return row[0]
        # 未查询到
        return None

    def get_all_memories(self, user_id: str) -> list:
        """
        获取指定用户的所有长期记忆列表。

        Args:
            user_id: 用户唯一标识。

        Returns:
            包含元组 [(key, value, category), ...] 的列表。
        """
        # 建立连接
        conn = sqlite3.connect(self.db_path)
        # 获取游标
        cursor = conn.cursor()
        # 按照分类排序查出所有记忆
        cursor.execute(
            "SELECT memory_key, memory_value, category FROM memories "
            "WHERE user_id = ? ORDER BY category",
            (user_id,)
        )
        # 获取全部记录行
        rows = cursor.fetchall()
        # 关闭连接
        conn.close()
        # 返回结果列表
        return rows

    def delete_memory(self, user_id: str, key: str) -> bool:
        """
        删除某条特定的记忆。

        Args:
            user_id: 用户唯一标识。
            key: 待删除的记忆键。

        Returns:
            布尔值，表示是否成功执行了删除。
        """
        # 建立连接
        conn = sqlite3.connect(self.db_path)
        # 获取游标
        cursor = conn.cursor()
        # 执行删除 SQL
        cursor.execute(
            "DELETE FROM memories WHERE user_id = ? AND memory_key = ?",
            (user_id, key)
        )
        # 获取受影响的行数
        rows_affected = cursor.rowcount
        # 提交事务
        conn.commit()
        # 关闭连接
        conn.close()

        # 如果影响行数大于 0
        if rows_affected > 0:
            # 返回删除成功
            return True
        # 未删掉任何数据
        return False

    def search_memories(self, user_id: str, keyword: str) -> list:
        """
        按关键词模糊搜索某位用户的长期记忆。

        Args:
            user_id: 用户唯一标识。
            keyword: 搜索关键词。

        Returns:
            匹配成功的记忆元组列表。
        """
        # 建立连接
        conn = sqlite3.connect(self.db_path)
        # 获取游标
        cursor = conn.cursor()
        # 模糊匹配 key 和 value
        cursor.execute(
            """
            SELECT memory_key, memory_value, category FROM memories
            WHERE user_id = ? AND (memory_key LIKE ? OR memory_value LIKE ?)
            """,
            (user_id, f"%{keyword}%", f"%{keyword}%")
        )
        # 提取全部匹配行
        rows = cursor.fetchall()
        # 关闭连接
        conn.close()
        # 返回结果
        return rows


def extract_and_save_memories(user_id: str, conversation_text: str, store: MemoryStore):
    """
    利用大模型提取对话中值得长期保存的用户事实与偏好信息，并写入数据库中。

    Args:
        user_id: 用户的唯一标识 ID。
        conversation_text: 本轮对话的上下文文本记录。
        store: SQLite 长期记忆持久化存储管理器实例。
    """
    # 实例化大模型
    model = create_model("deepseek", temperature=0.0)

    # 记忆提取的提示词模版
    prompt = ChatPromptTemplate.from_template(
        "分析以下对话内容，提取其中值得长期记忆的用户事实与偏好信息。\n\n"
        "提取核心原则：\n"
        "1. 提取用户的个人事实（如姓名、年龄、职业等），使用 identity 作为分类。\n"
        "2. 提取用户的偏好或偏爱（如喜欢的编程语言、偏好的代码风格、偏好的学习方法等），使用 preference 作为分类。\n"
        "3. 提取重要的背景事实（如正在学什么、正在参与的项目等），使用 fact 作为分类。\n"
        "4. 不要记录一些瞬时性、无长期保留价值的零碎对话细节。\n"
        "5. 如果同一个键已有更准确的信息，请提取并输出最新信息以做覆盖更新。\n\n"
        "要求直接输出且仅输出一个符合以下 JSON 结构的 JSON 数组（不要包装任何 ```json 标记或自然语言前缀）：\n"
        "[\n"
        "  {{\"key\": \"user_name\", \"value\": \"小明\", \"category\": \"identity\"}},\n"
        "  {{\"key\": \"fav_lang\", \"value\": \"Python\", \"category\": \"preference\"}}\n"
        "]\n\n"
        "如果对话中不包含任何值得记录的用户特征，请仅返回空数组 []。\n\n"
        "当前对话内容：\n"
        "{conversation}\n"
    )

    # 用 LCEL 组合提取链：模板 -> 模型 -> JSON 解析器
    chain = prompt | model | JsonOutputParser()

    try:
        # 执行链，获取结构化提取出的记忆数组
        memories = chain.invoke({"conversation": conversation_text})

        # 如果提取出的结果不是空的
        if memories:
            # 打印提取成功的调试信息
            print("\n💾 [系统通知] 大模型提取到了以下长期记忆：")
            # 遍历每一个提取出来的记忆键值对
            for mem in memories:
                # 取得键
                key = mem.get("key")
                # 取得值
                val = mem.get("value")
                # 取得分类
                cat = mem.get("category", "general")

                # 如果键和值都不为空
                if key and val:
                    # 持久化保存到本地 SQLite 数据库中
                    store.save_memory(user_id, key, val, cat)
                    # 打印保存详情
                    print(f"   - 保存: 键 '{key}' -> 值 '{val}' ({cat})")
            # 换行
            print("")
    # 捕获异常
    except Exception as e:
        # 打印报错
        print(f"❌ 记忆提取失败: {e}")


def main():
    """
    Day 8 课程 2 主测试程序。
    """
    # 标题
    print("=" * 60)
    print("🚀 Day 8 - 课程 2：SQLite 长期记忆存储与自动提取演练")
    print("=" * 60)

    # 实例化记忆管理器（使用默认路径 memories.db）
    store = MemoryStore()

    # 测试账号 ID
    test_user = "user_1001"

    # 清理之前可能存留的历史记忆以防止测试错乱
    all_old = store.get_all_memories(test_user)
    # 循环删除
    for key, _, _ in all_old:
        # 移除
        store.delete_memory(test_user, key)

    # 模拟一段对话文本，里面包含小明的信息和他的喜好
    sample_conversation = (
        "User: 你好，我是小明。我现在是一名高三的学生。\n"
        "AI: 你好小明！高三很辛苦吧，有什么我可以帮你的？\n"
        "User: 没事，我平时喜欢在空闲时间学点 Python 和大模型 Agent 技术，主要是喜欢实践。\n"
        "AI: 那很了不起！高三还能坚持自学 Python 和 Agent 技术，非常令人佩服！"
    )

    # 打印测试对话
    print(f"\n💬 [模拟对话内容]\n{sample_conversation}\n")

    # 执行记忆提取并自动保存到 SQLite 数据库中
    print("🔮 正在调用大模型对对话进行特征提取并写入 SQLite 持久化...")
    extract_and_save_memories(test_user, sample_conversation, store)

    # 从数据库读取已保存的完整记忆，验证持久化是否生效
    print("📋 [数据库查询结果] 当前保存在 SQLite 中的所有长期记忆：")
    db_memories = store.get_all_memories(test_user)

    # 遍历显示
    for k, v, c in db_memories:
        # 打印键值
        print(f"  • 分类: {c:12} | 键: {k:15} | 值: {v}")

    # 测试模糊检索功能
    print("\n🔍 [模糊匹配测试] 检索包含 'Python' 的记忆:")
    results = store.search_memories(test_user, "Python")
    # 遍历
    for k, v, c in results:
        # 打印
        print(f"    - 匹配到: {k} = {v}")
    # 换行
    print("=" * 60 + "\n")


# 运行判定
if __name__ == "__main__":
    # 执行 main
    main()
