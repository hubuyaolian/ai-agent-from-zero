# -*- coding: utf-8 -*-
"""
Day 10 演示：将 RAG 检索封装为大模型的工具，并配合手写 Agent 循环。

功能：展示大模型如何根据问题自主决策，在本地推理、使用计算器，或使用 RAG 工具查询私有知识库。
输入参数：无（内部自动写入技术文档进行混合场景提问测试）。
输出返回值：控制台打印 Agent 每一轮的思考（Thought）与执行行动（Action）细节。
"""

# 导入操作系统相关模块，用于创建与删除测试目录
import os
# 导入文件系统删除模块
import shutil
# 导入系统路径模块，用于支持从任意位置直接运行本脚本
import sys
# 导入路径处理工具，用于定位项目根目录
from pathlib import Path

# 将项目根目录加入模块搜索路径，保证 `python project_04_memory_rag/09_rag_agent.py` 可直接运行
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# 导入 LangChain 的 @tool 装饰器，将普通函数声明为 LLM 工具
from langchain_core.tools import tool
# 导入 LangChain 的消息类
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage
# 导入 Chroma 向量存储组件
from langchain_chroma import Chroma
# 导入本地 Embedding 包装类（底层依赖 sentence-transformers）
from langchain_community.embeddings import HuggingFaceEmbeddings
# 导入单文件加载类 TextLoader
from langchain_community.document_loaders import TextLoader
# 导入递归文本分块器
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 导入公共模型工厂函数
from common.model_factory import create_model


# ============================================================
# 全局临时变量声明（用于在 @tool 内部访问检索器）
# ============================================================
# 初始化全局的 RAG 检索器对象
global_retriever = None


def prepare_agent_source_document(directory):
    """
    在本地临时生成一篇技术项目部署与规格文档，作为 Agent 的外部知识库数据源。

    功能：创建临时文件夹，并写入一份关于 'SuperApp 官方生产部署规范' 的 Markdown 文档。
    输入参数：
        directory (str): 目标存放文档的本地文件夹路径。
    输出返回值：
        str: 物理写入的 Markdown 文件完整路径。
    """
    # 检查目录是否存在，不存在则创建
    if os.path.exists(directory):
        # 存在则跳过
        pass
    else:
        # 级联创建
        os.makedirs(directory)

    # 拼接测试说明文档物理路径
    file_path = os.path.join(directory, "superapp_deploy.md")

    # 写入部署规范说明
    with open(file_path, "w", encoding="utf-8") as f:
        # 写入内容
        f.write(
            "# SuperApp 生产部署与硬件规格规范\n\n"
            "## 1. 端口配置硬性要求\n"
            "SuperApp 在生产环境中的核心 HTTP 服务接口必须占用 **8848** 端口，"
            "而后台监控管理控制台服务则必须绑定在 **9900** 端口，且这两个端口在防火墙策略中"
            "均需设置为对外放行状态。\n\n"
            "## 2. 硬件与内存容量要求\n"
            "为了保障线上服务的可用性与吞吐率，SuperApp 单机实例在运行时的物理内存（RAM）"
            "配置标准如下：\n"
            "- **最低配置要求**：单机物理内存不得低于 **16** GB。\n"
            "- **推荐黄金配置**：建议物理内存为 **32** GB，以获取最高效的并发响应。\n\n"
            "## 3. 数据库连接池要求\n"
            "对于数据库连接池的最大连接数限制，默认在集群配置文件中被硬性约束为最高 **200**。"
        )

    # 打印成功日志
    print(f"📄 成功生成 RAG Agent 测试源文件: {file_path}")
    # 返回文件的完整路径
    return file_path


# ============================================================
# 定义大模型可用的工具列表（使用 @tool 声明）
# ============================================================

@tool
def search_knowledge_base(query: str) -> str:
    """从个人知识库中检索与查询相关的信息。

    当用户询问关于 SuperApp 框架的硬件规格、内存要求、服务器端口配置或数据库连接池等
    私有文档中所含的特定技术指标与规范时，必须且优先调用该工具进行检索。

    Args:
        query: 用户的问题或提取的检索关键词。

    Returns:
        str: 从知识库中检索出的最相关文档片段拼接的参考信息。
    """
    # 检查全局检索器是否已成功初始化
    if global_retriever is None:
        # 如果为 None，提示未加载
        return "错误：本地知识库检索器尚未初始化完成。"
    else:
        # 否则正常运行
        pass

    print(f"\n   [工具执行] 正在从知识库中检索关于 '{query}' 的段落...")
    # 使用检索器在 Chroma 本地库中进行相似度检索，默认召回 2 条
    docs = global_retriever.invoke(query)

    # 如果检索结果为空列表，表明没有匹配到任何数据
    if not docs:
        # 返回未找到提示
        return "知识库中未找到相关部署规范说明信息。"
    else:
        # 否则开始格式化
        pass

    # 初始化结果文本列表
    results = []
    # 循环遍历匹配出来的每一个文档节点（坚决不用单行推导式）
    for i, doc in enumerate(docs):
        # 提取文件来源，没有则设为默认值
        source = doc.metadata.get("source", "未知来源")
        # 将来源和文本片段拼接
        formatted_chunk = f"[资料 {i + 1}] (来源: {os.path.basename(source)})\n{doc.page_content}"
        # 将格式化好的单条片段加入列表
        results.append(formatted_chunk)

    # 用两个换行符将检索结果数组连接为大字符串
    formatted_output = "\n\n".join(results)
    # 返回给大模型作为外部观察结果 (Observation)
    return formatted_output


