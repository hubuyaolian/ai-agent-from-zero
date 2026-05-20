"""
Day 3 - 课程 3：自定义角色的对话 Agent（通过 System Prompt 塑造 Agent 的人格）。

功能：在课程 2 的基础上，通过 System Prompt 为 AI 定义不同的角色人格，
      让同一个 LLM 可以扮演不同的角色，展现截然不同的对话风格。
输入参数：无（通过终端交互输入）。
输出返回值：无（通过终端输出 AI 回复）。

============================================================
📚 核心概念讲解：System Prompt —— AI 的角色说明书
============================================================

一、什么是 System Prompt？

    System Prompt（系统提示语）是发送给 LLM 的一种特殊消息。
    它不是用户的对话内容，而是给 AI 的"角色说明书"。

    在 LangChain 中，消息有三种类型：
    - SystemMessage:  系统指令（定义 AI 的角色和行为）
    - HumanMessage:   用户（人类）的消息
    - AIMessage:      AI 助手的回复

    System Prompt 通常放在消息列表的最开头：
    messages = [
        SystemMessage("你是一位 Python 编程导师..."),  ← 角色说明
        HumanMessage("什么是列表？"),                  ← 用户提问
        AIMessage("列表是 Python 中..."),              ← AI 回答
        HumanMessage("能举个例子吗？"),                ← 继续对话
    ]

二、为什么 System Prompt 如此强大？

    System Prompt 决定了 AI 的：
    1. 角色身份：你是谁？（编程导师、翻译专家、心理咨询师...）
    2. 行为规则：你应该怎么做？（用代码回答、用问题引导...）
    3. 输出风格：你的语言风格是什么？（严谨、幽默、简洁...）
    4. 限制条件：你不应该做什么？（不编造信息、不超出专业范围...）

    同一个 LLM + 不同的 System Prompt = 完全不同的 AI 角色！

三、好的 System Prompt 长什么样？

    一个优秀的 System Prompt 应该包含：
    ✅ 明确的角色定义："你是一位..."
    ✅ 具体的行为规则："请遵循以下规则：1... 2... 3..."
    ✅ 输出格式要求："回答时请使用..."
    ✅ 适当的限制条件："不要..."

    ❌ 避免的写法：
    - 太笼统："你是一个好的 AI"
    - 太复杂：超过 1000 字的 System Prompt
    - 矛盾的指令："要详细但要简短"

四、本课的目标

    在本课中，我们将：
    1. 从 config.py 加载预定义的角色
    2. 让用户启动时选择一个角色
    3. 支持在对话中途切换角色
    4. 直观感受不同角色面对同一问题的不同回答风格

============================================================
"""

import sys  # 导入系统模块，用于修改模块搜索路径
import os  # 导入操作系统模块，用于路径操作

# 将上级目录（项目根目录）添加到 Python 模块搜索路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.model_factory import create_model  # 导入模型工厂函数  # noqa: E402
from common.config import list_available_providers  # 导入可用提供商列表  # noqa: E402

# 从项目配置文件导入预定义的角色
from project_02_chat_agent.config import (  # noqa: E402
    SYSTEM_PROMPTS,  # 预定义角色的 System Prompt 字典
    ROLE_NAMES,      # 角色名称列表
)

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
COLOR_YELLOW = "\033[33m"    # 黄色（用于警告信息）
COLOR_DIM = "\033[2m"        # 暗淡（用于分隔线）
COLOR_MAGENTA = "\033[35m"   # 品红色（用于角色信息）


