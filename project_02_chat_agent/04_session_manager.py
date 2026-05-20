"""
Day 4 - 课程 4：多会话管理 (Session Manager)。

功能：在单会话对话 Agent 的基础上，实现多会话隔离。
      不同会话使用不同的 Session ID 进行标识，从而在内存中维护独立的 ChatHistory。
      使用户可以灵活地在不同话题或用户之间切换，互不干扰。
输入参数：无（通过终端交互输入）。
输出返回值：无（通过终端输出 AI 回复和会话状态）。
"""

# 导入系统路径和运行模块
import sys
# 导入操作系统相关路径模块
import os

# 获取当前脚本文件所在的绝对路径目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将当前目录添加到 Python 搜索路径的开头
sys.path.insert(0, CURRENT_DIR)
# 将上级目录（项目根目录）添加到 Python 搜索路径的开头
sys.path.insert(0, os.path.join(CURRENT_DIR, '..'))

# 导入公共模块中的模型工厂函数
from common.model_factory import create_model  # noqa: E402
# 导入 LangChain 的消息类型基类和子类
from langchain_core.messages import (  # noqa: E402
    HumanMessage,    # 用户消息类
    AIMessage,       # AI 助手回复消息类
    SystemMessage,   # 系统指令设定消息类
)

# 终端中用于美化的 ANSI 转义颜色代码
COLOR_RESET = "\033[0m"      # 重置颜色和样式
COLOR_BOLD = "\033[1m"       # 文本加粗
COLOR_GREEN = "\033[32m"     # 绿色（用于用户输入提示）
COLOR_BLUE = "\033[34m"      # 蓝色（用于 AI 回复提示）
COLOR_CYAN = "\033[36m"      # 青色（用于系统提示信息）
COLOR_YELLOW = "\033[33m"    # 黄色（用于警告或命令说明）
COLOR_DIM = "\033[2m"        # 灰色/暗淡（用于线段和状态）
COLOR_MAGENTA = "\033[35m"   # 品红色（用于会话列表显示）


class ChatHistory:
    """
    对话历史管理器。

    功能：用于维护单个会话的消息历史记录列表。
    属性：
        messages (list): 存储当前会话所有的 LangChain 消息对象。
    """

    def __init__(self, system_prompt=None):
        """
        初始化单个会话的对话历史。

        输入参数：
            system_prompt (str, optional): 系统角色设定提示词。
        输出返回值：无。
        """
        # 初始化消息列表容器
        self.messages = []
        # 判断是否提供了系统设定提示词
        if system_prompt is not None:
            # 创建系统设定消息对象
            system_msg = SystemMessage(content=system_prompt)
            # 将系统消息添加到列表首位
            self.messages.append(system_msg)

    def add_user_message(self, content):
        """
        添加一条用户消息。

        输入参数：
            content (str): 用户发送的聊天文本。
        输出返回值：无。
        """
        # 创建人类消息对象
        user_msg = HumanMessage(content=content)
        # 添加至当前消息历史列表
        self.messages.append(user_msg)

    def add_ai_message(self, content):
        """
        添加一条 AI 的回复消息。

        输入参数：
            content (str): AI 的回复文本。
        输出返回值：无。
        """
        # 创建 AI 消息对象
        ai_msg = AIMessage(content=content)
        # 添加至当前消息历史列表
        self.messages.append(ai_msg)

    def get_messages(self):
        """
        获取当前会话的所有消息历史。

        输入参数：无。
        输出返回值：
            list: 包含当前会话中全部消息对象的列表。
        """
        # 返回当前消息列表
        return self.messages

    def clear(self):
        """
        清空当前会话的历史。

        输入参数：无。
        输出返回值：无。
        """
        # 将消息列表重置为空列表
        self.messages = []


