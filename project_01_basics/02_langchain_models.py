"""
==========================================================================
Day 1 - 课程 2：用 LangChain 框架调用多个大模型
==========================================================================

学习目标：
    1. 掌握 LangChain 框架的基本用法（ChatOpenAI / ChatGoogleGenerativeAI）
    2. 理解框架如何封装底层 HTTP 请求（对比课程 1 的手动调用）
    3. 学会通过工厂函数一键切换不同模型
    4. 掌握三种消息类型：SystemMessage、HumanMessage、AIMessage
    5. 理解 model.invoke() 的返回值结构（AIMessage 对象）

对比手动调用的区别：
    课程 1 中，我们手动：
        1. 构建 headers（Authorization Bearer Token）
        2. 构建 payload（model, messages, temperature）
        3. 发送 HTTP POST 请求
        4. 解析 JSON 响应
        5. 提取 choices[0].message.content

    使用 LangChain 后：
        model = ChatOpenAI(base_url=..., api_key=..., model=...)
        result = model.invoke("你好")
        print(result.content)
        → 一行代码搞定！框架帮你做了上面 5 个步骤。

    LangChain 的优势：
        - 统一接口：不同模型用相同的代码调用
        - 类型安全：消息和响应都是对象，不用手动处理 JSON
        - 易于扩展：可以链式组合模型、提示词模板、输出解析器
        - 生态丰富：支持记忆、工具、Agent 等高级功能

前置条件：
    - 已在 .env 文件中配置了至少一个模型的 API Key
    - 已安装 langchain-openai 和 langchain-google-genai
==========================================================================
"""

import sys  # 系统模块，用于修改 Python 模块搜索路径
import os  # 操作系统模块，用于路径操作

# ============================================================
# 路径配置：将项目根目录添加到 Python 模块搜索路径
# ============================================================
# __file__ 是当前脚本的文件路径
# os.path.dirname(__file__) 获取当前脚本所在目录（project_01_basics/）
# os.path.join(..., "..") 向上一级，到达项目根目录（agent/）
# os.path.abspath() 将相对路径转为绝对路径
# 这样 Python 就能找到 common 包中的模块了
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
# 将项目根目录插入到搜索路径的最前面
# 使用 insert(0, ...) 确保优先从项目根目录查找模块
sys.path.insert(0, project_root)

# 从公共模块导入工厂函数和配置函数
from common.model_factory import create_model  # noqa: E402  # 创建模型实例的工厂函数
from common.config import list_available_providers  # noqa: E402  # 列出可用的模型提供商

# 导入 LangChain 的消息类型
from langchain_core.messages import (  # noqa: E402
    HumanMessage,  # 用户消息类
    SystemMessage,  # 系统消息类
    AIMessage,  # AI 回复消息类
)


def demo_basic_call():
    """
    演示基础调用：用 LangChain 调用单个模型。

    功能：展示最简单的 LangChain 调用方式，一行代码完成对话。
    输入参数：无。
    输出返回值：无（直接打印结果到控制台）。
    """
    # 打印分隔线和标题
    print("=" * 60)
    print("演示 1：基础调用 —— 用 LangChain 调用 DeepSeek")
    print("=" * 60)

    # 使用工厂函数创建 DeepSeek 模型实例
    # create_model() 在内部做了以下事情：
    #   1. 从 config.py 读取 base_url 和 api_key
    #   2. 创建 ChatOpenAI(base_url=..., api_key=..., model=...) 实例
    model = create_model(provider="deepseek")

    # 打印模型信息
    print(f"\n模型类型: {type(model).__name__}")  # 打印模型的类名

    # ---- 方式 1：直接传入字符串 ----
    # model.invoke() 接受字符串时，会自动包装为 HumanMessage
    print("\n--- 方式 1：直接传入字符串 ---")
    result = model.invoke("你好，请用一句话介绍你自己。")  # 调用模型

    # 打印返回值的类型和内容
    print(f"返回值类型: {type(result).__name__}")  # AIMessage
    print(f"回答内容: {result.content}")  # 模型的回答文本

    # ---- 方式 2：传入消息列表 ----
    # 可以传入包含多种消息类型的列表，更灵活
    print("\n--- 方式 2：传入消息列表 ---")
    messages = [
        HumanMessage(content="1 + 1 等于几？"),  # 创建用户消息对象
    ]
    result = model.invoke(messages)  # 调用模型
    print(f"回答: {result.content}")  # 打印回答

    print()