class PersonaChatHistory:
    """
    支持角色切换的对话历史管理器。

    功能：在 ChatHistory 的基础上，增加了角色（Persona）管理功能。
          可以动态切换 System Prompt，让 AI 扮演不同的角色。

    属性：
        messages (list): 存储所有消息的列表。
        current_role (str): 当前使用的角色名称。
    """

    def __init__(self, role_name, system_prompt):
        """
        初始化带角色的对话历史管理器。

        功能：创建消息列表，并设置初始的角色 System Prompt。
        输入参数：
            role_name (str): 角色名称（如 "Python编程导师"）。
            system_prompt (str): 该角色的 System Prompt 内容。
        输出返回值：无。
        """
        # 记录当前角色名称
        self.current_role = role_name
        # 初始化消息列表，第一条为系统消息
        self.messages = [
            SystemMessage(content=system_prompt)
        ]

    def switch_role(self, role_name, system_prompt):
        """
        切换到新的角色。

        功能：清空对话历史，并设置新的角色 System Prompt。
              切换角色相当于开始一段全新的对话。
        输入参数：
            role_name (str): 新角色的名称。
            system_prompt (str): 新角色的 System Prompt 内容。
        输出返回值：无。
        """
        # 更新当前角色名称
        self.current_role = role_name
        # 重置消息列表，只保留新的系统消息
        self.messages = [
            SystemMessage(content=system_prompt)
        ]

    def add_user_message(self, content):
        """
        添加一条用户消息到历史记录中。

        功能：将用户的输入封装为 HumanMessage 并添加到消息列表。
        输入参数：
            content (str): 用户输入的消息文本。
        输出返回值：无。
        """
        # 创建用户消息并添加到列表
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
        # 创建 AI 消息并添加到列表
        ai_msg = AIMessage(content=content)
        self.messages.append(ai_msg)

    def get_messages(self):
        """
        获取完整的消息历史列表。

        功能：返回当前所有消息的列表，用于发送给 LLM。
        输入参数：无。
        输出返回值：
            list: 包含所有消息对象的列表。
        """
        # 返回消息列表
        return self.messages

    def get_message_count(self):
        """
        获取当前消息数量。

        功能：返回历史中的消息总数。
        输入参数：无。
        输出返回值：
            int: 消息列表中的消息总数。
        """
        # 返回列表长度
        return len(self.messages)

    def get_conversation_rounds(self):
        """
        获取对话轮数。

        功能：计算用户和 AI 之间完成了多少轮完整对话。
        输入参数：无。
        输出返回值：
            int: 对话轮数。
        """
        # 统计用户消息的数量
        rounds = 0
        for msg in self.messages:
            if isinstance(msg, HumanMessage):
                rounds += 1
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
          f"  🎭 角色扮演对话机器人 - Day 3 课程 3{COLOR_RESET}")
    # 打印副标题
    print(f"{COLOR_CYAN}"
          f"  通过 System Prompt 塑造 AI 的不同人格{COLOR_RESET}")
    # 打印分隔线
    print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}")
    # 打印使用说明
    print(f"{COLOR_YELLOW}  📝 使用说明：{COLOR_RESET}")
    # 打印退出指令
    print(f"     输入 {COLOR_BOLD}quit{COLOR_RESET} 或"
          f" {COLOR_BOLD}exit{COLOR_RESET}   退出对话")
    # 打印切换角色指令
    print(f"     输入 {COLOR_BOLD}/role{COLOR_RESET}"
          f"          切换 AI 角色")
    # 打印查看当前角色指令
    print(f"     输入 {COLOR_BOLD}/info{COLOR_RESET}"
          f"          查看当前角色信息")
    # 打印清除历史指令
    print(f"     输入 {COLOR_BOLD}clear{COLOR_RESET}"
          f"          清屏")
    # 打印分隔线
    print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}")


def print_separator():
    """
    打印分隔线。

    功能：在用户和 AI 的对话之间打印分隔线。
    输入参数：无。
    输出返回值：无（直接打印到终端）。
    """
    # 使用暗淡颜色打印短分隔线
    print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}")


