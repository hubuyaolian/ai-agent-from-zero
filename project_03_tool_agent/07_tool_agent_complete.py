"""
Day 7 - 课程 7：终极多工具命令行 Agent 应用程序。

学习目标：
    1. 整合前面学习的全部能力（对话历史、Token 管理、多工具集、LangGraph）。
    2. 实现“人类确认（Human-in-the-loop）”敏感工具操作的拦截与确认逻辑。
    3. 使用 MemorySaver 存档点（Checkpoint）进行会话状态生命周期维护。
"""

# 导入系统控制模块
import sys
# 导入操作系统相关库
import os
# 导入类型注解
from typing import Annotated
# 导入类型字典
from typing_extensions import TypedDict

# 取得当前脚本所在的绝对目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将项目根目录置入搜索路径首位
sys.path.insert(0, os.path.join(CURRENT_DIR, '..'))

# 从公共模块中导入模型构建工厂函数
from common.model_factory import create_model  # noqa: E402
# 统一导入本地定义的所有工具列表
from tools import ALL_TOOLS  # noqa: E402
# 导入 LangChain 基础消息类
from langchain_core.messages import (  # noqa: E402
    HumanMessage,    # 用户消息
    AIMessage,       # AI 消息
    SystemMessage,   # 系统指令消息
    ToolMessage,     # 工具执行结果消息
)
# 导入 LangGraph 状态图与结束标志
from langgraph.graph import StateGraph, END  # noqa: E402
# 导入内置消息追加归归约器
from langgraph.graph.message import add_messages  # noqa: E402
# 导入内存存档持久化器，用于维持多轮对话上下文
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

# 尝试导入 tiktoken 以精确控制上下文窗口大小
try:
    # 导入 tiktoken 包
    import tiktoken
# 捕捉导入报错
except ImportError:
    # 若缺失则置为空，后面走备用兜底逻辑
    tiktoken = None

# 终端 ANSI 样式彩色高亮代码
COLOR_RESET = "\033[0m"      # 重置样式
COLOR_GREEN = "\033[32m"     # 绿色表示用户
COLOR_BLUE = "\033[34m"      # 蓝色表示 AI 回复
COLOR_CYAN = "\033[36m"      # 青色表示系统运行
COLOR_YELLOW = "\033[33m"    # 黄色表示工具状态
COLOR_RED = "\033[31m"       # 红色表示报错或敏感警告

# 将所有导出的工具存入一个字典方便执行匹配
TOOLS_MAP = {}
# 循环遍历
for t in ALL_TOOLS:
    # 映射键值
    TOOLS_MAP[t.name] = t

# 设置预设的系统提示词
SYSTEM_PROMPT = (
    "你是一个极其强大且安全的 AI 编程/系统助手。\n"
    "你可以使用各种本地工具来辅助回答用户的提问。\n"
    "当用户的问题需要数学计算、文件读取、网络检索或运行代码时，"
    "请毫不犹豫地调用相应工具。"
)


class AgentState(TypedDict):
    """
    定义完整的 Agent 图运行状态。

    Attributes:
        messages: 包含全部多轮对话记录的消息数组。
    """
    messages: Annotated[list, add_messages]


def count_tokens_fallback(text):
    """
    备用的字符粗略估算 Token 数量函数。

    输入参数：
        text (str): 文本内容。
    输出返回值：
        int: 估算出的 Token 数量。
    """
    # 按照 1 个中文约 1-2 Token，英文单词约 1 Token 粗略估算
    return len(text) // 2


def count_message_tokens(msg):
    """
    计算单个消息对象的 Token 数量。

    输入参数：
        msg: 消息对象（HumanMessage/AIMessage 等）。
    输出返回值：
        int: Token 数量。
    """
    # 判断是否为字符串格式
    if isinstance(msg.content, str):
        # 提取文字
        text = msg.content
    # 不是字符串
    else:
        # 强制转换为字符串
        text = str(msg.content)

    # 如果 tiktoken 库已成功导入
    if tiktoken is not None:
        try:
            # 获取默认 cl100k_base 编码器实例
            encoding = tiktoken.get_encoding("cl100k_base")
            # 编码出 Token 数组并计算长度
            return len(encoding.encode(text))
        # 捕获异常
        except Exception:
            # 走字符估算兜底
            return count_tokens_fallback(text)
    # 没有 tiktoken 模块
    else:
        # 走字符估算
        return count_tokens_fallback(text)


