"""
Day 2 - 课程 3：LCEL 链式调用（LangChain Expression Language）。

==========================================================
什么是 LCEL？
==========================================================

LCEL（LangChain Expression Language）是 LangChain 的核心设计模式。
它使用 Python 的 | （管道）运算符把多个组件串联成一条处理链。

    基本思想（管道模式 / Pipe Pattern）：
    数据像水一样，从管道的一端流入，经过层层处理，从另一端流出。

    类比 Linux 命令行：
        cat file.txt | grep "hello" | wc -l
        读取文件     → 过滤行      → 统计行数

    在 LangChain 中：
        prompt | model | parser
        构造提示词  → LLM 生成  → 解析输出

为什么要用链（Chain）？

    1. 可组合性：像乐高积木一样，自由拼装组件
    2. 可读性：一行代码就能看懂整个处理流程
    3. 统一接口：所有组件都实现 Runnable 接口
       - .invoke()：同步调用（处理单个输入）
       - .batch()：批量调用（处理多个输入）
       - .stream()：流式调用（逐步返回结果）
    4. 可追踪：LangSmith 自动记录每个步骤的输入输出

底层原理：
    | 运算符本质是 Python 的 __or__ 方法重载。
    A | B 等价于 A.__or__(B)
    最终效果等价于：result = C(B(A(input)))
    即：先执行 A，A 的输出作为 B 的输入，B 的输出作为 C 的输入。

==========================================================
本课程涵盖内容：
    1. 最基础的链：prompt | model
    2. 完整链：prompt | model | parser
    3. RunnablePassthrough（透传数据）
    4. RunnableLambda（自定义处理步骤）
    5. 多步骤链的组合
    6. invoke() vs batch() 的区别
==========================================================
"""

# ============================================================
# 导入区域
# ============================================================
import sys  # 系统模块，用于修改模块搜索路径
import os  # 操作系统模块，用于路径操作
import time  # 时间模块，用于计时

# 将项目根目录添加到模块搜索路径
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), '..')
)

# 从 LangChain 导入提示词模板
from langchain_core.prompts import ChatPromptTemplate  # 聊天模板

# 从 LangChain 导入输出解析器
from langchain_core.output_parsers import StrOutputParser  # 字符串解析器

# 从 LangChain 导入 Runnable 组件
from langchain_core.runnables import RunnablePassthrough  # 透传组件
from langchain_core.runnables import RunnableLambda  # Lambda 自定义组件

# 从公共模块导入模型工厂和配置
from common.model_factory import create_model  # 模型创建工厂函数
from common.config import list_available_providers  # 列出可用提供商


def demo_01_basic_chain(model):
    """
    演示最基础的链：prompt | model。

    功能：展示如何将提示词模板和模型串联成一条链。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🔗 示例 1：最基础的链（prompt | model）")
    print("=" * 60)

    # ---- 第 1 步：创建提示词模板 ----
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个知识渊博的百科助手，回答简洁明了。"
        ),
        (
            "human",
            "请用不超过50字解释什么是{concept}"
        ),
    ])

    # ---- 第 2 步：用 | 运算符构建链 ----
    # prompt | model 表示：先用 prompt 格式化，再传给 model
    chain = prompt | model

    # ---- 第 3 步：调用链 ----
    # invoke() 方法接受一个字典作为输入
    result = chain.invoke({"concept": "人工智能"})

    # 注意：没有 parser，返回的是 AIMessage 对象
    print(f"\n返回类型: {type(result)}")
    print(f"返回内容: {result.content}")

    # ---- 对比：不用链的写法 ----
    print("\n--- 对比：不用链的等价写法 ---")
    # 手动分步调用（等价于上面的链）
    messages = prompt.format_messages(concept="人工智能")  # 格式化
    result_manual = model.invoke(messages)  # 调用模型
    print(f"手动调用结果: {result_manual.content}")
    print("（两种方式效果完全一样，链的写法更简洁）")


def demo_02_full_chain(model):
    """
    演示完整链：prompt | model | parser。

    功能：展示包含模板、模型和解析器的完整链。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🔗 示例 2：完整链（prompt | model | parser）")
    print("=" * 60)

    # 创建提示词模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个编程教练，善于用类比讲解。"),
        ("human", "用生活中的类比解释{concept}，不超过80字"),
    ])

    # 创建字符串解析器
    parser = StrOutputParser()

    # 构建完整链：模板 → 模型 → 解析器
    chain = prompt | model | parser

    # 调用链
    result = chain.invoke({"concept": "递归"})

    # 使用了 parser，返回的直接是纯文本字符串
    print(f"\n返回类型: {type(result)}")
    print(f"返回内容: {result}")

    # 再试一个例子
    result_2 = chain.invoke({"concept": "多线程"})
    print(f"\n第二个例子: {result_2}")