def display_role_menu():
    """
    显示角色选择菜单。

    功能：列出所有可用的角色及其简要说明。
    输入参数：无。
    输出返回值：无（直接打印到终端）。
    """
    # 打印分隔线
    print(f"\n{COLOR_DIM}{'─' * 50}{COLOR_RESET}")
    # 打印标题
    print(f"{COLOR_BOLD}{COLOR_MAGENTA}"
          f"  🎭 可用角色列表：{COLOR_RESET}")
    # 打印分隔线
    print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}")

    # 遍历所有角色并显示
    for i, role_name in enumerate(ROLE_NAMES):
        # 获取该角色的 System Prompt
        prompt = SYSTEM_PROMPTS[role_name]
        # 截取前 40 个字符作为简要描述
        preview = prompt[:40] + "..."
        # 打印序号、角色名和预览
        print(f"  {COLOR_BOLD}{i + 1}.{COLOR_RESET} "
              f"{COLOR_MAGENTA}{role_name}{COLOR_RESET}")
        print(f"     {COLOR_DIM}{preview}{COLOR_RESET}")

    # 打印底部分隔线
    print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}")


def select_role():
    """
    让用户选择一个角色。

    功能：显示角色菜单，并获取用户的选择。
    输入参数：无。
    输出返回值：
        tuple: (角色名称, System Prompt 内容)。
    """
    # 显示角色菜单
    display_role_menu()

    # 循环获取用户的有效输入
    while True:
        # 提示用户输入序号
        choice = input(
            f"\n{COLOR_GREEN}请选择角色序号 "
            f"(1-{len(ROLE_NAMES)}): {COLOR_RESET}"
        ).strip()

        # 尝试将输入转换为整数并验证范围
        try:
            # 将字符串转为整数
            index = int(choice) - 1
            # 检查是否在有效范围内
            if 0 <= index < len(ROLE_NAMES):
                # 获取选中的角色名称
                role_name = ROLE_NAMES[index]
                # 获取对应的 System Prompt
                system_prompt = SYSTEM_PROMPTS[role_name]
                # 打印确认信息
                print(f"\n{COLOR_MAGENTA}✅ 已选择角色: "
                      f"{COLOR_BOLD}{role_name}{COLOR_RESET}")
                # 返回角色名称和 System Prompt
                return role_name, system_prompt
        except ValueError:
            # 如果输入不是数字，忽略
            pass
        # 提示用户输入有效的序号
        print(f"{COLOR_YELLOW}⚠️  请输入有效的序号！{COLOR_RESET}")


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
            # 如果输入不是数字，忽略
            pass
        # 提示用户输入有效的序号
        print(f"{COLOR_YELLOW}⚠️  请输入有效的序号！{COLOR_RESET}")


def print_current_role_info(history):
    """
    打印当前角色的详细信息。

    功能：显示当前角色的名称和完整的 System Prompt。
    输入参数：
        history (PersonaChatHistory): 对话历史管理器实例。
    输出返回值：无（直接打印到终端）。
    """
    # 获取当前角色名称
    role_name = history.current_role
    # 获取该角色的 System Prompt
    system_prompt = SYSTEM_PROMPTS[role_name]

    # 打印角色信息
    print(f"\n{COLOR_DIM}{'─' * 50}{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_MAGENTA}"
          f"  🎭 当前角色: {role_name}{COLOR_RESET}")
    print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}")
    print(f"{COLOR_CYAN}  System Prompt 内容：{COLOR_RESET}")
    print(f"  {COLOR_DIM}{system_prompt}{COLOR_RESET}")
    print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}")

    # 打印对话统计
    msg_count = history.get_message_count()
    rounds = history.get_conversation_rounds()
    print(f"{COLOR_MAGENTA}  📊 当前对话: "
          f"{msg_count} 条消息 | "
          f"第 {rounds} 轮对话{COLOR_RESET}\n")


