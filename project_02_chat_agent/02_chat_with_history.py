"""
Day 3 - 课程 2：带消息历史的对话 Agent（加入记忆能力）。

功能：在课程 1 的基础上，通过维护消息历史列表，
      让 AI 拥有上下文记忆能力，能够记住之前的对话内容。
输入参数：无（通过终端交互输入）。
输出返回值：无（通过终端输出 AI 回复）。

============================================================
📚 核心概念讲解：为什么 AI 需要"记忆"？
============================================================

一、上一课的问题：AI 为什么没有记忆？

    在 01_simple_chatbot.py 中，我们每次调用 model.invoke() 时，
    只发送了当前这一条消息。

    这意味着：
    - 你说："我叫小明"
    - AI 说："你好小明！"
    - 你说："我叫什么名字？"
    - AI 说："我不知道你叫什么名字"  ← AI 已经"忘了"！

    原因很简单：LLM 本身是无状态的（Stateless）。
    每次 API 调用都是一次全新的、独立的请求。
    LLM 不会自动记住之前的对话。

二、记忆的本质：消息历史列表

    要让 AI 有"记忆"，关键在于：
    每次调用 API 时，把之前所有的对话历史都一起发送给 LLM。

    具体做法：
    1. 维护一个 messages 列表
    2. 用户说话时，将用户消息添加到列表
    3. AI 回复后，将 AI 的回复也添加到列表
    4. 每次调用 API 时，发送完整的消息列表

    messages = [
        {"role": "user", "content": "我叫小明"},
        {"role": "assistant", "content": "你好小明！很高兴认识你！"},
        {"role": "user", "content": "我叫什么名字？"},
        # AI 看到了完整历史，就能回答 "你叫小明"
    ]

三、Token 窗口限制

    LLM 有一个"上下文窗口"限制（Token Window），例如：
    - DeepSeek-V3: 64K tokens
    - GPT-4: 128K tokens
    - Gemini: 1M tokens

    这意味着消息历史不能无限增长！
    当历史太长时，需要进行截断或摘要。
    本课暂时不处理这个问题，后续课程会讲解。

四、LangChain 的消息类型

    LangChain 使用专门的消息类来表示不同角色的消息：
    - HumanMessage: 用户（人类）发送的消息
    - AIMessage: AI 助手的回复消息
    - SystemMessage: 系统指令（角色设定，下一课讲解）

============================================================
"""

import sys  # 导入系统模块，用于修改模块搜索路径
import os  # 导入操作系统模块，用于路径操作

# 将上级目录（项目根目录）添加到 Python 模块搜索路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.model_factory import create_model  # 导入模型工厂函数  # noqa: E402
from common.config import list_available_providers  # 导入可用提供商列表  # noqa: E402

# 导入 LangChain 的消息类型
from langchain_core.messages import (  # noqa: E402
    HumanMessage,   # 用户消息类
    AIMessage,      # AI 回复消息类
    SystemMessage,  # 系统指令消息类
)

# ============================================================
# 终端颜色代码（ANSI 转义序列）
# ============================================================
COLOR_RESET = "\033[0m"      # 重置所有样式
COLOR_BOLD = "\033[1m"       # 加粗
COLOR_GREEN = "\033[32m"     # 绿色（用于用户标识）
COLOR_BLUE = "\033[34m"      # 蓝色（用于 AI 标识）
COLOR_CYAN = "\033[36m"      # 青色（用于系统提示）
COLOR_YELLOW = "\033[33m"    # 黄色（用于警告/统计信息）
COLOR_DIM = "\033[2m"        # 暗淡（用于分隔线）
COLOR_MAGENTA = "\033[35m"   # 品红色（用于历史统计）


