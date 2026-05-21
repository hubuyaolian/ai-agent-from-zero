"""
Day 6 - 工具集：Python 代码沙箱执行器。

功能：接收一段 Python 代码，在受限的环境中执行并返回控制台标准输出。
"""

# 导入输入输出重定向模块
import io
# 导入系统控制模块
import sys
# 导入 LangChain 的 tool 装饰器
from langchain_core.tools import tool


@tool
def execute_python(code: str) -> str:
    """
    在一个受限制的局部沙箱环境中安全运行 Python 代码，返回代码在标准输出（print）的内容。

    Args:
        code: 待执行的完整 Python 代码块，例如 'print(2 ** 10)'。

    Returns:
        代码输出的控制台字符串结果；如果执行出错或含有危险指令，则返回错误描述。
    """
    # 定义禁止调用的危险关键字列表，保障执行安全
    banned_keywords = [
        "import os",      # 禁止导入 os 模块
        "import sys",     # 禁止导入 sys 模块
        "subprocess",     # 禁止调用子进程模块
        "shutil",         # 禁止调用文件高级操作模块
        "open(",          # 禁止代码直接打开本地文件进行读写
        "eval(",          # 禁止嵌套动态求值
        "exec(",          # 禁止嵌套执行命令
        "__builtins__",   # 禁止访问底层内建指令集
    ]

    # 遍历黑名单关键字
    for key in banned_keywords:
        # 如果代码中包含了当前黑名单词汇
        if key in code:
            # 拒绝执行并返回安全性报错
            return f"安全限制：代码中包含受限制的危险关键字 '{key}'，执行被阻断。"

    # 创建 StringIO 对象用于捕获打印的输出
    captured_stdout = io.StringIO()
    # 暂存原本系统的标准输出通道
    old_stdout = sys.stdout

    # 创建沙箱执行命名空间字典，禁绝默认的 builtins 里的危险函数
    sandbox_globals = {
        "__builtins__": {
            "abs": abs,
            "all": all,
            "any": any,
            "bin": bin,
            "bool": bool,
            "dict": dict,
            "dir": dir,
            "divmod": divmod,
            "enumerate": enumerate,
            "float": float,
            "format": format,
            "hex": hex,
            "int": int,
            "isinstance": isinstance,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "oct": oct,
            "ord": ord,
            "pow": pow,
            "print": print,
            "range": range,
            "repr": repr,
            "reversed": reversed,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "type": type,
            "zip": zip,
        }
    }

    try:
        # 将系统的标准输出重定向到自定义的捕获管道中
        sys.stdout = captured_stdout
        # 在受限的命名空间中安全执行 Python 代码
        exec(code, sandbox_globals)
        # 将输出管道还原为系统的标准输出
        sys.stdout = old_stdout
        # 从捕获管道中提取所有 print 的内容
        output_str = captured_stdout.getvalue()
        # 返回获取的输出内容
        return output_str
    # 捕获执行过程中的任何语法或运行时异常
    except Exception as e:
        # 还原系统标准输出
        sys.stdout = old_stdout
        # 返回执行异常的提示信息
        return f"运行错误：{e}"