class SessionManager:
    """
    多会话管理器。

    功能：维护一个会话字典，以 Session ID 为键隔离不同的 ChatHistory 实例。
          同时跟踪当前活跃的会话 ID。
    属性：
        sessions (dict): 存储所有会话的字典，格式为 {session_id: ChatHistory}。
        active_session_id (str): 当前处于激活状态的会话 ID。
    """

    def __init__(self):
        """
        初始化会话管理器。

        输入参数：无。
        输出返回值：无。
        """
        # 初始化存储会话的空字典
        self.sessions = {}
        # 初始时没有活跃的会话 ID
        self.active_session_id = None

    def create_session(self, session_id, system_prompt=None):
        """
        创建一个新会话。

        输入参数：
            session_id (str): 唯一标识会话的字符串。
            system_prompt (str, optional): 新会话的系统设定提示词。
        输出返回值：
            ChatHistory: 创建或已存在的会话历史管理器实例。
        """
        # 检查该会话 ID 是否已存在
        if session_id not in self.sessions:
            # 创建新的 ChatHistory 实例并存入字典中
            self.sessions[session_id] = ChatHistory(system_prompt=system_prompt)
        # 返回创建或现有的会话对象
        return self.sessions[session_id]

    def get_session(self, session_id):
        """
        获取指定 ID 的会话历史。

        输入参数：
            session_id (str): 会话的唯一 ID。
        输出返回值：
            ChatHistory: 对应 ID 的会话对象，如果不存在则返回 None。
        """
        # 从会话字典中获取对应值并返回
        return self.sessions.get(session_id)

    def delete_session(self, session_id):
        """
        删除指定的会话。

        输入参数：
            session_id (str): 需要删除的会话 ID。
        输出返回值：
            bool: 删除是否成功（会话存在且被成功删除）。
        """
        # 检查要删除的会话是否在字典中
        if session_id in self.sessions:
            # 从字典中弹出并删除该会话键值对
            self.sessions.pop(session_id)
            # 检查删除的是否是当前激活的会话
            if self.active_session_id == session_id:
                # 重置当前激活的会话 ID 为 None
                self.active_session_id = None
            # 返回删除成功
            return True
        # 返回删除失败
        return False

    def list_sessions(self):
        """
        获取所有活跃会话的 ID 列表。

        输入参数：无。
        输出返回值：
            list: 包含所有会话 ID 字符串的列表。
        """
        # 获取会话字典的所有键并转换为列表返回
        return list(self.sessions.keys())

    def set_active_session(self, session_id):
        """
        设置当前活跃的会话。

        输入参数：
            session_id (str): 要激活的会话 ID。
        输出返回值：
            bool: 激活切换是否成功（目标会话必须存在）。
        """
        # 确保激活的目标会话 ID 已经存在于字典中
        if session_id in self.sessions:
            # 将活跃的会话 ID 设置为目标 ID
            self.active_session_id = session_id
            # 返回设置成功
            return True
        # 返回设置失败
        return False


def print_help():
    """
    打印系统支持的命令说明。

    输入参数：无。
    输出返回值：无。
    """
    # 打印提示线
    print(f"\n{COLOR_YELLOW}  💡 支持的会话控制命令：{COLOR_RESET}")
    # 打印新建会话命令格式
    print("    /new <会话ID>      - 创建并切换到一个新会话")
    # 打印切换会话命令格式
    print("    /switch <会话ID>   - 切换到已有会话")
    # 打印列出会话命令格式
    print("    /list              - 列出所有会话列表")
    # 打印删除会话命令格式
    print("    /delete <会话ID>   - 删除指定会话")
    # 打印清空消息命令格式
    print("    /clear             - 清空当前活跃会话的记录")
    # 打印帮助命令格式
    print("    /help              - 显示此帮助命令菜单")
    # 打印退出命令格式
    print("    /quit 或 exit      - 退出程序\n")


