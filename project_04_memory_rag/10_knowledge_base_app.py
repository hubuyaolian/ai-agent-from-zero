# -*- coding: utf-8 -*-
"""
Day 10 综合实战项目：命令行个人知识库问答系统 (CLI Knowledge Base App)。

功能：提供一个交互式的命令行终端应用，支持单文件/多目录文档导入、文档物理删除、向量库状态统计，
      以及带有多轮对话记忆与引用来源追溯 (/source) 的检索增强生成 (RAG) 问答系统。
输入参数：交互式命令行输入。
输出返回值：控制台交互与回答渲染。
"""

# 导入操作系统相关模块，用于文件与路径操作
import os
# 导入文件系统删除模块
import shutil
# 导入 LangChain 基础消息类
from langchain_core.messages import HumanMessage, AIMessage
# 导入 Chroma 向量存储类
from langchain_chroma import Chroma
# 导入本地 Embedding 包装类（底层依赖 sentence-transformers）
from langchain_community.embeddings import HuggingFaceEmbeddings
# 导入单文件加载类 TextLoader
from langchain_community.document_loaders import TextLoader
# 导入递归文本分块器
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 导入模型创建工厂函数
from common.model_factory import create_model


# ============================================================
# 全局临时变量声明（用于记录系统运行状态）
# ============================================================
# 记录上一次问答时被召回的参考 Document 列表，用于 /source 查询
last_sources = []


def format_docs(docs):
    """
    将检索出的多个 Document 对象的文本内容拼接为一个完整的 Context 大字符串。

    功能：提取列表里的文本，并用双换行符连接它们（坚决不用单行推导式）。
    输入参数：
        docs (list[Document]): 检索出来的 Document 对象列表。
    输出返回值：
        str: 拼接后的参考文本。
    """
    # 初始化字符串列表，用于存放各个文档的文本内容
    formatted_texts = []
    # 遍历输入的每一个文档对象
    for doc in docs:
        # 将文档的文本内容追加到列表中
        formatted_texts.append(doc.page_content)
    # 用两个换行符将文本连接起来
    joined_text = "\n\n".join(formatted_texts)
    # 返回连接后的最终字符串
    return joined_text


def get_imported_docs(vectorstore):
    """
    从本地 ChromaDB 向量库中提取并过滤出所有已导入的文件名称。

    功能：通过 vectorstore.get() 获取库里所有文档的元数据，去重并过滤出已导入的文件名字。
    输入参数：
        vectorstore (Chroma): 本地 Chroma 向量库实例。
    输出返回值：
        list[str]: 包含所有已去重的导入文件名称列表。
    """
    # 尝试从向量库中获取所有记录的元数据列表
    db_data = vectorstore.get()
    # 提取其中的 metadatas 列表
    metadatas = db_data.get("metadatas", [])

    # 初始化一个集合，用于存储去重后的文件名
    unique_docs = set()
    # 遍历每一个元数据字典
    for meta in metadatas:
        # 如果元数据不为空且包含 source 属性
        if meta and "source" in meta:
            # 提取路径中的文件名
            file_name = os.path.basename(meta["source"])
            # 将文件名加入集合进行去重
            unique_docs.add(file_name)
        else:
            # 忽略空元数据或无 source 字段的记录
            pass

    # 将去重集合转化为排好序的列表形式
    sorted_docs = sorted(list(unique_docs))
    # 返回文件名列表
    return sorted_docs


def get_chunks_count(vectorstore):
    """
    统计当前向量数据库中已保存的文本块 (Chunks) 总数。

    功能：通过 vectorstore.get() 获取数据库里存储的所有记录 IDs 并计算其长度。
    输入参数：
        vectorstore (Chroma): 本地 Chroma 向量库实例。
    输出返回值：
        int: 数据库中已有的文本块总数量。
    """
    # 获取所有的记录
    db_data = vectorstore.get()
    # 提取其中的 ids 列表
    ids = db_data.get("ids", [])
    # 获取 ids 列表的长度
    count = len(ids)
    # 返回统计值
    return count


