# -*- coding: utf-8 -*-
"""
Day 10 演示：最简 RAG (检索增强生成) 管道的端到端实现。

功能：串联离线文档加载、文本分块、ChromaDB 向量索引，以及在线语义检索、Prompt 拼接与大模型生成全流程。
输入参数：无（内部自动创建临时技术文档进行系统问答测试）。
输出返回值：在控制台打印检索到的原文背景片段以及大模型最终生成的精确答案。
"""

# 导入操作系统相关模块，用于管理物理文件路径
import os
# 导入文件系统删除工具，用于重置测试目录
import shutil
# 导入系统路径模块，用于支持从任意位置直接运行本脚本
import sys
# 导入路径处理工具，用于定位项目根目录
from pathlib import Path

# 将项目根目录加入模块搜索路径，保证 `python project_04_memory_rag/08_simple_rag.py` 可直接运行
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# 导入 LangChain 的 Chroma 适配器
from langchain_chroma import Chroma
# 导入本地 Embedding 包装器（底层依赖 sentence-transformers）
from langchain_community.embeddings import HuggingFaceEmbeddings
# 导入单文件加载类 TextLoader
from langchain_community.document_loaders import TextLoader
# 导入递归文本分块器
from langchain_text_splitters import RecursiveCharacterTextSplitter
# 导入聊天 Prompt 模板类
from langchain_core.prompts import ChatPromptTemplate
# 导入字符串输出解析器
from langchain_core.output_parsers import StrOutputParser
# 导入直通透传组件，用于 LCEL 参数映射
from langchain_core.runnables import RunnablePassthrough
# 从项目公共模型工厂中导入模型创建函数
from common.model_factory import create_model


def prepare_source_document(directory):
    """
    在本地临时生成一篇详细的 AI 技术说明文档作为 RAG 数据源。

    功能：如果指定的目录不存在，先创建它，然后写入一篇关于 'LangGraph 核心设计原理' 的 Markdown 手册。
    输入参数：
        directory (str): 目标存放文档的本地文件夹路径。
    输出返回值：
        str: 物理写入的 Markdown 文件完整路径。
    """
    # 如果目标目录不存在，则通过操作系统 API 级联创建它
    if os.path.exists(directory):
        # 存在则跳过
        pass
    else:
        # 创建目录
        os.makedirs(directory)

    # 拼接出待生成的说明文档路径
    file_path = os.path.join(directory, "langgraph_manual.md")

    # 写入技术文档内容
    with open(file_path, "w", encoding="utf-8") as f:
        # 写入正文
        f.write(
            "# LangGraph 核心设计与状态图机指南\n\n"
            "## 1. 为什么使用 LangGraph？\n"
            "传统的 LangChain 链（LCEL）主要支持简单的有向无环图（DAG），无法很好地"
            "表达在复杂 Agent 场景中频繁出现的'循环往复'与'回溯迭代'逻辑。LangGraph 将"
            "整个 Agent 系统建模为一个由节点（Nodes）和边（Edges）构成的有向图，能够完美"
            "支持图的循环控制。\n\n"
            "## 2. 状态机制 (State)\n"
            "LangGraph 的灵魂在于其统一的'状态（State）'。整个图在运行过程中，会不断流转"
            "一个包含全部消息和运行数据的 TypedDict 状态对象。每一个节点都可以读取当前的状态，"
            "并返回需要更新的数据（增量更新），以此实现节点之间的信息共享和通信。\n\n"
            "## 3. 节点与边 (Nodes and Edges)\n"
            "- **节点 (Node)**：本质上是一个普通的 Python 函数，它接收当前的状态作为输入，"
            "进行大模型推理、工具调用或逻辑处理后，输出增量状态数据。\n"
            "- **普通边 (Normal Edge)**：指定一个节点在执行完成后，无条件跳转到下一个节点。\n"
            "- **条件边 (Conditional Edge)**：根据一个路由函数（Router）的计算结果，动态"
            "决定流程去往何方（例如：若大模型输出含有 tool_calls 则跳转到工具节点，否则跳转到结束点 END）。"
        )

    # 打印日志
    print(f"📄 成功生成 RAG 测试源文件: {file_path}")
    # 返回文件的完整路径
    return file_path


def format_docs(docs):
    """
    将检索到的多个 Document 对象的 page_content 拼接成一个大文本字符串。

    功能：提取列表里的文本，并用双换行符连接它们以形成最终的参考上下文（坚决不用单行推导式）。
    输入参数：
        docs (list[Document]): 检索出来的 Document 对象列表。
    输出返回值：
        str: 拼接后的完整参考文本。
    """
    # 创建一个空的字符串列表，用于存放各个文档的文本内容
    formatted_texts = []
    # 遍历输入的每一个文档对象
    for doc in docs:
        # 将文档的文本内容追加到列表中
        formatted_texts.append(doc.page_content)
    # 用两个换行符作为分隔符将列表中的文本连接起来
    joined_text = "\n\n".join(formatted_texts)
    # 返回连接后的最终字符串
    return joined_text


