"""
Day 2 - 课程 2：Output Parsers（输出解析器 / 结构化输出）。

==========================================================
为什么需要结构化输出？
==========================================================

LLM 默认返回的是「纯文本」，就像跟人聊天一样，回复是自由格式的。
但在实际应用中，我们经常需要 LLM 返回「结构化数据」：

    场景举例：
    1. 情感分析 → 需要返回 {"sentiment": "正面", "score": 0.95}
    2. 信息提取 → 需要返回 {"name": "张三", "age": 25}
    3. 分类任务 → 需要返回 {"category": "科技", "confidence": 0.8}

    问题：LLM 可能返回各种奇怪的格式：
    - "情感是正面的，分数大概是 0.95 左右"  （自然语言）
    - "```json\n{...}\n```"  （带有 markdown 代码块）
    - "{sentiment: 正面}"  （不合法的 JSON）

    解决方案：Output Parser（输出解析器）
    1. 在 Prompt 中告诉 LLM 应该用什么格式输出
    2. 对 LLM 的输出文本进行解析，提取结构化数据
    3. 自动验证输出是否符合预期格式

本质原理：
    解析器 = 格式指令（告诉 LLM 怎么输出） + 解析逻辑（从文本中提取数据）
    - StrOutputParser：直接提取文本内容（最简单）
    - JsonOutputParser：从文本中提取 JSON 并解析为 dict
    - PydanticOutputParser：用 Pydantic 模型验证和解析

==========================================================
本课程涵盖内容：
    1. StrOutputParser（纯文本解析）
    2. JsonOutputParser（JSON 解析）
    3. PydanticOutputParser（Pydantic 模型解析）
    4. get_format_instructions() 的作用
    5. 完整实战：文本分析返回结构化结果
==========================================================
"""

# ============================================================
# 导入区域
# ============================================================
import sys  # 系统模块，用于修改模块搜索路径
import os  # 操作系统模块，用于路径操作
import json  # JSON 模块，用于美化打印 JSON 数据

# 将项目根目录添加到模块搜索路径
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), '..')
)

# 从 LangChain 导入输出解析器
from langchain_core.output_parsers import StrOutputParser  # 字符串解析器
from langchain_core.output_parsers import JsonOutputParser  # JSON 解析器
from langchain_core.output_parsers import PydanticOutputParser  # Pydantic 解析器

# 从 LangChain 导入提示词模板
from langchain_core.prompts import ChatPromptTemplate  # 聊天模板

# 从 Pydantic 导入数据模型基类和字段描述
from pydantic import BaseModel  # 数据模型基类
from pydantic import Field  # 字段描述装饰器

# 从公共模块导入模型工厂和配置
from common.model_factory import create_model  # 模型创建工厂函数
from common.config import list_available_providers  # 列出可用提供商

# 导入类型提示
from typing import List  # 列表类型提示