def delete_document_by_name(vectorstore, filename):
    """
    根据文件名从本地 ChromaDB 数据库中物理删除对应文档的所有文本块。

    功能：提取数据库中所有元数据，过滤出 source 与指定 filename 匹配的 IDs，然后执行删除。
    输入参数：
        vectorstore (Chroma): 本地 Chroma 向量库实例。
        filename (str): 要物理删除的文件名称。
    输出返回值：
        bool: 删除操作是否执行成功且有文本块被移除。
    """
    # 获取数据库里所有的 ids 和 metadatas
    db_data = vectorstore.get()
    ids = db_data.get("ids", [])
    metadatas = db_data.get("metadatas", [])

    # 初始化用于存储待删除 ID 的列表
    ids_to_delete = []
    # 遍历所有数据，寻找匹配的条目
    for i in range(len(ids)):
        # 获取第 i 条记录的元数据
        meta = metadatas[i]
        # 获取第 i 条记录的 ID
        record_id = ids[i]
        # 校验 source 是否存在并匹配
        if meta and "source" in meta:
            # 提取文件名
            meta_filename = os.path.basename(meta["source"])
            # 如果文件名与要删除的目标文件名一致
            if meta_filename == filename:
                # 将 ID 追加到删除列表
                ids_to_delete.append(record_id)
            else:
                pass
        else:
            pass

    # 如果存在待删除的 ID
    if ids_to_delete:
        # 调用向量库的物理删除接口进行移除
        vectorstore.delete(ids=ids_to_delete)
        # 返回 True 表示成功删除了文档
        return True
    else:
        # 否则返回 False
        return False


def import_directory(vectorstore, text_splitter, dir_path):
    """
    批量扫描并导入指定本地目录下的所有 TXT 和 MD 格式文档。

    功能：遍历文件夹，寻找以 .txt 或 .md 结尾的文件，分块并添加进 Chroma 向量库。
    输入参数：
        vectorstore (Chroma): 本地 Chroma 向量库实例。
        text_splitter (RecursiveCharacterTextSplitter): 文本分块器。
        dir_path (str): 物理目录路径。
    输出返回值：
        int: 成功导入并向量化的文件总个数。
    """
    # 检查指定的目录是否存在于磁盘上
    if not os.path.exists(dir_path):
        # 不存在则直接返回 0
        return 0
    else:
        pass

    # 扫描目录下所有的文件和文件夹名称
    all_files = os.listdir(dir_path)
    # 初始化导入成功的文件计数器
    success_count = 0

    # 遍历该目录下的每一个文件名
    for filename in all_files:
        # 拼接出该文件的完整路径
        file_path = os.path.join(dir_path, filename)
        # 过滤只处理文件，排除文件夹
        if os.path.isfile(file_path):
            # 将文件名转为小写以检查后缀
            lower_name = filename.lower()
            # 仅解析 txt 和 md 格式文件
            if lower_name.endswith(".txt") or lower_name.endswith(".md"):
                try:
                    # 使用 TextLoader 读入该文件
                    loader = TextLoader(file_path=file_path, encoding="utf-8")
                    # 加载文档内容
                    docs = loader.load()
                    # 进行切块分片
                    chunks = text_splitter.split_documents(docs)
                    # 一次性追加进向量库
                    vectorstore.add_documents(chunks)
                    # 计数累加
                    success_count += 1
                except Exception as err:
                    # 打印单文件导入异常日志
                    print(f"⚠️ 导入文件 '{filename}' 失败，原因: {str(err)}")
            else:
                pass
        else:
            pass

    # 返回导入成功的个数
    return success_count


def show_welcome():
    """
    显示个人知识库系统启动欢迎栏和 ASCII Art。
    """
    print("\n" + "=" * 52)
    print("      📚 个人专属知识库命令行智能问答系统 v1.0")
    print("=" * 52)
    print("系统指令清单:")
    print("  /import <文件路径>  : 导入单个 TXT 或 MD 手册文档")
    print("  /import_dir <目录>  : 批量扫描并导入目录下所有 TXT/MD 文档")
    print("  /list_docs         : 列出当前数据库中已导入的文件清单")
    print("  /delete_doc <名称>  : 从向量库中物理清除指定名称的文件")
    print("  /stats             : 查看当前知识库文档及切片块数统计")
    print("  /source            : 追溯上一次 AI 回答检索到的参考来源")
    print("  /clear             : 清空当前的多轮对话会话记忆")
    print("  /reset             : 彻底清空本地向量数据库")
    print("  /quit              : 退出知识库系统")
    print("=" * 52)
    print("💡 直接在控制台键入你想问的问题即可进行基于文档的检索问答。")
    print("=" * 52 + "\n")