@tool
def calculator(expression: str) -> str:
    """计算数学表达式的值。

    当用户提问中包含数学运算、公式计算、数值求和、翻倍乘法或减法等纯算术需求时，
    调用该工具来计算结果。

    Args:
        expression: 数学表达式，例如 "32 * 2" 或 "8848 + 100"。

    Returns:
        str: 计算出的数值答案。
    """
    print(f"\n   [工具执行] 正在利用计算器计算数学表达式: '{expression}'...")
    # 利用 Python 的 eval 进行数学计算（限定只计算基础表达式，防注入）
    try:
        # 移除非法字符，只保留数字和基本运算符，确保安全性
        allowed_chars = "0123456789+-*/.() "
        # 移除非数字/算符的字符，过滤表达式
        sanitized = ""
        for char in expression:
            if char in allowed_chars:
                sanitized += char
            else:
                pass
        # 评估并计算表达式的值
        result = eval(sanitized)
        # 将数字结果转为字符串形式返回
        return str(result)
    except Exception as e:
        # 捕捉可能出现的计算异常
        return f"数学表达式计算失败，原因: {str(e)}"


def run_agent_loop(model, tools_map, messages):
    """
    手写执行 Agent 的自主思考与工具调用循环。

    功能：传入绑定了工具的模型与消息历史，通过 while 循环驱动模型进行 Thought -> Action -> Observation 的思考闭环，直到模型无需调用工具。
    输入参数：
        model (BaseChatModel): 绑定了工具列表的大模型实例。
        tools_map (dict): 工具名称到具体 Python 函数对象的映射字典。
        messages (list): 包含对话历史的消息对象列表。
    输出返回值：
        str: 大模型最终整理并给出的中文回答文本。
    """
    # 限制最大调用循环次数，防止陷入死循环
    max_iterations = 5
    # 当前已执行的循环计数器
    iteration = 0

    # 启动思考循环
    while iteration < max_iterations:
        # 累加循环计数
        iteration += 1
        print(f"\n🤖 Agent 正在进行第 {iteration} 轮思考...")

        # 调用大模型，传入当前的对话历史
        response = model.invoke(messages)

        # 将大模型本轮返回的响应消息（可能是 Thought/Tool Call 或最终文字）追加到历史消息中
        messages.append(response)

        # 检查大模型本轮响应中是否包含工具调用指令（tool_calls）
        if response.tool_calls:
            # 如果有工具调用，打印调用状态
            print(f"👉 大模型决定调用工具，共 {len(response.tool_calls)} 个调用指令。")

            # 遍历这组工具调用指令进行解析与执行
            for tool_call in response.tool_calls:
                # 提取大模型建议的工具名称
                tool_name = tool_call["name"]
                # 提取大模型建议传入的参数字典
                tool_args = tool_call["args"]
                # 提取本次调用的唯一 ID
                tool_id = tool_call["id"]

                print(f"   🛠️ 准备调用工具: {tool_name} | 参数: {tool_args}")

                # 根据工具名称从映射字典中找到具体的 Python 函数
                if tool_name in tools_map:
                    # 获取函数实体
                    tool_func = tools_map[tool_name]
                    # 调用该函数，传入对应的字典参数
                    try:
                        # 运行工具，获取结果
                        observation = tool_func.invoke(tool_args)
                    except Exception as err:
                        # 捕捉调用崩溃错误
                        observation = f"工具执行异常: {str(err)}"
                else:
                    # 未注册工具
                    observation = f"未找到名为 '{tool_name}' 的注册工具。"

                print(f"   📥 工具执行结果 (Observation): '{observation[:80]}...'")

                # 将工具执行结果封装为 ToolMessage 消息对象，并绑定对应的 id
                tool_message = ToolMessage(
                    content=str(observation),
                    tool_call_id=tool_id
                )
                # 将工具消息加入全局历史中，使大模型能够在下一轮继续思考
                messages.append(tool_message)
        else:
            # 如果大模型本轮没有发出工具调用指令，说明它已经整理出了最终答案
            print("✨ 大模型认为任务已完成，无需继续调用工具。")
            # 提取大模型的文本回复内容
            final_content = response.content
            # 返回最终的回答文本
            return final_content

    # 如果达到最大循环次数依然没有结束，返回安全提示
    return "Agent 思考已达到最大迭代限制，未能给出最终答复。"


