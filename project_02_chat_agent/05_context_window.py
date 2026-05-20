"""
Day 4 - 课程 5：Token 窗口管理 (Context Window)。

功能：演示三种防止大语言模型上下文窗口溢出的 Token 管理策略：
      1. 滑动窗口（保留最近 N 条消息）
      2. Token 预算硬限制（通过 tiktoken 精确计算并剪裁）
      3. 摘要压缩（通过 LLM 对历史消息进行合并摘要）
输入参数：无（通过终端交互输入进行测试）。
输出返回值：无（直接将剪裁前后的消息对比和效果打印输出）。
"""

# 导入系统路径模块
import sys
# 导入操作系统相关路径模块
import os

# 获取当前脚本所在绝对路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将当前目录添加至搜索路径首位
sys.path.insert(0, CURRENT_DIR)
# 将上级目录（项目根目录）添加至搜索路径首位
sys.path.insert(0, os.path.join(CURRENT_DIR, '..'))

# 导入公共模块中的模型工厂
from common.model_factory import create_model  # noqa: E402
# 导入 LangChain 基础消息类
from langchain_core.messages import (  # noqa: E402
    HumanMessage,    # 用户消息类
    AIMessage,       # AI 消息类
    SystemMessage,   # 系统规则设定消息类
)

# 尝试导入用于计算 Token 的 tiktoken 库
try:
    # 导入 tiktoken 包
    import tiktoken
# 捕获导入失败异常
except ImportError:
    # 若未安装，将 tiktoken 变量置为 None
    tiktoken = None

# ANSI 终端美化颜色代码
COLOR_RESET = "\033[0m"      # 重置样式
COLOR_BOLD = "\033[1m"       # 加粗
COLOR_GREEN = "\033[32m"     # 绿色
COLOR_BLUE = "\033[34m"      # 蓝色
COLOR_CYAN = "\033[36m"      # 青色
COLOR_YELLOW = "\033[33m"    # 黄色
COLOR_DIM = "\033[2m"        # 灰色
COLOR_MAGENTA = "\033[35m"   # 品红色


def calculate_tokens(text, model_name="cl100k_base"):
    """
    计算文本的 Token 数量。

    输入参数：
        text (str): 需要计算 Token 的文本。
        model_name (str): 编码器名称，默认使用 cl100k_base。
    输出返回值：
        int: 计算得到（或估算）的 Token 数量。
    """
    # 判断 tiktoken 库是否成功导入
    if tiktoken is not None:
        try:
            # 根据名称获取对应的编码器实例
            encoder = tiktoken.get_encoding(model_name)
            # 对文本编码，计算返回的 token 列表长度
            return len(encoder.encode(text))
        # 捕捉编码异常
        except Exception:
            # 异常时退回到估算逻辑
            pass
    # 估算公式：一个汉字或字符大约乘以 1.5 倍的 Token
    return int(len(text) * 1.5)


