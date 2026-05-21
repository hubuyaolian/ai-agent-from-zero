# -*- coding: utf-8 -*-
"""
Day 16 模块：AI 调研团队 — 协作流水线工作流定义 (Workflow Pattern) 🏗️

功能：构建基于 LangGraph 状态图的 AI 调研团队 V1 基础版（纯线性流水线）。
      定义共享状态（ResearchTeamState），组装并导出三个核心 Agent 的节点函数。
      引入 @agent_logger 日志计时装饰器，对每个阶段的执行耗时与字数指标进行无侵入式监控，增强系统可观测性。
      有向图流转顺序：researcher 节点 -> analyst 节点 -> writer 节点 -> END。
输入参数：无。
输出返回值：编译完成的 CompiledGraph 工作流应用。
"""

# 导入计时器模块
import time
# 导入操作符，用于状态字段的追加累加操作
import operator
# 导入保留函数签名的 wraps 装饰器
from functools import wraps
# 导入 TypedDict 状态结构、序列和累加类型
from typing import TypedDict, Annotated, Sequence

# 导入 LangChain 核心消息及消息追加算子
from langchain_core.messages import BaseMessage, AIMessage
# 导入 LangGraph 核心图结构与结束标识
from langgraph.graph import StateGraph, END

# 从本地 agents 模块中导入三个智能体核心运行函数
from agents.researcher import run_research
from agents.analyst import run_analysis
from agents.writer import run_writing


# ============================================================
# 1. 定义 AI 调研团队共享全局状态 (V1 State Schema)
# ============================================================

class ResearchTeamState(TypedDict):
    """
    AI 调研团队 V1 基础版共享全局状态结构。

    功能：在线性接力工作流中共享数据，记录当前状态与中间产出。
    字段说明：
        messages: 完整的对话消息历史，支持通过 operator.add 自动追加合并。
        topic: 被调研的中心技术方向主题。
        research_data: 调研专家节点（Researcher）搜集整理的事实数据文本。
        analysis_result: 分析专家节点（Analyst）提炼的深度洞察与趋势文本。
        final_report: 写作专家节点（Writer）最终整合润色的 Markdown 技术报告文本。
        status: 记录工作流当前的流转执行状态标记。
    """
    # 消息列表，声明为 operator.add 代表每次返回新消息都会自动追加，不会覆盖旧消息
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # 需要调研和研究的中心主题名称
    topic: str
    # 保存第一步调研专家的产出事实
    research_data: str
    # 保存第二步分析专家的深度分析洞察
    analysis_result: str
    # 保存第三步写作专家的最终整合 Markdown 报告
    final_report: str
    # 保存工作流运行状态标识字
    status: str


# ============================================================
# 2. 定义可观测性装饰器 (Decorator for Logging & Timing)
# ============================================================

def agent_logger(agent_name: str):
    """
    Agent 可观测性日志及计时装饰器（不修改原有节点函数逻辑）。

    功能：为节点函数在被调用时自动添加计时、分割线打印、耗时统计与字数输出统计功能。
    输入参数：
        agent_name (str): 用于控制台友好显示的智能体节点中文名称。
    输出返回值：
        function: 装饰后的包裹节点函数。
    """
    def decorator(func):
        # 保持原始函数的元数据（如 docstring 和函数名）不丢失
        @wraps(func)
        def wrapper(state):
            # 记录执行开始的时间戳
            start_time = time.time()
            print(f"\n{'=' * 60}")
            print(f"🚀 [{agent_name}] 开始触发执行...")
            print(f"{'=' * 60}")

            # 调用原始的物理节点函数，传入当前状态
            result = func(state)

            # 计算执行总共消耗的时间
            elapsed_time = time.time() - start_time

            # 声明检测到的文本字数长度
            output_len = 0
            # 遍历节点函数返回的字典状态增量
            for key, val in result.items():
                # 排除非文本字段 messages 和 status
                if key not in ("messages", "status"):
                    # 检查该字段值是否为文本字符串
                    if isinstance(val, str):
                        # 获取该文本的字符总数
                        output_len = len(val)
                        # 跳出循环
                        break

            # 打印该节点完成执行的统计指标
            print(f"\n✅ [{agent_name}] 执行完毕！")
            print(f"   ⏱️ 执行耗时: {elapsed_time:.2f} 秒")
            print(f"   📝 生成字数: {output_len} 字")
            print(f"{'=' * 60}")

            # 返回节点函数的结果
            return result
        # 返回闭包封装函数
        return wrapper
    # 返回二级装饰器
    return decorator


# ============================================================
# 3. 编写 LangGraph 节点函数逻辑 (Nodes)
# ============================================================