def main():
    """
    主运行函数。

    功能：离线处理文档（加载、分块、建索引），在线提问（语义检索、Prompt 组装、大模型问答），并在结束后清理环境。
    """
    # 设定临时生成的资源目录
    data_dir = "./temp_rag_resources"
    # 设定临时本地 Chroma 持久化目录
    db_dir = "./temp_rag_chroma"

    # 初始化清理旧环境
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    else:
        pass
    if os.path.exists(db_dir):
        shutil.rmtree(db_dir)
    else:
        pass

    # 步骤 1：离线索引阶段（加载与切片）
    print("--- [离线索引阶段] 开始 ---")
    # 动态在本地写入测试用的技术手册
    source_file = prepare_source_document(data_dir)

    # 使用 TextLoader 读入此文档
    loader = TextLoader(file_path=source_file, encoding="utf-8")
    documents = loader.load()

    # 初始化文本分块器（设置适中大小，保证段落基本完整）
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,  # 单个块最大 300 字符
        chunk_overlap=50,  # 块与块之间重叠 50 字符
        separators=["\n\n", "\n", "。", "！", "？", " "]
    )
    # 对文档节点进行切片分块
    chunks = text_splitter.split_documents(documents)
    print(f"✂️ 已将源文档切分为 {len(chunks)} 个文本块。")

    # 步骤 2：向量化并写入本地 ChromaDB 向量数据库
    print("\n🔮 正在配置本地 Embedding 并构建向量索引（首次运行会自动下载模型）...")
    # embedding 改走本地模型（无需 API Key），默认 BAAI/bge-small-zh-v1.5
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={"device": "cpu"},  # 无 GPU 环境走 CPU；有 GPU 可改 "cuda"
        encode_kwargs={"normalize_embeddings": True},
    )
    # 调用 Chroma 静态方法，一次性将文档块向量化并写入数据库中
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=db_dir  # 指定本地持久化磁盘路径
    )
    print("✅ 向量数据库建库成功！")
    print("--- [离线索引阶段] 结束 ---\n")

    # 步骤 3：在线查询阶段（构建 RAG 交互链）
    print("--- [在线查询阶段] 开始 ---")
    # 将向量库包装为标准的检索器抽象对象（Retriever）
    # search_kwargs={"k": 2} 表示在提问时，数据库只返回语义最接近的 2 条记录
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    # 使用公共大模型工厂创建聊天模型实例，默认走 xiaomi mimo
    model = create_model(provider="xiaomi mimo", temperature=0.0)

    # 编写专门的 RAG 专属 Prompt。
    # 核心要点：严格限制模型必须根据 Context 里的事实信息进行作答，拒绝无中生有的幻觉！
    rag_prompt = ChatPromptTemplate.from_template(
        "你是一个专业的技术文档助手。请严格基于以下参考资料来回答用户的问题。\n"
        "如果你在资料中无法找到答案，请如实回答 '根据现有参考资料，我无法回答该问题。'，"
        "切勿凭借历史记忆编造不存在的知识点。\n\n"
        "参考资料：\n"
        "{context}\n\n"
        "用户问题：{question}\n\n"
        "请用中文条理清晰地进行作答："
    )

    # 组装完整的 LangChain 表达式（LCEL）链。
    # - "context" 键：利用检索器 `retriever` 查出文档，并使用自定义 `format_docs` 转为纯文本字符串。
    # - "question" 键：利用 `RunnablePassthrough` 将传入的原始用户问题直接透传给 Prompt。
    # 然后数据输入到 rag_prompt 进行渲染，送给 model 进行推理，最后由 StrOutputParser 解析为纯文本。
    rag_chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | rag_prompt
        | model
        | StrOutputParser()
    )

    # 用户输入测试提问
    test_question = "LangGraph 里的状态 Edge 和普通 Edge 有什么区别？它为什么要用有向图构建？"
    print(f"❓ 用户提问: {test_question}")

    # 调用检索器，查看一下实际召回了什么片段（辅助教学观察）
    retrieved_docs = retriever.invoke(test_question)
    print(f"\n📢 [RAG 召回片段预览] 数据库共召回了 {len(retrieved_docs)} 条相关参考资料:")
    for idx, r_doc in enumerate(retrieved_docs):
        # 提取文件来源
        src = r_doc.metadata.get("source", "未知")
        # 打印各条片段
        print(f"  [召回 {idx + 1}] 来源: {os.path.basename(src)}")
        print(f"    内容: '{r_doc.page_content}'")

    print("\n🤖 正在请求大模型生成基于资料的答案...")
    # 执行大模型检索增强问答链
    final_answer = rag_chain.invoke(test_question)

    print("\n==================================================")
    print("⭐ 大模型 RAG 精准回答:")
    print("==================================================")
    print(final_answer)
    print("==================================================")
    print("--- [在线查询阶段] 结束 ---\n")

    # 步骤 4：清理本地临时创建的文件和库，恢复现场
    print("🧹 正在清理本地 RAG 临时文件夹和向量库...")
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    else:
        pass
    if os.path.exists(db_dir):
        shutil.rmtree(db_dir)
    else:
        pass
    print("✨ 最简 RAG 演示完成，工作区恢复清洁。")


# 判断是否作为主程序直接运行
if __name__ == "__main__":
    # 执行主程序
    main()