def demo_01_str_output_parser(model):
    """
    演示 StrOutputParser（字符串输出解析器）。

    功能：展示最简单的解析器，从 LLM 响应中提取纯文本内容。
          LLM 返回的是 AIMessage 对象，StrOutputParser 提取其中的
          .content 字符串属性。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("📝 示例 1：StrOutputParser（字符串解析器）")
    print("=" * 60)

    # ---- 对比：不使用解析器 vs 使用解析器 ----
    # 不使用解析器时，model.invoke() 返回的是 AIMessage 对象
    raw_response = model.invoke("用一句话解释什么是 Python")
    # 打印原始返回类型
    print(f"\n未使用解析器时的返回类型: {type(raw_response)}")
    # 打印原始返回对象（包含 content、metadata 等）
    print(f"原始返回对象: {raw_response}")

    # 使用 StrOutputParser 构建链
    # prompt | model | parser 是 LangChain 的链式调用
    parser = StrOutputParser()  # 创建字符串解析器实例
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个知识渊博的助手，回答简洁。"),
        ("human", "{question}"),
    ])

    # 构建链：模板 → 模型 → 解析器
    chain = prompt | model | parser

    # 调用链，获取纯文本结果
    parsed_response = chain.invoke(
        {"question": "用一句话解释什么是 Python"}
    )
    # 打印解析后的返回类型
    print(f"\n使用解析器后的返回类型: {type(parsed_response)}")
    # 打印解析后的纯文本内容
    print(f"解析后的文本: {parsed_response}")

    # 原理说明
    print("\n💡 原理说明：")
    print("  StrOutputParser 做的事情非常简单：")
    print("  AIMessage 对象 → 提取 .content → 返回纯字符串")


def demo_02_json_output_parser(model):
    """
    演示 JsonOutputParser（JSON 输出解析器）。

    功能：展示如何让 LLM 返回 JSON 格式数据，
          并自动解析为 Python 字典。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("📋 示例 2：JsonOutputParser（JSON 解析器）")
    print("=" * 60)

    # 创建 JSON 输出解析器
    json_parser = JsonOutputParser()

    # 获取格式指令（这些指令会被插入到提示词中）
    format_instructions = json_parser.get_format_instructions()
    # 打印格式指令，查看解析器生成了什么提示
    print(f"\nJSON 解析器的格式指令:\n{format_instructions}")

    # 创建提示词模板，包含格式指令
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个数据分析助手。"
            "请严格按照指定格式输出。\n"
            "{format_instructions}"
        ),
        (
            "human",
            "请分析以下城市的基本信息，返回一个 JSON 对象，"
            "包含字段：city（城市名）、country（国家）、"
            "population（人口，单位万）、"
            "famous_for（以什么闻名，列出3项）。\n"
            "城市：{city}"
        ),
    ])

    # 构建链：模板 → 模型 → JSON 解析器
    chain = prompt | model | json_parser

    # 调用链
    result = chain.invoke({
        "city": "杭州",
        "format_instructions": format_instructions
    })

    # 打印结果类型（应该是 dict）
    print(f"\n返回类型: {type(result)}")
    # 美化打印 JSON 结果
    print("解析结果:")
    print(json.dumps(
        result,
        ensure_ascii=False,  # 支持中文显示
        indent=2  # 缩进 2 格
    ))

    # 演示可以像普通字典一样访问数据
    print(f"\n城市名称: {result.get('city', '未知')}")
    print(f"所属国家: {result.get('country', '未知')}")

    # 原理说明
    print("\n💡 原理说明：")
    print("  1. get_format_instructions() 生成提示文本")
    print("     告诉 LLM: '请返回 JSON 格式'")
    print("  2. LLM 返回包含 JSON 的文本")
    print("  3. 解析器用 json.loads() 提取并解析")