def run_chat_with_persona():
    """
    运行支持角色扮演的对话机器人主循环。

    功能：让用户选择 AI 角色，进行带记忆的对话，
          并支持在对话过程中动态切换角色。
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

    # 让用户选择初始角色
    print(f"\n{COLOR_CYAN}📌 首先，请选择 AI 的角色：{COLOR_RESET}")
    role_name, system_prompt = select_role()

    # 创建带角色的对话历史管理器
    history = PersonaChatHistory(
        role_name=role_name,
        system_prompt=system_prompt
    )

    # 打印提示信息
    print(f"\n{COLOR_CYAN}🚀 角色扮演对话已启动！"
          f"当前角色: {COLOR_BOLD}{role_name}{COLOR_RESET}")
    print(f"{COLOR_CYAN}   输入 /role 可以随时切换角色{COLOR_RESET}\n")

    # ---- 第二步：对话循环 ----
    while True:
        # 显示当前角色和对话统计
        rounds = history.get_conversation_rounds()
        print(f"{COLOR_MAGENTA}  🎭 [{history.current_role}] | "
              f"第 {rounds} 轮对话{COLOR_RESET}")

        # ========================================
        # 阶段 1：感知 —— 获取用户输入
        # ========================================
        try:
            # 显示用户提示符，等待输入
            user_input = input(
                f"{COLOR_BOLD}{COLOR_GREEN}👤 你: {COLOR_RESET}"
            )
        except (KeyboardInterrupt, EOFError):
            # 处理中断
            print(f"\n\n{COLOR_CYAN}👋 再见！{COLOR_RESET}")
            break

        # 去除空白字符
        user_input = user_input.strip()

        # 如果输入为空，跳过
        if not user_input:
            continue

        # 检查是否是退出命令
        if user_input.lower() in ("quit", "exit"):
            print(f"\n{COLOR_CYAN}👋 感谢使用，再见！{COLOR_RESET}")
            break

        # 检查是否是清屏命令
        if user_input.lower() == "clear":
            # 清屏
            os.system("clear")
            # 重新打印欢迎信息
            print_welcome()
            continue

        # 检查是否是切换角色命令
        if user_input.lower() == "/role":
            # 让用户选择新角色
            new_role_name, new_system_prompt = select_role()
            # 切换角色（会清空对话历史）
            history.switch_role(new_role_name, new_system_prompt)
            # 打印切换成功的提示
            print(f"\n{COLOR_MAGENTA}🔄 角色已切换为: "
                  f"{COLOR_BOLD}{new_role_name}{COLOR_RESET}")
            print(f"{COLOR_YELLOW}  ⚠️  对话历史已重置"
                  f"（新角色，新开始）{COLOR_RESET}\n")
            continue

        # 检查是否是查看角色信息命令
        if user_input.lower() == "/info":
            # 打印当前角色的详细信息
            print_current_role_info(history)
            continue

        # ========================================
        # 阶段 2：记录 —— 将用户消息添加到历史
        # ========================================
        history.add_user_message(user_input)

        # ========================================
        # 阶段 3：思考 —— 调用 LLM（含角色 + 历史）
        # ========================================
        print_separator()
        print(f"{COLOR_DIM}  ⏳ {history.current_role}思考中..."
              f"{COLOR_RESET}")

        try:
            # 调用模型，发送完整的消息历史
            # 消息列表的第一条是 SystemMessage（角色说明书）
            # 后面是完整的对话历史
            # LLM 会根据 System Prompt 的指示来调整回答风格
            response = model.invoke(history.get_messages())

            # ========================================
            # 阶段 4：记录 —— 将 AI 回复添加到历史
            # ========================================
            history.add_ai_message(response.content)

            # ========================================
            # 阶段 5：行动 —— 输出 AI 回复
            # ========================================
            print(f"\n{COLOR_BOLD}{COLOR_BLUE}"
                  f"🤖 [{history.current_role}]: "
                  f"{COLOR_RESET}{response.content}\n")

        except Exception as error:
            # 如果调用模型出错，打印错误信息
            print(f"\n{COLOR_YELLOW}❌ 调用模型时出错: "
                  f"{error}{COLOR_RESET}\n")
            # 移除刚才添加的用户消息，保持历史一致性
            if history.messages:
                last_msg = history.messages[-1]
                if isinstance(last_msg, HumanMessage):
                    history.messages.pop()


# ============================================================
# 主程序入口
# ============================================================
if __name__ == '__main__':
    # 运行角色扮演对话机器人
    run_chat_with_persona()
