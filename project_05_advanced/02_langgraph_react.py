# -*- coding: utf-8 -*-
"""
Day 11 演示：使用 LangGraph 的 create_react_agent 搭建 ReAct 状态图。

功能：利用 LangGraph 预构建组件，无缝整合大模型与外部工具，演示如何流式追踪
      并打印 ReAct 状态图中各步骤的流转消息（AIMessage, ToolMessage）。
输入参数：无。
输出返回值：控制台流式渲染 Agent 的每个状态流节点信息。
"""

# 导入 LangChain 的 @tool 装饰器，将普通函数快速封装为规范工具
from langchain_core.tools import tool
# 导入 LangChain 的 HumanMessage 消息类
from langchain_core.messages import HumanMessage
# 导入 LangGraph 预构建的 ReAct 状态图构建器
from langgraph.prebuilt import create_react_agent

# 从公共模型工厂中导入模型创建函数
from common.model_factory import create_model


# ============================================================
# 利用 @tool 装饰器定义 Agent 的外部可用工具
# ============================================================

@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气情况。

    当用户询问关于某一个特定城市（如北京、上海等）的温度、气象或晴雨情况时，
    调用此工具获取最新数据。

    Args:
        city: 城市的中文名称。

    Returns:
        str: 查询到的天气气温信息。
    """
    # 剔除城市名称的多余空格
    city_name = city.strip()
    # 匹配北京天气
    if city_name == "北京":
        # 返回北京数据
        return "北京今天晴天，气温为 28°C。"
    # 匹配上海天气
    elif city_name == "上海":
        # 返回上海数据
        return "上海今天多云，气温为 32°C。"
    # 匹配其他城市
    else:
        # 返回默认未找到
        return f"抱歉，暂未查询到 {city_name} 的实时气象信息。"


@tool
def calculate(expression: str) -> str:
    """计算数学四则运算表达式的值。

    当需要对数值进行加、减、乘、除等算术处理，计算温差、比例或倍数时，
    调用此工具获取高精度的计算数值。

    Args:
        expression: 四则运算算式字符串，例如 "32 - 28"。

    Returns:
        str: 算术计算出的答案。
    """
    try:
        # 移除非安全字符，防止代码执行注入漏洞
        allowed_chars = "0123456789+-*/.() "
        # 过滤表达式
        sanitized = ""
        for char in expression:
            if char in allowed_chars:
                sanitized += char
            else:
                pass
        # 使用 eval 计算数学结果值
        val = eval(sanitized)
        # 将结果转化为字符串返回
        return str(val)
    except Exception as err:
        # 捕获公式异常并返回报错提示
        return f"算术运算失败，原因: {str(err)}"


def main():
    """
    主运行函数。

    功能：初始化 Qwen 模型，定义 ReAct 系统提示词，利用 LangGraph 编译状态图，流式运行任务并解析流数据。
    """
    print("🧠 正在配置底层大模型（xiaomi mimo）并绑定外部工具...")
    # 教学阶段 04 之后默认 LLM 统一走 xiaomi mimo，温度设为 0.0
    base_model = create_model(provider="xiaomi mimo", temperature=0.0)

    # 将定义的工具存入工具列表中
    my_tools = [get_weather, calculate]

    # 定义系统提示词，用于精细引导大模型的推理行为与输出态度
    system_prompt = (
        "你是一个善于思考的专业 AI 技术顾问。\n"
        "在回答用户问题时，请严格遵守以下思维闭环：\n"
        "1. 仔细阅读并理解用户的指令意图。\n"
        "2. 拆解问题，分步骤使用工具来获取外部真实事实，请不要凭空胡乱猜想。\n"
        "3. 得到所有必要的事实后，进行逻辑推演，得出客观的结论。\n\n"
        "请始终保持条理分明，用最亲切的态度给学员做出解答。"
    )

    print("\n📦 正在使用 LangGraph create_react_agent 编译状态图机...")
    # 编译生成 ReAct 状态图 Agent。
    # 这一步内部会为我们自动构建 Node (大模型节点、工具节点) 以及 Edge (条件路由边、普通跳转边)。
    agent_app = create_react_agent(
        model=base_model,  # 绑定的模型实例
        tools=my_tools,  # 工具列表
        prompt=system_prompt  # 注入系统提示词
    )
    print("✅ 状态图机编译成功！")

    # 设计复合测试问题
    complex_question = "帮我查一下，今天上海和北京的气温各是多少度？它们相差多少度？哪个城市更热？"
    print("\n⚔️ 场景演练开始！")
    print(f"❓ 问题内容: '{complex_question}'")

    # 构建启动状态状态输入字典
    initial_state = {
        "messages": [HumanMessage(content=complex_question)]
    }

    # 启动流式追踪执行。
    # 注意：我们这里使用 stream_mode="values" 模式。
    # 这一模式每当有任何节点（如 agent 节点或 action 节点）修改了 State 中的 values 属性时，
    # 就会向外抛出一个完整的、更新后的 values 状态包。
    print("\n🚀 开始流式执行节点追踪 (stream_mode='values'):")
    print("=" * 60)

    # 遍历流式发生的事件流
    for event in agent_app.stream(initial_state, stream_mode="values"):
        # 检查事件中是否存在 "messages" 列表，并且列表不为空
        if "messages" in event and event["messages"]:
            # 提取消息历史列表中的最后一条最新消息
            last_message = event["messages"][-1]

            # 识别并打印该消息的类型与发送主体
            msg_type = last_message.type.upper()

            # 根据消息类型输出不同的颜色或格式
            if msg_type == "HUMAN":
                # 用户提问消息
                print(f"\n👤 [用户输入] >>> {last_message.content}")
            elif msg_type == "AI":
                # AI 模型生成的思考或工具调用消息
                print("\n🤖 [AI 思考/生成]:")
                # 检查模型是否输出 tool_calls 指令
                if last_message.tool_calls:
                    # 遍历并打印具体的工具调用
                    for tc in last_message.tool_calls:
                        print(f"   👉 指令: 调用外部工具 '{tc['name']}'，参数为: {tc['args']}")
                else:
                    # 否则是正常生成的文本回答
                    print(last_message.content)
            elif msg_type == "TOOL":
                # 工具执行结果反馈消息
                print("\n🔧 [工具 Observation]:")
                print(f"   📥 反馈数据: '{last_message.content}'")
            else:
                # 其他类型消息
                print(f"\n💬 [{msg_type}]: {last_message.content}")
        else:
            # 异常或无消息事件
            pass

    print("=" * 60)
    print("✨ LangGraph 预构建 ReAct 流式追踪演练圆满结束。")


# 判断是否由命令行直接启动
if __name__ == "__main__":
    # 执行主程序
    main()