def demo_switch_model():
    """
    演示模型切换：只改一个参数，就能切换到不同模型。

    功能：展示 LangChain + 工厂函数的核心优势——
          同一套代码，通过修改 provider 参数，即可调用不同的模型。
    输入参数：无。
    输出返回值：无（直接打印结果到控制台）。
    """
    # 打印分隔线和标题
    print("=" * 60)
    print("演示 2：模型切换 —— 只需改一个参数")
    print("=" * 60)

    # 获取所有已配置 API Key 的模型提供商
    available_providers = list_available_providers()
    print(f"\n当前可用的模型提供商: {available_providers}")

    # 定义要提问的问题
    question = "请用一句话解释什么是机器学习。"
    print(f"统一问题: {question}\n")

    # 遍历所有可用的提供商，逐个调用
    for provider in available_providers:
        # 打印当前正在调用的模型
        print(f"--- 调用 {provider} ---")

        # 使用 try-except 包裹，防止某个模型调用失败影响其他模型
        try:
            # 创建该提供商的模型实例
            # 注意：只需要改变 provider 参数，其他代码完全一样！
            model = create_model(provider=provider)

            # 调用模型获取回答
            result = model.invoke(question)

            # 打印模型的回答
            print(f"回答: {result.content}")
        except Exception as e:
            # 如果调用失败，打印错误信息但继续运行
            print(f"调用失败: {e}")

        # 打印空行分隔不同模型的输出
        print()


def demo_message_types():
    """
    演示三种消息类型：SystemMessage、HumanMessage、AIMessage。

    功能：详细讲解 LangChain 中的三种消息类型及其用途。
          - SystemMessage: 系统级指令，设定模型的行为规则
          - HumanMessage: 用户的输入消息
          - AIMessage: 模型的回复消息（也可以手动创建，用于模拟对话历史）
    输入参数：无。
    输出返回值：无（直接打印结果到控制台）。
    """
    # 打印分隔线和标题
    print("=" * 60)
    print("演示 3：三种消息类型详解")
    print("=" * 60)

    # 创建模型实例
    model = create_model(provider="deepseek")

    # ---- SystemMessage 演示 ----
    print("\n--- SystemMessage（系统消息） ---")
    print("作用：设定模型的行为规则，类似于给模型一个'人设'")
    print("特点：用户看不到这条消息，但模型会严格遵守")

    # 构建包含系统消息的对话
    messages_with_system = [
        SystemMessage(content="你是一位诗人，所有回答都必须用诗歌的形式。"),  # 系统指令
        HumanMessage(content="请介绍一下春天。"),  # 用户问题
    ]

    # 调用模型
    result = model.invoke(messages_with_system)
    print(f"回答（诗歌形式）:\n{result.content}")

    # ---- AIMessage 演示 ----
    print("\n--- AIMessage（AI 消息） ---")
    print("作用：表示模型之前的回复，用于构建对话历史")
    print("特点：可以手动创建，模拟之前的对话上下文")

    # 构建包含对话历史的消息列表
    # 手动创建 AIMessage 来模拟之前的对话
    messages_with_history = [
        SystemMessage(content="你是一位 Python 编程专家。"),  # 系统指令
        HumanMessage(content="Python 是什么？"),  # 用户第一个问题
        AIMessage(content="Python 是一种高级编程语言，以简洁易读著称。"),  # 模拟的模型回答
        HumanMessage(content="它有什么主要特点？"),  # 用户的后续问题（依赖上下文）
    ]

    # 调用模型
    # 模型会看到完整的对话历史，理解"它"指的是 Python
    result = model.invoke(messages_with_history)
    print(f"回答（基于上下文）:\n{result.content}")

    print()


def demo_invoke_result():
    """
    演示 model.invoke() 的返回值结构。

    功能：详细展示 AIMessage 对象的各个属性，
          帮助理解 LangChain 的返回值不仅仅是文本。
    输入参数：无。
    输出返回值：无（直接打印结果到控制台）。
    """
    # 打印分隔线和标题
    print("=" * 60)
    print("演示 4：invoke() 返回值结构详解")
    print("=" * 60)

    # 创建模型实例
    model = create_model(provider="deepseek")

    # 调用模型
    result = model.invoke("你好")

    # 逐个展示 AIMessage 对象的属性
    print(f"\n返回值类型: {type(result).__name__}")  # 类型名称
    print(f"content（回答文本）: {result.content}")  # 最常用的属性

    # response_metadata 包含了完整的 API 响应元数据
    print(f"\nresponse_metadata（响应元数据）:")
    # 安全地访问可能存在的元数据字段
    if hasattr(result, "response_metadata"):
        # 遍历元数据字典，打印每个字段
        for key, value in result.response_metadata.items():
            print(f"  {key}: {value}")

    # usage_metadata 包含了 Token 使用量信息
    print(f"\nusage_metadata（Token 使用量）:")
    if hasattr(result, "usage_metadata"):
        # 检查 usage_metadata 是否为 None
        if result.usage_metadata is not None:
            print(f"  输入 Token 数: {result.usage_metadata.get('input_tokens', 'N/A')}")
            print(f"  输出 Token 数: {result.usage_metadata.get('output_tokens', 'N/A')}")
            print(f"  总 Token 数: {result.usage_metadata.get('total_tokens', 'N/A')}")
        else:
            print("  (无 Token 使用量信息)")

    print()


