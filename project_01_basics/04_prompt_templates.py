"""
Day 2 - 课程 1：Prompt Template（提示词模板）。

==========================================================
什么是 Prompt Template？
==========================================================

在与 LLM 对话时，我们经常需要构造各种提示词（Prompt）。
如果每次都手动拼接字符串，会遇到很多问题：

    1. 硬编码问题：
       - 手动拼接：f"请将{text}翻译成{language}"
       - 模板方式：PromptTemplate(template="请将{text}翻译成{language}")
       看起来差不多？但模板的优势在于：可以复用、可以序列化、可以组合！

    2. 消息角色管理：
       - LLM 需要区分 system（系统设定）、human（用户输入）、ai（助手回复）
       - ChatPromptTemplate 帮你管理这些角色消息

    3. 可组合性：
       - 模板可以和 Model、Parser 组成 Chain（链）
       - 这是 LangChain 的核心设计思想

本质原理：
    PromptTemplate 本质就是对 Python f-string 的封装。
    它把"字符串格式化"这件事变成了一个可复用、可组合的对象。
    template.format(name="张三") 等价于 f"你好，{name}"

==========================================================
本课程涵盖内容：
    1. PromptTemplate 基本用法
    2. ChatPromptTemplate 用法
    3. from_messages() 构建方式
    4. partial 变量（部分预填充）
    5. MessagesPlaceholder（对话历史占位符）
==========================================================
"""

# ============================================================
# 导入区域
# ============================================================
import sys  # 系统模块，用于修改模块搜索路径
import os  # 操作系统模块，用于路径操作

# 将项目根目录添加到模块搜索路径，以便导入 common 模块
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), '..')
)

# 从 LangChain 导入提示词模板相关的类
from langchain_core.prompts import PromptTemplate  # 基础字符串模板
from langchain_core.prompts import ChatPromptTemplate  # 聊天消息模板
from langchain_core.prompts import MessagesPlaceholder  # 消息占位符
from langchain_core.prompts import HumanMessagePromptTemplate  # 人类消息模板
from langchain_core.prompts import SystemMessagePromptTemplate  # 系统消息模板
from langchain_core.messages import HumanMessage  # 人类消息对象
from langchain_core.messages import AIMessage  # AI 消息对象
from datetime import datetime  # 日期时间模块，用于 partial 演示

# 从公共模块导入模型工厂和配置
from common.model_factory import create_model  # 模型创建工厂函数
from common.config import list_available_providers  # 列出可用提供商


def demo_01_basic_prompt_template(model):
    """
    演示 PromptTemplate 的基本用法。

    功能：展示如何创建字符串模板并填充变量。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("📝 示例 1：PromptTemplate 基本用法")
    print("=" * 60)

    # ---- 方式 1：使用 from_template 类方法创建 ----
    # 这是最常用的创建方式，自动从模板字符串中提取变量名
    prompt_1 = PromptTemplate.from_template(
        "请用简洁的语言解释什么是{concept}，"
        "并举一个{domain}领域的例子。"
    )
    # 打印模板信息，查看自动提取的变量
    print(f"\n模板变量: {prompt_1.input_variables}")

    # 使用 format() 方法填充变量，生成最终的提示词字符串
    formatted_1 = prompt_1.format(
        concept="递归",
        domain="计算机科学"
    )
    # 打印格式化后的提示词
    print(f"格式化结果:\n{formatted_1}")

    # 调用模型，传入格式化后的提示词
    print("\n🤖 模型回复:")
    response_1 = model.invoke(formatted_1)  # 调用模型
    print(response_1.content)  # 打印回复内容

    # ---- 方式 2：直接构造函数创建 ----
    # 显式指定模板字符串和变量名列表
    prompt_2 = PromptTemplate(
        template="将以下内容翻译成{language}：\n{text}",
        input_variables=["language", "text"]  # 显式声明变量
    )
    # 填充变量并打印
    formatted_2 = prompt_2.format(
        language="英语",
        text="人工智能正在改变世界"
    )
    # 打印格式化后的提示词
    print(f"\n翻译模板格式化结果:\n{formatted_2}")

    # 调用模型
    print("\n🤖 模型回复:")
    response_2 = model.invoke(formatted_2)  # 调用模型
    print(response_2.content)  # 打印回复内容


def demo_02_chat_prompt_template(model):
    """
    演示 ChatPromptTemplate 的用法。

    功能：展示如何使用聊天消息模板管理多角色对话。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("💬 示例 2：ChatPromptTemplate 用法")
    print("=" * 60)

    # ---- 使用元组列表快速创建 ----
    # 每个元组的格式：(角色, 消息内容)
    # 角色可以是 "system"、"human"、"ai"
    chat_prompt = ChatPromptTemplate.from_messages([
        (
            "system",  # 系统角色：设定 AI 的行为和身份
            "你是一位资深的{role}专家，"
            "擅长用通俗易懂的方式讲解专业知识。"
            "回答要简洁明了，不超过100字。"
        ),
        (
            "human",  # 人类角色：用户的提问
            "请解释一下{question}"
        ),
    ])

    # 打印模板的输入变量
    print(f"\n模板输入变量: {chat_prompt.input_variables}")

    # 填充变量，生成消息列表
    messages = chat_prompt.format_messages(
        role="Python 编程",
        question="什么是装饰器（decorator）"
    )

    # 遍历并打印每条消息的类型和内容
    print("\n生成的消息列表:")
    for msg in messages:
        # 获取消息类型名称（如 SystemMessage、HumanMessage）
        msg_type = type(msg).__name__
        print(f"  [{msg_type}] {msg.content}")

    # 调用模型
    print("\n🤖 模型回复:")
    response = model.invoke(messages)  # 传入消息列表
    print(response.content)  # 打印回复内容