class ChatHistory:
    """
    对话历史管理器。

    功能：维护一个消息列表，记录用户和 AI 之间的完整对话历史。
          这个列表就是 AI "记忆"的本质——每次调用 LLM 时，
          把完整的历史都发送过去，让 LLM 知道之前发生了什么。

    属性：
        messages (list): 存储所有消息的列表（HumanMessage / AIMessage / SystemMessage）。
    """

    def __init__(self, system_prompt=None):
        """
        初始化对话历史管理器。

        功能：创建一个空的消息列表，可选地设置系统角色提示。
        输入参数：
            system_prompt (str, optional): 系统角色提示语。
                如果提供，会作为第一条消息添加到历史中。
                System Prompt 决定了 AI 的角色和行为模式。
        输出返回值：无。
        """
        # 初始化空的消息列表
        self.messages = []

        # 如果提供了系统提示语，将其作为第一条消息添加
        if system_prompt:
            # 使用 SystemMessage 类型创建系统消息
            system_msg = SystemMessage(content=system_prompt)
            # 添加到消息列表的开头
            self.messages.append(system_msg)

    def add_user_message(self, content):
        """
        添加一条用户消息到历史记录中。

        功能：将用户的输入封装为 HumanMessage 并添加到消息列表。
        输入参数：
            content (str): 用户输入的消息文本。
        输出返回值：无。
        """
        # 创建 HumanMessage 对象并添加到列表末尾
        user_msg = HumanMessage(content=content)
        self.messages.append(user_msg)

    def add_ai_message(self, content):
        """
        添加一条 AI 回复消息到历史记录中。

        功能：将 AI 的回复封装为 AIMessage 并添加到消息列表。
        输入参数：
            content (str): AI 回复的消息文本。
        输出返回值：无。
        """
        # 创建 AIMessage 对象并添加到列表末尾
        ai_msg = AIMessage(content=content)
        self.messages.append(ai_msg)

    def get_messages(self):
        """
        获取完整的消息历史列表。

        功能：返回当前所有消息的列表，用于发送给 LLM。
              LLM 通过阅读这个完整列表来"理解"之前的对话上下文。
        输入参数：无。
        输出返回值：
            list: 包含所有消息对象的列表。
        """
        # 直接返回消息列表
        return self.messages

    def clear(self):
        """
        清空对话历史。

        功能：删除所有消息记录，重新开始。
              注意：如果有 SystemMessage，也会一起被清除。
        输入参数：无。
        输出返回值：无。
        """
        # 清空消息列表
        self.messages = []

    def get_message_count(self):
        """
        获取当前消息数量。

        功能：返回历史中的消息总数（包含所有类型的消息）。
        输入参数：无。
        输出返回值：
            int: 消息列表中的消息总数。
        """
        # 返回列表的长度
        return len(self.messages)

    def get_conversation_rounds(self):
        """
        获取对话轮数（一轮 = 用户提问 + AI 回复）。

        功能：计算用户和 AI 之间完成了多少轮完整对话。
        输入参数：无。
        输出返回值：
            int: 对话轮数。
        """
        # 统计 HumanMessage 的数量作为对话轮数
        rounds = 0
        # 遍历所有消息
        for msg in self.messages:
            # 如果是用户消息，轮数加 1
            if isinstance(msg, HumanMessage):
                rounds += 1
        # 返回对话轮数
        return rounds


def print_welcome():
    """
    打印欢迎信息和使用说明。

    功能：在程序启动时显示美观的欢迎界面。
    输入参数：无。
    输出返回值：无（直接打印到终端）。
    """
    # 打印顶部分隔线
    print(f"\n{COLOR_DIM}{'═' * 60}{COLOR_RESET}")
    # 打印标题
    print(f"{COLOR_BOLD}{COLOR_CYAN}"
          f"  🧠 带记忆的对话机器人 - Day 3 课程 2{COLOR_RESET}")
    # 打印副标题
    print(f"{COLOR_CYAN}"
          f"  通过消息历史赋予 AI 记忆能力{COLOR_RESET}")
    # 打印分隔线
    print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}")
    # 打印使用说明
    print(f"{COLOR_YELLOW}  📝 使用说明：{COLOR_RESET}")
    # 打印退出指令
    print(f"     输入 {COLOR_BOLD}quit{COLOR_RESET} 或"
          f" {COLOR_BOLD}exit{COLOR_RESET}  退出对话")
    # 打印清除历史指令
    print(f"     输入 {COLOR_BOLD}clear{COLOR_RESET}"
          f"        清除对话历史")
    # 打印查看历史指令
    print(f"     输入 {COLOR_BOLD}history{COLOR_RESET}"
          f"      查看消息历史")
    # 打印分隔线
    print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}")
    # 打印记忆提示
    print(f"\n{COLOR_CYAN}  💡 小技巧：试试告诉 AI 你的名字，"
          f"然后问它是否记得！{COLOR_RESET}\n")


def print_separator():
    """
    打印分隔线。

    功能：在用户和 AI 的对话之间打印分隔线。
    输入参数：无。
    输出返回值：无（直接打印到终端）。
    """
    # 使用暗淡颜色打印短分隔线
    print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}")


