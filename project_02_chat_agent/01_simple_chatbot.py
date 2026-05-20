"""
Day 3 - 课程 1：最简单的对话循环（从零理解 Agent 的基本结构）。

功能：实现一个最基础的对话机器人，展示 AI Agent 的核心循环结构。
      用户输入问题，AI 给出回答，循环往复。
输入参数：无（通过终端交互输入）。
输出返回值：无（通过终端输出 AI 回复）。

============================================================
📚 核心概念讲解：什么是 Agent 的核心循环？
============================================================

一、Agent 的本质

    Agent（智能体）这个词听起来很高大上，但它的核心其实非常简单：
    就是一个「感知 → 思考 → 行动」的循环。

    具体来说：
    1. 感知（Perception）：接收用户的输入（键盘输入、语音、图像等）
    2. 思考（Thinking）：将输入发送给 LLM，让大模型进行推理
    3. 行动（Action）：将 LLM 的回复展示给用户（输出到屏幕、语音播放等）
    4. 循环（Loop）：重复以上步骤，直到用户选择退出

    用代码表示就是：
        while True:
            user_input = input()       # 1. 感知：获取输入
            response = llm(user_input) # 2. 思考：调用 LLM
            print(response)            # 3. 行动：输出结果
            # 然后自动回到循环开头     # 4. 循环

二、这个版本的特点和局限

    ✅ 特点：
    - 结构极简，一目了然
    - 完整展示了 Agent 的核心循环
    - 可以正常和 AI 对话

    ❌ 局限：
    - 没有记忆能力！每次对话都是独立的
    - AI 不知道你之前说过什么
    - 原因：每次只发送当前这一条消息给 LLM

    为什么没有记忆？
    因为 LLM 本身是无状态的（Stateless）。
    每次调用 API，LLM 都像是"失忆"了一样，不知道之前的对话内容。
    想要 AI 有记忆，就需要我们自己维护对话历史——这就是下一课的内容！

============================================================
"""

import sys  # 导入系统模块，用于修改模块搜索路径
import os  # 导入操作系统模块，用于路径操作

# 将上级目录（项目根目录）添加到 Python 模块搜索路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.model_factory import create_model  # 导入模型工厂函数  # noqa: E402
from common.config import list_available_providers  # 导入可用提供商列表  # noqa: E402

# ============================================================
# 终端颜色代码（ANSI 转义序列）
# ============================================================
# 使用 ANSI 转义序列来美化终端输出，让对话界面更加清晰美观
COLOR_RESET = "\033[0m"      # 重置所有样式
COLOR_BOLD = "\033[1m"       # 加粗
COLOR_GREEN = "\033[32m"     # 绿色（用于用户标识）
COLOR_BLUE = "\033[34m"      # 蓝色（用于 AI 标识）
COLOR_CYAN = "\033[36m"      # 青色（用于系统提示）
COLOR_YELLOW = "\033[33m"    # 黄色（用于警告信息）
COLOR_DIM = "\033[2m"        # 暗淡（用于分隔线）


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
    print(f"{COLOR_BOLD}{COLOR_CYAN}  🤖 最简对话机器人 - Day 3 课程 1{COLOR_RESET}")
    # 打印副标题
    print(f"{COLOR_CYAN}  理解 Agent 的核心循环：感知 → 思考 → 行动{COLOR_RESET}")
    # 打印分隔线
    print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}")
    # 打印使用说明
    print(f"{COLOR_YELLOW}  📝 使用说明：{COLOR_RESET}")
    # 打印退出指令
    print(f"     输入 {COLOR_BOLD}quit{COLOR_RESET} 或"
          f" {COLOR_BOLD}exit{COLOR_RESET} 退出对话")
    # 打印清屏指令
    print(f"     输入 {COLOR_BOLD}clear{COLOR_RESET} 清屏")
    # 打印底部分隔线
    print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}")
    # 打印重要提示
    print(f"\n{COLOR_YELLOW}  ⚠️  注意：此版本没有记忆功能，"
          f"每次对话都是独立的！{COLOR_RESET}\n")


