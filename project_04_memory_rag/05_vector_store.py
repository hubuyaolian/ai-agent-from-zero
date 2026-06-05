# -*- coding: utf-8 -*-
"""
Day 9 演示：ChromaDB 本地向量数据库的增删改查。

功能：演示如何使用 LangChain 集成的 Chroma 客户端进行向量的存储与近邻语义检索。
输入参数：无。
输出返回值：在控制台输出文档写入日志和检索匹配结果。
"""

# 导入操作系统相关模块，用于文件路径操作
import os
# 导入文件系统删除模块，用于重置测试环境
import shutil
# 导入 LangChain 的 Document 文档基础类
from langchain_core.documents import Document
# 导入 LangChain-Chroma 适配器
from langchain_chroma import Chroma
# 导入本地 Embedding 包装类（底层依赖 sentence-transformers）
from langchain_community.embeddings import HuggingFaceEmbeddings


def reset_database(directory_path):
    """
    清理并重置本地向量数据库持久化目录。

    功能：如果指定的目录存在，将其强制递归删除，以保证每次运行测试时都是全新的数据库。
    输入参数：
        directory_path (str): 本地持久化文件夹的绝对或相对路径。
    输出返回值：
        None
    """
    # 检查指定的目录是否存在于磁盘上
    if os.path.exists(directory_path):
        # 打印清理日志
        print(f"🧹 正在清理已有的数据库目录: {directory_path}")
        # 递归删除整个目录树
        shutil.rmtree(directory_path)
        # 打印完成日志
        print("✅ 清理完成。")
    else:
        # 目录不存在，无需清理
        pass


def main():
    """
    主运行函数。

    功能：配置 Embedding 模型，初始化本地 Chroma 集合，插入示例文档并进行多维度相似度搜索。
    """
    # 定义数据库持久化文件夹的相对路径
    db_directory = "./chroma_db_demo"

    # 在创建前，重置一下数据库，确保演示不受历史残留数据干扰
    reset_database(db_directory)

    print("🔮 正在初始化本地 Embedding 模型（首次运行会自动下载）...")
    # 教学阶段 04 之后默认 LLM 是 xiaomi mimo，embedding 改走本地模型（无需 API Key）
    # 默认模型：BAAI/bge-small-zh-v1.5，中文专用、~93M 参数
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={"device": "cpu"},  # 无 GPU 环境走 CPU；有 GPU 可改 "cuda"
        encode_kwargs={"normalize_embeddings": True},  # 归一化后余弦相似度等价于点积
    )

    print("\n📦 正在连接/创建本地 Chroma 向量存储...")
    # 初始化本地向量库。如果该目录不存在，Chroma 会自动在磁盘上创建它
    vectorstore = Chroma(
        collection_name="learning_concepts",  # 向量集合的名称
        embedding_function=embeddings,  # 指定生成向量时所用的嵌入模型
        persist_directory=db_directory  # 设定数据持久化存储的本地目录路径
    )

    print("\n📝 正在准备测试文档...")
    # 创建几个带有丰富元数据（Metadata）的 Document 对象
    docs = [
        Document(
            page_content="LangChain 是一个用于构建大语言模型 (LLM) 应用的开源开发框架。",
            metadata={"source": "langchain_guide.md", "chapter": 1, "topic": "intro"}
        ),
        Document(
            page_content="LangGraph 是 LangChain 团队开发的 Agent 编排框架，支持使用图结构构建多 Agent 协同系统。",
            metadata={"source": "langgraph_guide.md", "chapter": 1, "topic": "advanced"}
        ),
        Document(
            page_content="RAG (检索增强生成) 是一种在大模型生成回答前，先从外部数据源检索相关知识的技术。",
            metadata={"source": "rag_tutorial.md", "chapter": 2, "topic": "rag"}
        ),
        Document(
            page_content="ChromaDB 是一个轻量级、开源的嵌入式向量数据库，非常适合本地部署和快速原型开发。",
            metadata={"source": "chromadb_manual.md", "chapter": 3, "topic": "vector_db"}
        ),
    ]

    print("\n💾 正在将文档写入本地向量数据库...")
    # 将 Document 数组添加进本地库。Chroma 内部会自动调用 embeddings 接口获取每条 page_content 的高维向量
    vectorstore.add_documents(docs)
    print("✅ 文档数据向量化并写入本地磁盘成功！")

    print("\n🔍 场景一：进行普通语义相似度检索 (Similarity Search)...")
    query_1 = "什么是 LangChain 框架？"
    print(f"用户提问: '{query_1}'")

    # 进行检索，请求返回最接近的 2 条结果
    results_1 = vectorstore.similarity_search(
        query=query_1,  # 检索关键词/句子
        k=2  # 返回匹配数量
    )

    # 遍历打印检索出来的文档信息
    for i, doc in enumerate(results_1):
        # 打印匹配排名和文本内容
        print(f"  匹配 [{i + 1}] | 内容: {doc.page_content}")
        # 打印元数据来源
        print(f"         | 来源: {doc.metadata['source']} | 章节: {doc.metadata['chapter']}")

    print("\n🔍 场景二：带分数相似度检索 (Similarity Search with Score)...")
    query_2 = "我想了解本地运行的向量数据库"
    print(f"用户提问: '{query_2}'")

    # 进行带相似度分数的检索。
    # 注意：Chroma 返回的 score 是 L2 距离（欧氏距离平方）。距离越小，代表语义越接近！
    results_2 = vectorstore.similarity_search_with_score(
        query=query_2,  # 检索查询
        k=2  # 返回最接近的 2 个
    )

    # 循环遍历文档与对应分数
    for i, item in enumerate(results_2):
        # 拆包获取文档对象与 L2 距离分数
        doc = item[0]
        score = item[1]
        # 打印检索结果及 L2 距离
        print(f"  匹配 [{i + 1}] | L2 距离(越小越近): {score:.4f}")
        print(f"         | 内容: {doc.page_content}")
        print(f"         | 来源: {doc.metadata['source']}")

    # 演示结束，再次清理测试数据库
    print("\n🧹 演示结束，正在清理临时测试库...")
    reset_database(db_directory)
    print("✨ 本地 ChromaDB 完整演示结束。")


# 判断是否由命令行直接启动
if __name__ == "__main__":
    # 执行主程序
    main()