def print_history_stats(history):
    """
    打印当前对话历史的统计信息。

    功能：显示消息数量和对话轮数，让用户直观感受历史在增长。
    输入参数：
        history (ChatHistory): 对话历史管理器实例。
    输出返回值：无（直接打印到终端）。
    """
    # 获取消息总数
    msg_count = history.get_message_count()
    # 获取对话轮数
    rounds = history.get_conversation_rounds()
    # 打印统计信息（使用品红色突出显示）
    print(f"{COLOR_MAGENTA}  📊 消息历史: "
          f"{msg_count} 条消息 | "
          f"第 {rounds} 轮对话{COLOR_RESET}")


def print_message_history(history):
    """
    打印完整的消息历史记录。

    功能：以清晰的格式展示所有历史消息，方便用户查看和理解。
    输入参数：
        history (ChatHistory): 对话历史管理器实例。
    输出返回值：无（直接打印到终端）。
    """
    # 获取所有消息
    messages = history.get_messages()

    # 如果没有消息，提示用户
    if not messages:
        print(f"\n{COLOR_YELLOW}  📭 暂无消息历史。{COLOR_RESET}\n")
        return

    # 打印标题
    print(f"\n{COLOR_DIM}{'─' * 50}{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}"
          f"  📜 消息历史记录 "
          f"(共 {len(messages)} 条){COLOR_RESET}")
    print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}")

    # 遍历并打印每条消息
    for i, msg in enumerate(messages):
        # 根据消息类型选择不同的显示样式
        if isinstance(msg, SystemMessage):
            # 系统消息用青色显示
            print(f"  {COLOR_CYAN}[系统] {msg.content[:50]}...{COLOR_RESET}")
        elif isinstance(msg, HumanMessage):
            # 用户消息用绿色显示
            print(f"  {COLOR_GREEN}[用户] {msg.content}{COLOR_RESET}")
        elif isinstance(msg, AIMessage):
            # AI 消息用蓝色显示（截取前 80 个字符）
            preview = msg.content[:80]
            # 如果内容被截断，添加省略号
            if len(msg.content) > 80:
                preview += "..."
            print(f"  {COLOR_BLUE}[AI]   {preview}{COLOR_RESET}")

    # 打印底部分隔线
    print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}\n")


def select_provider():
    """
    让用户选择模型提供商。

    功能：列出所有可用的模型提供商，让用户选择一个。
    输入参数：无。
    输出返回值：
        str: 用户选择的模型提供商名称。
    """
    # 获取所有已配置 API Key 的提供商
    available = list_available_providers()

    # 如果没有可用的提供商，提示用户并退出
    if not available:
        print(f"{COLOR_YELLOW}❌ 没有找到可用的模型提供商！{COLOR_RESET}")
        print("请检查 .env 文件中是否配置了 API Key。")
        sys.exit(1)

    # 如果只有一个提供商，直接使用
    if len(available) == 1:
        # 获取唯一的提供商名称
        provider = available[0]
        print(f"{COLOR_CYAN}🔧 使用模型提供商: "
              f"{COLOR_BOLD}{provider}{COLOR_RESET}")
        return provider

    # 如果有多个提供商，让用户选择
    print(f"\n{COLOR_CYAN}🔧 请选择模型提供商：{COLOR_RESET}")
    # 遍历并显示所有可用的提供商
    for i, provider_name in enumerate(available):
        # 打印序号和提供商名称
        print(f"  {COLOR_BOLD}{i + 1}.{COLOR_RESET} {provider_name}")

    # 循环获取用户的有效输入
    while True:
        # 提示用户输入序号
        choice = input(f"\n{COLOR_GREEN}请输入序号 "
                       f"(1-{len(available)}): {COLOR_RESET}").strip()
        # 尝试将输入转换为整数并验证范围
        try:
            # 将字符串转为整数
            index = int(choice) - 1
            # 检查是否在有效范围内
            if 0 <= index < len(available):
                # 获取选中的提供商名称
                selected = available[index]
                print(f"{COLOR_CYAN}✅ 已选择: "
                      f"{COLOR_BOLD}{selected}{COLOR_RESET}")
                return selected
        except ValueError:
            # 如果输入不是数字，忽略并提示重新输入
            pass
        # 提示用户输入有效的序号
        print(f"{COLOR_YELLOW}⚠️  请输入有效的序号！{COLOR_RESET}")


