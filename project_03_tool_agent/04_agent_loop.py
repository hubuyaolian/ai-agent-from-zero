"""
Day 6 - 课程 4：自动化的 Agent Loop (智能体循环)。

学习目标：
    1. 掌握如何通过 while True 循环构建自动化的推理与行动（ReAct 雏形）循环。
    2. 掌握多轮工具调用的处理，直到大模型认为问题被完全解决。
    3. 在命令行中优雅直观地展示 Agent 的决策与工具执行链条。
"""

# 导入系统模块
import sys
# 导入系统路径模块
import os
# 导入时间模块，用于全局超时熔断
import time

# 取得当前脚本所在的绝对路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将项目根目录置入搜索路径首位
sys.path.insert(0, os.path.join(CURRENT_DIR, '..'))

# 从公共模块中导入模型构建工厂函数
from common.model_factory import create_model  # noqa: E402
# 从公共模块中导入终端 ANSI 颜色常量
from common.colors import (  # noqa: E402
    COLOR_RESET, COLOR_GREEN, COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW,
)
# 统一导入已定义的全部工具列表
from tools import ALL_TOOLS  # noqa: E402
# 导入 LangChain 的消息基础类
from langchain_core.messages import (  # noqa: E402
    HumanMessage,    # 用户发送的消息
    ToolMessage,     # 反馈工具执行结果的消息
)

# 建立工具名称到工具实例字典的映射，便于动态调用
TOOLS_MAP = {}
# 遍历工具列表
for t in ALL_TOOLS:
    # 建立映射关系
    TOOLS_MAP[t.name] = t


def run_agent_loop(user_query):
    """
    运行手写的 Agent 自动循环（Agent Loop）。

    功能：接收用户问题，循环调用 LLM 和工具，直到完成任务并返回最终答复。
    输入参数：
        user_query (str): 用户的问题或命令。
    输出返回值：无。
    """
    # 实例化底层大模型，使用低温度以确保工具参数生成的确定性
    model = create_model("deepseek", temperature=0.1)
    # 将包含所有工具定义的列表绑定到模型实例
    model_with_tools = model.bind_tools(ALL_TOOLS)

    # 打印用户指令
    print(f"\n{COLOR_GREEN}用户 > {user_query}{COLOR_RESET}")

    # 初始化维护当前会话的完整消息记录列表
    messages = [
        # 写入用户的第一条问题
        HumanMessage(content=user_query)
    ]

    # 初始化累计循环计数器
    loop_count = 0
    # 限制最大运行步骤数，防止陷入无限死循环
    max_loops = 5
    # 全局超时阈值（秒），防止单次请求消耗过长时间（第三层防御）
    timeout_seconds = 60
    # 记录循环开始时间
    start_time = time.time()

    # 启动自动化的推理与行动循环
    while loop_count < max_loops:
        # 累加循环步数
        loop_count += 1

        # 检查是否超出全局超时阈值
        if time.time() - start_time > timeout_seconds:
            print(f"❌ 警告：Agent 运行超出 {timeout_seconds} 秒全局超时限制，强制中止！")
            break
        # 打印当前思考提示
        print(f"{COLOR_CYAN}🤔 AI 正在思考... [步数: {loop_count}]{COLOR_RESET}")

        try:
            # 携带历史消息列表调用绑定了工具的模型实例进行推理
            response = model_with_tools.invoke(messages)
            # 将模型的推理结果消息对象追加到会话记录中
            messages.append(response)

            # 判定大模型是否决定在此步调用本地工具
            if response.tool_calls:
                # 打印决定调用的工具总数
                print(f"🤖 AI 决定调用 {len(response.tool_calls)} 个本地工具：")

                # 遍历这组需要调用的工具条目
                for tool_call in response.tool_calls:
                    # 取得调用标识 ID
                    tool_call_id = tool_call["id"]
                    # 取得被请求工具名称
                    tool_name = tool_call["name"]
                    # 取得模型生成的参数
                    tool_args = tool_call["args"]

                    # 打印正在调用的工具名与入参
                    print(f"   {COLOR_YELLOW}📧 调用工具: {tool_name}{COLOR_RESET}")
                    print(f"      参数: {tool_args}")

                    # 从映射字典中查找该工具对象
                    target_tool = TOOLS_MAP.get(tool_name)

                    # 如果工具存在于本地映射中
                    if target_tool is not None:
                        # 触发该工具的 invoke 进行计算并取得返回值
                        tool_output = target_tool.invoke(tool_args)
                    # 未在本地找到该工具
                    else:
                        # 返回错误说明
                        tool_output = f"错误：本地不存在名为 '{tool_name}' 的工具。"

                    # 打印执行完毕的工具反馈数据
                    print(f"      结果: {tool_output}")

                    # 将执行返回值构建成 ToolMessage 对象
                    tool_msg = ToolMessage(
                        content=str(tool_output),  # 返回数据必须转为字符串
                        tool_call_id=tool_call_id,  # 关联对应的 tool_call.id
                        name=tool_name  # 工具名称
                    )
                    # 追加工具结果消息对象到历史中，供下一次循环时发送给 LLM
                    messages.append(tool_msg)
            # 模型没有输出 tool_calls，意味着任务已经分析完毕，形成了最终自然语言回答
            else:
                # 输出 AI 的最终自然语言回复
                print(f"\n{COLOR_BLUE}AI > {response.content}{COLOR_RESET}\n")
                # 跳出 while 循环，结束当前会话的交互
                break

        # 捕获循环过程中的网络、连接或大模型服务等异常
        except Exception as e:
            # 打印出错提示
            print(f"❌ 运行异常: {e}")
            # 异常跳出，防止持续循环
            break
    # 如果超出了设定的最大循环限制次数
    else:
        # 打印超限警告
        print(f"❌ 警告：Agent 运行超出了最大 {max_loops} 轮次限制，强行中止！")


def main():
    """
    Day 6 课程 4 主测试程序。
    """
    # 打印欢迎标题
    print("=" * 60)
    print("🚀 Day 6 - 课程 4：手写自动化的 Agent Loop 演示")
    print("=" * 60)

    # 复杂联合任务：需要进行数学运算，并将计算结果写入文本文件中
    run_agent_loop(
        "帮我算一下 829 乘以 356 等于多少，"
        "然后把算出来的具体结果写到名为 result.txt 的文件中。"
    )


# 主程序入口运行
if __name__ == "__main__":
    # 运行 main
    main()
