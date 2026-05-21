# -*- coding: utf-8 -*-
"""
Day 11 演示：纯手写实现底层 ReAct (Reasoning + Acting) 学术原理解密。

功能：不依赖 LangGraph 等图编排框架，利用精心构建的 System Prompt 引导大模型输出
      结构化的 Thought 与 Action，在外层用 Python while 循环进行解析和工具流转，
      直观展示 ReAct 的工作原理。
输入参数：无。
输出返回值：在控制台打印每一轮交替输出的 Thought、Action 及 Observation。
"""

# 导入正则表达式库，用于提取大模型输出的 Action 指令
import re
# 导入 LangChain 的消息对象
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# 从公共模型工厂中导入模型创建函数
from common.model_factory import create_model


# ============================================================
# 模拟的外部本地工具函数定义
# ============================================================

def get_weather(city):
    """
    模拟查询指定城市天气情况的工具。

    功能：根据传入的城市名称，返回硬编码的模拟气温与天气状况。
    输入参数：
        city (str): 城市名称。
    输出返回值：
        str: 气温和天气文字说明。
    """
    # 统一转为去空格的干净字符串
    city_clean = city.strip()
    # 模拟北京的天气
    if city_clean == "北京":
        # 返回北京气温
        return "北京今天晴天，气温 28°C"
    # 模拟上海的天气
    elif city_clean == "上海":
        # 返回上海气温
        return "上海今天多云，气温 32°C"
    # 其他未知城市
    else:
        # 返回未录入天气
        return f"{city_clean}的天气数据暂未录入系统。"


def calculate(expression):
    """
    模拟计算基础数学算术表达式值的工具。

    功能：使用 Python 底层算术执行传入的数学字符串，返回结果。
    输入参数：
        expression (str): 数学算式，如 "32 - 28"。
    输出返回值：
        str: 计算出的数值字符串。
    """
    try:
        # 移除非法字符，只保留数字与四则运算算符，保障执行安全性
        allowed = "0123456789+-*/.() "
        # 过滤表达式
        clean_expr = ""
        for char in expression:
            if char in allowed:
                clean_expr += char
            else:
                pass
        # 计算值
        res = eval(clean_expr)
        # 返回结果
        return str(res)
    except Exception as err:
        # 捕获异常并返回异常提示
        return f"数学公式解析计算出错: {str(err)}"


# ============================================================
# ReAct 核心循环引擎实现
# ============================================================

def parse_action(text):
    """
    使用正则表达式解析大模型输出文本中的 Action 行。

    功能：提取 'Action: tool_name(arg)' 中的工具名称和括号里的参数。
    输入参数：
        text (str): 大模型响应的纯文本内容。
    输出返回值：
        tuple: (tool_name, tool_arg) 字符串对，若未匹配到则返回 (None, None)。
    """
    # 定义正则表达式，匹配 'Action:' 开头、后接非换行符直至括号的结构
    # 格式支持: Action: get_weather("北京") 或 Action: calculate(32 - 28)
    pattern = r"Action:\s*([a-zA-Z0-9_]+)\((.*)\)"
    # 执行正则匹配
    match = re.search(pattern, text)

    # 检查是否成功匹配
    if match:
        # 提取第一组：工具名
        tool_name = match.group(1).strip()
        # 提取第二组：参数字符串，并剥离掉可能包含的首尾双引号/单引号
        tool_arg = match.group(2).strip().strip('"').strip("'")
        # 返回提取出来的键值对
        return tool_name, tool_arg
    else:
        # 匹配失败返回空值
        return None, None