def main():
    """
    主运行函数。

    功能：准备本地 RAG 临时索引，配置全局检索器，注册多工具并初始化手写 Agent，进行单工具与混合跨工具复合任务演练，最后还原测试现场。
    """
    # 引入并修改全局检索器变量
    global global_retriever

    # 设定临时测试文件夹和 Chroma 持久化目录
    temp_docs_dir = "./temp_rag_agent_docs"
    temp_chroma_dir = "./temp_rag_agent_chroma"

    # 初始化重置清理旧环境
    if os.path.exists(temp_docs_dir):
        shutil.rmtree(temp_docs_dir)
    else:
        pass
    if os.path.exists(temp_chroma_dir):
        shutil.rmtree(temp_chroma_dir)
    else:
        pass

    # 1. 准备本地临时 RAG 检索器环境
    print("--- [RAG 向量库构建] 开始 ---")
    # 生成部署规格 Markdown 文档
    doc_path = prepare_agent_source_document(temp_docs_dir)
    # 加载文档
    loader = TextLoader(file_path=doc_path, encoding="utf-8")
    documents = loader.load()
    # 拆分分块
    splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=30)
    chunks = splitter.split_documents(documents)

    # 配置本地 Embedding 模型（无需 API Key），默认 BAAI/bge-small-zh-v1.5
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    # 存入本地库
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=temp_chroma_dir
    )
    # 初始化全局检索器（Top-2）
    global_retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    print("✅ RAG 向量数据库及全局检索器配置成功！")
    print("--- [RAG 向量库构建] 结束 ---\n")

    # 2. 组装多功能 Agent
    print("--- [Agent 混合编排调试] 开始 ---")
    # 创建底层大模型，使用统一的 create_model 工厂函数，默认走 xiaomi mimo
    base_model = create_model(provider="xiaomi mimo", temperature=0.0)

    # 组合模型可调用的全部工具
    agent_tools = [search_knowledge_base, calculator]

    # 将大模型与这组工具进行绑定
    # bind_tools 会在后台将工具的 JSON Schema 参数注入到大模型系统底层的 API 参数中
    bound_model = base_model.bind_tools(agent_tools)

    # 构建工具名称到实际函数的物理映射字典，以便在 Python while 循环中调用
    tools_map = {
        "search_knowledge_base": search_knowledge_base,
        "calculator": calculator
    }

    # ============================================================
    # 测试用例 1：复合式提问（需要同时触发 RAG 检索工具 与 计算器工具！）
    # ============================================================
    print("\n⚔️ 场景：复合型跨工具混合调度任务演练")
    complex_question = (
        "帮我查询一下项目部署手册中推荐的黄金内存配置是多少 GB？"
        "如果我计划部署 5 个完全相同的单机实例，请帮我计算一共推荐配备多少 GB 的总内存容量？"
    )
    print(f"❓ 提问内容: '{complex_question}'")

    # 初始化多轮对话的消息历史（包含系统提示与用户首问）
    messages = [
        SystemMessage(
            content=(
                "你是一个超级智能运维助手。你可以调用 search_knowledge_base 来查找关于 SuperApp 的"
                "部署规范，同时你也可以调用 calculator 来计算具体的数值。请结合两者给出最终精准回复。"
            )
        ),
        HumanMessage(content=complex_question)
    ]

    # 启动手写 while 循环 Agent
    final_reply = run_agent_loop(bound_model, tools_map, messages)

    print("\n==================================================")
    print("⭐ RAG Agent 混合编排最终精准回答:")
    print("==================================================")
    print(final_reply)
    print("==================================================")
    print("--- [Agent 混合编排调试] 结束 ---\n")

    # 3. 清理测试资源，收尾工作区
    print("🧹 正在清理本地 RAG 临时文件夹和向量库...")
    if os.path.exists(temp_docs_dir):
        shutil.rmtree(temp_docs_dir)
    else:
        pass
    if os.path.exists(temp_chroma_dir):
        shutil.rmtree(temp_chroma_dir)
    else:
        pass
    print("✨ RAG Agent 演示完成，测试环境已恢复。")


# 判断是否由命令行主程序启动
if __name__ == "__main__":
    # 执行主程序
    main()
