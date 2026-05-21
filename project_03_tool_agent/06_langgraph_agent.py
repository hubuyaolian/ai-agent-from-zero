"""
Day 7 - 课程 6：使用 LangGraph 构建工具 Agent。

学习目标：
    1. 掌握 LangGraph 的三个核心概念：状态 (State)、节点 (Node)、边 (Edge)。
    2. 掌握如何使用 StateGraph 构建带条件路由的图结构 Agent。
    3. 掌握 LangGraph 中 Reducer 归约器对消息列表的自动追加合并机制。
"""

# 导入系统模块
import sys
# 导入系统路径模块
import os
# 导入类型注解模块
from typing import Annotated
# 导入类型提示字典
from typing_extensions import TypedDict

# 取得当前脚本所在的绝对路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将项目根目录置入搜索路径首位
sys.path.insert(0, os.path.join(CURRENT_DIR, '..'))

# 从公共模块中导入模型构建工厂函数
from common.model_factory import create_model  # noqa: E402
# 从本地工具集中导入搜索与计算器工具
from tools import web_search, calculate  # noqa: E402
# 导入 LangChain 基础消息类
from langchain_core.messages import ToolMessage  # noqa: E402
# 导入 LangGraph 状态图与结束节点常数
from langgraph.graph import StateGraph, END  # noqa: E402
# 导入 LangGraph 内置的消息列表 Reducer 归约合并函数
from langgraph.graph.message import add_messages  # noqa: E402

# 建立本地运行工具字典映射，方便图中的工具节点动态调度
TOOLS_MAP = {
    "web_search": web_search,  # 搜索工具
    "calculate": calculate  # 计算器工具
}

# 实例化大模型，设低温度以保证确定性
MODEL = create_model("deepseek", temperature=0.1)
# 将工具绑定至模型
MODEL_WITH_TOOLS = MODEL.bind_tools([web_search, calculate])


class AgentState(TypedDict):
    """
    定义在 LangGraph 的各个节点间进行流转的状态类。

    Attributes:
        messages: 使用 add_messages 归约器注解的消息列表，
                  每次节点返回新消息时会自动追加而不会覆盖。
    """
    messages: Annotated[list, add_messages]


def agent_node(state: AgentState):
    """
    Agent 节点函数：负责调用绑定的 LLM 模型进行推理。

    输入参数：
        state: 当前图的状态。
    输出返回值：
        dict: 更新的状态字典，会被 Reducer 自动追加到 messages 列表。
    """
    # 打印节点执行提示
    print("\n[Node: agent] 正在调用大模型推理...")
    # 调用绑定了工具的模型
    response = MODEL_WITH_TOOLS.invoke(state["messages"])
    # 返回字典，消息将被追加到 messages
    return {"messages": [response]}


def tool_node(state: AgentState):
    """
    工具节点函数：执行模型决策出的工具调用列表。

    输入参数：
        state: 当前图的状态。
    输出返回值：
        dict: 包含工具执行结果 ToolMessage 的字典。
    """
    # 打印节点执行提示
    print("[Node: tools] 正在执行本地工具函数...")
    # 获取最后一条 AI 消息（包含 tool_calls 命令）
    last_message = state["messages"][-1]
    # 创建保存工具执行结果的空列表
    results = []

    # 遍历上一轮模型返回的所有工具调用请求
    for tool_call in last_message.tool_calls:
        # 获取调用唯一标识 ID
        tool_call_id = tool_call["id"]
        # 获取调用的工具名
        tool_name = tool_call["name"]
        # 获取调用的参数
        tool_args = tool_call["args"]

        # 打印执行细节
        print(f"   🔧 触发: {tool_name} (ID: {tool_call_id})")
        print(f"      参数: {tool_args}")

        # 查找对应名称的本地工具函数
        target_tool = TOOLS_MAP.get(tool_name)

        # 校验工具是否存在
        if target_tool is not None:
            # 运行工具
            tool_output = target_tool.invoke(tool_args)
        # 本地不存在对应工具
        else:
            # 报错
            tool_output = f"错误：未找到工具 '{tool_name}'"

        # 打印运行返回值
        print(f"      结果: {tool_output}")

        # 用 ToolMessage 对执行结果进行封装
        tool_msg = ToolMessage(
            content=str(tool_output),  # 强制转换为字符串
            tool_call_id=tool_call_id,  # 关联原 ID
            name=tool_name  # 工具名
        )
        # 将生成的 ToolMessage 追加到结果列表
        results.append(tool_msg)

    # 返回要追加的消息列表
    return {"messages": results}


def should_continue(state: AgentState) -> str:
    """
    条件边路由函数：根据当前状态决定图执行流程的下一步走向。

    输入参数：
        state: 当前图的状态。
    输出返回值：
        str: "tools" 表示继续前往工具节点；"end" 表示前往流程终点。
    """
    # 提取最后一条消息
    last_message = state["messages"][-1]
    # 判断该消息是否包含了工具调用命令
    if last_message.tool_calls:
        # 打印流向
        print("[Edge: should_continue] -> 存在工具调用，前往 tools 节点")
        # 返回去工具节点
        return "tools"

    # 打印流向
    print("[Edge: should_continue] -> 无工具调用，前往 END 终点")
    # 返回流程结束
    return "end"


def build_agent_graph():
    """
    手动装配和编译 LangGraph 状态图的函数。

    功能：添加节点与边，并编译生成可执行的 Runnable 应用。
    输出返回值：
        CompiledGraph: 编译后的状态图。
    """
    # 初始化状态图，指定状态数据结构为 AgentState
    workflow = StateGraph(AgentState)

    # 添加推理节点
    workflow.add_node("agent", agent_node)
    # 添加工具执行节点
    workflow.add_node("tools", tool_node)

    # 设置图的初始入口点为推理节点
    workflow.set_entry_point("agent")

    # 在推理节点后添加条件边路由
    workflow.add_conditional_edges(
        "agent",  # 条件边的起点
        should_continue,  # 条件决策函数
        {
            "tools": "tools",  # 决策函数返回 'tools' 则跳转到 'tools' 节点
            "end": END  # 返回 'end' 则直接跳转至 END 终点结束
        }
    )

    # 添加从工具执行节点返回到推理节点的普通边
    workflow.add_edge("tools", "agent")

    # 编译整个状态图流转流程
    compiled_app = workflow.compile()
    # 返回编译出的可运行图实例
    return compiled_app


def main():
    """
    Day 7 课程 6 主测试入口。
    """
    # 打印欢迎标题
    print("=" * 60)
    print("🚀 Day 7 - 课程 6：用 LangGraph 构建状态机 Tool Agent")
    print("=" * 60)

    # 编译生成状态图应用程序
    app = build_agent_graph()

    # 联合测试：查询北京天气并计算数字
    test_input = {
        "messages": [
            # 传入多步骤问题
            {"role": "user", "content": "北京的天气如何？然后算一下 12345 + 54321 等于多少？"}
        ]
    }

    try:
        # 调用编译好的图，传入初始输入
        final_state = app.invoke(test_input)
        # 获取最终回复消息
        final_msg = final_state["messages"][-1]
        # 打印最终结果
        print("\n" + "=" * 50)
        print(f"🤖 AI 最终回复: {final_msg.content}")
        print("=" * 50 + "\n")
    # 捕获图运行异常
    except Exception as e:
        # 打印
        print(f"❌ 运行异常: {e}")


# 运行判定
if __name__ == "__main__":
    # 执行 main
    main()
