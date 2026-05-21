# -*- coding: utf-8 -*-
"""
Day 9 演示：文档加载器 (Document Loaders)。

功能：演示如何使用 LangChain 提供的 TextLoader 和 DirectoryLoader 读入单文本文件和批量目录文件。
输入参数：无（代码内部动态生成临时演示文档）。
输出返回值：在控制台打印加载出的 Document 对象及其元数据 (Metadata) 信息。
"""

# 导入操作系统底层模块，用于路径及目录创建
import os
# 导入文件系统删除模块，用于环境重置清理
import shutil
# 导入 LangChain 的单文本加载器
from langchain_community.document_loaders import TextLoader
# 导入 LangChain 的目录批量加载器
from langchain_community.document_loaders import DirectoryLoader


def prepare_sample_files(target_dir):
    """
    动态在本地磁盘中生成几个测试用的临时文档。

    功能：先创建指定的文件夹，然后在其中分别写入一个 TXT 文件和一个 MD Markdown 文件。
    输入参数：
        target_dir (str): 目标测试文件夹路径。
    输出返回值：
        None
    """
    # 检查目标文件夹是否存在，如果不存在则创建它
    if os.path.exists(target_dir):
        # 存在则跳过
        pass
    else:
        # 创建多级目录
        os.makedirs(target_dir)

    # 拼接测试 TXT 文件的绝对/相对路径
    txt_path = os.path.join(target_dir, "ai_agent_intro.txt")
    # 拼接测试 Markdown 文件的绝对/相对路径
    md_path = os.path.join(target_dir, "python_tips.md")

    # 写入测试 TXT 文件
    with open(txt_path, "w", encoding="utf-8") as txt_file:
        # 写入内容
        txt_file.write(
            "AI Agent 是指能够自主感知环境、做出决策并采取行动的智能实体系统。\n"
            "它不仅能调用大模型，还能使用计算器、搜索引擎等一系列外部工具。"
        )

    # 写入测试 Markdown 文件
    with open(md_path, "w", encoding="utf-8") as md_file:
        # 写入 Markdown 格式内容
        md_file.write(
            "# Python 最佳实践清单\n\n"
            "## 编写高质量 Python 代码\n"
            "- 每一个函数都必须写明 Docstring 注释说明输入输出参数。\n"
            "- 尽量不要使用过于生硬的三元运算符以增加可读性。\n"
            "- 遵循 PEP8 规范进行代码排版格式化。"
        )

    # 打印准备就绪的提示
    print(f"📁 已在磁盘成功生成测试临时目录: {target_dir}")
    print(f" 📄 生成测试文件: {os.path.basename(txt_path)}")
    print(f" 📄 生成测试文件: {os.path.basename(md_path)}")


def cleanup_directory(target_dir):
    """
    递归删除测试生成的临时文件和文件夹。

    功能：删除指定的文件夹及其子文件夹，保证临时文件不被留在学员的工作区中。
    输入参数：
        target_dir (str): 要清理的目标测试文件夹路径。
    输出返回值：
        None
    """
    # 检查目标文件夹是否存在
    if os.path.exists(target_dir):
        # 递归清理
        shutil.rmtree(target_dir)
        # 打印日志
        print(f"🧹 临时测试目录 {target_dir} 清理成功！")
    else:
        # 不存在则无须清理
        pass


def main():
    """
    主运行函数。

    功能：创建临时文件，使用 TextLoader 加载单文件，使用 DirectoryLoader 加载多文件，并分析打印元数据。
    """
    # 设定临时测试文件夹的名称
    temp_dir = "./temp_loader_docs"

    # 第一步：在本地准备测试用的多格式文件
    prepare_sample_files(temp_dir)

    print("\n1. 正在演示 TextLoader (加载单个 TXT 纯文本文件)...")
    # 构建指定 TXT 文件的路径
    txt_file_path = os.path.join(temp_dir, "ai_agent_intro.txt")
    # 初始化 TextLoader 加载器，并指定用 UTF-8 编码读取中文，避免乱码
    single_loader = TextLoader(file_path=txt_file_path, encoding="utf-8")
    # 调用 load 方法将文本内容解析成 Document 数组形式
    single_docs = single_loader.load()

    # 读取返回的第一个 Document 实例（单文件加载通常只返回一个 Document）
    doc = single_docs[0]
    # 打印加载成功后的提示信息
    print("✅ 单文件加载成功！")
    # 打印文本块的字符长度
    print(f"  文档内容长度: {len(doc.page_content)} 字符")
    # 打印文本块的前面部分内容
    print(f"  文档前部内容: '{doc.page_content}'")
    # 打印自动附带的元数据字典，TextLoader 默认元数据只包含 source (文件路径)
    print(f"  自动生成元数据: {doc.metadata}")

    print("\n2. 正在演示 DirectoryLoader (批量加载目录下特定格式的多文件)...")
    # 初始化 DirectoryLoader。
    # 它的工作原理是遍历指定目录，对符合 glob 规则的文件自动寻找合适的加载器（默认是 TextLoader）去处理。
    dir_loader = DirectoryLoader(
        path=temp_dir,  # 指定目标文件夹路径
        glob="*.*",  # 匹配该目录下的所有文件，也可以过滤比如 "*.md"
        loader_cls=TextLoader,  # 指定底层加载类为 TextLoader
        loader_kwargs={"encoding": "utf-8"}  # 传给 TextLoader 的编码参数，支持中文
    )
    # 调用 load 批量加载文件
    batch_docs = dir_loader.load()

    # 打印批量加载出文档的总个数
    print(f"✅ 批量加载成功！共检索并加载了 {len(batch_docs)} 个文件。")

    # 循环遍历每一个加载出的 Document 实例
    for i, loaded_doc in enumerate(batch_docs):
        # 提取当前文档的来源路径
        source = loaded_doc.metadata.get("source", "未知来源")
        # 提取文件名字作为输出信息
        filename = os.path.basename(source)
        # 打印各个文档的加载匹配信息
        print(f"  [文件 {i + 1}] 名称: {filename}")
        print(f"         第一行片段: '{loaded_doc.page_content.splitlines()[0]}'")
        print(f"         元数据详情: {loaded_doc.metadata}")

    # 第三步：清理生成的临时环境，保持工作区清爽
    print("\n3. 正在重置环境...")
    cleanup_directory(temp_dir)
    print("✨ 文档加载器演示程序圆满结束。")


# 判断是否由命令行直接启动
if __name__ == "__main__":
    # 执行主程序
    main()
