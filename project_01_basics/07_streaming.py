"""
Day 2 - 课程 4：流式输出（Streaming）。

==========================================================
什么是流式输出？
==========================================================

普通调用模式（非流式）：
    用户发送问题 → 等待...... → 一次性收到完整回复
    体验就像：发一条微信，等对方打完整段话再发过来。

流式输出模式：
    用户发送问题 → 立即开始逐字/逐词收到回复
    体验就像：看对方在微信里「正在输入...」，字一个个蹦出来。

为什么需要流式输出？
    1. 用户体验：不用干等，立即看到 LLM 在"思考"
    2. 首字延迟（Time to First Token, TTFT）：
       - 非流式：可能等 3-5 秒才看到内容
       - 流式：通常 0.5 秒内就看到第一个字
    3. 感知速度：同样的总生成时间，流式感觉快得多

SSE（Server-Sent Events）原理：
    流式输出在 Web 应用中通常基于 SSE 协议实现。
    SSE 是 HTTP 的一种扩展，允许服务器持续向客户端推送数据。

    工作流程：
    1. 客户端发送请求
    2. 服务器保持连接不断开
    3. 服务器每生成一小段文本，就立即推送给客户端
    4. 客户端收到后立即显示
    5. 全部生成完毕后关闭连接

    在 LangChain 中：
    - model.stream() 返回一个迭代器（iterator）
    - 每次迭代返回一个 chunk（数据块）
    - chunk 包含一小段新生成的文本

==========================================================
本课程涵盖内容：
    1. model.stream() 基本用法
    2. 逐 chunk 打印（打字效果）
    3. 在 chain 中使用流式输出
    4. astream（异步流式）
    5. 流式 vs 非流式对比
    6. stream_print() 工具函数封装
==========================================================
"""

# ============================================================
# 导入区域
# ============================================================
import sys  # 系统模块，用于修改模块搜索路径和刷新输出
import os  # 操作系统模块，用于路径操作
import time  # 时间模块，用于计时对比
import asyncio  # 异步编程模块，用于 astream 演示

# 将项目根目录添加到模块搜索路径
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), '..')
)

# 从 LangChain 导入提示词模板
from langchain_core.prompts import ChatPromptTemplate  # 聊天模板

# 从 LangChain 导入输出解析器
from langchain_core.output_parsers import StrOutputParser  # 字符串解析器

# 从公共模块导入模型工厂和配置
from common.model_factory import create_model  # 模型创建工厂函数
from common.config import list_available_providers  # 列出可用提供商


# ============================================================
# 工具函数（供后续复用）
# ============================================================
def stream_print(stream_response, end_marker="\n"):
    """
    流式打印工具函数（可复用）。

    功能：接收一个流式响应迭代器，逐块打印内容，
          模拟打字机效果。同时收集完整文本并返回。
    输入参数：
        stream_response: 流式响应的迭代器对象，
                         来自 model.stream() 或 chain.stream()。
        end_marker (str): 打印结束后的尾部标记，
                          默认为换行符。
    输出返回值：
        str: 收集到的完整文本内容。
    """
    # 初始化完整文本收集器
    full_text = ""
    # 遍历流式响应的每一个块（chunk）
    for chunk in stream_response:
        # 判断 chunk 的类型
        # 如果是字符串（来自带 StrOutputParser 的 chain）
        if isinstance(chunk, str):
            # 直接使用字符串内容
            content = chunk
        else:
            # 如果是 AIMessageChunk 对象（来自 model.stream()）
            content = chunk.content
        # 实时打印内容，不换行，立即刷新缓冲区
        print(content, end="", flush=True)
        # 将内容累加到完整文本中
        full_text += content
    # 所有块打印完毕后，打印尾部标记
    print(end_marker)
    # 返回收集到的完整文本
    return full_text


def demo_01_basic_stream(model):
    """
    演示 model.stream() 的基本用法。

    功能：展示如何使用模型的 stream() 方法获取流式响应。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🌊 示例 1：model.stream() 基本用法")
    print("=" * 60)

    # ---- 使用 stream() 获取流式响应 ----
    print("\n🤖 流式输出（注意观察逐字显示效果）:")
    # model.stream() 返回一个迭代器
    # 每次迭代得到一个 AIMessageChunk 对象
    stream_response = model.stream(
        "请用100字左右介绍一下 Python 编程语言的特点"
    )

    # 使用工具函数打印流式输出
    full_text = stream_print(stream_response)

    # 打印分隔线
    print(f"\n完整文本长度: {len(full_text)} 个字符")


def demo_02_chunk_details(model):
    """
    演示逐 chunk 打印并查看 chunk 的详细信息。

    功能：展示每个 chunk 的结构和内容，
          帮助理解流式输出的底层数据格式。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🔍 示例 2：查看 chunk 的详细信息")
    print("=" * 60)

    # 获取流式响应
    stream_response = model.stream("用一句话介绍人工智能")

    # 打印前几个 chunk 的详细信息
    print("\n每个 chunk 的详细信息（仅展示前 5 个）:")
    # 初始化计数器
    chunk_count = 0
    # 初始化完整文本收集器
    full_text = ""

    # 遍历所有 chunk
    for chunk in stream_response:
        # 累加完整文本
        full_text += chunk.content
        # 只展示前 5 个 chunk 的详细信息
        if chunk_count < 5:
            print(f"\n  chunk[{chunk_count}]:")
            # 打印 chunk 的类型
            print(f"    类型: {type(chunk).__name__}")
            # 打印 chunk 的内容（用 repr 显示特殊字符）
            print(f"    内容: {repr(chunk.content)}")
        # 计数器加 1
        chunk_count += 1

    # 打印统计信息
    print(f"\n\n总共收到 {chunk_count} 个 chunk")
    print(f"完整文本: {full_text}")

    # 原理说明
    print("\n💡 原理说明：")
    print("  每个 chunk 是一个 AIMessageChunk 对象")
    print("  chunk.content 包含一小段新生成的文本")
    print("  所有 chunk.content 拼接起来就是完整回复")


