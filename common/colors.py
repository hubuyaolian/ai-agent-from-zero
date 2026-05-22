"""
终端 ANSI 颜色常量定义。

功能：统一管理终端输出中使用的 ANSI 转义序列颜色码，避免在各课程脚本中重复定义。
使用方式：from common.colors import COLOR_RESET, COLOR_GREEN, ...
"""

COLOR_RESET = "\033[0m"      # 重置样式
COLOR_GREEN = "\033[32m"     # 绿色表示用户输入
COLOR_BLUE = "\033[34m"      # 蓝色表示 AI 回复
COLOR_CYAN = "\033[36m"      # 青色表示系统状态
COLOR_YELLOW = "\033[33m"    # 黄色表示工具执行/警告
COLOR_RED = "\033[31m"       # 红色表示错误/敏感操作