def print_separator():
    """
    打印分隔线。

    功能：在用户和 AI 的对话之间打印分隔线，使输出更清晰。
    输入参数：无。
    输出返回值：无（直接打印到终端）。
    """
    # 使用暗淡颜色打印短分隔线
    print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}")


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


def run_chatbot():
    """
    运行最简对话机器人的主循环。

    功能：实现 Agent 的核心循环——感知(输入) → 思考(LLM) → 行动(输出)。
          这是 Agent 最基础、最核心的结构。
    输入参数：无。
    输出返回值：无（通过终端进行交互）。
    """
    # ---- 第一步：初始化 ----
    # 打印欢迎信息
    print_welcome()

    # 让用户选择模型提供商
    provider = select_provider()

    # 使用工厂函数创建模型实例
    # 这里只需一行代码，就能创建任何提供商的模型——这就是工厂模式的威力
    model = create_model(provider=provider)

    # 打印提示信息
    print(f"\n{COLOR_CYAN}🚀 对话机器人已启动！开始和 AI 聊天吧！{COLOR_RESET}\n")

    # ---- 第二步：核心循环 ----
    # 这就是 Agent 的核心！一个简单的 while True 循环
    # 循环的每一轮都是一次完整的「感知 → 思考 → 行动」
    while True:
        # ========================================
        # 阶段 1：感知（Perception）—— 获取用户输入
        # ========================================
        try:
            # 显示用户提示符，等待用户输入
            user_input = input(
                f"{COLOR_BOLD}{COLOR_GREEN}👤 你: {COLOR_RESET}"
            )
        except (KeyboardInterrupt, EOFError):
            # 处理 Ctrl+C 或 Ctrl+D 中断
            print(f"\n\n{COLOR_CYAN}👋 再见！{COLOR_RESET}")
            break

        # 去除输入两端的空白字符
        user_input = user_input.strip()

        # 如果输入为空，跳过本轮循环
        if not user_input:
            continue

        # 检查是否是退出命令
        if user_input.lower() in ("quit", "exit"):
            print(f"\n{COLOR_CYAN}👋 感谢使用，再见！{COLOR_RESET}")
            break

        # 检查是否是清屏命令
        if user_input.lower() == "clear":
            # 使用 ANSI 转义序列清屏
            os.system("clear")
            # 重新打印欢迎信息
            print_welcome()
            continue

        # ========================================
        # 阶段 2：思考（Thinking）—— 调用 LLM 推理
        # ========================================
        # 打印分隔线
        print_separator()
        # 显示"思考中"的提示
        print(f"{COLOR_DIM}  ⏳ AI 思考中...{COLOR_RESET}")

        try:
            # 调用模型进行推理
            # 注意：这里每次只发送当前一条消息，所以 AI 没有上下文记忆
            # 这就是为什么这个版本没有记忆能力的原因
            response = model.invoke(user_input)

            # ========================================
            # 阶段 3：行动（Action）—— 输出 AI 回复
            # ========================================
            # 打印 AI 的回复（response.content 是回复文本）
            print(f"\n{COLOR_BOLD}{COLOR_BLUE}🤖 AI: "
                  f"{COLOR_RESET}{response.content}\n")

        except Exception as error:
            # 如果调用模型出错，打印错误信息
            print(f"\n{COLOR_YELLOW}❌ 调用模型时出错: "
                  f"{error}{COLOR_RESET}\n")

        # ========================================
        # 阶段 4：循环（Loop）—— 自动回到循环开头
        # ========================================
        # while True 会自动回到循环开头，继续下一轮对话
        # 这就完成了 Agent 的一个完整循环！


# ============================================================
# 主程序入口
# ============================================================
if __name__ == '__main__':
    # 运行最简对话机器人
    run_chatbot()