def main():
    """
    程序主入口。

    功能：演示多会话管理的控制台交互，使用 DeepSeek 模型回复。
    输入参数：无。
    输出返回值：无。
    """
    # 打印顶部分隔线
    print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}")
    # 打印系统标题
    print(f"{COLOR_BOLD}{COLOR_CYAN}  📂 多会话管理器控制台 (Session Manager) - Day 4{COLOR_RESET}")
    # 打印系统状态
    print(f"{COLOR_CYAN}  实现跨会话数据隔离，支持动态创建和自由切换{COLOR_RESET}")
    # 打印底部分隔线
    print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}")

    # 调用函数打印帮助菜单
    print_help()

    # 初始化会话管理器实例
    manager = SessionManager()

    # 默认创建第一个工作会话
    default_session_id = "default"
    # 创建默认会话，设定系统初始提示词
    manager.create_session(default_session_id, "你是一个擅长多会话隔离的技术专家。")
    # 将默认会话设置为当前活跃会话
    manager.set_active_session(default_session_id)

    # 打印当前激活状态提示
    print(f"{COLOR_CYAN}  默认已激活会话: {COLOR_BOLD}'default'{COLOR_RESET}\n")

    # 创建大语言模型实例
    model = create_model("deepseek")

    # 启动交互式控制台的主循环
    while True:
        # 获取当前活跃的会话 ID
        active_id = manager.active_session_id
        # 判断当前是否有激活的会话
        if active_id is None:
            # 提示没有激活会话
            input_prompt = f"{COLOR_YELLOW}(无活跃会话) 请输入命令 > {COLOR_RESET}"
        # 如果存在活跃会话
        else:
            # 提示当前活跃会话 ID
            input_prompt = f"{COLOR_GREEN}(会话: {active_id}) 用户 > {COLOR_RESET}"

        # 获取用户在控制台的输入，去除首尾多余空格
        user_input = input(input_prompt).strip()

        # 检查用户是否输入空行
        if not user_input:
            # 跳过本次循环继续等待输入
            continue

        # 判断用户是否输入退出程序指令
        if user_input.lower() == "/quit":
            # 打印退出提示
            print(f"\n{COLOR_CYAN}  已退出多会话系统。再见！{COLOR_RESET}\n")
            # 终止主循环
            break
        # 兼容单独输入 exit 退出
        if user_input.lower() == "exit":
            # 打印退出提示
            print(f"\n{COLOR_CYAN}  已退出多会话系统。再见！{COLOR_RESET}\n")
            # 终止主循环
            break

        # 判断用户是否输入帮助信息查询命令
        if user_input.lower() == "/help":
            # 打印帮助说明菜单
            print_help()
            # 继续下一次输入等待
            continue

        # 处理新建会话命令
        if user_input.startswith("/new "):
            # 提取会话名称
            new_id = user_input[5:].strip()
            # 检查提取出的会话 ID 是否为空
            if not new_id:
                # 打印错误提示
                print(f"{COLOR_YELLOW}  ⚠️ 请提供非空的会话 ID。{COLOR_RESET}")
                # 继续等待
                continue
            # 创建该会话，并附带专属的系统角色设定
            manager.create_session(new_id, f"你是在会话 '{new_id}' 中为用户提供帮助的助手。")
            # 将新建会话设为激活状态
            manager.set_active_session(new_id)
            # 打印成功新建并切换提示
            print(f"{COLOR_CYAN}  ✨ 成功创建并切换到新会话: '{new_id}'{COLOR_RESET}\n")
            # 继续等待
            continue

        # 处理切换已有会话命令
        if user_input.startswith("/switch "):
            # 提取目标会话 ID
            target_id = user_input[8:].strip()
            # 尝试在管理器中切换到该会话
            success = manager.set_active_session(target_id)
            # 判断切换是否成功
            if success:
                # 打印成功切换提示
                print(f"{COLOR_CYAN}  🔄 已经成功切换到会话: '{target_id}'{COLOR_RESET}\n")
            # 切换失败
            else:
                # 打印会话不存在的警告
                print(f"{COLOR_YELLOW}  ⚠️ 切换失败！未找到会话 ID: '{target_id}'{COLOR_RESET}")
            # 继续等待
            continue

        # 处理列出当前所有会话列表的命令
        if user_input.lower() == "/list":
            # 获取当前所有会话 ID
            sessions = manager.list_sessions()
            # 打印会话列表信息标题
            print(f"\n{COLOR_MAGENTA}  📋 活跃会话列表：{COLOR_RESET}")
            # 循环遍历每一个会话
            for s_id in sessions:
                # 判断当前遍历的会话是否是活跃会话
                if s_id == manager.active_session_id:
                    # 打印带有星号标记的当前激活会话
                    print(f"    * {COLOR_BOLD}{COLOR_GREEN}{s_id}{COLOR_RESET} (当前活跃)")
                # 非活跃会话
                else:
                    # 正常打印会话 ID
                    print(f"      {s_id}")
            # 打印行尾换行
            print()
            # 继续等待
            continue

        # 处理删除会话命令
        if user_input.startswith("/delete "):
            # 提取待删除的会话 ID
            del_id = user_input[8:].strip()
            # 尝试调用管理器删除指定会话
            success = manager.delete_session(del_id)
            # 判断删除是否成功
            if success:
                # 打印删除成功提示
                print(f"{COLOR_CYAN}  ❌ 成功删除会话: '{del_id}'{COLOR_RESET}")
                # 检查删除会话后是否有处于激活状态的会话
                if manager.active_session_id is None:
                    # 提示用户当前无活跃会话
                    print(f"{COLOR_YELLOW}  ⚠️ 当前活跃会话已删除，请创建或切换到其它会话！{COLOR_RESET}")
                # 打印换行
                print()
            # 删除失败
            else:
                # 打印未找到的警告
                print(f"{COLOR_YELLOW}  ⚠️ 删除失败！未找到会话 ID: '{del_id}'{COLOR_RESET}")
            # 继续等待
            continue

        # 处理清空当前会话历史命令
        if user_input.lower() == "/clear":
            # 检查当前是否有活跃的会话
            if active_id is not None:
                # 获取当前活跃会话对象
                active_session = manager.get_session(active_id)
                # 调用清空历史方法
                active_session.clear()
                # 打印清空成功提示
                print(f"{COLOR_CYAN}  🧹 会话 '{active_id}' 的消息历史已成功清空。{COLOR_RESET}\n")
            # 无活跃会话
            else:
                # 提示先切换到活跃会话
                print(f"{COLOR_YELLOW}  ⚠️ 当前没有活跃会话，无法清空。{COLOR_RESET}")
            # 继续等待
            continue

        # 拦截其它普通对话消息
        # 检查当前是否存在激活的会话对象
        if active_id is None:
            # 提示用户必须选择会话后才能聊天
            print(f"{COLOR_YELLOW}  ⚠️ 请先使用 /new 或 /switch 创建或进入一个会话！{COLOR_RESET}")
            # 继续下一轮循环
            continue

        # 获取当前正在使用的会话历史管理器
        session = manager.get_session(active_id)
        # 将用户输入的消息加入当前会话历史中
        session.add_user_message(user_input)

        # 打印 AI 正在思考的提示信息
        print(f"\n{COLOR_CYAN}  🤔 AI 正在思考...{COLOR_RESET}")

        try:
            # 调用大语言模型，并传入当前活跃会话的完整消息历史列表
            response = model.invoke(session.get_messages())
            # 提取 AI 的纯文本回复内容
            ai_reply = response.content
            # 将 AI 的回复存入当前活跃会话历史列表中
            session.add_ai_message(ai_reply)

            # 打印分隔虚线
            print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}")
            # 输出 AI 助手的名字和回复内容
            print(f"{COLOR_BLUE}AI > {COLOR_RESET}{ai_reply}")
            # 打印分隔虚线
            print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}\n")

        # 捕获调用大模型过程中产生的各种异常
        except Exception as err:
            # 打印调用出错的警告信息
            print(f"{COLOR_YELLOW}  ❌ 调用大模型出错！原因：{err}{COLOR_RESET}\n")


# 运行脚本的常规入口判断
if __name__ == '__main__':
    # 启动主函数
    main()