@agent_logger("🔍 调研智能体")
def research_node(state: ResearchTeamState) -> dict:
    """
    调研专家节点函数。

    功能：从状态中读取 topic 字段，调用底层 run_research，然后写入 research_data 并向状态追加 AIMessage。
    输入参数：
        state (ResearchTeamState): 共享全局状态字典。
    输出返回值：
        dict: 更新研究数据、工作历史消息及当前状态标识。
    """
    # 提取要研究的核心话题
    topic = state["topic"]
    # 触发客观事实搜集函数
    research_result = run_research(topic)
    # 返回状态更新增量
    return {
        # 追加一条完成调研的 AI 提示消息
        "messages": [AIMessage(
            content=f"[调研结果已成功归档] 字数：{len(research_result)}",
            name="researcher"
        )],
        # 写入调研结果字段
        "research_data": research_result,
        # 更新状态字
        "status": "research_completed"
    }


@agent_logger("📊 分析智能体")
def analysis_node(state: ResearchTeamState) -> dict:
    """
    分析专家节点函数。

    功能：从状态中提取上游 researcher 节点留下的 research_data 原始数据，调用底层 run_analysis，
          然后写入 analysis_result 并向状态追加 AIMessage。
    输入参数：
        state (ResearchTeamState): 共享全局状态字典。
    输出返回值：
        dict: 更新分析洞察结果、工作历史消息及当前状态标识。
    """
    # 提取核心话题
    topic = state["topic"]
    # 提取上游已经完成的调研原始数据 facts
    research_data = state["research_data"]
    # 触发分析专家提炼高含金量洞察点
    analysis_result = run_analysis(topic, research_data)
    # 返回状态更新增量
    return {
        # 追加一条完成深度分析的 AI 提示消息
        "messages": [AIMessage(
            content=f"[分析提炼已成功归档] 字数：{len(analysis_result)}",
            name="analyst"
        )],
        # 写入分析洞察结果字段
        "analysis_result": analysis_result,
        # 更新状态字
        "status": "analysis_completed"
    }


@agent_logger("✍️ 写作智能体")
def writing_node(state: ResearchTeamState) -> dict:
    """
    写作专家节点函数。

    功能：从状态中分别读取 research_data 与 analysis_result，调用底层 run_writing，
          然后写入 final_report 并向状态追加 AIMessage。
    输入参数：
        state (ResearchTeamState): 共享全局状态字典。
    输出返回值：
        dict: 更新最终研究报告、工作历史消息及当前状态标识。
    """
    # 提取核心话题
    topic = state["topic"]
    # 提取调研数据素材
    research_data = state["research_data"]
    # 提取分析深度洞察
    analysis_result = state["analysis_result"]
    # 触发写作主编高度整合撰写出排版完美的 Markdown 报告
    final_report = run_writing(topic, research_data, analysis_result)
    # 返回状态更新增量
    return {
        # 追加一条完成润色写作的 AI 提示消息
        "messages": [AIMessage(
            content="[最终研究报告编排已成功收官]",
            name="writer"
        )],
        # 写入最终研究报告字段
        "final_report": final_report,
        # 更新状态字
        "status": "report_completed"
    }


# ============================================================
# 4. 构建并编译工作流图 (Graph Construction)
# ============================================================

def build_research_team_workflow():
    """
    构建并编译 AI 调研团队基础 V1 版的有向状态图。

    功能：注册三大 Worker 节点，以 researcher -> analyst -> writer -> END 的固定顺序线性组装并编译。
    输入参数：
        无。
    输出返回值：
        CompiledGraph: 编译完成后可直接调用的工作流运行时对象。
    """
    # 基于 ResearchTeamState 结构体声明状态图
    workflow = StateGraph(ResearchTeamState)

    # 注册三大核心处理节点
    # 注册调研节点
    workflow.add_node("researcher", research_node)
    # 注册分析节点
    workflow.add_node("analyst", analysis_node)
    # 注册写作节点
    workflow.add_node("writer", writing_node)

    # 设定工作流的唯一起始执行点为 researcher 节点
    workflow.set_entry_point("researcher")

    # 连接物理有向边，构筑纯线性接力协作流
    # 第一步：调研完毕后流向分析节点
    workflow.add_edge("researcher", "analyst")
    # 第二步：分析完毕后流向写作节点进行润色整编
    workflow.add_edge("analyst", "writer")
    # 第三步：写作完毕后流向终点 END 标志收尾
    workflow.add_edge("writer", END)

    # 编译有向状态图，完成构建并返回
    return workflow.compile()


# ============================================================
# 5. 本地运行测试自检入口
# ============================================================

if __name__ == "__main__":
    # 定义测试话题
    test_topic = "边缘计算（Edge Computing）在智能电网中的典型应用场景与网络安全挑战"
    print("🛠️ 正在本地测试编译 V1 基础版工作流...")
    # 编译工作流
    app = build_research_team_workflow()
    print("✅ 工作流图机编译成功，开始模拟跑通...")
    # 传入初始状态
    final_output = app.invoke({
        "messages": [AIMessage(content="测试流程触发")],
        "topic": test_topic,
        "research_data": "",
        "analysis_result": "",
        "final_report": "",
        "status": "started"
    })
    print("\n⭐ 最终报告产出预览:")
    print("-" * 70)
    print(final_output["final_report"][:200] + "\n...")
    print("-" * 70)
    print("✨ V1 工作流本地编译与模拟调用完美通过！")
