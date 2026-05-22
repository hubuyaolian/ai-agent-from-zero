"""
Day 6 - 课程 5：工具调用的错误处理与大模型自我纠错。

学习目标：
    1. 掌握如何在 Agent Loop 中捕获本地工具执行抛出的各类异常。
    2. 掌握将捕获的错误信息包装为 ToolMessage 返回给大模型的流程。
    3. 体验大模型在收到错误反馈后如何进行合理的自我修正与重试。
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
# 导入 LangChain 的 tool 装饰器
from langchain_core.tools import tool  # noqa: E402
# 导入 LangChain 的消息基础类
from langchain_core.messages import (  # noqa: E402
    HumanMessage,    # 用户发送的消息
    ToolMessage,     # 反馈工具执行结果的消息
)


@tool
def fetch_api_data(endpoint: str) -> str:
    # 注意：此工具故意不放入 tools/ 目录，因为它专为演示错误处理而设计
    # （包含故意抛出异常的 error_test 端点），不是通用工具
    """
    获取指定 API 端点的数据。

    Args:
        endpoint: 目标端点相对路径，如 'users'、'products'、'error_test'。

    Returns:
        返回获取到的 JSON 数据字符串描述。
    """
    # 清除首尾空白
    ep_clean = endpoint.strip().lower()

    # 如果模型尝试请求了一个会导致错误的测试端点
    if ep_clean == "error_test":
        # 故意抛出一个数值类型值异常
        raise ValueError("数据库连接池超时，当前端点 'error_test' 无法提供响应服务！")

    # 正常的模拟端点数据返回
    if ep_clean == "users":
        # 返回模拟的用户 JSON 数据
        return '{"status": "success", "data": [{"id": 1, "name": "张三"}]}'
    # 其他未知端点
    else:
        # 返回普通数据
        return f'{{"status": "success", "data": "未找到端点 {endpoint} 的数据"}}'


# 建立工具名称到工具对象实例的字典映射
TOOLS_MAP = {
    "fetch_api_data": fetch_api_data  # 映射获取 API 数据工具
}


def run_error_handling_agent(user_query):
    """
    运行具备异常捕获与纠错反馈的 Agent 循环。

    功能：演示工具出错后，如何通过 ToolMessage 反馈报错并引导 LLM 进行自我修正。
    输入参数：
        user_query (str): 用户问题。
    输出返回值：无。
    """
    # 实例化底层大模型，使用低温度以保证确定性
    model = create_model("deepseek", temperature=0.1)
    # 将 fetch_api_data 工具绑定到大模型上
    model_with_tools = model.bind_tools([fetch_api_data])

    # 打印用户提问
    print(f"\n{COLOR_GREEN}用户 > {user_query}{COLOR_RESET}")

    # 初始化会话消息列表并装入初始的人类问题
    messages = [
        HumanMessage(content=user_query)
    ]

    # 初始化循环计数器
    loop_count = 0
    # 设置最大循环限制
    max_loops = 5
    # 全局超时阈值（秒），防止单次请求消耗过长时间（第三层防御）
    timeout_seconds = 60
    # 记录循环开始时间
    start_time = time.time()

    # 启动循环
    while loop_count < max_loops:
        # 计数器递增
        loop_count += 1

        # 检查是否超出全局超时阈值
        if time.time() - start_time > timeout_seconds:
            print(f"❌ 警告：Agent 运行超出 {timeout_seconds} 秒全局超时限制，强制中止！")
            break
        # 打印状态提示
        print(f"{COLOR_CYAN}🤔 AI 正在思考... [步数: {loop_count}]{COLOR_RESET}")

        try:
            # 大模型进行推理，决策是否调用工具
            response = model_with_tools.invoke(messages)
            # 将模型推理出的消息加入历史消息中
            messages.append(response)

            # 判断是否有工具调用
            if response.tool_calls:
                # 打印工具调用数量
                print(f"🤖 AI 决定调用 {len(response.tool_calls)} 个工具：")

                # 循环遍历每个工具调用
                for tool_call in response.tool_calls:
                    # 取得调用唯一标识 ID
                    tool_call_id = tool_call["id"]
                    # 取得工具函数名称
                    tool_name = tool_call["name"]
                    # 取得模型推理出的输入参数
                    tool_args = tool_call["args"]

                    # 打印触发详情
                    print(f"   🔧 正在触发工具: {tool_name}")
                    print(f"      参数: {tool_args}")

                    # 检索对应名称的本地函数
                    target_tool = TOOLS_MAP.get(tool_name)

                    # 如果找到了对应的工具
                    if target_tool is not None:
                        try:
                            # 尝试执行该工具
                            tool_output = target_tool.invoke(tool_args)
                        # 核心点：捕获工具执行中抛出的所有异常
                        except Exception as tool_err:
                            # 格式化出包含报错的特殊结果文本
                            tool_output = f"工具执行发生异常: {tool_err}"
                            # 打印黄色高亮系统警告
                            print(f"      {COLOR_YELLOW}⚠️ [系统捕获错误] {tool_output}{COLOR_RESET}")
                    # 未在映射中找到工具
                    else:
                        # 赋值错误提示
                        tool_output = f"错误：未找到名为 '{tool_name}' 的工具。"

                    # 用 ToolMessage 反馈捕获的报错数据
                    tool_msg = ToolMessage(
                        content=str(tool_output),  # 将错误堆栈/信息作为 content 发送
                        tool_call_id=tool_call_id,  # 关联原 ID
                        name=tool_name  # 工具名
                    )
                    # 追加至历史消息中，供大模型在下一步自我反省纠错
                    messages.append(tool_msg)
            # 无工具调用，完成自然语言最终响应
            else:
                # 打印 AI 最终回复
                print(f"\n{COLOR_BLUE}AI > {response.content}{COLOR_RESET}\n")
                # 正常退出循环
                break

        # 捕获外部框架或请求过程中的其他异常
        except Exception as e:
            # 打印出错提示
            print(f"❌ 运行异常: {e}")
            # 异常退出
            break
    # 超出循环次数的情形
    else:
        # 强行终止并打印警告
        print(f"❌ 警告：超出最大 {max_loops} 轮次限制，纠错失败！")


def main():
    """
    Day 6 课程 5 主测试入口。
    """
    # 打印欢迎标题
    print("=" * 60)
    print("🚀 Day 6 - 课程 5：工具调用异常捕获与自我纠错演示")
    print("=" * 60)

    # 引导任务：先引导大模型调用 error_test 产生异常，观察其是否能根据报错反馈换用正常的 users 端点重试
    run_error_handling_agent(
        "帮我调用 API 获取 'error_test' 端点的数据。"
        "如果该端点报错，请换用 'users' 端点尝试重新获取数据。"
    )


# 运行判断
if __name__ == "__main__":
    # 执行
    main()
