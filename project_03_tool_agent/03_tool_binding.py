"""
Day 5 - 课程 3：将工具绑定到模型并执行工具流闭环。

学习目标：
    1. 掌握用 bind_tools() 将 LangChain 工具绑定至模型实例。
    2. 理解大模型推理后返回的 AIMessage 中 tool_calls 的解析。
    3. 掌握如何使用 ToolMessage 反馈工具计算结果，并获取大模型最终答复。
"""

# 导入系统模块
import sys
# 导入系统路径模块
import os


# 取得当前脚本所在的绝对目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将项目根目录置入搜索路径首位
sys.path.insert(0, os.path.join(CURRENT_DIR, '..'))

# 从公共模块中导入模型构建工厂函数
from common.model_factory import create_model  # noqa: E402
# 导入 LangChain 的 tool 装饰器
from langchain_core.tools import tool  # noqa: E402
# 导入 LangChain 的消息基础类
from langchain_core.messages import (  # noqa: E402
    HumanMessage,    # 人类消息类
    ToolMessage,     # 工具执行结果消息类
)


@tool
def get_weather(city: str) -> str:
    """
    获取指定中国城市的当前天气情况。

    Args:
        city: 城市名称，如 '北京'、'上海'。

    Returns:
        天气描述。
    """
    # 模拟简单的天气字典
    weather_dict = {
        "北京": "北京今天晴天，气温28°C，微风。",
        "上海": "上海今天小雨，气温24°C，东风3级。",
    }
    # 从字典中读取天气，若不存在则返回默认描述
    weather_result = weather_dict.get(city, f"{city}天气晴朗，气温26°C。")
    # 返回执行结果
    return weather_result


@tool
def search_products(keyword: str, max_price: float = 1000.0) -> str:
    """
    根据商品关键词和价格限制搜索匹配商品。

    Args:
        keyword: 搜索关键词，例如 '手机'、'书'。
        max_price: 最高价格上限，默认 1000.0 元。

    Returns:
        包含符合条件的商品信息的描述文字。
    """
    # 模拟简单的商品库
    products = [
        {"name": "Python从入门到精通", "price": 89.0},
        {"name": "极客蓝牙耳机", "price": 299.0},
        {"name": "智能运动手表", "price": 899.0},
    ]

    # 初始化空结果列表
    results = []
    # 循环遍历商品库
    for p in products:
        # 价格判断
        if p["price"] > max_price:
            # 价格超限则跳过
            continue

        # 关键词名称包含匹配
        if keyword in p["name"]:
            # 添加格式化条目
            results.append(f"{p['name']} ({p['price']}元)")

    # 结果非空判断
    if len(results) > 0:
        # 返回拼接文本
        return "\n".join(results)
    # 未匹配到商品的情况
    else:
        # 返回未找到
        return f"未找到价格低于 {max_price} 元且含 '{keyword}' 的商品。"


# 建立一个工具名称到工具对象实例的字典映射，供后续动态执行使用
TOOLS_MAP = {
    "get_weather": get_weather,  # 映射天气工具
    "search_products": search_products  # 映射商品搜索工具
}


def run_binding_chat(user_question):
    """
    使用 LangChain 的 bind_tools 接口演示整个工具调用的生命周期。

    功能：演示自动 Schema 绑定、工具触发判断、动态执行与最终自然语言合成。
    输入参数：
        user_question (str): 用户的提问文本。
    输出返回值：无。
    """
    # 使用工厂函数创建默认的 DeepSeek 模型实例（绑定工具通常建议温度设为 0.1 左右）
    model = create_model("deepseek", temperature=0.1)

    # 声明绑定工具列表，这里将天气工具与搜索工具都绑定至模型上
    model_with_tools = model.bind_tools([get_weather, search_products])

    # 打印用户输入
    print(f"\n💬 用户输入: {user_question}")

    # 初始化维护会话消息队列，加入当前人类问题
    messages = [
        HumanMessage(content=user_question)
    ]

    try:
        # 第一次请求大模型推理，附带工具配置
        response = model_with_tools.invoke(messages)
        # 将第一轮 AI 返回的消息对象追加到会话记录中
        messages.append(response)

        # 判断大模型返回的消息体中是否带有工具调用的命令列表
        if response.tool_calls:
            # 打印 AI 决定调用工具的消息
            print(f"🤖 AI 决定调用 {len(response.tool_calls)} 个工具")

            # 遍历这组工具调用
            for tool_call in response.tool_calls:
                # 获取本次调用的标识 ID
                tool_call_id = tool_call["id"]
                # 获取大模型决定的工具名称
                tool_name = tool_call["name"]
                # 获取大模型计算生成的参数字典
                tool_args = tool_call["args"]

                # 打印调用的工具细节信息
                print(f"   🔧 正在触发工具: {tool_name} (ID: {tool_call_id})")
                print(f"      参数: {tool_args}")

                # 从映射字典中动态查找该工具对象
                target_tool = TOOLS_MAP.get(tool_name)

                # 判断是否存在该工具
                if target_tool is not None:
                    # 通过 invoke 传递参数字典在本地执行该工具，返回结果
                    tool_result = target_tool.invoke(tool_args)
                # 未匹配到对应工具
                else:
                    # 返回错误提示文字
                    tool_result = f"错误：未在映射中找到工具 '{tool_name}'"

                # 打印本地执行完后的输出结果
                print(f"      执行结果: {tool_result}")

                # 将工具执行结果封装为 ToolMessage
                tool_msg = ToolMessage(
                    content=str(tool_result),  # 反馈的数据必须转化为字符串形式
                    tool_call_id=tool_call_id,  # 必须传入对应 tool_call 的 ID 进行绑定
                    name=tool_name  # 工具名称
                )
                # 追加到会话消息中
                messages.append(tool_msg)

            # 打印反馈提示
            print("🔄 正在将 ToolMessage 反馈至大模型进行最终自然语言生成...")
            # 第二次调用已绑定工具的模型实例（模型依据传入的消息记录中包含 ToolMessage 生成自然回复）
            final_response = model_with_tools.invoke(messages)
            # 打印大模型输出的最终自然语言回答内容
            print(f"🤖 AI 最终回复: {final_response.content}\n")
        # 模型没有要求触发任何工具，直接回答了普通文本
        else:
            # 打印普通内容
            print(f"🤖 AI 直接回复: {response.content}\n")

    # 捕获整个推理和本地执行过程中的异常
    except Exception as e:
        # 输出错误原因
        print(f"❌ 发生异常: {e}\n")


def main():
    """
    Day 5 课程 3 主测试入口。
    """
    # 打印欢迎标题
    print("=" * 60)
    print("🚀 Day 5 - 课程 3：用 bind_tools() 实现多工具调用闭环")
    print("=" * 60)

    # 示例 1：触发天气查询工具
    run_binding_chat("北京的天气如何？")

    # 示例 2：触发商品搜索工具
    run_binding_chat("我想找一下低于 500 元的耳机商品。")

    # 示例 3：常规问答，不触发任何工具
    run_binding_chat("大语言模型是如何通过几百亿参数做预测的？")


# 主程序入口运行
if __name__ == "__main__":
    # 运行 main
    main()
