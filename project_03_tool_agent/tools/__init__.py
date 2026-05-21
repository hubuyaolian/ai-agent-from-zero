"""
Day 6 - 工具集统一接口模块。

功能：导入并对外导出全部的内置 Agent 工具，并提供 ALL_TOOLS 统一绑定数组。
"""

# 从数学计算模块中导入计算工具
from tools.calculator import calculate
# 从网页检索模块中导入搜索工具
from tools.web_search import web_search
# 从文件模块中导入读文件工具
from tools.file_ops import read_file
# 从文件模块中导入写文件工具
from tools.file_ops import write_file
# 从文件模块中导入列文件夹工具
from tools.file_ops import list_directory
# 从系统模块中导入时间获取工具
from tools.system_info import get_system_time
# 从系统模块中导入环境信息获取工具
from tools.system_info import get_system_info
# 从代码执行模块中导入沙箱执行工具
from tools.code_executor import execute_python

# 定义导出的所有工具，统一绑定到大模型
ALL_TOOLS = [
    calculate,          # 数学计算工具
    web_search,         # 模拟网页搜索工具
    read_file,          # 读文件工具
    write_file,         # 写文件工具
    list_directory,     # 列出目录文件工具
    get_system_time,    # 系统当前时间获取工具
    get_system_info,    # 运行环境及操作系统信息工具
    execute_python,     # Python 受限沙箱代码运行工具
]

# 统一导出全部工具模块名称
__all__ = [
    "calculate",
    "web_search",
    "read_file",
    "write_file",
    "list_directory",
    "get_system_time",
    "get_system_info",
    "execute_python",
    "ALL_TOOLS",
]