def demo_03_chain_stream(model):
    """
    演示在 chain 中使用流式输出。

    功能：展示如何在 LCEL 链中使用 stream() 方法。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("⛓️ 示例 3：在 chain 中使用流式输出")
    print("=" * 60)

    # ---- 构建链 ----
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个{role}，善于深入浅出地讲解。"
        ),
        (
            "human",
            "请用通俗的语言解释{topic}，不超过150字。"
        ),
    ])
    # 创建解析器
    parser = StrOutputParser()
    # 构建完整链
    chain = prompt | model | parser

    # ---- 使用 chain.stream() ----
    print("\n🤖 链的流式输出:")
    # chain.stream() 也返回迭代器
    # 因为加了 StrOutputParser，每个 chunk 是字符串
    stream_response = chain.stream({
        "role": "计算机科学教授",
        "topic": "什么是哈希表（Hash Table）"
    })

    # 使用工具函数打印
    full_text = stream_print(stream_response)
    print(f"\n完整文本长度: {len(full_text)} 个字符")


def demo_04_async_stream(model):
    """
    演示 astream（异步流式输出）。

    功能：展示如何使用 async/await 语法进行异步流式调用。
          异步编程适合 Web 应用等需要高并发的场景。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("⚡ 示例 4：astream（异步流式输出）")
    print("=" * 60)

    # ---- 异步基础概念说明 ----
    print("\n📖 async/await 简介：")
    print("  同步（sync）：一件事做完才能做下一件")
    print("  异步（async）：等待时可以去做其他事情")
    print("  async def：定义异步函数")
    print("  await：等待异步操作完成")
    print("  async for：异步遍历迭代器")

    # ---- 定义异步流式调用函数 ----
    async def async_stream_demo():
        """
        异步流式输出演示函数。

        功能：使用 model.astream() 进行异步流式调用。
        输入参数：无。
        输出返回值：
            str: 收集到的完整文本内容。
        """
        # 初始化完整文本收集器
        full_text = ""
        print("\n🤖 异步流式输出:")
        # 使用 async for 遍历异步流式响应
        async for chunk in model.astream(
            "用50字介绍 Python 的 asyncio 模块"
        ):
            # 获取 chunk 的内容
            content = chunk.content
            # 实时打印，不换行
            print(content, end="", flush=True)
            # 累加到完整文本
            full_text += content
        # 打印换行符
        print()
        # 返回完整文本
        return full_text

    # ---- 运行异步函数 ----
    # asyncio.run() 是运行异步函数的入口
    result = asyncio.run(async_stream_demo())
    print(f"\n完整文本长度: {len(result)} 个字符")

    # 补充说明
    print("\n💡 何时使用异步流式？")
    print("  1. Web 框架（FastAPI、Django 等）")
    print("  2. 需要同时处理多个流式请求")
    print("  3. I/O 密集型应用")