def trim_history(messages_list, max_tokens=3000):
    """
    剪裁消息列表，确保消息总 Token 数量不超过设定的预算，保留 System 消息。

    输入参数：
        messages_list (list): 当前的历史消息列表。
        max_tokens (int): 最大允许的 Token 数量。
    输出返回值：
        list: 剪裁后的新消息列表。
    """
    # 初始化统计总 Token 的变量
    total_tokens = 0
    # 提取系统消息列表
    system_msgs = []
    # 提取非系统消息列表
    non_system_msgs = []

    # 循环遍历整个消息数组
    for msg in messages_list:
        # 判断如果是 SystemMessage
        if isinstance(msg, SystemMessage):
            # 加入系统消息集合
            system_msgs.append(msg)
            # 累加 Token 计数
            total_tokens += count_message_tokens(msg)
        # 如果是其他对话消息
        else:
            # 加入非系统消息集合
            non_system_msgs.append(msg)

    # 逆序统计非系统消息以保留最新对话
    kept_non_system = []
    # 倒序遍历普通历史
    for msg in reversed(non_system_msgs):
        # 计算当前消息的 Token 数
        msg_token = count_message_tokens(msg)
        # 如果累加后仍然在预算额度范围以内
        if total_tokens + msg_token <= max_tokens:
            # 在首部插入消息以保持原有顺序
            kept_non_system.insert(0, msg)
            # 累加 Token 计数
            total_tokens += msg_token
        # 预算超出
        else:
            # 跳过更旧的消息
            break

    # 合并系统配置与剩余的普通消息后返回
    return system_msgs + kept_non_system


def agent_node(state: AgentState):
    """
    推理节点：进行 Token 限制修剪，并调用大模型推理。
    """
    # 提取当前状态中保存的原始消息数组
    raw_msgs = state["messages"]

    # 实施 Token 窗口剪裁限制（控制在 3000 Token 内）
    trimmed_msgs = trim_history(raw_msgs, max_tokens=3000)

    # 实例化大模型，使用低温度以确保工具参数生成的确定性
    model = create_model("deepseek", temperature=0.1)
    # 将工具列表绑定到大模型上
    model_with_tools = model.bind_tools(ALL_TOOLS)

    # 运行大模型预测生成响应消息
    response = model_with_tools.invoke(trimmed_msgs)

    # 返回消息对象，通过归约器追加到 messages 中
    return {"messages": [response]}


def tool_node(state: AgentState):
    """
    工具节点：在运行敏感工具（写文件、运行代码）前，请求用户交互确认。
    """
    # 获取最后一条包含 tool_calls 的 AI 推理消息
    last_message = state["messages"][-1]
    # 初始化本次所有工具执行的响应列表
    results = []

    # 遍历上一轮模型返回的所有工具调用请求
    for tool_call in last_message.tool_calls:
        # 提取相关参数
        tool_call_id = tool_call["id"]
        # 工具函数名
        tool_name = tool_call["name"]
        # 模型推理参数
        tool_args = tool_call["args"]

        # 定义需要人类确认的敏感危险工具清单
        sensitive_tools = ["write_file", "execute_python"]

        # 判定当前工具是否属于敏感操作
        if tool_name in sensitive_tools:
            # 打印红色醒目的安全拦截询问
            print(f"\n{COLOR_RED}⚠️  [安全防御拦截] AI 正在尝试执行敏感本地操作！{COLOR_RESET}")
            print(f"    工具名称: {tool_name}")
            print(f"    传入参数: {tool_args}")
            # 请求用户输入 y 进行确认
            confirm_input = input("👉 请问是否允许执行该操作？输入 y 同意，输入其他任意键拒绝: ")
            # 转换并去空白处理
            confirm_clean = confirm_input.strip().lower()

            # 判断如果用户拒绝授权执行
            if confirm_clean != "y":
                # 记录拒绝状态提示
                tool_output = "错误：用户拒绝了该敏感工具执行请求，操作被安全拦截中止。"
                # 打印橙黄色拒绝说明
                print(f"    {COLOR_YELLOW}🚫 已拒绝执行该操作。{COLOR_RESET}\n")

                # 构建 ToolMessage 并追加
                results.append(ToolMessage(
                    content=tool_output,
                    tool_call_id=tool_call_id,
                    name=tool_name
                ))
                # 跳过该敏感工具的本地真实运行
                continue

        # 打印正在执行的状态提示
        print(f"   {COLOR_YELLOW}📧 正在触发本地工具: {tool_name}{COLOR_RESET}")

        # 查找本地工具函数
        target_tool = TOOLS_MAP.get(tool_name)

        # 检验工具是否在本地注册
        if target_tool is not None:
            try:
                # 尝试执行本地工具
                tool_output = target_tool.invoke(tool_args)
            # 捕获工具执行过程报错
            except Exception as e:
                # 格式化错误
                tool_output = f"工具执行异常: {e}"
        # 本地无此工具
        else:
            # 设定错误
            tool_output = f"错误：本地不存在名为 '{tool_name}' 的工具。"

        # 封装为 ToolMessage 消息对象
        tool_msg = ToolMessage(
            content=str(tool_output),  # 转为字符串
            tool_call_id=tool_call_id,  # 关联 ID
            name=tool_name  # 工具名
        )
        # 加入结果列表
        results.append(tool_msg)

    # 返回状态字典更新
    return {"messages": results}