def demo_03_pydantic_output_parser(model):
    """
    演示 PydanticOutputParser（Pydantic 输出解析器）。

    功能：展示如何使用 Pydantic 模型定义数据结构，
          让 LLM 返回符合特定 Schema 的结构化数据。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🏗️ 示例 3：PydanticOutputParser（Pydantic 解析器）")
    print("=" * 60)

    # ---- 第 1 步：定义 Pydantic 数据模型 ----
    # Pydantic 模型定义了期望的输出结构和类型
    class BookReview(BaseModel):
        """
        书评数据模型。

        功能：定义 LLM 返回的书评结构化数据格式。
        """

        # 书名字段，必须是字符串类型
        title: str = Field(
            description="书籍的标题名称"
        )
        # 作者字段，必须是字符串类型
        author: str = Field(
            description="书籍的作者姓名"
        )
        # 评分字段，必须是整数类型（1-10 分）
        rating: int = Field(
            description="评分，1到10的整数"
        )
        # 摘要字段，必须是字符串类型
        summary: str = Field(
            description="一句话概括这本书的核心内容"
        )
        # 推荐理由字段，必须是字符串列表类型
        reasons: List[str] = Field(
            description="推荐理由，列出2-3条"
        )

    # ---- 第 2 步：创建 Pydantic 解析器 ----
    pydantic_parser = PydanticOutputParser(
        pydantic_object=BookReview  # 指定目标数据模型
    )

    # 获取格式指令
    format_instructions = pydantic_parser.get_format_instructions()
    # 打印格式指令（包含了 JSON Schema 信息）
    print(f"\nPydantic 解析器的格式指令:\n{format_instructions}")

    # ---- 第 3 步：构建提示词和链 ----
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个专业的书评人。"
            "请严格按照指定格式输出。\n"
            "{format_instructions}"
        ),
        (
            "human",
            "请对《{book_name}》这本书写一个简短的书评。"
        ),
    ])

    # 构建链：模板 → 模型 → Pydantic 解析器
    chain = prompt | model | pydantic_parser

    # ---- 第 4 步：调用链并获取结果 ----
    result = chain.invoke({
        "book_name": "三体",
        "format_instructions": format_instructions
    })

    # 打印结果类型（应该是 BookReview 实例）
    print(f"\n返回类型: {type(result)}")
    # 打印 Pydantic 对象的各个字段
    print(f"书名: {result.title}")
    print(f"作者: {result.author}")
    print(f"评分: {result.rating}/10")
    print(f"摘要: {result.summary}")
    print("推荐理由:")
    # 遍历推荐理由列表
    for i, reason in enumerate(result.reasons):
        print(f"  {i + 1}. {reason}")

    # 也可以转换为字典
    result_dict = result.model_dump()
    print(f"\n转为字典: {result_dict}")

    # 原理说明
    print("\n💡 原理说明：")
    print("  1. Pydantic 模型定义了数据的 Schema")
    print("  2. get_format_instructions() 将 Schema")
    print("     转为 LLM 能理解的文本指令")
    print("  3. LLM 按指令输出 JSON 字符串")
    print("  4. 解析器将 JSON 解析并验证为 Pydantic 对象")


def demo_04_practical_example(model):
    """
    实战案例：让 LLM 分析一篇文本，返回结构化结果。

    功能：综合运用 PydanticOutputParser，实现一个完整的
          文本分析流程（提取标题、摘要、关键词、情感）。
    输入参数：
        model: LangChain 聊天模型实例。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🚀 实战案例：文本分析（结构化输出）")
    print("=" * 60)

    # ---- 第 1 步：定义文本分析结果的数据模型 ----
    class TextAnalysis(BaseModel):
        """
        文本分析结果数据模型。

        功能：定义文本分析返回的所有结构化字段。
        """

        # 文章标题（由 LLM 自动提取或生成）
        title: str = Field(
            description="文章的标题或主题，不超过20字"
        )
        # 文章摘要（一段话概括）
        summary: str = Field(
            description="文章的核心内容摘要，50字以内"
        )
        # 关键词列表（提取 3-5 个关键词）
        keywords: List[str] = Field(
            description="文章的关键词，3到5个"
        )
        # 情感分析结果
        sentiment: str = Field(
            description="文章的情感倾向：正面/负面/中性"
        )
        # 情感置信度（0-1 的浮点数）
        confidence: float = Field(
            description="情感判断的置信度，0到1之间的小数"
        )
        # 文章分类
        category: str = Field(
            description="文章所属分类，如科技/教育/娱乐/财经等"
        )

    # ---- 第 2 步：准备待分析的文本 ----
    sample_text = """
    近日，中国科学院发布了最新的量子计算研究成果。
    研究团队成功实现了 100 个量子比特的纠缠态制备，
    这一突破性进展标志着我国在量子计算领域迈入了
    世界领先行列。专家表示，量子计算将在药物研发、
    金融风控、气象预测等领域发挥重要作用。这项研究
    已发表在国际顶级学术期刊 Nature 上，获得了国际
    同行的高度评价。
    """

    # ---- 第 3 步：创建解析器和链 ----
    # 创建 Pydantic 解析器
    analysis_parser = PydanticOutputParser(
        pydantic_object=TextAnalysis  # 指定目标数据模型
    )
    # 获取格式指令
    format_instructions = analysis_parser.get_format_instructions()

    # 创建提示词模板
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个专业的文本分析助手。"
            "请仔细分析用户提供的文本，"
            "并严格按照指定格式返回分析结果。\n"
            "{format_instructions}"
        ),
        (
            "human",
            "请分析以下文本：\n\n{text}"
        ),
    ])

    # 构建链：模板 → 模型 → 解析器
    chain = prompt | model | analysis_parser

    # ---- 第 4 步：执行分析 ----
    print("\n📄 待分析文本:")
    print(f"  {sample_text.strip()}")

    # 调用链进行分析
    analysis = chain.invoke({
        "text": sample_text,
        "format_instructions": format_instructions
    })

    # ---- 第 5 步：展示结果 ----
    print("\n📊 分析结果:")
    print(f"  标题: {analysis.title}")
    print(f"  摘要: {analysis.summary}")

    # 打印关键词列表
    keywords_str = "、".join(analysis.keywords)
    print(f"  关键词: {keywords_str}")

    print(f"  情感: {analysis.sentiment}")
    print(f"  置信度: {analysis.confidence:.2f}")
    print(f"  分类: {analysis.category}")

    # 将结果转为 JSON 格式输出
    print("\n📋 JSON 格式结果:")
    result_json = analysis.model_dump()
    print(json.dumps(
        result_json,
        ensure_ascii=False,  # 支持中文
        indent=2  # 缩进 2 格
    ))


