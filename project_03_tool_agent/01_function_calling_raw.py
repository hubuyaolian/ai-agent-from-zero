"""
Day 5 - 课程 1：原始 API 调用工具调用（不使用框架）。

学习目标：
    1. 理解大模型工具调用的底层交互逻辑与通信协议（HTTP POST）。
    2. 掌握请求体中 tools 参数的 JSON 声明结构。
    3. 掌握解析 tool_calls 返回数据的处理逻辑。
    4. 手动执行本地 Python 工具函数并将结果反馈回大模型。
"""

# 导入系统模块
import sys
# 导入系统路径模块
import os
# 导入 JSON 序列化反序列化库
import json
# 导入 HTTP 请求库
import requests

# 取得当前脚本的绝对目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将上级目录（根目录）插入系统搜索路径首位
sys.path.insert(0, os.path.join(CURRENT_DIR, '..'))

# 导入公共模块中的配置获取函数
from common.config import get_model_config  # noqa: E402


def get_weather(city):
    """
    获取指定城市的当前天气。

    功能：模拟本地天气数据接口。
    输入参数：
        city (str): 城市名称。
    输出返回值：
        str: 包含天气的描述文字。
    """
    # 模拟简单的天气字典
    weather_dict = {
        "北京": "北京今天晴天，气温28°C，微风。",
        "上海": "上海今天小雨，气温24°C，东风3级。",
        "广州": "广州今天多云，气温32°C，南风2级。",
    }
    # 从字典获取数据，没有则返回默认描述
    weather_result = weather_dict.get(city, f"{city}天气晴朗，气温26°C。")
    # 返回执行结果
    return weather_result


def calculate(expression):
    """
    计算数学表达式的值。

    功能：支持基本的加减乘除与乘方算术运算。
    输入参数：
        expression (str): 数学表达式，如 "123 * 456"。
    输出返回值：
        str: 计算结果或错误描述。
    """
    # 限制安全的计算字符集
    allowed_chars = "0123456789+-*/(). "
    # 遍历输入的表达式中的每个字符
    for char in expression:
        # 如果当前字符不在安全字符集中
        if char not in allowed_chars:
            # 返回安全性警告
            return "错误：输入包含非法或不安全的字符！"

    try:
        # 执行算术求值
        calc_result = eval(expression)
        # 将求值结果转为字符串并返回
        return str(calc_result)
    # 捕捉表达式求值过程中的异常
    except Exception as e:
        # 返回运算错误提示
        return f"运算错误：{e}"


# 定义大模型支持的工具的 JSON Schema 清单
TOOLS_SCHEMA = [
    {
        "type": "function",  # 指定工具类别为函数型
        "function": {  # 函数详细属性
            "name": "get_weather",  # 函数的名称
            "description": "获取指定城市的当前天气状况信息。",  # 函数功能描述
            "parameters": {  # 参数定义的 JSON Schema
                "type": "object",  # 参数必须为对象（字典）
                "properties": {  # 参数包含哪些属性
                    "city": {  # city 属性描述
                        "type": "string",  # 必须是字符串
                        "description": "需要查询的城市名称，如 '北京'、'上海'。"  # 描述
                    }
                },
                "required": ["city"]  # 必填的参数列表
            }
        }
    },
    {
        "type": "function",  # 指定工具类别为函数型
        "function": {  # 函数详细属性
            "name": "calculate",  # 函数名称
            "description": "对一个简单的数学表达式执行计算，返回精准结果。",  # 功能描述
            "parameters": {  # 参数定义
                "type": "object",  # 必须是对象
                "properties": {  # 属性
                    "expression": {  # 表达式属性描述
                        "type": "string",  # 必须是字符串
                        "description": "标准的数学表达式，如 '123 * 456'。"  # 详细说明
                    }
                },
                "required": ["expression"]  # 必填属性
            }
        }
    }
]


