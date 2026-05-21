# -*- coding: utf-8 -*-
"""
Day 9 演示：文本分块策略 (Text Splitting / Chunking)。

功能：演示如何使用 LangChain 的 RecursiveCharacterTextSplitter 对长文档进行分块，并对比不同分块大小参数的效果。
输入参数：无（内部定义长篇测试文本）。
输出返回值：在控制台打印并比较不同分块大小下文本块的字数、重合度以及分块实例片段。
"""

# 导入 LangChain 的递归字符文本分块器
from langchain_text_splitters import RecursiveCharacterTextSplitter
# 导入 LangChain 的 Document 文档类，以便将文本转化为标准的文档节点
from langchain_core.documents import Document


def print_chunks_analysis(label, chunks):
    """
    分析并辅助打印分块后的统计结果。

    功能：统计分块数量，并循环打印各个块的字符长度和内容缩略。
    输入参数：
        label (str): 当前演示策略的标签说明名称。
        chunks (list[Document]): 文本切分后的 Document 对象列表。
    输出返回值：
        None
    """
    # 打印策略名称标题
    print("\n======================================")
    print(f"📊 策略: {label}")
    print("======================================")
    # 打印切分后文本块的总数量
    print(f"分块总数: {len(chunks)} 个块")

    # 循环遍历前 3 个块（如果块数不够，则遍历所有块）
    limit = 3
    # 确定要遍历打印的实际数量，防止越界
    if len(chunks) < limit:
        # 如果块数比限制少，则全量打印
        limit = len(chunks)
    else:
        # 否则只打印限制数量
        pass

    # 遍历进行展示
    for i in range(limit):
        # 提取当前块对应的 Document 对象
        chunk = chunks[i]
        # 获取当前块内容的字符字数
        chunk_len = len(chunk.page_content)
        # 提取该块的文本内容
        content = chunk.page_content
        # 对文本行数进行规范缩减，避免控制台打印过长
        # 替换换行为空格，以便单行显示概要
        clean_content = content.replace("\n", " ")
        # 截取前 80 个字符进行预览，若有剩余加省略号
        if len(clean_content) > 80:
            # 截断
            preview = clean_content[:80] + "..."
        else:
            # 足够短直接完整输出
            preview = clean_content
        # 打印各个块的具体特征指标
        print(f"  [块 {i + 1}] 字符长度: {chunk_len} 字")
        print(f"         内容预览: {preview}")

    # 打印策略分割结束标记
    print("-" * 38)


def main():
    """
    主运行函数。

    功能：定义一段超过 1000 字符的多段落深度分析长文本，初始化两种不同参数的分块器进行试验和比对。
    """
    # 定义一段关于 AI Agent 演进的中长篇测试文本（多段落，用于进行文本切分）
    long_article = (
        "人工智能代理（AI Agent）是通往通用人工智能（AGI）道路上的关键探索方向。与传统的"
        "单向交互语言模型相比，Agent 的核心价值在于其具备自主感知、推理、规划、记忆和工具"
        "调用的闭环能力。在整个架构设计中，规划（Planning）组件主要负责对复杂的目标任务进行"
        "多阶段拆解和动态路径规划；而记忆（Memory）组件则细分为短期工作记忆和基于外部数据库"
        "持久化存储的长期记忆。\n\n"
        "在 RAG（检索增强生成）系统蓬勃发展的今天，文本分块（Chunking）是影响信息召回精度和"
        "回答完整度的第一道命门。如果我们将 chunk_size 设置得过大，在向量化检索时就会带入"
        "大量的语义噪声，稀释了最核心的知识，使检索出的上下文不够精确。然而，如果我们一味"
        "追求精细，把 chunk_size 设置得非常小，比如几十个字符，那么原本连贯的上下文句子就会"
        "惨遭斩断，大模型接收到碎片化的知识后，很难拼凑出逻辑完整的事实，从而极大增加了回答"
        "出现幻觉的概率。\n\n"
        "这就对 chunk_overlap（重合重叠字数）这一参数提出了高度的工程设计要求。通过设置合理"
        "的重合边界，比如 10% 到 20% 的重叠区间，系统能够确保在切分处的上下文语义能够平滑过渡。"
        "即使某一个极为核心的实体概念不幸恰好落在物理切分边界线上，它也能够在前后相邻的两个"
        "文档切片中同时被完整保留，从而彻底规避了传统按字数强行截断所导致的语义信息丢失弊端。"
        "在实际工程项目中，开发者需要根据所采用的 Embedding 模型的最大 token 支持长度，以及"
        "底座 LLM 的上下文窗口大小，在这两个相互制衡的参数中进行反复的实验与调优，找到那个"
        "能够完美平衡精度和连贯性的最佳平衡点。"
    )

    # 封装为标准的 LangChain Document 对象，并补充模拟的元数据
    sample_doc = Document(
        page_content=long_article,
        metadata={"title": "Agent 与 RAG 最佳实践手册", "author": "专家讲师"}
    )

    # 打印原始文章的基础数据
    print(f"📝 原始文章字符总长度: {len(long_article)} 字")

    print("\n🔍 方案一：采用小分块策略 (chunk_size=200, chunk_overlap=30)")
    # 初始化第一个分块器：偏重精细化检索，但较容易切碎上下文
    splitter_small = RecursiveCharacterTextSplitter(
        chunk_size=200,  # 目标单个分块最大 200 字符
        chunk_overlap=30,  # 相邻两个块物理重叠 30 字符
        separators=["\n\n", "\n", "。", "！", "？", " ", ""]  # 按段落、行、句子的优先级进行安全切分
    )
    # 对示例文档进行分块处理
    chunks_small = splitter_small.split_documents([sample_doc])
    # 打印分析结果
    print_chunks_analysis("小分块策略 (chunk_size=200)", chunks_small)

    print("\n🔍 方案二：采用中大分块平衡策略 (chunk_size=500, chunk_overlap=100)")
    # 初始化第二个分块器：兼顾上下文连贯性与语义提取的完整度
    splitter_medium = RecursiveCharacterTextSplitter(
        chunk_size=500,  # 目标单个分块最大 500 字符
        chunk_overlap=100,  # 相邻两个块物理重叠 100 字符
        separators=["\n\n", "\n", "。", "！", "？", " ", ""]  # 分割优先级定义
    )
    # 对示例文档进行分块处理
    chunks_medium = splitter_medium.split_documents([sample_doc])
    # 打印分析结果
    print_chunks_analysis("中分块平衡策略 (chunk_size=500)", chunks_medium)

    print("\n💡 教学启发对比总结:")
    print("  1. 当采用 200 字小分块时，文档被划分为了更多的小碎片。这有助于在向量检索时定位非常精确的一句话，但会导致上下文割裂。")
    print("  2. 当采用 500 字中分块时，分块数明显变少，但每个分块的信息含量非常充足，大模型回答时有丰富的上下文做支撑。")
    print("  3. 观察重叠区域 (Overlap)，它使得即使句子被断开，相邻分块依然可以通过重叠文字维持前后承接的语义脉络。")


# 判断是否自命令行启动
if __name__ == "__main__":
    # 执行主程序
    main()
