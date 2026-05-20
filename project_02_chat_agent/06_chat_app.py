"""
Day 4 - 课程 6：综合对话应用 (Chat App)。

功能：整合多会话管理与 Token 窗口控制，实现一个功能完备的交互式终端对话应用。
      支持多会话隔离、角色扮演切换、大模型切换，并自动在后台应用 Token 窗口预算限制。
输入参数：无（通过终端交互输入进行测试）。
输出返回值：无（直接将交互界面和回复输出至控制台）。
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

# 从项目配置中导入角色设定、角色列表及默认模型获取函数
from config import (  # noqa: E402
    SYSTEM_PROMPTS,       # 预定义的系统角色提示词字典
    ROLE_NAMES,           # 可用角色名称列表
    get_default_model,    # 获取模型实例函数
)

# 导入公共模块中的可用提供商列表获取函数
from common.config import list_available_providers  # noqa: E402
# 导入 LangChain 消息基础类
from langchain_core.messages import (  # noqa: E402
    HumanMessage,    # 用户消息类
    AIMessage,       # AI 消息类
    SystemMessage,   # 系统消息类
)

# 尝试导入 tiktoken 库用于精确 token 计算
try:
    # 导入 tiktoken 包
    import tiktoken
# 捕获包导入失败的异常
except ImportError:
    # 若缺失则置为 None
    tiktoken = None

# ANSI 终端转义颜色代码定义
COLOR_RESET = "\033[0m"      # 重置样式
COLOR_BOLD = "\033[1m"       # 文本加粗
COLOR_GREEN = "\033[32m"     # 绿色表示用户
COLOR_BLUE = "\033[34m"      # 蓝色表示 AI
COLOR_CYAN = "\033[36m"      # 青色表示系统
COLOR_YELLOW = "\033[33m"    # 黄色表示警告
COLOR_DIM = "\033[2m"        # 灰色表示辅助线
COLOR_MAGENTA = "\033[35m"   # 品红色表示列表


def get_token_count(text, model_name="cl100k_base"):
    """
    计算文本的 Token 数量。

    输入参数：
        text (str): 待计算的文本内容。
        model_name (str): 编码模型名称。
    输出返回值：
        int: Token 数量。
    """
    # 检查 tiktoken 库是否可用
    if tiktoken is not None:
        try:
            # 取得对应的分词编码器
            encoder = tiktoken.get_encoding(model_name)
            # 对输入文本分词并返回长度
            return len(encoder.encode(text))
        # 捕捉异常
        except Exception:
            # 异常时降级到估算逻辑
            pass
    # 汉字/字符数乘 1.5 倍估算
    return int(len(text) * 1.5)


class ManagedHistory:
    """
    带 Token 自动修剪功能的会话对话历史。

    功能：维护某一个会话的消息记录，并根据预算修剪过往历史或自动生成摘要。
    属性：
        messages (list): 消息历史。
        system_prompt (str): 该会话的 System Prompt。
        role_name (str): 该会话当前扮演的角色名称。
    """

    def __init__(self, role_name, system_prompt=None):
        """
        初始化会话历史。

        输入参数：
            role_name (str): 会话所扮演的角色。
            system_prompt (str, optional): 对应的提示词。
        输出返回值：无。
        """
        # 保存角色名称到属性
        self.role_name = role_name
        # 保存系统提示语到属性
        self.system_prompt = system_prompt
        # 初始化空列表用于存储消息对象
        self.messages = []
        # 判断提示词是否非空
        if system_prompt is not None:
            # 实例化系统消息并追加
            self.messages.append(SystemMessage(content=system_prompt))

    def add_user_message(self, content):
        """
        添加一条用户发送的消息。

        输入参数：
            content (str): 消息文本。
        输出返回值：无。
        """
        # 实例化用户消息类并追加到消息历史
        self.messages.append(HumanMessage(content=content))

    def add_ai_message(self, content):
        """
        添加一条 AI 回复的消息。

        输入参数：
            content (str): AI 的文本回复。
        输出返回值：无。
        """
        # 实例化 AI 消息类并追加到消息历史
        self.messages.append(AIMessage(content=content))

    def get_messages(self):
        """
        获取当前会话的全部消息历史。

        输入参数：无。
        输出返回值：
            list: 消息列表。
        """
        # 返回列表
        return self.messages

    def count_total_tokens(self):
        """
        计算并获取当前整个历史中全部消息的 Token 数量。

        输入参数：无。
        输出返回值：
            int: 累计 Token 数量。
        """
        # 初始化累加变量
        total = 0
        # 遍历列表中的所有消息对象
        for msg in self.messages:
            # 累加各消息的 Token 数量
            total += get_token_count(msg.content)
        # 返回总和
        return total

    def apply_token_budget(self, max_tokens):
        """
        修剪历史消息以满足 Token 限制。

        输入参数：
            max_tokens (int): 限制的最大 Token。
        输出返回值：无。
        """
        # 确认是否存在系统消息（第 0 位是否是 SystemMessage）
        has_system = isinstance(self.messages[0], SystemMessage) if self.messages else False

        # 如果没有消息，或者只有系统消息，则不进行裁剪
        if len(self.messages) <= 1:
            # 退出当前函数
            return

        # 循环移除最旧的普通消息，直到总 Token 小于等于限额
        while self.count_total_tokens() > max_tokens:
            # 判断系统消息后是否还有可删除的普通聊天记录
            if has_system and len(self.messages) > 1:
                # 剔除系统提示之后的第 1 条消息（即最早的用户/AI 消息）
                self.messages.pop(1)
            # 无系统消息的情况
            elif not has_system and len(self.messages) > 0:
                # 直接剔除第一条消息
                self.messages.pop(0)
            # 如果只剩唯一一条系统消息了，则中断，不将系统设定清除
            else:
                # 退出循环
                break

    def apply_summary_compression(self, model, threshold_tokens):
        """
        使用 LLM 将除最后两条活跃消息外的历史自动生成摘要。

        输入参数：
            model: 模型实例。
            threshold_tokens (int): 触发摘要的 Token 阈值。
        输出返回值：无。
        """
        # 计算当前累积的总 Token 数
        total_tokens = self.count_total_tokens()
        # 若没超出阈值，直接跳过
        if total_tokens <= threshold_tokens:
            # 退出函数
            return

        # 确认是否存在首位系统消息
        has_system = isinstance(self.messages[0], SystemMessage) if self.messages else False

        # 拆分系统消息和聊天消息
        if has_system:
            # 截取普通聊天记录
            chat_msgs = self.messages[1:]
        else:
            # 无系统消息，则全部都是聊天记录
            chat_msgs = self.messages[:]

        # 确保保留最新 2 条聊天消息，其余部分起码要大于 1 条才适合压缩
        if len(chat_msgs) <= 3:
            # 消息条数太少，直接放弃压缩
            return

        # 待压缩的消息
        to_summarize = chat_msgs[:-2]
        # 需完好保留的最新两条活跃消息
        keep_msgs = chat_msgs[-2:]

        # 循环拼接每一条待压缩的文本
        summary_text_list = []
        # 遍历需要总结的消息
        for msg in to_summarize:
            # 依据类型划分出角色标签
            role = "用户" if isinstance(msg, HumanMessage) else "AI"
            # 组装格式化字符串并添加
            summary_text_list.append(f"{role}: {msg.content}")

        # 用换行符拼接成完整文本
        conversation_text = "\n".join(summary_text_list)

        # 构造给 LLM 的总结指令 Prompt
        summarize_prompt = (
            "请将以下对话历史精炼压缩成一段不超过 100 字的摘要：\n\n"
            f"{conversation_text}"
        )

        # 打印自动执行系统摘要压缩的黄色提示
        print(f"\n{COLOR_YELLOW}  ⚡ [系统状态] 当前 Token 数为 "
              f"{total_tokens}，超过阈值 {threshold_tokens}。"
              f"正在自动生成历史摘要并清理内存...{COLOR_RESET}")

        try:

            # 阻塞调用模型进行摘要生成
            response = model.invoke([HumanMessage(content=summarize_prompt)])
            # 提炼出生成的总结结果
            summary_result = response.content

            # 生成表示历史摘要的系统消息对象
            summary_system_msg = SystemMessage(
                content=f"以下为早期对话历史的摘要：{summary_result}"
            )

            # 初始化构建全新的历史列表
            new_messages = []
            # 如果最初存在自定义的系统角色设定，先写入第一位
            if has_system:
                # 添加初始系统设定
                new_messages.append(self.messages[0])
            # 将摘要消息写入
            new_messages.append(summary_system_msg)
            # 拼接保留下来的最新两条活跃对话消息
            new_messages.extend(keep_msgs)

            # 更新当前对象的消息历史属性
            self.messages = new_messages
            # 输出压缩完毕和新 Token 数据提示
            print(f"{COLOR_GREEN}  ✨ 摘要生成完毕！当前已降低至: "
                  f"{self.count_total_tokens()} tokens{COLOR_RESET}\n")

        # 捕获压缩过程错误，防止程序崩溃
        except Exception as e:

            # 打印错误原因
            print(f"{COLOR_YELLOW}  ⚠️ 自动摘要合并异常: {e}{COLOR_RESET}")

    def clear(self):
        """
        清空当前会话的历史（保留 System Prompt）。

        输入参数：无。
        输出返回值：无。
        """
        # 将消息重置为空列表
        self.messages = []
        # 检查是否存在系统指令设定
        if self.system_prompt is not None:
            # 重新追加系统消息对象到首位
            self.messages.append(SystemMessage(content=self.system_prompt))


class SessionManager:
    """
    带滑动窗口与自动摘要管理的会话管理器。

    功能：隔离多个会话，并随时跟踪处于激活状态的会话 ID。
    属性：
        sessions (dict): 保存格式为 {session_id: ManagedHistory}。
        active_session_id (str): 当前活跃会话 ID。
    """

    def __init__(self):
        """
        初始化会话管理器。

        输入参数：无。
        输出返回值：无。
        """
        # 初始化存储会话的空字典
        self.sessions = {}
        # 活跃会话 ID 初始化为 None
        self.active_session_id = None

    def create_session(self, session_id, role_name, system_prompt=None):
        """
        创建一个新会话。

        输入参数：
            session_id (str): 会话 ID。
            role_name (str): 角色名称。
            system_prompt (str, optional): 角色提示词。
        输出返回值：
            ManagedHistory: 创建的会话对象实例。
        """
        # 判断当前 ID 是否在字典中不存在
        if session_id not in self.sessions:
            # 实例化带管理的对话历史类并写入字典
            self.sessions[session_id] = ManagedHistory(
                role_name=role_name,
                system_prompt=system_prompt
            )

        # 返回对应会话对象
        return self.sessions[session_id]

    def get_session(self, session_id):
        """
        获取指定会话对象。

        输入参数：
            session_id (str): 会话唯一 ID。
        输出返回值：
            ManagedHistory: 目标会话对象。
        """
        # 从会话字典获取
        return self.sessions.get(session_id)

    def delete_session(self, session_id):
        """
        删除一个会话。

        输入参数：
            session_id (str): 会话 ID。
        输出返回值：
            bool: 是否删除成功。
        """
        # 确认目标 ID 是否存在
        if session_id in self.sessions:
            # 移除键值对
            self.sessions.pop(session_id)
            # 检查删除的是否是当前处于活跃状态的会话
            if self.active_session_id == session_id:
                # 置当前激活 ID 为 None
                self.active_session_id = None
            # 返回成功
            return True
        # 返回失败
        return False

    def list_sessions(self):
        """
        获取所有会话的 ID 列表。

        输入参数：无。
        输出返回值：
            list: 会话 ID 列表。
        """
        # 转换为列表形式返回
        return list(self.sessions.keys())

    def set_active_session(self, session_id):
        """
        设置活跃的会话。

        输入参数：
            session_id (str): 会话 ID。
        输出返回值：
            bool: 是否设置成功。
        """
        # 保证设置的目标在字典中存在
        if session_id in self.sessions:
            # 设置活跃 ID 为目标
            self.active_session_id = session_id
            # 返回成功
            return True
        # 返回失败
        return False


class ChatApp:
    """
    综合对话应用主逻辑。

    功能：封装多会话、换模型、换角色、Token 限制等所有应用控制流程。
    属性：
        manager (SessionManager): 隔离多会话的管理器实例。
        provider (str): 当前大语言模型提供商。
        temperature (float): 大模型生成温度。
        model: 模型实例。
        max_tokens (int): 限制最大 Token 数量。
        threshold_tokens (int): 触发摘要的 Token 阈值。
    """

    def __init__(self):
        """
        初始化综合对话应用。

        输入参数：无。
        输出返回值：无。
        """
        # 实例化会话管理器
        self.manager = SessionManager()
        # 默认大语言模型提供商设为 deepseek
        self.provider = "deepseek"
        # 默认设定生成温度为 0.7
        self.temperature = 0.7
        # 限制每条会话的总 Token 额度上限为 400
        self.max_tokens = 400
        # 设定只要超过 300 Token 即在后台引发摘要压缩
        self.threshold_tokens = 300

        # 根据当前配置创建出模型实例对象并赋值
        self.model = get_default_model(
            provider=self.provider,
            temperature=self.temperature
        )

        # 创建默认名为 'default' 的初始化会话，默认角色设为 '默认助手'
        default_prompt = SYSTEM_PROMPTS.get("默认助手")
        # 调用管理器创建出该会话
        self.manager.create_session("default", "默认助手", default_prompt)
        # 将默认会话置为活跃激活状态
        self.manager.set_active_session("default")

    def print_welcome(self):
        """
        输出美观的欢迎和提示信息。

        输入参数：无。
        输出返回值：无。
        """
        # 打印顶部分隔线
        print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}")
        # 打印应用标题
        print(f"{COLOR_BOLD}{COLOR_CYAN}  🦸 综合对话 App (Chat App CLI) - Day 4 终极实战{COLOR_RESET}")
        # 打印特性列表
        print(f"{COLOR_CYAN}  整合功能: 多会话隔离、模型及角色切换、Token 预算控制{COLOR_RESET}")
        # 打印底部分隔线
        print(f"{COLOR_DIM}{'═' * 60}{COLOR_RESET}")

        # 调用函数输出指令提示菜单
        self.print_help()

    def print_help(self):
        """
        打印可控制命令清单。

        输入参数：无。
        输出返回值：无。
        """
        # 打印标题
        print(f"\n{COLOR_YELLOW}  📌 控制台支持的交互命令：{COLOR_RESET}")
        # 新建会话命令
        print("    /new <会话ID>      - 创建并切换到一个新会话（默认助手角色）")
        # 切换会话命令
        print("    /switch <会话ID>   - 切换到已有的会话")
        # 列出所有会话
        print("    /sessions          - 显示当前全部会话状态与 Token 统计")
        # 删除会话
        print("    /delete <会话ID>   - 删除指定会话")
        # 切换扮演角色
        print("    /role              - 给当前会话切换系统预定义角色")
        # 切换模型提供商
        print("    /model             - 切换当前的底层大语言模型")
        # 查看详细消息历史
        print("    /history           - 打印当前活跃会话的完整历史详情")
        # 清空当前历史
        print("    /clear             - 清空当前活跃会话历史")
        # 打印帮助信息
        print("    /help              - 显示此命令帮助菜单")
        # 退出应用
        print("    /quit 或 exit      - 退出程序\n")

    def handle_role_change(self):

        """
        处理修改当前活跃会话的角色。

        说明：更改角色将更新并清空对应会话的消息历史，防止设定冲突。
        输入参数：无。
        输出返回值：无。
        """
        # 取得当前活跃会话 ID
        active_id = self.manager.active_session_id
        # 若当前没有活跃会话，抛出警告并直接返回
        if active_id is None:
            # 打印警告
            print(f"{COLOR_YELLOW}  ⚠️ 当前没有活跃会话，无法更改角色。{COLOR_RESET}")
            # 退出当前函数
            return

        # 打印角色挑选提示标题
        print(f"\n{COLOR_MAGENTA}  🎭 请选择您想为当前会话切换的角色编号：{COLOR_RESET}")
        # 循环列出所有可选的系统角色名称
        for idx, r_name in enumerate(ROLE_NAMES):
            # 输出序号与名称
            print(f"    [{idx + 1}] {r_name}")

        # 捕获用户在终端的序号输入
        try:
            # 读取输入去除首尾空格
            choice_str = input(f"\n{COLOR_CYAN}请输入编号 > {COLOR_RESET}").strip()
            # 转换为 1 索引的数值
            choice_idx = int(choice_str) - 1

            # 校验输入的索引是否在合法数组范围内
            if choice_idx >= 0 and choice_idx < len(ROLE_NAMES):
                # 取得挑选的角色文本名称
                selected_role = ROLE_NAMES[choice_idx]
                # 取得对应的提示词
                selected_prompt = SYSTEM_PROMPTS.get(selected_role)

                # 获取当前的活跃会话历史实例
                session = self.manager.get_session(active_id)
                # 修改该会话的角色属性
                session.role_name = selected_role
                # 更新其系统设定属性
                session.system_prompt = selected_prompt
                # 执行清空以重写系统消息
                session.clear()

                # 输出修改成功通知
                print(f"{COLOR_CYAN}  ✨ 会话 '{active_id}' 角色已成功"
                      f"切换为 '{selected_role}' 并重置历史。{COLOR_RESET}\n")

            # 校验索引超出范围
            else:
                # 打印范围溢出警告
                print(f"{COLOR_YELLOW}  ⚠️ 输入的编号超出范围！{COLOR_RESET}\n")
        # 捕获不合法的数值格式输入
        except ValueError:
            # 提示非数值
            print(f"{COLOR_YELLOW}  ⚠️ 输入格式不正确，请输入有效的数字编号！{COLOR_RESET}\n")

    def handle_model_change(self):
        """
        处理底层大语言模型的切换。

        输入参数：无。
        输出返回值：无。
        """
        # 获取系统可用的提供商数组
        available = list_available_providers()

        # 打印挑选提示
        print(f"\n{COLOR_MAGENTA}  🤖 请选择您想切换的大模型提供商编号（当前: {self.provider}）：{COLOR_RESET}")
        # 循环列出可用的提供商
        for idx, p_name in enumerate(available):
            # 格式化输出到控制台
            print(f"    [{idx + 1}] {p_name}")

        # 捕获终端序号选择
        try:
            # 读取输入
            choice_str = input(f"\n{COLOR_CYAN}请输入编号 > {COLOR_RESET}").strip()
            # 转为 0 索引
            choice_idx = int(choice_str) - 1

            # 检查索引是否有效
            if choice_idx >= 0 and choice_idx < len(available):
                # 取得新选择的提供商名称
                new_provider = available[choice_idx]
                # 更新本应用的 provider 属性
                self.provider = new_provider

                # 打印模型重建状态
                print(f"{COLOR_CYAN}  🔄 正在连接并创建新模型 {new_provider} ...{COLOR_RESET}")
                # 重新构建大语言模型实例
                self.model = get_default_model(
                    provider=new_provider,
                    temperature=self.temperature
                )
                # 打印成功提示
                print(f"{COLOR_GREEN}  ✨ 底层大模型已成功更换为: '{new_provider}'{COLOR_RESET}\n")
            # 校验失败
            else:
                # 警告输出
                print(f"{COLOR_YELLOW}  ⚠️ 输入的编号超出范围！{COLOR_RESET}\n")
        # 捕捉异常
        except ValueError:
            # 警告输出
            print(f"{COLOR_YELLOW}  ⚠️ 输入格式不正确，请输入有效的数字编号！{COLOR_RESET}\n")
        # 捕获连接或工厂函数出错
        except Exception as err:
            # 报告详细错误
            print(f"{COLOR_YELLOW}  ⚠️ 实例化大模型发生异常，已退回：{err}{COLOR_RESET}\n")

    def handle_sessions_list(self):
        """
        打印所有活跃会话的状态和 Token 计数统计。

        输入参数：无。
        输出返回值：无。
        """
        # 获取管理器中所有会话 ID 数组
        sessions = self.manager.list_sessions()
        # 打印标题
        print(f"\n{COLOR_MAGENTA}  📋 活跃会话状态统计列表：{COLOR_RESET}")
        # 循环每一个 ID
        for s_id in sessions:
            # 根据 ID 取得具体的会话对象
            session = self.manager.get_session(s_id)
            # 取得该会话累计的 Token 数量
            toks = session.count_total_tokens()
            # 取得当前扮演的角色名称
            role = session.role_name

            # 区分当前激活和普通状态
            if s_id == self.manager.active_session_id:
                # 加粗高亮输出
                print(f"    * {COLOR_BOLD}{COLOR_GREEN}{s_id}{COLOR_RESET} "
                      f"[角色: {role}] ({toks} tokens) (当前活跃)")

            else:
                # 正常辅助色输出
                print(f"      {s_id} [角色: {role}] ({toks} tokens)")
        # 输出空行
        print()

    def handle_history_detail(self):
        """
        打印当前会话的所有历史消息和对应 Token 占用细节。

        输入参数：无。
        输出返回值：无。
        """
        # 取得当前活跃会话 ID
        active_id = self.manager.active_session_id
        # 校验是否为空
        if active_id is None:
            # 打印警告
            print(f"{COLOR_YELLOW}  ⚠️ 当前没有活跃会话。{COLOR_RESET}")
            # 退出当前函数
            return

        # 取得活跃会话历史实例
        session = self.manager.get_session(active_id)
        # 获取消息数组
        msgs = session.get_messages()

        # 打印明细标题
        print(f"\n{COLOR_CYAN}  📜 会话 '{active_id}' (共 {len(msgs)} 条消息) 详情：{COLOR_RESET}")
        # 循环列举
        for idx, m in enumerate(msgs):
            # 获取单条消息 token 数
            tok = get_token_count(m.content)
            # 判断消息发送来源类型
            if isinstance(m, SystemMessage):
                # 系统消息
                prefix = f"{COLOR_YELLOW}[系统指令]"
            elif isinstance(m, HumanMessage):
                # 用户消息
                prefix = f"{COLOR_GREEN}[用户消息]"
            else:
                # AI 消息
                prefix = f"{COLOR_BLUE}[ AI 消息]"

            # 打印详细明细行
            print(f"    {COLOR_DIM}[{idx}]{COLOR_RESET} {prefix} ({tok}t) > {m.content}")
        # 打印当前总消耗情况
        print(f"  {COLOR_MAGENTA}总计占用: {session.count_total_tokens()} "
              f"/ {self.max_tokens} tokens{COLOR_RESET}\n")

    def run(self):

        """
        启动应用主循环。

        输入参数：无。
        输出返回值：无。
        """
        # 首先打印欢迎大界面和帮助菜单
        self.print_welcome()

        # 启动 CLI 无限循环
        while True:
            # 获取最新的活跃会话 ID
            active_id = self.manager.active_session_id
            # 判断是否存在活跃会话
            if active_id is None:
                # 无会话交互提示
                prompt_str = f"{COLOR_YELLOW}(无活跃会话) 请输入指令 > {COLOR_RESET}"
            # 存在活跃会话的情况
            else:
                # 获取该会话对象
                session = self.manager.get_session(active_id)
                # 实时计算该会话 Token
                toks = session.count_total_tokens()
                # 取得其当前角色名称
                role = session.role_name
                # 拼接展示会话 ID、扮演角色和所剩 Token 的综合提示符
                prompt_str = f"{COLOR_GREEN}({active_id} | {role} | {toks}t) 用户 > {COLOR_RESET}"

            # 获取用户输入并去除空格
            user_input = input(prompt_str).strip()

            # 忽略空输入
            if not user_input:
                # 循环继续
                continue

            # 处理退出应用指令
            if user_input.lower() == "/quit":
                # 输出再见
                print(f"\n{COLOR_CYAN}  已退出综合对话应用。祝学习愉快！{COLOR_RESET}\n")
                # 退出
                break
            # 兼容普通 exit 输入
            if user_input.lower() == "exit":
                # 输出再见
                print(f"\n{COLOR_CYAN}  已退出综合对话应用。祝学习愉快！{COLOR_RESET}\n")
                # 退出
                break

            # 处理帮助指令
            if user_input.lower() == "/help":
                # 调用打印菜单
                self.print_help()
                # 循环继续
                continue

            # 处理查看统计指令
            if user_input.lower() == "/sessions":
                # 调用列表打印方法
                self.handle_sessions_list()
                # 继续
                continue

            # 处理查看明细历史指令
            if user_input.lower() == "/history":
                # 调用查看历史方法
                self.handle_history_detail()
                # 继续
                continue

            # 处理角色修改指令
            if user_input.lower() == "/role":
                # 调用角色修改方法
                self.handle_role_change()
                # 继续
                continue

            # 处理模型切换指令
            if user_input.lower() == "/model":
                # 调用模型切换方法
                self.handle_model_change()
                # 继续
                continue

            # 处理新建会话逻辑
            if user_input.startswith("/new "):
                # 提起会话 ID
                new_id = user_input[5:].strip()
                # 校验非空
                if not new_id:
                    # 提示非空
                    print(f"{COLOR_YELLOW}  ⚠️ 请输入有效的会话 ID。{COLOR_RESET}")
                    # 继续
                    continue
                # 获取系统默认角色设定
                default_prompt = SYSTEM_PROMPTS.get("默认助手")
                # 创建新会话对象，设定为默认助手
                self.manager.create_session(new_id, "默认助手", default_prompt)
                # 激活该会话
                self.manager.set_active_session(new_id)
                # 打印成功
                print(f"{COLOR_CYAN}  ✨ 成功创建并激活会话 '{new_id}'{COLOR_RESET}\n")
                # 继续
                continue

            # 处理切换会话逻辑
            if user_input.startswith("/switch "):
                # 提炼目标 ID
                target_id = user_input[8:].strip()
                # 切换当前激活会话
                success = self.manager.set_active_session(target_id)
                # 判断成功与否
                if success:
                    # 提示切换成功
                    print(f"{COLOR_CYAN}  🔄 成功切换至会话 '{target_id}'{COLOR_RESET}\n")
                else:
                    # 提示未找到
                    print(f"{COLOR_YELLOW}  ⚠️ 未找到会话 ID: '{target_id}'{COLOR_RESET}")
                # 继续
                continue

            # 处理删除会话逻辑
            if user_input.startswith("/delete "):
                # 提炼删除 ID
                del_id = user_input[8:].strip()
                # 尝试删除
                success = self.manager.delete_session(del_id)
                # 判断
                if success:
                    # 打印成功
                    print(f"{COLOR_CYAN}  ❌ 会话 '{del_id}' 已经成功删除。{COLOR_RESET}")
                    # 判断当前是否还有激活会话
                    if self.manager.active_session_id is None:
                        # 提醒
                        print(f"{COLOR_YELLOW}  ⚠️ 当前无活跃会话，请使用 /new 或 /switch！{COLOR_RESET}")
                    # 打印换行
                    print()
                else:
                    # 提示未找到
                    print(f"{COLOR_YELLOW}  ⚠️ 找不到该会话 ID: '{del_id}'{COLOR_RESET}")
                # 继续
                continue

            # 处理清空当前历史指令
            if user_input.lower() == "/clear":
                # 校验活跃
                if active_id is not None:
                    # 清空当前活跃会话消息
                    self.manager.get_session(active_id).clear()
                    # 打印成功
                    print(f"{COLOR_CYAN}  🧹 会话 '{active_id}' 的消息历史已成功清空。{COLOR_RESET}\n")
                else:
                    # 打印警告
                    print(f"{COLOR_YELLOW}  ⚠️ 当前没有活跃会话，操作失效。{COLOR_RESET}")
                # 继续
                continue

            # 阻止无会话状态直接对话
            if active_id is None:
                # 打印指引
                print(f"{COLOR_YELLOW}  ⚠️ 请先建立或切换到一个活跃会话后，再开始打字聊天！{COLOR_RESET}")
                # 继续
                continue

            # 取得当前的活跃会话历史对象
            active_session = self.manager.get_session(active_id)
            # 添加人类的文本消息
            active_session.add_user_message(user_input)

            # --- 自动 Token 窗口管理机制 ---
            # 1. 自动进行大模型摘要压缩（如果超过门槛值 300）
            active_session.apply_summary_compression(self.model, self.threshold_tokens)
            # 2. 自动进行 Token 预算硬裁剪（如果仍超出最大 400 阈值）
            active_session.apply_token_budget(self.max_tokens)

            # 打印大模型正在思考状态
            print(f"\n{COLOR_CYAN}  🤔 ({self.provider}) AI 正在思考...{COLOR_RESET}")

            try:
                # 调用当前大模型实例，传入裁剪或摘要化处理后的整个历史列表
                response = self.model.invoke(active_session.get_messages())
                # 获取回复的纯文本内容
                reply_content = response.content
                # 追加到会话消息历史中
                active_session.add_ai_message(reply_content)

                # --- 再次整理 Token 窗口保障新回复添加后不瞬间超标 ---
                active_session.apply_token_budget(self.max_tokens)

                # 输出分割线并打印结果
                print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}")
                # 输出 AI 回复文本
                print(f"{COLOR_BLUE}AI ({self.provider}) > {COLOR_RESET}{reply_content}")
                # 输出分割线
                print(f"{COLOR_DIM}{'─' * 50}{COLOR_RESET}\n")

            # 捕获调用大语言模型时的错误
            except Exception as e:
                # 打印报错内容
                print(f"{COLOR_YELLOW}  ⚠️ 连接或调用大模型出错，原因为: {e}{COLOR_RESET}\n")


def main():
    """
    程序主入口。

    输入参数：无。
    输出返回值：无。
    """
    # 实例化综合对话应用类
    app = ChatApp()
    # 运行其主循环
    app.run()


# 运行入口常规判断
if __name__ == '__main__':
    # 启动
    main()