def demo_03_from_messages(model):
    """
    演示 from_messages() 的多种构建方式。

    功能：展示使用消息模板对象构建聊天模板的方式。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🔨 示例 3：from_messages() 构建方式")
    print("=" * 60)

    # ---- 使用消息模板对象构建（更精细的控制） ----
    # 这种方式可以对每条消息进行更细致的配置
    chat_prompt = ChatPromptTemplate.from_messages([
        # 使用 SystemMessagePromptTemplate 创建系统消息
        SystemMessagePromptTemplate.from_template(
            "你是一个{style}风格的诗人，"
            "请用优美的语言回答问题。"
        ),
        # 使用 HumanMessagePromptTemplate 创建用户消息
        HumanMessagePromptTemplate.from_template(
            "请写一首关于{topic}的短诗（四行以内）"
        ),
    ])

    # 填充变量生成消息列表
    messages = chat_prompt.format_messages(
        style="唐诗",
        topic="秋天的月亮"
    )

    # 打印消息列表
    print("\n生成的消息:")
    for msg in messages:
        # 获取消息类型名称
        msg_type = type(msg).__name__
        print(f"  [{msg_type}] {msg.content}")

    # 调用模型
    print("\n🤖 模型回复:")
    response = model.invoke(messages)  # 传入消息列表
    print(response.content)  # 打印回复内容

    # ---- 混合使用元组和消息对象 ----
    print("\n--- 混合构建方式 ---")
    # 在 from_messages 中可以混合使用元组和消息对象
    mixed_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个友善的助手。"),  # 元组方式
        HumanMessagePromptTemplate.from_template(  # 模板对象方式
            "用一句话概括：{content}"
        ),
    ])
    # 格式化并调用模型
    mixed_messages = mixed_prompt.format_messages(
        content="机器学习是人工智能的一个分支"
    )
    # 调用模型获取回复
    response = model.invoke(mixed_messages)
    print(f"🤖 模型回复: {response.content}")


def demo_04_partial_variables(model):
    """
    演示 partial 变量（部分预填充）。

    功能：展示如何预先填充模板的部分变量，
          剩余变量在实际使用时再填充。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🧩 示例 4：partial 变量（部分预填充）")
    print("=" * 60)

    # ---- 方式 1：用字符串值进行 partial ----
    # 创建一个包含三个变量的模板
    full_prompt = PromptTemplate.from_template(
        "你是一个{language}专家。"
        "请用{style}的风格回答：{question}"
    )
    # 打印原始模板的变量
    print(f"\n原始模板变量: {full_prompt.input_variables}")

    # 使用 partial() 预填充部分变量
    # 这会返回一个新的模板，只需要填充剩余的变量
    partial_prompt = full_prompt.partial(
        language="Python",  # 预填充语言
        style="幽默"  # 预填充风格
    )
    # 打印 partial 后的变量（只剩 question）
    print(f"partial 后的变量: {partial_prompt.input_variables}")

    # 使用时只需要填充剩余变量
    formatted = partial_prompt.format(
        question="什么是列表推导式？"
    )
    # 打印格式化结果
    print(f"格式化结果: {formatted}")

    # 调用模型
    print("\n🤖 模型回复:")
    response = model.invoke(formatted)  # 调用模型
    print(response.content)  # 打印回复内容

    # ---- 方式 2：用函数进行 partial（动态值） ----
    print("\n--- 使用函数进行 partial ---")

    def get_current_time():
        """
        获取当前时间的格式化字符串。

        功能：返回当前日期和时间。
        输入参数：无。
        输出返回值：
            str: 格式化的时间字符串。
        """
        # 获取当前时间并格式化
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 创建带有时间变量的模板
    time_prompt = PromptTemplate(
        template=(
            "当前时间是 {current_time}。\n"
            "请回答用户的问题：{question}"
        ),
        input_variables=["question"],  # 需要用户填充的变量
        partial_variables={
            "current_time": get_current_time  # 用函数动态生成
        }
    )
    # 打印需要用户填充的变量
    print(f"需要填充的变量: {time_prompt.input_variables}")

    # 格式化时，current_time 会自动调用函数获取当前时间
    formatted_time = time_prompt.format(
        question="现在是上午还是下午？"
    )
    # 打印格式化结果
    print(f"格式化结果: {formatted_time}")

    # 调用模型
    print("\n🤖 模型回复:")
    response = model.invoke(formatted_time)  # 调用模型
    print(response.content)  # 打印回复内容