def demo_03_runnable_passthrough(model):
    """
    演示 RunnablePassthrough（透传组件）。

    功能：展示如何使用 RunnablePassthrough 传递和组合数据。
          RunnablePassthrough 会将输入原封不动地传递到下一步。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("➡️ 示例 3：RunnablePassthrough（透传组件）")
    print("=" * 60)

    # ---- 基本用法：透传输入 ----
    # RunnablePassthrough 会将输入原封不动地传递
    passthrough = RunnablePassthrough()
    # 演示透传效果
    result = passthrough.invoke("你好，世界")
    print(f"\n透传结果: {result}")

    # ---- 实际用法：与 assign 结合使用 ----
    # RunnablePassthrough.assign() 可以在保留原始输入的同时，
    # 添加新的计算字段
    print("\n--- assign() 的用法 ---")

    # 定义一个处理函数：计算文本长度
    def get_text_length(inputs):
        """
        计算文本长度。

        功能：接收包含 text 字段的字典，返回文本长度。
        输入参数：
            inputs (dict): 包含 "text" 键的字典。
        输出返回值：
            int: 文本的字符数。
        """
        # 获取文本内容并计算长度
        return len(inputs["text"])

    # 使用 assign 在透传基础上添加新字段
    chain_with_assign = RunnablePassthrough.assign(
        text_length=RunnableLambda(get_text_length)
    )

    # 调用链
    result = chain_with_assign.invoke(
        {"text": "LangChain 是一个强大的框架"}
    )
    # 结果中既有原始的 text，也有新增的 text_length
    print("输入: {'text': 'LangChain 是一个强大的框架'}")
    print(f"输出: {result}")

    # ---- 在链中使用 Passthrough ----
    print("\n--- 在完整链中使用 ---")

    # 创建提示词模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个文本分析助手。"),
        (
            "human",
            "以下文本共 {text_length} 个字符：\n"
            "{text}\n"
            "请用一句话概括这段文本。"
        ),
    ])
    # 创建解析器
    parser = StrOutputParser()

    # 构建链：先透传并添加长度 → 再格式化 → 模型 → 解析
    full_chain = chain_with_assign | prompt | model | parser

    # 调用链
    summary = full_chain.invoke(
        {"text": "Python 是一种广泛使用的高级编程语言，"
         "以其简洁的语法和丰富的库生态系统而闻名。"}
    )
    print(f"概括结果: {summary}")


def demo_04_runnable_lambda(model):
    """
    演示 RunnableLambda（自定义处理步骤）。

    功能：展示如何用 RunnableLambda 将普通 Python 函数
          包装成链中的一个处理步骤。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("⚙️ 示例 4：RunnableLambda（自定义处理步骤）")
    print("=" * 60)

    # ---- 定义自定义处理函数 ----
    def preprocess_text(text):
        """
        文本预处理函数。

        功能：对输入文本进行清理和标准化。
        输入参数：
            text (str): 待处理的原始文本。
        输出返回值：
            str: 处理后的干净文本。
        """
        # 去除首尾空白
        cleaned = text.strip()
        # 将多个空格替换为单个空格
        cleaned = " ".join(cleaned.split())
        # 返回处理后的文本
        return cleaned

    def add_emoji(text):
        """
        为文本添加表情符号。

        功能：在文本前后添加装饰性表情符号。
        输入参数：
            text (str): 原始文本。
        输出返回值：
            str: 添加了表情符号的文本。
        """
        # 在前后添加星号表情
        return f"✨ {text} ✨"

    def to_uppercase_first(text):
        """
        将文本的首字符大写。

        功能：对英文文本的首字符进行大写处理。
        输入参数：
            text (str): 原始文本。
        输出返回值：
            str: 首字符大写后的文本。
        """
        # 检查文本是否为空
        if not text:
            return text
        # 首字符大写
        return text[0].upper() + text[1:]

    # ---- 将函数包装为 RunnableLambda ----
    preprocess = RunnableLambda(preprocess_text)
    add_emoji_step = RunnableLambda(add_emoji)
    uppercase_step = RunnableLambda(to_uppercase_first)

    # ---- 构建纯函数链 ----
    # 多个 RunnableLambda 也可以用 | 串联
    text_pipeline = preprocess | uppercase_step | add_emoji_step

    # 测试纯函数链
    test_text = "  hello   world   "
    result = text_pipeline.invoke(test_text)
    print(f"\n输入: '{test_text}'")
    print(f"输出: '{result}'")

    # ---- 结合 LLM 使用 ----
    print("\n--- 结合 LLM 使用 ---")

    def format_question(topic):
        """
        格式化问题。

        功能：将主题词包装成完整的问题字典。
        输入参数：
            topic (str): 问题主题。
        输出返回值：
            dict: 包含 topic 键的字典。
        """
        # 将主题封装为字典，供提示词模板使用
        return {"topic": topic.strip()}

    # 创建提示词模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个趣味科普作者。"),
        ("human", "用一个有趣的比喻解释{topic}，不超过50字"),
    ])
    # 创建解析器
    parser = StrOutputParser()

    # 构建完整链：预处理 → 格式化 → 模板 → 模型 → 解析 → 添加表情
    full_chain = (
        RunnableLambda(preprocess_text)
        | RunnableLambda(format_question)
        | prompt
        | model
        | parser
        | RunnableLambda(add_emoji)
    )

    # 调用链
    result = full_chain.invoke("  量子纠缠  ")
    print("输入: '  量子纠缠  '")
    print(f"输出: {result}")