def demo_05_stream_vs_invoke(model):
    """
    对比流式 vs 非流式的用户体验差异。

    功能：通过计时对比，展示流式和非流式调用的
          首字延迟（TTFT）和总时间差异。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("⚖️ 示例 5：流式 vs 非流式对比")
    print("=" * 60)

    # 定义测试问题
    test_question = "请介绍一下 Python 的三大特点，每个特点用一句话说明"

    # ---- 非流式调用 ----
    print("\n--- 非流式调用（invoke）---")
    # 记录开始时间
    start_time = time.time()
    # 使用 invoke 同步调用
    response = model.invoke(test_question)
    # 记录结束时间
    end_time = time.time()
    # 计算总耗时
    invoke_total = end_time - start_time
    # 打印结果（一次性显示）
    print(f"🤖 回复: {response.content}")
    print(f"⏱️ 总耗时: {invoke_total:.2f} 秒")
    print("（用户在这段时间内什么都看不到，只能干等）")

    # ---- 流式调用 ----
    print("\n--- 流式调用（stream）---")
    # 记录开始时间
    start_time = time.time()
    # 初始化首字时间记录
    first_token_time = None
    # 初始化完整文本
    full_text = ""

    print("🤖 回复: ", end="")
    # 使用 stream 流式调用
    for chunk in model.stream(test_question):
        # 记录首字到达时间
        if first_token_time is None:
            first_token_time = time.time()
        # 获取内容
        content = chunk.content
        # 实时打印
        print(content, end="", flush=True)
        # 累加文本
        full_text += content
    # 打印换行
    print()

    # 记录结束时间
    end_time = time.time()
    # 计算各项耗时
    stream_total = end_time - start_time
    ttft = first_token_time - start_time

    # 打印时间统计
    print(f"⏱️ 首字延迟（TTFT）: {ttft:.2f} 秒")
    print(f"⏱️ 总耗时: {stream_total:.2f} 秒")
    print("（用户在首字延迟后就能看到内容，体验更好）")

    # ---- 对比总结 ----
    print("\n--- 对比总结 ---")
    print(f"  非流式总耗时:   {invoke_total:.2f} 秒")
    print(f"  流式首字延迟:   {ttft:.2f} 秒")
    print(f"  流式总耗时:     {stream_total:.2f} 秒")
    print()
    print("  📌 关键发现：")
    print("  - 总耗时差不多（LLM 生成速度相同）")
    print("  - 流式的首字延迟远小于非流式的等待时间")
    print("  - 流式输出让用户「感觉」更快")


def demo_06_stream_print_usage(model):
    """
    演示 stream_print() 工具函数的使用。

    功能：展示封装好的 stream_print() 函数的各种用法，
          以及如何在后续课程中复用。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🛠️ 示例 6：stream_print() 工具函数")
    print("=" * 60)

    # 打印函数说明
    print("\nstream_print() 函数已在文件顶部定义，可供复用。")
    print("使用方式非常简单：")

    # ---- 用法 1：直接用于 model.stream() ----
    print("\n--- 用法 1：model.stream() ---")
    print("🤖 ", end="")
    # 调用 stream_print 并获取完整文本
    text_1 = stream_print(
        model.stream("用一句话解释什么是闭包（closure）")
    )

    # ---- 用法 2：用于 chain.stream() ----
    print("\n--- 用法 2：chain.stream() ---")
    # 构建链
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个编程导师。"),
        ("human", "用一个类比解释{concept}"),
    ])
    # 创建解析器
    parser = StrOutputParser()
    # 构建完整链
    chain = prompt | model | parser

    print("🤖 ", end="")
    # 对链使用 stream_print
    text_2 = stream_print(
        chain.stream({"concept": "回调函数"})
    )

    # ---- 用法 3：收集完整文本做后续处理 ----
    print("\n--- 用法 3：收集文本做后续处理 ---")
    print("🤖 ", end="")
    full_text = stream_print(
        model.stream("列出 Python 的 3 个优点，每个一行")
    )
    # 对收集到的文本做后续处理
    line_count = full_text.count("\n") + 1
    char_count = len(full_text)
    print(f"\n📊 文本统计: {line_count} 行, {char_count} 字符")

    # 复用说明
    print("\n💡 复用方法：")
    print("  在其他文件中：")
    print("  from project_01_basics.07_streaming "
          "import stream_print")
    print("  或者将此函数移到 common/ 公共模块中")


def main():
    """
    主函数：按顺序运行所有演示示例。

    功能：初始化模型并依次执行各个演示函数。
    输入参数：无。
    输出返回值：无。
    """
    # 打印课程标题
    print("=" * 60)
    print("📚 Day 2 - 课程 4：流式输出（Streaming）")
    print("=" * 60)

    # 获取可用的模型提供商列表
    providers = list_available_providers()
    # 打印可用提供商
    print(f"\n可用的模型提供商: {providers}")

    # 检查是否有可用的提供商
    if not providers:
        # 没有配置任何 API Key
        print("❌ 错误：没有找到可用的模型提供商！")
        print("请在 .env 文件中配置至少一个 API Key。")
        return

    # 使用第一个可用的提供商创建模型
    provider = providers[0]
    print(f"使用模型提供商: {provider}")

    # 创建模型实例
    model = create_model(
        provider=provider,
        temperature=0.7  # 生成温度
    )
    print(f"模型创建成功: {model}")

    # 依次运行各个演示示例
    demo_01_basic_stream(model)  # 示例 1
    demo_02_chunk_details(model)  # 示例 2
    demo_03_chain_stream(model)  # 示例 3
    demo_04_async_stream(model)  # 示例 4
    demo_05_stream_vs_invoke(model)  # 示例 5
    demo_06_stream_print_usage(model)  # 示例 6

    # 打印课程结束信息
    print("\n" + "=" * 60)
    print("✅ 课程 4 完成！")
    print("=" * 60)
    print("\n💡 核心要点回顾：")
    print("  1. model.stream() 返回流式迭代器")
    print("  2. 每个 chunk 包含一小段新生成的文本")
    print("  3. chain.stream() 在链中也能流式输出")
    print("  4. astream() 用于异步场景")
    print("  5. 流式输出大幅降低首字延迟（TTFT）")
    print("  6. stream_print() 工具函数可直接复用")


# 当直接运行此文件时执行主函数
if __name__ == '__main__':
    main()