def should_continue(state: AgentState) -> str:
    """
    路由选择函数：根据是否有未执行的 tool_calls 决定后续流转。
    """
    # 提取最后一条消息
    last_message = state["messages"][-1]
    # 如果有工具调用指令
    if last_message.tool_calls:
        # 流向 tools 节点
        return "tools"
    # 无工具调用，结束图运行
    return "end"


def build_app():
    """
    构建、链接并编译带 MemorySaver 的有向图。

    输出返回值：
        CompiledGraph: 编译后的状态图应用。
    """
    # 初始化状态图
    workflow = StateGraph(AgentState)

    # 注册推理节点
    workflow.add_node("agent", agent_node)
    # 注册工具执行节点
    workflow.add_node("tools", tool_node)

    # 设置起始点
    workflow.set_entry_point("agent")

    # 配置条件边跳转
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )

    # 配置工具节点流回推理节点的普通边
    workflow.add_edge("tools", "agent")

    # 实例化内存持久化存档对象，用于在多轮对话间缓存 messages 状态
    memory = MemorySaver()

    # 编译整个状态图，并将存档器传入
    compiled_app = workflow.compile(checkpointer=memory)
    # 返回编译好的图
    return compiled_app


def list_tools_cli():
    """
    命令行下列出所有可用的本地工具。
    """
    # 打印提示
    print(f"\n{COLOR_CYAN}--- 当前注册的所有本地工具 ({len(ALL_TOOLS)} 个) ---{COLOR_RESET}")
    # 遍历工具
    for t in ALL_TOOLS:
        # 提取第一行描述
        desc_line = t.description.strip().split("\n")[0]
        # 打印名称与简短描述
        print(f"  • {COLOR_YELLOW}{t.name}{COLOR_RESET}: {desc_line}")
    # 换行
    print("")


def print_cli_welcome():
    """
    打印命令行启动的欢迎面板。
    """
    # 打印欢迎条幅
    print("=" * 65)
    print("🤖 LangGraph 终极多工具命令行 Agent 助手")
    print("=" * 65)
    print("  系统指令集 (输入斜杠指令触发):")
    print("    /tools    - 查看所有当前注册的本地工具及其描述")
    print("    /history  - 显示当前会话的完整历史对话消息记录")
    print("    /clear    - 清除当前会话的全部历史上下文")
    print("    /quit     - 退出该应用程序")
    print("=" * 65)


def show_chat_history(messages):
    """
    打印显示当前的对话历史消息细节。

    输入参数：
        messages (list): 对话历史消息列表。
    """
    # 标题提示
    print(f"\n{COLOR_CYAN}=== 当前对话历史消息记录 ({len(messages)} 条) ==={COLOR_RESET}")
    # 遍历历史消息
    for idx, msg in enumerate(messages):
        # 判断消息来源角色并设置打印颜色前缀
        if isinstance(msg, SystemMessage):
            # 系统消息置灰
            prefix = "[System]"
        elif isinstance(msg, HumanMessage):
            # 用户消息绿色
            prefix = f"{COLOR_GREEN}[User]{COLOR_RESET}"
        elif isinstance(msg, AIMessage):
            # AI 消息蓝色
            prefix = f"{COLOR_BLUE}[AI]{COLOR_RESET}"
            # 如果 AI 消息包含工具调用
            if msg.tool_calls:
                # 提取工具调用名称列表
                t_names = [tc['name'] for tc in msg.tool_calls]
                # 拼接成逗号分隔字符串
                t_names_str = ", ".join(t_names)
                # 拼接至前缀
                prefix += (
                    f" {COLOR_YELLOW}"
                    f"(请求调用工具: {t_names_str})"
                    f"{COLOR_RESET}"
                )

        elif isinstance(msg, ToolMessage):
            # 工具反馈黄色
            prefix = f"{COLOR_YELLOW}[Tool: {msg.name}]{COLOR_RESET}"
        else:
            # 兜底通用
            prefix = "[Unknown]"

        # 打印每行对话内容（缩短多行显示）
        content_snippet = str(msg.content).strip().replace("\n", " ")
        # 如果长度较长则截断
        if len(content_snippet) > 80:
            # 截取前 80 字符并加省略号
            content_snippet = content_snippet[:80] + "..."

        # 打印编号、角色和摘要
        print(f" {idx + 1:02d}. {prefix}: {content_snippet}")
    # 换行
    print("")