def demo_05_messages_placeholder(model):
    """
    演示 MessagesPlaceholder（消息占位符）。

    功能：展示如何在模板中预留位置，
          用于插入对话历史记录，为后续多轮对话做铺垫。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("📋 示例 5：MessagesPlaceholder（消息占位符）")
    print("=" * 60)

    # ---- 创建带有对话历史占位符的模板 ----
    # MessagesPlaceholder 用于在模板中预留一个位置
    # 运行时可以插入一组消息（比如对话历史）
    chat_prompt = ChatPromptTemplate.from_messages([
        (
            "system",  # 系统消息：设定 AI 身份
            "你是一个乐于助人的 AI 助手。"
            "请根据对话历史和用户的新问题进行回答。"
        ),
        # MessagesPlaceholder 会被替换为一组消息
        # variable_name 指定在调用时用什么变量名传入消息
        MessagesPlaceholder(
            variable_name="chat_history"  # 对话历史的变量名
        ),
        (
            "human",  # 用户的新消息
            "{question}"
        ),
    ])

    # 打印模板的输入变量
    print(f"\n模板输入变量: {chat_prompt.input_variables}")

    # ---- 模拟多轮对话 ----
    # 构造模拟的对话历史
    fake_history = [
        HumanMessage(content="我叫小明"),  # 第 1 轮用户消息
        AIMessage(content="你好小明！很高兴认识你。"),  # 第 1 轮 AI 回复
        HumanMessage(content="我喜欢编程"),  # 第 2 轮用户消息
        AIMessage(  # 第 2 轮 AI 回复
            content="编程是一项很棒的技能！你喜欢用什么语言？"
        ),
    ]

    # 填充模板：传入对话历史和新问题
    messages = chat_prompt.format_messages(
        chat_history=fake_history,  # 对话历史
        question="你还记得我叫什么名字吗？"  # 新问题
    )

    # 打印生成的完整消息列表
    print("\n完整的消息列表（包含历史）:")
    for i, msg in enumerate(messages):
        # 获取消息类型名称
        msg_type = type(msg).__name__
        # 截断过长的内容以便显示
        content = msg.content
        if len(content) > 50:
            content = content[:50] + "..."
        print(f"  [{i}] {msg_type}: {content}")

    # 调用模型
    print("\n🤖 模型回复:")
    response = model.invoke(messages)  # 传入完整消息列表
    print(response.content)  # 打印回复内容

    # ---- 可选的 MessagesPlaceholder ----
    print("\n--- 可选的 MessagesPlaceholder ---")
    # 设置 optional=True，当没有传入该变量时不会报错
    optional_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个助手。"),
        MessagesPlaceholder(
            variable_name="history",
            optional=True  # 设为可选，不传也不报错
        ),
        ("human", "{input}"),
    ])
    # 不传入 history 变量，直接使用
    messages_no_history = optional_prompt.format_messages(
        input="你好！"
    )
    # 调用模型
    response = model.invoke(messages_no_history)
    print(f"🤖 无历史时的回复: {response.content}")


def demo_06_template_principle():
    """
    原理讲解：模板的本质。

    功能：通过代码演示，揭示 PromptTemplate 的底层原理。
    输入参数：无。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🔬 原理讲解：模板的本质")
    print("=" * 60)

    # ---- 对比：手动 f-string vs PromptTemplate ----
    # 定义变量
    name = "张三"  # 用户名
    topic = "机器学习"  # 话题

    # 方式 1：传统 f-string
    result_fstring = f"你好 {name}，请解释一下 {topic}"
    print(f"\nf-string 结果: {result_fstring}")

    # 方式 2：PromptTemplate
    template = PromptTemplate.from_template(
        "你好 {name}，请解释一下 {topic}"
    )
    # format() 方法本质上就是调用 Python 的 str.format()
    result_template = template.format(
        name=name,
        topic=topic
    )
    print(f"模板结果:      {result_template}")

    # 验证两者结果完全一致
    is_same = (result_fstring == result_template)
    print(f"两者结果一致:  {is_same}")

    # ---- 模板的额外优势 ----
    print("\n--- 模板相比 f-string 的优势 ---")
    print("1. 可复用：同一个模板可以用不同变量多次调用")
    print("2. 可序列化：模板可以保存为 JSON/YAML 文件")
    print("3. 可组合：模板可以通过 | 运算符与模型组成链")
    print("4. 可验证：自动检查是否所有变量都已填充")
    print("5. 可追踪：LangSmith 等工具可以追踪模板的使用")