class ManagedHistory:
    """
    带 Token 窗口管理功能的对话历史管理器。

    功能：维护消息历史，并提供滑动窗口截断、Token 硬预算修剪以及摘要压缩等策略。
    属性：
        messages (list): 存储所有消息的列表。
        system_prompt (str): 会话的系统设定提示词。
    """

    def __init__(self, system_prompt=None):
        """
        初始化管理器。

        输入参数：
            system_prompt (str, optional): 系统角色设定提示词。
        输出返回值：无。
        """
        # 初始化为空列表
        self.messages = []
        # 保存系统提示语至属性中
        self.system_prompt = system_prompt
        # 判断系统设定提示词是否为空
        if system_prompt is not None:
            # 创建系统设定消息对象
            system_msg = SystemMessage(content=system_prompt)
            # 添加到消息列表的第一位
            self.messages.append(system_msg)

    def add_user_message(self, content):
        """
        添加一条用户消息。

        输入参数：
            content (str): 用户聊天文本。
        输出返回值：无.
        """
        # 实例化人类消息类
        user_msg = HumanMessage(content=content)
        # 添加至列表尾部
        self.messages.append(user_msg)

    def add_ai_message(self, content):
        """
        添加一条 AI 回复消息。

        输入参数：
            content (str): AI 回复文本。
        输出返回值：无。
        """
        # 实例化 AI 消息类
        ai_msg = AIMessage(content=content)
        # 添加至列表尾部
        self.messages.append(ai_msg)

    def get_messages(self):
        """
        获取当前全部消息历史。

        输入参数：无。
        输出返回值：
            list: 当前所有消息列表。
        """
        # 直接返回列表
        return self.messages

    def count_total_tokens(self):
        """
        计算当前消息历史的总 Token 数量。

        输入参数：无。
        输出返回值：
            int: 消息历史总 token 数值。
        """
        # 初始化总数变量
        total = 0
        # 循环遍历列表中每一条消息对象
        for msg in self.messages:
            # 计算每条消息内容的 token 数并累加
            total += calculate_tokens(msg.content)
        # 返回总 token 数
        return total

    def apply_sliding_window(self, max_kept_messages=6):
        """
        应用滑动窗口截断策略。

        说明：始终保留 index 0 处的 SystemMessage（如果存在）。
              修剪其余消息，使非系统消息数量不超过限制。
        输入参数：
            max_kept_messages (int): 限制保留的最大非系统消息条数。
        输出返回值：无。
        """
        # 如果当前消息总数非常少，无需处理直接返回
        if len(self.messages) <= 1:
            # 退出当前函数
            return

        # 判断第一条消息是否是 SystemMessage
        has_system = isinstance(self.messages[0], SystemMessage)

        # 检查除系统消息外，其它消息条数是否超过限制
        # 初始化除去系统消息的消息列表
        if has_system:
            # 截取系统消息之外的聊天记录列表
            chat_msgs = self.messages[1:]
        # 如果没有系统消息
        else:
            # 聊天记录就是全部消息列表
            chat_msgs = self.messages[:]

        # 判断非系统消息数是否超出设定的最大限制
        if len(chat_msgs) > max_kept_messages:
            # 截取最近的限制条数的消息
            trimmed_chats = chat_msgs[-max_kept_messages:]
            # 重新拼装整个消息列表
            if has_system:
                # 重新将系统消息与修剪后的消息拼合
                self.messages = [self.messages[0]] + trimmed_chats
            # 没有系统消息的情况
            else:
                # 直接将修剪后的列表赋予消息列表
                self.messages = trimmed_chats

    def apply_token_budget(self, max_tokens=150):
        """
        应用 Token 硬限制预算修剪策略。

        说明：计算总 Token 消耗。如果超过 max_tokens，
              则从最早的非系统消息开始删除，直到总 Token 数在预算内。
        输入参数：
            max_tokens (int): 允许的最大 Token 上限。
        输出返回值：无。
        """
        # 判断首条消息是否为系统消息
        has_system = isinstance(self.messages[0], SystemMessage) if self.messages else False

        # 如果没有消息，或者只有一条系统消息且它本身超额，直接退出
        if len(self.messages) <= 1:
            # 退出函数
            return

        # 循环修剪，直到总 token 不超过预算
        while self.count_total_tokens() > max_tokens:
            # 判断在系统消息后是否有可供删除的普通聊天消息
            if has_system and len(self.messages) > 1:
                # 移除系统消息后的第一条（即最老的一条）普通消息
                self.messages.pop(1)
            # 无系统消息的情况
            elif not has_system and len(self.messages) > 0:
                # 直接移除最老的一条普通消息
                self.messages.pop(0)
            # 如果只剩一条系统消息了，则停止删除，防止被清空
            else:
                # 终止循环
                break

    def apply_summary_compression(self, model, threshold_tokens=200):
        """
        应用摘要压缩策略。

        说明：若当前 Token 超过阈值，使用大语言模型将除最新两条消息外的历史对话进行摘要总结。
              然后用摘要系统提示语替代历史对话。
        输入参数：
            model: 大语言模型实例。
            threshold_tokens (int): 触发摘要压缩的 Token 阈值。
        输出返回值：无。
        """
        # 计算当前消息历史的总 token
        total_tokens = self.count_total_tokens()
        # 判断当前总 token 是否超过了设定的阈值
        if total_tokens <= threshold_tokens:
            # 未超额，无需压缩直接返回
            return

        # 判断首位是否是系统消息
        has_system = isinstance(self.messages[0], SystemMessage) if self.messages else False

        # 区分出系统消息和聊天消息
        if has_system:
            # 提取聊天记录
            chat_msgs = self.messages[1:]
        else:
            # 全部消息都作为聊天消息
            chat_msgs = self.messages[:]

        # 保证至少留有两条最新的消息作为当前话茬（例如：最新一轮问答）
        if len(chat_msgs) <= 3:
            # 消息太少不进行压缩
            return

        # 划分出需要被压缩的部分（除最新 2 条之外的更早的历史）
        to_summarize = chat_msgs[:-2]
        # 保留最晚新发生的 2 条消息
        keep_msgs = chat_msgs[-2:]

        # 格式化待压缩的对话为文本，用于发给 LLM
        summary_text_list = []
        # 遍历需要压缩的消息
        for msg in to_summarize:
            # 判断消息发送人角色
            role = "用户" if isinstance(msg, HumanMessage) else "AI"
            # 拼装格式化行
            summary_text_list.append(f"{role}: {msg.content}")

        # 合并所有文本行
        conversation_text = "\n".join(summary_text_list)

        # 编写总结 Prompt 提示词
        summarize_prompt = (
            "请将以下用户和 AI 的对话历史，精简总结为一段不超过 100 字的内容，"
            "并尽量保留其中的关键事实（如姓名、偏好或核心事件）：\n\n"
            f"{conversation_text}"
        )

        # 打印状态提示
        print(f"\n{COLOR_YELLOW}  ⚡ [系统提示] Token 达到限额 "
              f"({total_tokens} tokens)，"
              f"正在进行历史摘要压缩...{COLOR_RESET}")

        try:

            # 调用大语言模型，让它返回一段总结文本
            summary_response = model.invoke([HumanMessage(content=summarize_prompt)])
            # 获取总结出来的文本内容
            summary_result = summary_response.content

            # 生成一个包含摘要的新系统消息
            summary_message_content = f"以下是之前的对话历史摘要：{summary_result}"
            # 实例化为 SystemMessage
            summary_system_msg = SystemMessage(content=summary_message_content)

            # 重新拼装整个消息列表
            new_messages = []
            # 如果最初带有自定义系统提示词，先将其放回首位
            if has_system:
                # 放入初始 SystemMessage
                new_messages.append(self.messages[0])
            # 将总结好的摘要消息放入列表
            new_messages.append(summary_system_msg)
            # 再追加保留下来的最新 2 条活跃对话消息
            new_messages.extend(keep_msgs)

            # 更新当前对象的历史消息列表
            self.messages = new_messages
            # 打印压缩成功和修剪后的 token 状态
            print(f"{COLOR_GREEN}  ✨ 摘要压缩成功！当前总 Token 数"
                  f"已降低为: {self.count_total_tokens()} "
                  f"tokens{COLOR_RESET}\n")

        # 捕获压缩调用过程中的异常
        except Exception as e:
            # 打印出错原因，但不崩溃，保留原始历史
            print(f"{COLOR_YELLOW}  ⚠️ 历史摘要压缩失败！原因: {e}{COLOR_RESET}")


