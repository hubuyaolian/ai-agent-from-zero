"""
Day 8 - 课程 3：集成长期记忆与短期历史的完整持久化 Memory Agent。

学习目标：
    1. 学习如何在会话起始时，查询 SQLite 中的长期记忆并动态注入 System Prompt。
    2. 掌握多轮交互并在每轮结束后，异步/背景提取新特征保存至 SQLite 的完整流程。
    3. 支持命令行下用户查询全部长期记忆 (/memories) 和删除指令 (/forget <key>)。
"""

# 导入系统控制模块
import sys
# 导入操作系统相关库
import os

# 取得当前脚本所在的绝对目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将项目根目录置入搜索路径首位
sys.path.insert(0, os.path.join(CURRENT_DIR, '..'))

# 从公共模块中导入模型构建工厂函数
from common.model_factory import create_model  # noqa: E402
# 导入动态导入模块
import importlib

# 动态加载带有数字前缀的长期记忆管理模块以避免语法解析错误
_lt_mem_mod = importlib.import_module(
    "project_04_memory_rag.02_long_term_memory"
)
# 从加载的模块中提取 MemoryStore 类
MemoryStore = _lt_mem_mod.MemoryStore
# 从加载的模块中提取 extract_and_save_memories 函数
extract_and_save_memories = _lt_mem_mod.extract_and_save_memories
# 导入 LangChain 基础消息类
from langchain_core.messages import (  # noqa: E402
    HumanMessage,    # 用户消息
    SystemMessage,   # 系统设置消息
)

# 终端 ANSI 样式彩色高亮代码
COLOR_RESET = "\033[0m"      # 重置样式
COLOR_GREEN = "\033[32m"     # 绿色表示用户
COLOR_BLUE = "\033[34m"      # 蓝色表示 AI 回复
COLOR_CYAN = "\033[36m"      # 青色表示系统运行
COLOR_YELLOW = "\033[33m"    # 黄色表示警告
COLOR_RED = "\033[31m"       # 红色表示错误错误或警告提示


class MemoryAgent:
    """
    具备长期记忆注入与提取能力的 Agent 交互类。
    """

    def __init__(self, user_id: str):
        """
        初始化 MemoryAgent。

        Args:
            user_id: 用户的唯一标识。
        """
        # 保存用户标识
        self.user_id = user_id
        # 实例化 SQLite 长期记忆管理器
        self.store = MemoryStore()
        # 实例化底层大模型，使用稍微带有创造力的 temperature
        self.model = create_model("xiaomi mimo", temperature=0.7)
        # 初始化短期会话历史消息队列
        self.short_term_history = []

    def _get_injected_system_message(self) -> SystemMessage:
        """
        获取拼接了当前用户全部长期记忆的 SystemMessage。

        Returns:
            SystemMessage 对象。
        """
        # 从数据库中拉取当前用户的全部长期记忆
        memories = self.store.get_all_memories(self.user_id)

        # 构建默认的基础系统指令提示词
        base_prompt = (
            "你是一个极其友好且具有优秀记忆力的 AI 对话助手。\n"
            "你会根据用户的个人事实与偏好信息，提供更加个性化、贴心的回复。\n"
            "在与用户交谈时，不要刻意列举你的记忆，而是要自然地将记忆应用在回复中。\n"
        )

        # 如果有存储的长期记忆
        if memories:
            # 开始准备拼接长期记忆背景信息
            memory_context = "\n当前用户的长期记忆背景：\n"
            # 遍历每条长期记忆
            for k, v, c in memories:
                # 拼接每项记忆
                memory_context += f"- [{c}] {k}: {v}\n"
        # 无记忆
        else:
            # 拼接无记忆说明
            memory_context = "\n当前用户暂无长期记忆存储。\n"

        # 合并出完整的系统提示词字符串
        final_prompt = base_prompt + memory_context
        # 封装为 SystemMessage 并返回
        return SystemMessage(content=final_prompt)

    def chat_turn(self, user_text: str):
        """
        执行一轮包含“记忆注入 - 消息回复 - 记忆提取”的完整会话。

        Args:
            user_text: 用户本轮输入的纯文本。
        """
        # 构建动态注入最新长期记忆的系统消息
        system_msg = self._get_injected_system_message()

        # 封装当前用户消息
        user_msg = HumanMessage(content=user_text)

        # 拼接本轮模型请求所需的完整列表：最新系统记忆设定 + 短期历史消息 + 当前提问
        request_messages = [system_msg] + self.short_term_history + [user_msg]

        try:
            # 调用大模型生成回复
            response = self.model.invoke(request_messages)

            # 打印回复
            print(f"\n{COLOR_BLUE}AI > {response.content}{COLOR_RESET}\n")

            # 将本轮的“问”与“答”追加入短期历史列表中，以支持本轮会话的短期连贯性
            self.short_term_history.append(user_msg)
            # 追加回复
            self.short_term_history.append(response)

            # 提取本轮交互对话的纯文本格式，用于大模型分析
            current_turn_text = f"User: {user_text}\nAI: {response.content}"

            # 触发自动记忆分析与后台 SQLite 存储
            extract_and_save_memories(self.user_id, current_turn_text, self.store)

        # 捕获异常
        except Exception as e:
            # 打印错误
            print(f"❌ 运行异常: {e}")

    def show_memories(self):
        """
        控制台打印当前用户在 SQLite 中的所有长期记忆。
        """
        # 查询所有记忆
        memories = self.store.get_all_memories(self.user_id)
        # 标题
        print(f"\n{COLOR_CYAN}=== 当前用户 '{self.user_id}' 的长期记忆 ({len(memories)} 条) ==={COLOR_RESET}")
        # 如果列表为空
        if not memories:
            # 提示为空
            print("  （暂无记忆数据）")
        # 存在数据
        else:
            # 遍历并打印
            for k, v, c in memories:
                # 显示
                print(f"  • [{c:10}] {k:15} -> {v}")
        # 换行
        print("")

    def forget_memory(self, key: str):
        """
        删除指定的记忆项。

        Args:
            key: 待删除的记忆键名。
        """
        # 执行删除
        success = self.store.delete_memory(self.user_id, key)
        # 判断结果
        if success:
            # 提示删除成功
            print(f"{COLOR_YELLOW}✅ 成功删除记忆键: '{key}'{COLOR_RESET}\n")
        # 未删除
        else:
            # 提示键不存在
            print(f"{COLOR_RED}❌ 未找到对应的记忆键: '{key}'{COLOR_RESET}\n")