def main():
    """
    主函数：按顺序运行所有演示示例。

    功能：初始化模型并依次执行各个演示函数。
    输入参数：无。
    输出返回值：无。
    """
    # 打印课程标题
    print("=" * 60)
    print("📚 Day 2 - 课程 1：Prompt Template（提示词模板）")
    print("=" * 60)

    # 获取可用的模型提供商列表
    providers = list_available_providers()
    # 打印可用提供商
    print(f"\n可用的模型提供商: {providers}")

    # 检查是否有可用的提供商
    if not providers:
        # 没有配置任何 API Key，提示用户
        print("❌ 错误：没有找到可用的模型提供商！")
        print("请在 .env 文件中配置至少一个 API Key。")
        return

    # 使用第一个可用的提供商创建模型
    provider = providers[0]  # 选择第一个可用的提供商
    print(f"使用模型提供商: {provider}")

    # 创建模型实例
    model = create_model(
        provider=provider,  # 模型提供商
        temperature=0.7  # 生成温度
    )
    # 打印模型信息
    print(f"模型创建成功: {model}")

    # 依次运行各个演示示例
    demo_01_basic_prompt_template(model)  # 示例 1
    demo_02_chat_prompt_template(model)  # 示例 2
    demo_03_from_messages(model)  # 示例 3
    demo_04_partial_variables(model)  # 示例 4
    demo_05_messages_placeholder(model)  # 示例 5
    demo_06_template_principle()  # 原理讲解

    # 打印课程结束信息
    print("\n" + "=" * 60)
    print("✅ 课程 1 完成！")
    print("=" * 60)
    print("\n💡 核心要点回顾：")
    print("  1. PromptTemplate：简单的字符串模板")
    print("  2. ChatPromptTemplate：管理多角色消息")
    print("  3. from_messages()：灵活构建消息列表")
    print("  4. partial：预填充部分变量")
    print("  5. MessagesPlaceholder：为对话历史留位")
    print("  6. 本质：f-string 的高级封装")


# 当直接运行此文件时执行主函数
if __name__ == '__main__':
    main()