def demo_model_parameters():
    """
    演示 ChatOpenAI 的核心参数。

    功能：通过实际调用展示 temperature 和 max_tokens 参数的效果。
    输入参数：无。
    输出返回值：无（直接打印结果到控制台）。
    """
    # 打印分隔线和标题
    print("=" * 60)
    print("演示 5：核心参数详解（temperature & max_tokens）")
    print("=" * 60)

    # ---- temperature 参数演示 ----
    print("\n--- temperature（温度参数） ---")
    print("温度控制输出的随机性和创造力：")
    print("  - 0.0: 每次回答几乎一样（确定性输出，适合事实性问答）")
    print("  - 0.7: 适中的随机性（默认值，适合大多数场景）")
    print("  - 1.0: 高随机性（适合创意写作）")

    # 定义要测试的问题
    question = "请用一句话描述太阳。"

    # 定义要测试的温度值列表
    temperatures = [0.0, 0.7, 1.0]

    # 遍历不同温度值进行对比
    for temp in temperatures:
        # 创建不同温度的模型实例
        model = create_model(provider="deepseek", temperature=temp)
        # 调用模型
        result = model.invoke(question)
        # 打印结果
        print(f"  temperature={temp}: {result.content}")

    # ---- max_tokens 参数演示 ----
    print("\n--- max_tokens（最大输出长度） ---")
    print("限制模型生成的最大 Token 数（约等于字数的 1.5 倍）")

    # 创建限制了最大输出长度的模型实例
    model_short = create_model(
        provider="deepseek",
        max_tokens=50,  # 限制最多生成 50 个 Token
    )
    # 调用模型
    result = model_short.invoke("请详细介绍一下 Python 编程语言的历史。")
    # 打印结果
    print(f"  max_tokens=50 的输出: {result.content}")
    print("  （注意：输出可能被截断）")

    print()


# ============================================================
# 主程序入口
# ============================================================
if __name__ == "__main__":
    # 打印课程标题
    print()
    print("*" * 60)
    print("*  Day 1 - 课程 2：用 LangChain 调用多个大模型")
    print("*" * 60)
    print()

    # 检查是否有可用的模型提供商
    providers = list_available_providers()

    # 如果没有可用的提供商，提示用户配置 API Key
    if not providers:
        print("[警告] 没有找到任何可用的模型提供商！")
        print("请确保已在 .env 文件中配置了至少一个模型的 API Key。")
        print("参考 .env.example 文件了解配置格式。")
    else:
        # 打印可用的提供商列表
        print(f"检测到 {len(providers)} 个可用的模型提供商: {providers}")
        print("\n开始运行演示...\n")

        # 演示 1：基础调用
        demo_basic_call()

        # 演示 2：模型切换
        demo_switch_model()

        # 演示 3：三种消息类型
        demo_message_types()

        # 演示 4：返回值结构
        demo_invoke_result()

        # 演示 5：核心参数
        demo_model_parameters()

        # 打印课程总结
        print("=" * 60)
        print("课程 2 总结")
        print("=" * 60)
        print("你已经学会了：")
        print("  1. 用 LangChain 的 ChatOpenAI 调用大模型")
        print("  2. 通过工厂函数一键切换不同模型")
        print("  3. 三种消息类型：SystemMessage、HumanMessage、AIMessage")
        print("  4. model.invoke() 的返回值结构（AIMessage 对象）")
        print("  5. temperature 和 max_tokens 的作用")
        print()
        print("对比课程 1，LangChain 帮你封装了底层的：")
        print("  - HTTP 请求的构建和发送")
        print("  - JSON 响应的解析")
        print("  - 错误处理和重试机制")
        print("  - 消息格式的标准化")
        print()
        print("下一课，我们将让多个模型回答同一个问题，对比它们的效果！")
        print("=" * 60)