def demo_05_multi_step_chain(model):
    """
    演示多步骤链的组合（翻译 → 摘要 → 格式化）。

    功能：展示如何将多个 LLM 调用串联成一条多步骤链，
          每一步的输出作为下一步的输入。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🔄 示例 5：多步骤链（翻译 → 摘要 → 格式化）")
    print("=" * 60)

    # 创建字符串解析器（每一步都需要）
    parser = StrOutputParser()

    # ---- 第 1 步：翻译链 ----
    translate_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业翻译。"),
        ("human", "将以下中文翻译成英文：\n{text}"),
    ])
    # 翻译链：模板 → 模型 → 解析器
    translate_chain = translate_prompt | model | parser

    # ---- 第 2 步：摘要链 ----
    summary_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个摘要专家。"),
        (
            "human",
            "用一句中文概括以下英文文本的核心意思：\n{text}"
        ),
    ])
    # 摘要链：模板 → 模型 → 解析器
    summary_chain = summary_prompt | model | parser

    # ---- 第 3 步：格式化链 ----
    format_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个文案编辑。"),
        (
            "human",
            "请将以下内容格式化为社交媒体帖子风格，"
            "添加合适的表情符号和标签：\n{text}"
        ),
    ])
    # 格式化链：模板 → 模型 → 解析器
    format_chain = format_prompt | model | parser

    # ---- 组合多步骤链 ----
    # 注意：每一步的输出是字符串，但下一步需要 dict
    # 所以我们用 RunnableLambda 进行转换
    def wrap_text(text):
        """
        将字符串包装为字典。

        功能：将纯文本封装成字典格式，供下一个链使用。
        输入参数：
            text (str): 待包装的文本字符串。
        输出返回值：
            dict: 包含 text 键的字典。
        """
        return {"text": text}

    # 构建完整的多步骤链
    full_chain = (
        translate_chain  # 第 1 步：翻译（中→英）
        | RunnableLambda(wrap_text)  # 包装为字典
        | summary_chain  # 第 2 步：摘要
        | RunnableLambda(wrap_text)  # 包装为字典
        | format_chain  # 第 3 步：格式化
    )

    # 准备输入文本
    input_text = "人工智能正在深刻改变人类社会的方方面面"

    # 分步执行，展示每一步的结果
    print(f"\n📥 原始输入: {input_text}")

    # 执行第 1 步：翻译
    step1_result = translate_chain.invoke({"text": input_text})
    print(f"\n🔤 第 1 步（翻译）: {step1_result}")

    # 执行第 2 步：摘要
    step2_result = summary_chain.invoke({"text": step1_result})
    print(f"📝 第 2 步（摘要）: {step2_result}")

    # 执行第 3 步：格式化
    step3_result = format_chain.invoke({"text": step2_result})
    print(f"🎨 第 3 步（格式化）: {step3_result}")

    # 使用完整链一步到位
    print("\n--- 使用完整链一步到位 ---")
    final_result = full_chain.invoke({"text": input_text})
    print(f"🎯 最终结果: {final_result}")


def demo_06_invoke_vs_batch(model):
    """
    演示 invoke() vs batch() 的区别。

    功能：展示单次调用和批量调用的不同使用方式和性能差异。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("📦 示例 6：invoke() vs batch()")
    print("=" * 60)

    # 创建一个简单的链
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个翻译助手，只输出翻译结果。"),
        ("human", "将以下词语翻译成英文：{word}"),
    ])
    # 创建解析器
    parser = StrOutputParser()
    # 构建链
    chain = prompt | model | parser

    # ---- invoke()：单次调用 ----
    print("\n--- invoke()：处理单个输入 ---")
    # 记录开始时间
    start_time = time.time()
    # 逐个调用
    result_1 = chain.invoke({"word": "人工智能"})
    result_2 = chain.invoke({"word": "机器学习"})
    result_3 = chain.invoke({"word": "深度学习"})
    # 计算耗时
    invoke_time = time.time() - start_time

    # 打印结果
    print(f"  人工智能 → {result_1}")
    print(f"  机器学习 → {result_2}")
    print(f"  深度学习 → {result_3}")
    print(f"  总耗时: {invoke_time:.2f} 秒")

    # ---- batch()：批量调用 ----
    print("\n--- batch()：批量处理多个输入 ---")
    # 准备批量输入（列表中的每个元素是一个字典）
    batch_inputs = [
        {"word": "人工智能"},
        {"word": "机器学习"},
        {"word": "深度学习"},
    ]

    # 记录开始时间
    start_time = time.time()
    # batch() 接受一个列表，返回一个结果列表
    batch_results = chain.batch(batch_inputs)
    # 计算耗时
    batch_time = time.time() - start_time

    # 打印结果
    for i, result in enumerate(batch_results):
        # 获取对应的输入词
        word = batch_inputs[i]["word"]
        print(f"  {word} → {result}")
    print(f"  总耗时: {batch_time:.2f} 秒")

    # ---- 对比总结 ----
    print("\n--- 对比总结 ---")
    print(f"  invoke() 逐个调用: {invoke_time:.2f} 秒")
    print(f"  batch() 批量调用:  {batch_time:.2f} 秒")
    # 判断批量是否更快
    if batch_time < invoke_time:
        # 批量更快
        speedup = invoke_time / batch_time
        print(f"  batch() 快了约 {speedup:.1f} 倍！")
    else:
        # 可能因为网络等原因差异不大
        print("  （耗时相近，batch 的优势在并发场景更明显）")

    # 说明
    print("\n💡 说明：")
    print("  invoke()：适合处理单个输入")
    print("  batch()：适合处理多个输入，可能并行执行")
    print("  stream()：适合实时展示（下一课详解）")