def demo_05_parser_principle():
    """
    原理讲解：输出解析器的本质。

    功能：通过代码演示，揭示输出解析器的底层工作原理。
    输入参数：无。
    输出返回值：无（直接打印结果）。
    """
    # 打印章节标题
    print("\n" + "=" * 60)
    print("🔬 原理讲解：输出解析器的本质")
    print("=" * 60)

    # ---- 模拟 JsonOutputParser 的核心逻辑 ----
    print("\n--- 模拟 JSON 解析的核心逻辑 ---")

    # 假设 LLM 返回了以下文本
    llm_output = """
    根据你的要求，我分析了这篇文章：
    ```json
    {"title": "量子计算突破", "sentiment": "正面"}
    ```
    以上是分析结果。
    """
    print(f"LLM 原始输出:\n{llm_output}")

    # 解析器的核心逻辑：从文本中提取 JSON
    # 第 1 步：尝试查找 JSON 代码块
    content = llm_output.strip()  # 去除首尾空白
    # 检查是否包含 markdown 代码块
    if "```json" in content:
        # 提取代码块中的 JSON 内容
        start = content.find("```json") + 7  # 找到 ```json 后的位置
        end = content.find("```", start)  # 找到结束的 ```
        json_str = content[start:end].strip()  # 提取中间的内容
    else:
        # 没有代码块，尝试直接解析整个文本
        json_str = content

    # 第 2 步：解析 JSON 字符串为字典
    result = json.loads(json_str)
    print(f"提取的 JSON: {result}")
    print(f"结果类型: {type(result)}")

    # 总结
    print("\n--- 解析器工作流程总结 ---")
    print("1. 格式指令阶段：生成提示文本，告诉 LLM 输出格式")
    print("2. LLM 生成阶段：LLM 按指令输出文本")
    print("3. 解析阶段：从文本中提取并验证结构化数据")
    print("\n各解析器的解析方式：")
    print("  StrOutputParser → 直接提取 .content 属性")
    print("  JsonOutputParser → 正则提取 JSON + json.loads()")
    print("  PydanticOutputParser → JSON 解析 + Pydantic 验证")


def main():
    """
    主函数：按顺序运行所有演示示例。

    功能：初始化模型并依次执行各个演示函数。
    输入参数：无。
    输出返回值：无。
    """
    # 打印课程标题
    print("=" * 60)
    print("📚 Day 2 - 课程 2：Output Parsers（输出解析器）")
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
        temperature=0.3  # 结构化输出用较低温度
    )
    print(f"模型创建成功: {model}")

    # 依次运行各个演示示例
    demo_01_str_output_parser(model)  # 示例 1
    demo_02_json_output_parser(model)  # 示例 2
    demo_03_pydantic_output_parser(model)  # 示例 3
    demo_04_practical_example(model)  # 实战案例
    demo_05_parser_principle()  # 原理讲解

    # 打印课程结束信息
    print("\n" + "=" * 60)
    print("✅ 课程 2 完成！")
    print("=" * 60)
    print("\n💡 核心要点回顾：")
    print("  1. StrOutputParser：提取纯文本（最简单）")
    print("  2. JsonOutputParser：解析 JSON 为字典")
    print("  3. PydanticOutputParser：验证并解析为对象")
    print("  4. get_format_instructions() 是关键桥梁")
    print("  5. 本质：格式指令 + 文本解析")


# 当直接运行此文件时执行主函数
if __name__ == '__main__':
    main()