def run_cli_app():
    """
    启动并管理命令行循环界面。
    """
    # 打印欢迎面板
    print_cli_welcome()

    # 编译生成 LangGraph 应用
    app = build_app()

    # 设定当前会话的唯一线程 ID 标识，用于存档器寻址
    thread_config = {
        "configurable": {
            "thread_id": "cli_session_01"  # 唯一的会话线程号
        }
    }

    # 第一次初始化：在存档器的线程状态中存入初始 SystemMessage
    # 这样大模型就能够知道其系统设定，且该状态后续会一直持久化在图内存中
    app.update_state(
        thread_config,
        {"messages": [SystemMessage(content=SYSTEM_PROMPT)]}
    )

    # 启动命令行主循环
    while True:
        try:
            # 读取用户输入
            user_input = input("👤 用户 > ")
            # 清理空白字符
            clean_input = user_input.strip()

            # 如果用户输入为空
            if not clean_input:
                # 忽略，继续等待下一次输入
                continue

            # 处理退出指令
            if clean_input.lower() == "/quit":
                # 打印告别文字
                print("👋 再见！期待与您的下一次对话。")
                # 退出循环
                break

            # 处理查看工具指令
            if clean_input.lower() == "/tools":
                # 列出工具
                list_tools_cli()
                # 继续等待输入
                continue

            # 处理清除历史历史指令
            if clean_input.lower() == "/clear":
                # 重新写入全新的初始 SystemMessage，会覆盖/重置当前会话历史
                app.update_state(
                    thread_config,
                    {"messages": [SystemMessage(content=SYSTEM_PROMPT)]},
                    as_node="agent"  # 模拟由 agent 节点进行覆盖重置
                )
                # 提示成功
                print(f"{COLOR_CYAN}已清除并重置当前历史上下文消息。{COLOR_RESET}\n")
                # 继续下一次输入
                continue

            # 处理查看历史指令
            if clean_input.lower() == "/history":
                # 从 MemorySaver 中提取当前线程状态的快照对象
                state_snapshot = app.get_state(thread_config)
                # 打印历史记录
                show_chat_history(state_snapshot.values.get("messages", []))
                # 继续下一次输入
                continue

            # 执行常规会话：通过向已有的 Graph 传入新 HumanMessage 启动推理
            # MemorySaver 会自动把这个新 HumanMessage 附加到该 thread_id 已有的状态中
            graph_input = {
                "messages": [HumanMessage(content=clean_input)]
            }

            # 执行有向图，并传入会话线程配置以追踪历史
            final_state = app.invoke(graph_input, thread_config)

            # 获取并提取图执行完毕后最新添加的一条 AI 回复消息
            final_msg = final_state["messages"][-1]

            # 打印 AI 最终输出的自然语言自然回答内容
            print(f"\n{COLOR_BLUE}AI 最终回答 > {final_msg.content}{COLOR_RESET}\n")

        # 捕获用户在终端 Ctrl+C/Ctrl+D 强行中止动作
        except (KeyboardInterrupt, EOFError):
            # 优雅退出提示
            print("\n👋 终端交互被强行中断，退出程序。")
            # 跳出主循环
            break
        # 捕获其他任何未知的严重运行时异常
        except Exception as e:
            # 打印错误原因
            print(f"\n❌ 系统运行时发生错误: {e}\n")


def main():
    """
    Day 7 课程 7 主入口。
    """
    # 启动命令行主应用
    run_cli_app()


# 主程序入口运行判定
if __name__ == "__main__":
    # 执行 main
    main()
