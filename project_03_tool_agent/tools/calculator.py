"""
Day 6 - 工具集：安全计算器工具。

功能：对数学表达式进行求值，提供精确数学计算结果，防止大模型算错。
输入参数：数学表达式字符串。
输出返回值：计算结果字符串。
"""

# 导入安全评估模块
import ast
# 导入运算符字典
import operator
# 导入 LangChain 的 tool 装饰器
from langchain_core.tools import tool

# 预定义支持的安全数学二元运算符
SUPPORTED_OPERATORS = {
    ast.Add: operator.add,        # 加法
    ast.Sub: operator.sub,        # 减法
    ast.Mult: operator.mul,       # 乘法
    ast.Div: operator.truediv,    # 除法
    ast.Pow: operator.pow,        # 幂运算
    ast.USub: operator.neg,       # 一元负号
}


def safe_eval_node(node):
    """
    递归对抽象语法树 AST 节点进行安全求值计算。

    输入参数：
        node: AST 语法树节点。
    输出返回值：
        float/int: 数值结果。
    """
    # 如果是数值常量节点
    if isinstance(node, ast.Constant):
        # 直接返回常数值
        return node.value
    # 如果是二元运算符节点
    elif isinstance(node, ast.BinOp):
        # 递归求左子树的值
        left = safe_eval_node(node.left)
        # 递归求右子树的值
        right = safe_eval_node(node.right)
        # 取得运算符的类型
        op_type = type(node.op)
        # 确认该运算符是否在支持的运算符列表中
        if op_type in SUPPORTED_OPERATORS:
            # 执行对应运算并返回结果
            return SUPPORTED_OPERATORS[op_type](left, right)
        # 不支持该运算符的情形
        else:
            # 抛出未实现异常
            raise NotImplementedError(f"不支持的运算符: {op_type}")
    # 如果是一元运算符节点（如负数）
    elif isinstance(node, ast.UnaryOp):
        # 递归求操作数的值
        operand = safe_eval_node(node.operand)
        # 取得一元运算符类型
        op_type = type(node.op)
        # 确认该一元运算符是否被支持
        if op_type in SUPPORTED_OPERATORS:
            # 执行对应的一元运算并返回
            return SUPPORTED_OPERATORS[op_type](operand)
        # 不支持该运算符的情形
        else:
            # 抛出异常
            raise NotImplementedError(f"不支持的一元运算符: {op_type}")
    # 遇到任何其他类型非法节点
    else:
        # 抛出语法异常
        raise TypeError(f"不支持的安全计算表达式元素: {node}")


@tool
def calculate(expression: str) -> str:
    """
    对一个包含加、减、乘、除、乘方（**）的数学表达式进行安全计算，返回精确结果。

    Args:
        expression: 待计算的数学表达式字符串，例如 '123 * 456'、'(2 + 3) * 5'、'2 ** 10'。

    Returns:
        计算出来的数值结果字符串；若格式错误或运算异常，则返回对应错误描述。
    """
    try:
        # 去除表达式两端的空白字符
        clean_expr = expression.strip()
        # 将表达式解析为 AST 抽象语法树
        tree = ast.parse(clean_expr, mode='eval')
        # 递归遍历语法树求出表达式的值
        val = safe_eval_node(tree.body)
        # 将计算出的数值转化为字符串返回
        return str(val)
    # 捕获除以零的错误
    except ZeroDivisionError:
        # 返回被零除的错误提示
        return "计算错误：不能除以零！"
    # 捕获其他任何异常
    except Exception as e:
        # 返回运算失败异常描述
        return f"计算错误：{e}"
