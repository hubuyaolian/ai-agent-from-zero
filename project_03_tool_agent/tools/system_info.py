"""
Day 6 - 工具集：系统信息查询工具。

功能：获取当前的系统时间、操作系统类别及 Python 运行时版本。
"""

# 导入时间日期库
import datetime
# 导入系统信息提取库
import platform
# 导入系统模块
import sys
# 导入 LangChain 的 tool 装饰器
from langchain_core.tools import tool


@tool
def get_system_time() -> str:
    """
    获取当前主机的系统时间。

    Returns:
        包含当前系统时间的格式化字符串，如 '2026-05-20 12:30:45'。
    """
    # 取得本地当前的日期与时间
    now = datetime.datetime.now()
    # 将时间对象转化为年-月-日 时:分:秒的格式
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
    # 返回格式化结果
    return f"当前系统时间为: {formatted_time}"


@tool
def get_system_info() -> str:
    """
    获取当前运行环境的操作系统类别、硬件平台和 Python 运行版本信息。

    Returns:
        包含 OS 名称、架构和 Python 版本详细信息的描述文本。
    """
    # 提取操作系统名称（如 Windows, Darwin, Linux）
    os_name = platform.system()
    # 提取硬件架构（如 x86_64, arm64）
    machine = platform.machine()
    # 提取 Python 的主次版本号
    py_version = sys.version.split()[0]

    # 将提取的信息合并格式化
    info_str = (
        f"操作系统: {os_name}\n"
        f"硬件架构: {machine}\n"
        f"Python版本: {py_version}"
    )
    # 返回合并的描述字符串
    return info_str
