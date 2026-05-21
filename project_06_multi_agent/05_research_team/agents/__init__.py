# -*- coding: utf-8 -*-
"""
AI 调研团队智能体模块初始化文件。

功能：对调研专家（Researcher）、分析专家（Analyst）以及写作专家（Writer）的
      核心运行函数进行统一包装与导出，提供模块化调用的统一命名空间。
输入参数：无。
输出返回值：对外暴露各个 Worker 节点可独立运行的业务函数。
"""

# 从独立的 researcher 模块导入核心调研运行函数
from .researcher import run_research
# 从独立的 analyst 模块导入核心分析提炼运行函数
from .analyst import run_analysis
# 从独立的 writer 模块导入核心写作润色运行函数
from .writer import run_writing

# 定义对外公开的接口列表，规范导出行为
__all__ = [
    "run_research",
    "run_analysis",
    "run_writing"
]