def demo_07_chain_principle():
    """
    原理讲解：| 运算符和链的本质。

    功能：通过代码演示，揭示 LCEL 链的底层原理。
    输入参数：无。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🔬 原理讲解：| 运算符和链的本质")
    print("=" * 60)

    # ---- Python 的 __or__ 方法 ----
    print("\n--- Python 的 __or__ 方法重载 ---")
    print("在 Python 中，| 运算符可以被重载：")
    print("  a | b 等价于 a.__or__(b)")
    print("  这不是新发明，而是 Python 的标准特性")
    print()
    print("LangChain 的 Runnable 基类重载了 __or__：")
    print("  class Runnable:")
    print("      def __or__(self, other):")
    print("          return RunnableSequence(self, other)")

    # ---- 链的执行流程 ----
    print("\n--- 链的执行流程 ---")
    print("prompt | model | parser 的执行过程：")
    print()
    print("  输入: {'concept': '递归'}")
    print("    ↓")
    print("  prompt.invoke({'concept': '递归'})")
    print("    → [SystemMessage(...), HumanMessage(...)]")
    print("    ↓")
    print("  model.invoke([SystemMessage, HumanMessage])")
    print("    → AIMessage(content='递归是...')")
    print("    ↓")
    print("  parser.invoke(AIMessage(...))")
    print("    → '递归是...'")
    print("    ↓")
    print("  输出: '递归是...'")

    # ---- 等价的手动写法 ----
    print("\n--- 等价的手动写法 ---")
    print("chain = prompt | model | parser")
    print("chain.invoke(input)")
    print()
    print("等价于：")
    print("step1 = prompt.invoke(input)")
    print("step2 = model.invoke(step1)")
    print("step3 = parser.invoke(step2)")
    print()
    print("也等价于：")
    print("parser(model(prompt(input)))")

    # ---- Runnable 统一接口 ----
    print("\n--- Runnable 统一接口 ---")
    print("所有链组件都实现了 Runnable 接口：")
    print("  .invoke(input)  → 同步执行，返回单个结果")
    print("  .batch(inputs)  → 批量执行，返回结果列表")
    print("  .stream(input)  → 流式执行，逐步返回结果")
    print("  .ainvoke(input) → 异步执行")
    print("  .astream(input) → 异步流式执行")


def main():
    """
    主函数：按顺序运行所有演示示例。

    功能：初始化模型并依次执行各个演示函数。
    输入参数：无。
    输出返回值：无。
    """
    # 打印课程标题
    print("=" * 60)
    print("📚 Day 2 - 课程 3：LCEL 链式调用")
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
    demo_01_basic_chain(model)  # 示例 1
    demo_02_full_chain(model)  # 示例 2
    demo_03_runnable_passthrough(model)  # 示例 3
    demo_04_runnable_lambda(model)  # 示例 4
    demo_05_multi_step_chain(model)  # 示例 5
    demo_06_invoke_vs_batch(model)  # 示例 6
    demo_07_chain_principle()  # 原理讲解

    # 打印课程结束信息
    print("\n" + "=" * 60)
    print("✅ 课程 3 完成！")
    print("=" * 60)
    print("\n💡 核心要点回顾：")
    print("  1. prompt | model | parser 是最常用的链")
    print("  2. RunnablePassthrough 透传数据")
    print("  3. RunnableLambda 自定义处理步骤")
    print("  4. 多步骤链可以串联多个 LLM 调用")
    print("  5. invoke() 单次调用，batch() 批量调用")
    print("  6. | 运算符 = __or__ 方法重载")


# 当直接运行此文件时执行主函数
if __name__ == '__main__':
    main()