def run_chat_with_history():
    """
    运行带记忆功能的对话机器人主循环。

    功能：使用 ChatHistory 类管理对话上下文，
          让 AI 能够记住之前的对话内容。
          每次调用 LLM 时，发送完整的消息历史。
    输入参数：无。
    输出返回值：无（通过终端进行交互）。
    """
    # ---- 第一步：初始化 ----
    # 打印欢迎信息
    print_welcome()

    # 让用户选择模型提供商
    provider = select_provider()

    # 使用工厂函数创建模型实例
    model = create_model(provider=provider)

    # 创建对话历史管理器（带默认系统提示）
    # system_prompt 告诉 AI 它是一个友好的助手
    history = ChatHistory(
        system_prompt="你是一个友好、有记忆力的 AI 助手。"
                      "请记住用户在对话中提到的所有信息，"
                      "并在需要时引用这些信息。"
                      "请用中文回答。"
    )

    # 打印提示信息
    print(f"\n{COLOR_CYAN}🚀 对话机器人已启动！"
          f"这次 AI 有记忆了！{COLOR_RESET}\n")

    # ---- 第二步：对话循环 ----
    while True:
        # 显示当前历史统计
        print_history_stats(history)

        # ========================================
        # 阶段 1：感知 —— 获取用户输入
        # ========================================
        try:
            # 显示用户提示符，等待输入
            user_input = input(
                f"{COLOR_BOLD}{COLOR_GREEN}👤 你: {COLOR_RESET}"
            )
        except (KeyboardInterrupt, EOFError):
            # 处理 Ctrl+C 或 Ctrl+D 中断
            print(f"\n\n{COLOR_CYAN}👋 再见！{COLOR_RESET}")
            break

        # 去除输入两端的空白字符
        user_input = user_input.strip()

        # 如果输入为空，跳过本轮
        if not user_input:
            continue

        # 检查是否是退出命令
        if user_input.lower() in ("quit", "exit"):
            print(f"\n{COLOR_CYAN}👋 感谢使用，再见！{COLOR_RESET}")
            break

        # 检查是否是清除历史命令
        if user_input.lower() == "clear":
            # 清空对话历史
            history.clear()
            print(f"\n{COLOR_YELLOW}🗑️  对话历史已清除！"
                  f"AI 的记忆已重置。{COLOR_RESET}\n")
            continue

        # 检查是否是查看历史命令
        if user_input.lower() == "history":
            # 打印完整的消息历史
            print_message_history(history)
            continue

        # ========================================
        # 阶段 2：记录 —— 将用户消息添加到历史
        # ========================================
        # 将用户的输入添加到消息历史中
        # 这是实现"记忆"的关键步骤之一
        history.add_user_message(user_input)

        # ========================================
        # 阶段 3：思考 —— 调用 LLM（发送完整历史）
        # ========================================
        print_separator()
        print(f"{COLOR_DIM}  ⏳ AI 思考中...{COLOR_RESET}")

        try:
            # 🔑 核心区别在这里！
            # 上一课：model.invoke(user_input)  ← 只发送当前消息
            # 这一课：model.invoke(history.get_messages())  ← 发送完整历史
            # 正是这个区别，让 AI 拥有了"记忆"能力！
            response = model.invoke(history.get_messages())

            # ========================================
            # 阶段 4：记录 —— 将 AI 回复添加到历史
            # ========================================
            # 将 AI 的回复也添加到历史中
            # 这样下一轮对话时，AI 也能"回忆"自己说过什么
            history.add_ai_message(response.content)

            # ========================================
            # 阶段 5：行动 —— 输出 AI 回复
            # ========================================
            print(f"\n{COLOR_BOLD}{COLOR_BLUE}🤖 AI: "
                  f"{COLOR_RESET}{response.content}\n")

        except Exception as error:
            # 如果调用模型出错，打印错误信息
            print(f"\n{COLOR_YELLOW}❌ 调用模型时出错: "
                  f"{error}{COLOR_RESET}\n")
            # 出错时需要移除刚才添加的用户消息，保持历史一致性
            # 因为这条消息没有得到有效回复
            if history.messages:
                # 如果最后一条是刚添加的用户消息，移除它
                last_msg = history.messages[-1]
                if isinstance(last_msg, HumanMessage):
                    history.messages.pop()


# ============================================================
# 主程序入口
# ============================================================
if __name__ == '__main__':
    # 运行带记忆功能的对话机器人
    run_chat_with_history()
