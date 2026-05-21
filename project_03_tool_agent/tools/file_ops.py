"""
Day 6 - 工具集：文件操作工具。

功能：提供读文件、写文件和列出目录内容的功能，包含安全沙箱路径防越权限制。
"""

# 导入系统路径库
import os
# 导入 LangChain 的 tool 装饰器
from langchain_core.tools import tool

# 定义允许操作的安全工作根目录
SAFE_ROOT = "/Users/huangyang/code/agent"


def is_safe_path(filepath):
    """
    检查文件路径是否属于安全工作根目录，防止跨目录遍历越权漏洞。

    输入参数：
        filepath (str): 待检测的相对或绝对路径。
    输出返回值：
        tuple: (是否安全布尔值, 绝对路径字符串)。
    """
    # 转换为绝对路径
    abs_path = os.path.abspath(filepath)
    # 获取安全工作目录的绝对路径
    abs_safe_root = os.path.abspath(SAFE_ROOT)
    # 判断 abs_path 是否是以 abs_safe_root 开头
    if abs_path.startswith(abs_safe_root):
        # 属于工作目录范围，返回安全和绝对路径
        return True, abs_path
    # 越权操作，返回不安全及空
    else:
        # 返回失败
        return False, ""


@tool
def read_file(filepath: str) -> str:
    """
    读取工作目录范围内的指定文本文件的内容。

    Args:
        filepath: 文件路径，如 'test.txt' 或 'project_03_tool_agent/notes.txt'。

    Returns:
        文件的全部文本内容；如果读取失败，则返回以 '错误：' 开头的提示信息。
    """
    # 检测路径安全性
    is_safe, abs_path = is_safe_path(filepath)
    # 如果判断为不安全
    if not is_safe:
        # 返回安全防范越权错误提示
        return f"错误：拒绝访问！路径 '{filepath}' 超出了安全目录范围。"

    # 判断文件在本地是否存在且它是一个普通文件
    if not os.path.isfile(abs_path):
        # 返回文件不存在提示
        return f"错误：文件 '{filepath}' 不存在或不是一个标准的文件。"

    try:
        # 打开文件以只读 UTF-8 方式读取
        with open(abs_path, 'r', encoding='utf-8') as f:
            # 读取全部文件内容
            content = f.read()
        # 返回文件内容
        return content
    # 捕捉其它文件异常
    except Exception as e:
        # 返回错误信息
        return f"错误：读取文件时发生异常: {e}"


@tool
def write_file(filepath: str, content: str) -> str:
    """
    向工作目录范围内的文本文件写入内容（会直接覆盖旧内容，如果不存在则自动创建文件）。

    Args:
        filepath: 目标文件路径，例如 'output.txt'。
        content: 准备写入文件的字符串内容。

    Returns:
        写入成功或失败的提示性字符串。
    """
    # 校验路径安全
    is_safe, abs_path = is_safe_path(filepath)
    # 安全检查不通过
    if not is_safe:
        # 返回防越权提示
        return f"错误：拒绝写入！路径 '{filepath}' 超出了安全目录范围。"

    try:
        # 确保文件的父级目录都已创建存在
        parent_dir = os.path.dirname(abs_path)
        # 如果父级文件夹不存在
        if not os.path.exists(parent_dir):
            # 自动递归创建该父级文件夹
            os.makedirs(parent_dir, exist_ok=True)

        # 以覆盖写入模式打开该文件
        with open(abs_path, 'w', encoding='utf-8') as f:
            # 写入传入的文本内容
            f.write(content)
        # 返回操作成功提示
        return f"成功：内容已成功写入到文件 '{filepath}' 中。"
    # 捕获任何异常
    except Exception as e:
        # 返回写入失败异常提示
        return f"错误：向文件写入内容时发生异常: {e}"


@tool
def list_directory(dir_path: str = ".") -> str:
    """
    列出工作目录范围内指定文件夹的内容列表。

    Args:
        dir_path: 目标文件夹相对路径，默认值为 '.' 代表当前工作根目录。

    Returns:
        文件夹下所有子文件和子文件夹的名称列表（换行符拼接）；失败则返回错误提示。
    """
    # 验证目标文件夹安全性
    is_safe, abs_path = is_safe_path(dir_path)
    # 安全检验不通过
    if not is_safe:
        # 返回安全错误提示
        return f"错误：拒绝访问！路径 '{dir_path}' 超出了安全目录范围。"

    # 验证是否为合法文件夹
    if not os.path.isdir(abs_path):
        # 返回不存在提示
        return f"错误：文件夹 '{dir_path}' 不存在或不是一个标准的文件夹。"

    try:
        # 获取该文件夹下所有的条目名称列表
        items = os.listdir(abs_path)
        # 如果文件夹是空的
        if len(items) == 0:
            # 返回空目录说明
            return f"文件夹 '{dir_path}' 内容为空。"
        # 使用换行符将所有的条目拼接
        items_str = "\n".join(items)
        # 返回列表
        return items_str
    # 捕捉报错
    except Exception as e:
        # 返回错误说明
        return f"错误：列出文件夹内容时发生异常: {e}"