def raw_tool_chat(user_question):
    """
    完整演示 Function Calling 底层生命周期的函数。

    功能：处理单次提问的工具调用逻辑并打印全生命周期的控制台消息。
    输入参数：
        user_question (str): 用户的提问文本。
    输出返回值：无。
    """
    # 获取 DeepSeek 模型的配置参数
    config = get_model_config("deepseek")
    # 获取大模型的端点请求地址
    api_url = f"{config['base_url']}/chat/completions"
    # 获取大模型 API 的请求头部信息
    headers = {
        "Authorization": f"Bearer {config['api_key']}",  # 携带 Bearer 令牌
        "Content-Type": "application/json"  # 数据格式为 JSON
    }

    # 初始化存储所有对话消息的列表
    messages = [
        # 加入当前的用户提问
        {"role": "user", "content": user_question}
    ]

    # 打印提示：展示初始用户输入
    print(f"\n💬 用户输入: {user_question}")

    # 构建调用大模型接口的请求负载字典
    payload = {
        "model": config["default_model"],  # 大模型对应的具体型号名称
        "messages": messages,  # 消息历史数组
        "tools": TOOLS_SCHEMA,  # 传入当前所支持的所有本地工具的定义定义
        "temperature": 0.1  # 使用极低温度确保工具调用的参数高度稳定精准
    }

    try:
        # 发送第一次 HTTP POST 阻碍请求
        response = requests.post(api_url, headers=headers, json=payload)
        # 获取第一次请求响应的 JSON 对象数据
        response_data = response.json()

        # 判断请求响应是否包含错误状态
        if "error" in response_data:
            # 打印出错提示信息
            print(f"❌ 接口请求报错: {response_data['error']}")
            # 退出当前聊天处理函数
            return

        # 提炼出响应回包里的消息体字典
        choice_message = response_data["choices"][0]["message"]
        # 将本次返回的 AI 消息（无论是否含 tool_calls）追加到对话历史中
        messages.append(choice_message)

        # 判断模型是否在返回值中声明了需要调用本地工具的 tool_calls 列表
        if choice_message.get("tool_calls"):
            # 获取全部的工具调用条目列表
            tool_calls = choice_message["tool_calls"]
            # 打印调试信息：AI 判定需要调用几个工具
            print(f"🤖 AI 回复: 决定调用 {len(tool_calls)} 个本地工具！")

            # 遍历每个工具调用条目
            for tool_call in tool_calls:
                # 获取该工具调用的唯一 ID
                tool_call_id = tool_call["id"]
                # 获取被大模型选中调用的函数名称
                func_name = tool_call["function"]["name"]
                # 获取模型为函数生成的输入参数（JSON 格式字符串）
                func_args_str = tool_call["function"]["arguments"]
                # 将字符串反序列化为字典对象
                func_args = json.loads(func_args_str)

                # 打印被调用的函数名以及参数
                print(f"   🔧 正在触发本地工具: {func_name} (ID: {tool_call_id})")
                print(f"      参数: {func_args_str}")

                # 根据被调用名称判定指向
                if func_name == "get_weather":
                    # 执行天气服务函数并取得返回值
                    tool_output = get_weather(city=func_args.get("city"))
                # 如果调用的是计算器服务
                elif func_name == "calculate":
                    # 执行计算服务函数并取得返回值
                    tool_output = calculate(expression=func_args.get("expression"))
                # 未匹配到任何本地工具名称
                else:
                    # 返回提示
                    tool_output = f"错误：未在本地找到名为 '{func_name}' 的工具。"

                # 打印出本地工具函数的实际执行结果
                print(f"      结果: {tool_output}")

                # 创建角色为 tool 的消息追加到当前对话消息列表中以反馈结果
                messages.append({
                    "role": "tool",  # 设置角色为 tool 表示工具输出
                    "tool_call_id": tool_call_id,  # 关联原 tool_call 的 ID
                    "name": func_name,  # 工具名称
                    "content": tool_output  # 工具函数真正的执行返回值
                })

            # 打印提示：第二步把反馈发回大模型
            print("🔄 正在将工具执行结果反馈至大模型...")

            # 组建第二次大模型请求负载（这次不需要重复附带 tools 参数了）
            second_payload = {
                "model": config["default_model"],  # 默认模型名称
                "messages": messages,  # 包含用户、assistant(tool_calls) 和 tool(结果) 的消息列表
                "temperature": 0.7  # 使用常温生成回复
            }

            # 发送第二次 HTTP POST 请求大模型
            second_response = requests.post(api_url, headers=headers, json=second_payload)
            # 获取第二次响应的 JSON 结果
            second_data = second_response.json()
            # 获取大模型的最终自然语言回复内容
            final_content = second_data["choices"][0]["message"]["content"]
            # 打印大模型参考工具结果后的最终回复
            print(f"🤖 AI 最终回复: {final_content}\n")
        # 模型没有判定需要执行工具调用
        else:
            # 打印普通的回复文本内容
            print(f"🤖 AI 直接回复: {choice_message.get('content')}\n")

    # 捕获请求过程中的任何网络或系统异常
    except Exception as e:
        # 输出异常详情
        print(f"❌ 发生异常: {e}\n")


def main():
    """
    Day 5 课程 1 主测试入口。
    """
    # 打印欢迎标题
    print("=" * 60)
    print("🚀 Day 5 - 课程 1：手写原始 Function Calling 闭环演示")
    print("=" * 60)

    # 示例 1：测试天气工具调用
    raw_tool_chat("我想知道上海和广州的天气情况如何？")

    # 示例 2：测试数学计算工具调用
    raw_tool_chat("你能帮我算一下 379 乘以 642 等于多少吗？")

    # 示例 3：测试不需要调用工具的常规普通提问
    raw_tool_chat("Python 里的 lambda 表达式怎么写？")


# 主程序入口运行
if __name__ == "__main__":
    # 启动 main
    main()