def run_interactive_loop():
    """
    运行持久化 Memory Agent 的交互式命令行循环。
    """
    # 设定固定的测试用户账号，以此演示跨程序重启的持久化效果
    user_id = "user_999"
    # 创建 Agent 实例
    agent = MemoryAgent(user_id)

    # 打印欢迎面板
    print("=" * 65)
    print("🤖 Day 8 - 课程 3：集成 SQLite 长期记忆命令行 Agent")
    print(f"   当前登录用户账号: {user_id} (数据在重启后依然持久保留)")
    print("=" * 65)
    print("  系统指令集 (输入斜杠指令触发):")
    print("    /memories  - 查看保存在本地 SQLite 中的所有长期记忆")
    print("    /forget <键> - 从数据库中彻底删除一条特定的记忆")
    print("    /quit      - 退出程序")
    print("=" * 65)

    # 启动命令行主循环
    while True:
        try:
            # 读取用户输入
            user_input = input("👤 用户 > ")
            # 去掉空白字符
            clean_input = user_input.strip()

            # 空输入处理
            if not clean_input:
                # 忽略，继续等待下一次输入
                continue

            # 处理退出指令
            if clean_input.lower() == "/quit":
                # 打印告别
                print("👋 再见！")
                # 退出
                break

            # 处理查看所有记忆指令
            if clean_input.lower() == "/memories":
                # 打印记忆
                agent.show_memories()
                # 继续
                continue

            # 处理删除某项记忆指令
            if clean_input.lower().startswith("/forget "):
                # 分割出键值
                parts = clean_input.split(" ", 1)
                # 提取具体的 key
                target_key = parts[1].strip()
                # 执行删除
                agent.forget_memory(target_key)
                # 继续
                continue

            # 执行常规对话会话
            agent.chat_turn(clean_input)

        # 捕获用户在终端 Ctrl+C/Ctrl+D 强行中止动作
        except (KeyboardInterrupt, EOFError):
            # 退出提示
            print("\n👋 终端交互中断，退出程序。")
            # 退出
            break
        # 捕获其他任何异常
        except Exception as e:
            # 打印错误
            print(f"\n❌ 系统运行时发生错误: {e}\n")


def main():
    """
    Day 8 课程 3 主入口。
    """
    # 启动命令行交互
    run_interactive_loop()


# 主程序入口运行判定
if __name__ == "__main__":
    # 执行 main
    main()