def print_message_list(messages, title):
    """
    打印当前的消息列表状态。

    输入参数：
        messages (list): 消息列表。
        title (str): 列表标题。
    输出返回值：无。
    """
    # 打印标题
    print(f"\n{COLOR_BOLD}{COLOR_CYAN}--- {title} ---{COLOR_RESET}")
    # 遍历并输出每条消息的类型与内容
    for index, msg in enumerate(messages):
        # 根据消息类型分配不同前缀
        if isinstance(msg, SystemMessage):
            # 系统消息前缀
            prefix = "[系统设定]"
        elif isinstance(msg, HumanMessage):
            # 用户消息前缀
            prefix = "[用户输入]"
        else:
            # AI 消息前缀
            prefix = "[ AI 回复 ]"
        # 计算当前消息的 token 长度
        toks = calculate_tokens(msg.content)
        # 格式化输出到控制台
        print(f"  {COLOR_DIM}[{index}]{COLOR_RESET} {prefix} ({toks}t): {msg.content}")
    # 打印尾部换行
    print()


def main():
    """
    主程序入口。

    功能：通过构造的长模拟对话，直观演示三种窗口修剪策略的作用效果。
    输入参数：无。
    输出返回值：无。
    """
    # 打印顶部分隔线
    print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}")
    # 打印课程标题
    print(f"{COLOR_BOLD}{COLOR_CYAN}  🧠 Token 窗口管理演示 (Context Window) - Day 4{COLOR_RESET}")
    # 打印副标题说明
    print(f"{COLOR_CYAN}  演示：1.滑动窗口 2.Token硬限制 3.大模型摘要压缩{COLOR_RESET}")
    # 打印底部分隔线
    print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}\n")

    # 创建大语言模型实例，用于摘要功能
    model = create_model("deepseek")

    # ============================================================
    # 准备一套较长的模拟对话，用于演示裁剪
    # ============================================================
    sys_prompt = "你是一个善于帮助用户理清思路的咨询师。"

    # 1. 演示滑动窗口策略
    # 实例化带管理的对话历史类
    history_sliding = ManagedHistory(system_prompt=sys_prompt)
    # 添加第 1 轮问答
    history_sliding.add_user_message("你好，我叫李华。")
    history_sliding.add_ai_message("你好，李华！今天想聊聊什么？")
    # 添加第 2 轮问答
    history_sliding.add_user_message("我目前正在学习大语言模型。")
    history_sliding.add_ai_message("那非常棒，大模型是当今最热门的技术之一。")
    # 添加第 3 轮问答
    history_sliding.add_user_message("我想写一个具有多轮会话的 Agent。")
    history_sliding.add_ai_message("理解了，需要维护消息列表来让它具有记忆。")
    # 添加第 4 轮问答
    history_sliding.add_user_message("同时我还需要解决 token 溢出的隐患。")
    history_sliding.add_ai_message("可以用滑动窗口或者摘要压缩来预防。")

    # 打印裁剪前的消息状态
    print_message_list(
        history_sliding.get_messages(),
        "应用滑动窗口前 (总 Token: {})".format(
            history_sliding.count_total_tokens()
        )
    )

    # 应用滑动窗口截断：限制保留最近的 4 条普通消息
    history_sliding.apply_sliding_window(max_kept_messages=4)
    # 打印裁剪后的消息状态
    print_message_list(history_sliding.get_messages(), "应用滑动窗口后 (保留最近 4 条非系统消息)")

    # 2. 演示 Token 预算硬限制策略
    # 重新填充一条相同对话
    history_budget = ManagedHistory(system_prompt=sys_prompt)
    history_budget.add_user_message("你好，我叫李华。")
    history_budget.add_ai_message("你好，李华！今天想聊聊什么？")
    history_budget.add_user_message("我目前正在学习大语言模型。")
    history_budget.add_ai_message("那非常棒，大模型是当今最热门的技术之一。")
    history_budget.add_user_message("我想写一个具有多轮会话的 Agent。")
    history_budget.add_ai_message("理解了，需要维护消息列表来让它具有记忆。")

    # 打印硬裁剪前的状态
    print_message_list(
        history_budget.get_messages(),
        "应用 Token 预算硬限制前 (总 Token: {})".format(
            history_budget.count_total_tokens()
        )
    )

    # 应用 Token 硬预算裁剪：只给 80 tokens 的额度（包含系统消息）
    history_budget.apply_token_budget(max_tokens=80)
    # 打印裁剪后的状态
    print_message_list(history_budget.get_messages(), "应用 Token 预算限制后 (严格限制总 Token <= 80)")

    # 3. 演示 LLM 摘要压缩策略
    # 重新填充一条较长对话
    history_summary = ManagedHistory(system_prompt=sys_prompt)
    history_summary.add_user_message("你好，我叫李华，是一个来自北京的 Python 程序员。")
    history_summary.add_ai_message("你好，李华！北京的 Python 同行，非常高兴能为你服务。")
    history_summary.add_user_message("我目前在开发一个智能客服项目，主要用 LangChain。")
    history_summary.add_ai_message("LangChain 是构建 LLM 应用的优秀框架，它组件很丰富。")
    history_summary.add_user_message("是的，但大模型经常丢掉前文的信息，这很令人头疼。")
    history_summary.add_ai_message("这正是我们需要管理上下文窗口的原因。")

    # 打印压缩前状态
    print_message_list(
        history_summary.get_messages(),
        "应用大模型摘要压缩前 (总 Token: {})".format(
            history_summary.count_total_tokens()
        )
    )

    # 设定触发阈值为 120 tokens，如果超出，则利用大模型进行摘要总结
    history_summary.apply_summary_compression(model=model, threshold_tokens=120)
    # 打印压缩后状态
    print_message_list(history_summary.get_messages(), "应用大模型摘要压缩后 (保留最初设定、中间摘要以及最新两句)")


# 运行判断
if __name__ == '__main__':
    # 运行主逻辑
    main()