def main():
    """
    主运行函数。

    功能：初始化 Qwen 模型，定义 ReAct 系统提示词，执行交替循环驱动 Thought 与 Action，展示底层解密效果。
    """
    print("🧠 正在初始化底层大模型（通义千问）...")
    # 使用公共模型工厂创建 Qwen 实例。
    # 特别注意：我们将 temperature 设为 0.0，使大模型的输出完全具备确定性和逻辑约束力！
    chat_model = create_model(provider="qwen", temperature=0.0)

    # 精心编写的 ReAct 学术解密 System Prompt。
    # 核心原理：强力规约大模型在每一步必须显式写出 Thought 与 Action 标签，并禁止一次性编造 Observation！
    react_system_prompt = (
        "你是一个善于分步思考、逻辑极度严密的 AI 助理。请遵循 ReAct (Reasoning + Acting) 范式解决用户问题。\n"
        "你需要交替输出推理(Thought)与行动(Action)。你的输出必须严格遵循以下格式：\n\n"
        "Thought: 思考你目前掌握的信息，判断还需要什么，并决定下一步调用什么工具。\n"
        "Action: 决定调用的外部工具。格式必须且只能为：工具名(参数)。例如：get_weather(北京)\n\n"
        "【重要规则】\n"
        "1. 每次你只需且只能输出一个 Thought 和一个 Action 组合。输出 Action 后必须立即停止输出，静待系统反馈 Observation！\n"
        "2. 不要自己编造 'Observation:' 行，这一行将由系统运行物理工具后，在下一轮自动拼接输入给你。\n"
        "3. 当你掌握了足够信息可以回答用户时，请不要输出 Action，而是直接以 Final Answer 格式输出，例如：\n"
        "Final Answer: 你的最终完整回答。\n\n"
        "【可调用的外部工具库】\n"
        "1. get_weather(city: str) -> str: 查询指定城市天气情况，参数为纯中文城市名字（如：北京）。\n"
        "2. calculate(expression: str) -> str: 计算基础数学四则运算表达式的值，参数为算式（如：32-28）。\n"
    )

    # 准备测试提问：对比北京和上海哪座城市更热，并且计算它们气温的差值是多少。
    user_query = "帮我查询一下：今天北京和上海哪个城市更热？并且它们的气温相差多少度？"

    print(f"\n❓ 用户提问: '{user_query}'")

    # 初始化全局多轮消息列表，载入 System Prompt 和用户提问
    messages = [
        SystemMessage(content=react_system_prompt),
        HumanMessage(content=user_query)
    ]

    # 定义最大循环步数，防止死循环
    max_steps = 6
    # 当前步数计数器
    step = 0
    # 工具名字到 Python 物理函数对象的字典绑定映射
    tools_map = {
        "get_weather": get_weather,
        "calculate": calculate
    }

    # 启动手写 ReAct 引擎的主循环
    while step < max_steps:
        # 累加步数
        step += 1
        print(f"\n--- [ReAct Step {step}] ---")

        # 调用大模型，传入全部包含 Observation 往复拼接的消息历史
        response = chat_model.invoke(messages)

        # 提取模型本次输出的纯文本内容
        output_text = response.content
        # 打印大模型本轮输出的思考内容
        print(output_text)

        # 将大模型本轮的 AIMessage 追加到消息队列中
        messages.append(AIMessage(content=output_text))

        # 检查模型本轮响应中是否给出了最终回答 "Final Answer:"
        if "Final Answer:" in output_text:
            print("\n🎉 ReAct 循环顺利结束，Agent 给出最终答案！")
            break
        else:
            pass

        # 解析模型输出中的 Action 行，识别出工具名及入参
        tool_name, tool_arg = parse_action(output_text)

        # 如果成功解析出工具及参数
        if tool_name and tool_arg:
            # 检查工具是否在已注册映射表中
            if tool_name in tools_map:
                # 获取工具函数
                func = tools_map[tool_name]
                # 物理执行工具
                print(f"   [系统物理执行] 调用外部工具: {tool_name} | 参数: '{tool_arg}'")
                observation_res = func(tool_arg)
            else:
                # 工具未找到
                observation_res = f"错误：未注册名为 '{tool_name}' 的工具。"

            # 打印系统反馈回来的观察结果
            print(f"   [观察结果反馈] Observation: '{observation_res}'")

            # 关键一步！构建 Observation 字符串，作为一条 HumanMessage 追加回消息队列中。
            # 这是 ReAct 的精髓所在：用 Observation 充当新一轮的环境感知输入，引导大模型进行下一步推理！
            observation_msg = HumanMessage(content=f"Observation: {observation_res}")
            messages.append(observation_msg)
        else:
            # 既没有 Final Answer，也没有解析出 Action，可能发生格式偏差
            print("⚠️ 未匹配到标准 Action 或 Final Answer 格式，正在强制补充提示...")
            error_hint = HumanMessage(
                content="系统提示：你的回复没有符合 Action(参数) 格式或 Final Answer 格式，请继续按规范执行。"
            )
            messages.append(error_hint)

    # 循环退出自检
    if step >= max_steps:
        print("\n⚠️ 达到最大思考深度限制，未完成完整问答。")
    else:
        pass


# 判断是否自命令行直接运行
if __name__ == "__main__":
    # 执行主程序
    main()