def main():
    """
    主控制台 CLI 交互逻辑。

    功能：初始化持久化向量数据库与大模型，启动无限交互循环，解析斜杠系统指令或执行 RAG 多轮会话问答。
    """
    # 引用并编辑全局上次参考 Document 列表变量
    global last_sources

    # 定义本地持久化向量库的物理存储路径
    db_persist_dir = "./personal_knowledge_base"

    print("🔮 正在加载本地 Embedding 模块（首次运行会自动下载模型）...")
    # embedding 改走本地模型（无需 API Key），默认 BAAI/bge-small-zh-v1.5
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    # 初始化/载入本地持久化 Chroma 数据库
    vectorstore = Chroma(
        collection_name="personal_kb",
        embedding_function=embeddings,
        persist_directory=db_persist_dir
    )

    # 初始化大模型实例，使用统一的 create_model 工厂函数，默认走 xiaomi mimo
    chat_model = create_model(provider="xiaomi mimo", temperature=0.2)

    # 定义文本分块工具：chunk_size=400，重合度=50
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", " "]
    )

    # 初始化多轮对话记忆列表
    chat_history = []

    # 打印系统启动信息
    show_welcome()

    # 启动命令行死循环，等待用户指令输入
    while True:
        try:
            # 接收终端用户输入，并剔除前后首尾无用的空格
            user_input = input("[用户] >>> ").strip()
        except (KeyboardInterrupt, EOFError):
            # 用户强行终止或流结束时安全退出
            print("\n👋 感谢使用个人知识库系统，再见！")
            break

        # 如果输入内容为空，继续等待下一次输入
        if not user_input:
            continue
        else:
            pass

        # ---- 场景 1：解析斜杠开头的系统操作指令 ----
        if user_input.startswith("/"):
            # 将指令与可能的后续路径参数进行分离
            # maxsplit=1 表示仅以第一个空格分隔为两部分
            parts = user_input.split(" ", 1)
            # 提取第一个子项作为具体指令，并转为小写
            cmd = parts[0].lower()

            # 1. 退出系统
            if cmd == "/quit":
                print("👋 正在退出知识库问答系统，感谢使用！")
                break

            # 2. 清空多轮对话会话记忆
            elif cmd == "/clear":
                # 重置对话列表
                chat_history = []
                print("🧹 对话多轮会话历史已清空！")

            # 3. 统计状态
            elif cmd == "/stats":
                # 计算已导入的文件数
                doc_list = get_imported_docs(vectorstore)
                doc_num = len(doc_list)
                # 计算总切片 Chunks 数量
                chunks_num = get_chunks_count(vectorstore)
                # 打印统计报表
                print("📊 当前个人知识库统计:")
                print(f"   - 已加载文档总数: {doc_num} 个")
                print(f"   - 向量切片块总数: {chunks_num} 个块")
                print(f"   - 本地持久化路径: {db_persist_dir}")

            # 4. 列出文件清单
            elif cmd == "/list_docs":
                # 从向量库的元数据中去重提取出所有的文件名列表
                docs = get_imported_docs(vectorstore)
                # 如果文件列表为空
                if not docs:
                    print("📂 当前知识库空空如也，请先导入文档！")
                else:
                    print("📂 当前已导入知识库的文档清单:")
                    # 循环遍历打印
                    for idx, d_name in enumerate(docs):
                        print(f"  [{idx + 1}] {d_name}")

            # 5. 彻底清空重置库
            elif cmd == "/reset":
                # 双重确认
                confirm = input("⚠️ 此操作将清空本地全部向量数据库，确认继续？(y/n): ").strip().lower()
                if confirm == "y":
                    # 重置内存状态
                    chat_history = []
                    last_sources = []
                    # 清理物理存储文件夹
                    if os.path.exists(db_persist_dir):
                        shutil.rmtree(db_persist_dir)
                    else:
                        pass
                    # 重新创建/建立空的向量库实例
                    vectorstore = Chroma(
                        collection_name="personal_kb",
                        embedding_function=embeddings,
                        persist_directory=db_persist_dir
                    )
                    print("✅ 本地向量数据库已彻底清空并重置完成。")
                else:
                    print("❌ 操作已取消。")

            # 6. 单文件导入
            elif cmd == "/import":
                # 校验路径参数是否存在
                if len(parts) < 2:
                    print("❌ 参数错误！用法: /import <文件路径>")
                    continue
                else:
                    pass
                # 提取目标文件的相对/绝对路径
                target_file = parts[1]

                # 检查该文件是否在物理磁盘中真实存在
                if not os.path.exists(target_file):
                    print(f"❌ 导入失败！文件未找到: {target_file}")
                    continue
                else:
                    pass

                try:
                    # 使用 TextLoader 读入指定的文件
                    loader = TextLoader(file_path=target_file, encoding="utf-8")
                    loaded_docs = loader.load()
                    # 分块切片
                    chunks = text_splitter.split_documents(loaded_docs)
                    # 写入向量库
                    vectorstore.add_documents(chunks)
                    # 获取文件名
                    fname = os.path.basename(target_file)
                    print(f"✅ 成功导入文件: {fname} (共划分为 {len(chunks)} 个文本块)")
                except Exception as ex:
                    print(f"❌ 导入出错: {str(ex)}")

            # 7. 目录批量导入
            elif cmd == "/import_dir":
                # 校验路径参数是否存在
                if len(parts) < 2:
                    print("❌ 参数错误！用法: /import_dir <目录路径>")
                    continue
                else:
                    pass
                # 提取目标目录路径
                target_dir = parts[1]

                # 检查目标文件夹是否存在
                if not os.path.exists(target_dir):
                    print(f"❌ 导入失败！目录未找到: {target_dir}")
                    continue
                else:
                    pass

                print(f"📂 正在扫描目录 '{target_dir}' 下的 TXT 和 MD 文件...")
                # 调用目录导入函数进行级联插入
                imported_num = import_directory(vectorstore, text_splitter, target_dir)
                print(f"✅ 批量导入结束！成功向量化导入了 {imported_num} 个文档文件。")

            # 8. 物理删除文档
            elif cmd == "/delete_doc":
                # 校验文件名参数是否存在
                if len(parts) < 2:
                    print("❌ 参数错误！用法: /delete_doc <文档文件名>")
                    continue
                else:
                    pass
                # 提取待删除的文件基础名称
                target_fname = parts[1]

                # 调用物理删除匹配函数
                success = delete_document_by_name(vectorstore, target_fname)
                if success:
                    print(f"✅ 成功从向量库中物理清除了文档: '{target_fname}' 及其全部切片块。")
                else:
                    print(f"⚠️ 清除失败！未在数据库中找到名为 '{target_fname}' 的导入记录。")

            # 9. 追溯参考源
            elif cmd == "/source":
                # 检查上一次是否成功召回了参考段落
                if not last_sources:
                    print("📖 提示: 尚未进行提问检索，或上一次回答没有可用的参考来源。")
                else:
                    print("📖 上一次 AI 回答所检索到的参考来源明细:")
                    # 遍历打印参考文档片段
                    for index, source_doc in enumerate(last_sources):
                        # 获取文件来源
                        f_source = source_doc.metadata.get("source", "未知")
                        # 格式化输出
                        print(f"  [来源 {index + 1}] 文件名: {os.path.basename(f_source)}")
                        print(f"            参考片段: '{source_doc.page_content}'")
                        print("-" * 52)

            # 10. 未知指令提示
            else:
                print(f"❌ 未知指令: '{cmd}'。请输入正确的指令，直接提问可免加斜杠。")

        # ---- 场景 2：直接问答检索交互阶段 ----
        else:
            # 获取文本块总数，检查知识库是否已经有了基础数据
            total_chunks = get_chunks_count(vectorstore)
            if total_chunks == 0:
                # 给出友好提示
                print("🤖 🤖: 您好！当前本地知识库尚无任何文档，请先使用 /import 或 /import_dir 指令导入一些参考手册哦！")
                continue
            else:
                pass

            print("🤖 正在检索本地知识库并整理回答...")
            # 将向量库包装为标准的 Top-3 检索器
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            # 调用检索器，查找出最相关的 3 个文档节点
            matched_docs = retriever.invoke(user_input)

            # 更新全局的 last_sources 引用，以便用户追溯 /source
            last_sources = matched_docs

            # 提取 matched_docs 的文本内容，格式化为大字符串
            context_string = format_docs(matched_docs)

            # 准备定制的系统消息，注入当前的参考上下文资料
            system_message_content = (
                "你是一个贴心的个人知识库智能小助手。\n"
                "请严格基于以下参考资料来回答用户的问题。如果参考资料里没有提及相关内容，"
                "请说 '抱歉，根据我目前在个人知识库中检索到的参考资料，没有找到相关信息。'，不要瞎编。\n\n"
                "【重要参考资料如下】:\n"
                f"{context_string}\n\n"
                "请结合参考资料及之前的多轮对话历史，给用户以有条理、语气亲切的中文解答："
            )

            # 构建符合多轮对话的消息历史列表
            messages = [
                # 放入包含召回 Context 的系统消息
                HumanMessage(content=system_message_content)
            ]

            # 限制将历史消息（最近的 6 轮对话，即 3 对 Human-AI 消息）拼接进来以节省 tokens 上下文
            limit_history = chat_history[-6:]
            for hist_msg in limit_history:
                messages.append(hist_msg)

            # 将当前用户输入的消息追加进对话调用中
            messages.append(HumanMessage(content=user_input))

            try:
                # 调用大模型，传入组装好的全部多轮上下文与参考事实
                ai_response = chat_model.invoke(messages)

                print("\n[AI 助手] 🤖: ")
                print(ai_response.content)
                print("\n" + "-" * 52)

                # 将当前这一轮的 Human 输入和 AI 回答记录追加进全局会话记忆中
                chat_history.append(HumanMessage(content=user_input))
                chat_history.append(AIMessage(content=ai_response.content))

            except Exception as e_api:
                # 捕捉 API 调用崩溃
                print(f"❌ 大模型问答调用出错，原因: {str(e_api)}")


# 判断是否由命令行直接启动
if __name__ == "__main__":
    # 执行主程序交互
    main()
