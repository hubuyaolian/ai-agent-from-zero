# -*- coding: utf-8 -*-
"""
Day 15 演示：多 Agent 协作架构 — 主管模式 (Supervisor Pattern) 👨‍💼

功能：使用 LangGraph 状态机搭建一个由主管智能体（Supervisor）统一调度、
      三大专业智能体（Researcher 调研、Coder 编码、Writer 写作）协同执行的任务分配系统。
      - 主管节点 (Supervisor)：根据用户的初始请求以及已完成的工作，使用大模型决策下一个工作的 Worker 节点，或者决定“FINISH”结束。
      - 调研节点 (Researcher)：负责整理和搜索话题的核心技术特点与对比信息。
      - 编码节点 (Coder)：负责针对特定技术栈编写可运行的经典示例代码。
      - 写作节点 (Writer)：负责将调研的文字和代码，排版撰写为排版精美的 Markdown 报告。
      生动演示在多 Agent 系统中，如何通过大模型作为中枢决策层，动态路由与组装复杂的协作流程。
输入参数：无。
输出返回值：控制台打印整个路由决策链路、各 Worker 的协作日志以及最终的完美技术报告。
"""

# 导入正则表达式库用于提取决策标签
import re
# 导入系统路径模块，用于支持从任意位置直接运行本脚本
import sys
# 导入路径处理工具，用于定位项目根目录
from pathlib import Path
# 导入 TypedDict 用于声明图共享的状态
from typing import TypedDict, List

# 将项目根目录加入模块搜索路径，保证 `python project_06_multi_agent/03_supervisor_pattern.py` 可直接运行
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# 导入 LangChain 的底层消息消息模型
from langchain_core.messages import SystemMessage, HumanMessage
# 导入 LangGraph 状态图定义及终点 END
from langgraph.graph import StateGraph, END

# 从全局通用模型工厂中导入大模型实例化函数
from common.model_factory import create_model


# ============================================================
# 1. 定义多 Agent 共享的全局图状态 (State Schema)
# ============================================================

class MultiAgentState(TypedDict):
    """
    主管模式下的共享全局状态结构。

    功能：提供给 Supervisor 与各 Worker 读取、改写的数据载体。
    字段说明：
        request: 用户的原始输入任务请求。
        completed_work: 已完成工作的文本记录列表，供 Supervisor 跟踪。
        next_agent: 主管决策的下一个执行者（researcher/coder/writer/FINISH）。
        research_result: 调研智能体输出的技术对比和原始素材。
        coder_result: 编码智能体生成的示例代码文字。
        writer_result: 写作智能体撰写的最终整合版 Markdown 报告。
    """
    # 记录用户的原始请求文本
    request: str
    # 记录已完成动作的简要历史列表
    completed_work: List[str]
    # 记录主管决策的下一个路由目标
    next_agent: str
    # 保存调研工人的中间产出
    research_result: str
    # 保存编码工人的中间产出
    coder_result: str
    # 保存写作工人的最终产出
    writer_result: str


# ============================================================
# 2. 定义 Supervisor（主管）节点的决策逻辑
# ============================================================

def supervisor_node(state: MultiAgentState):
    """
    主管决策节点 (supervisor_node)。

    功能：分析用户初始请求与已完成的工作历史，通过大模型推理并输出下一个分发的 Worker 节点。
    输入参数：
        state (MultiAgentState): 共享全局状态字典。
    输出返回值:
        dict: 更新 next_agent 路由标识。
    """
    # 打印提示，标志进入主管节点
    print("\n👨‍💼 [Node: Supervisor] 主管正在审阅任务状态并规划下一步分发...")

    # 从公共工厂实例化决策模型（教学阶段 04 之后默认 LLM 走 xiaomi mimo），0.0 温度确保指令遵循稳定性
    model = create_model(provider="xiaomi mimo", temperature=0.0)

    # 提取已完成的工作历史并拼接成可读字符串
    work_history_str = "\n".join(state["completed_work"])
    # 如果已完成历史为空，给出默认占位说明
    if not work_history_str:
        # 赋予无历史说明
        work_history_str = "无"

    # 构建专门发给主管大模型的系统 Prompt
    system_prompt = (
        "你是一个极其聪慧的团队主管（Supervisor Agent）。\n"
        "你手下有三个专业的工人智能体：\n"
        "1. researcher: 负责信息搜索、资料收集以及竞品/技术对比。\n"
        "2. coder: 负责根据调研背景编写和调试规范、高质量的示例代码。\n"
        "3. writer: 负责收集调研结果和示例代码，进行高度整合并输出精美的 Markdown 报告。\n\n"
        "你的职责是：\n"
        "根据用户的【初始请求】以及已经【已完成的工作】，合理决定下一步应该由哪一个工人处理。\n"
        "你需要保持极高的条理性和科学性，如果全部工作均已完成，请做出 'FINISH' 决策。\n\n"
        "注意必须满足的路由前置逻辑条件：\n"
        "- 必须首先进行 'researcher' 调研，因为没有调研材料，后面的编码和写作都无法展开！\n"
        "- 在 'researcher' 完成调研后，如果用户请求中包含了编写代码的要求，必须分配给 'coder' 编写代码。\n"
        "- 在调研和编码都完成后，最终必须分配给 'writer' 进行报告的润色和最终整合撰写。\n"
        "- 只有当 writer 已经生成了最终整合的 Markdown 报告，你才能做出 'FINISH' 决策。\n\n"
        "【输出格式规范】\n"
        "你必须且只能在输出的最后，把你的路由决策放在 <decision> 标签中，例如：\n"
        "<decision>researcher</decision> 或 <decision>coder</decision> 或 "
        "<decision>writer</decision> 或 <decision>FINISH</decision>\n"
        "不要包含任何标点符号在大标签内。请只选择这四者之一！"
    )

    # 构建传递给主管的用户上下文 Prompt
    user_prompt = (
        f"【初始请求】: {state['request']}\n"
        f"【当前已完成的工作】: \n{work_history_str}\n\n"
        "请决策下一步分配给谁："
    )

    # 合并为 LangChain 格式消息列表
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    # 调用大模型生成决策响应
    response = model.invoke(messages)
    # 获取输出的纯文本内容
    content = response.content.strip()

    # 打印主管的思考过程摘要
    print("👨‍💼 [Node: Supervisor] 主管思考分析完毕。")

    # 使用正则表达式匹配标签中的决策词
    match = re.search(r"<decision>(.*?)</decision>", content)
    # 判断是否成功匹配到标签
    if match:
        # 提取匹配到的决策词并去除两侧空格
        decision = match.group(1).strip()
    else:
        # 如果未匹配到，则回退到安全判断逻辑
        decision = "FINISH"
        # 判断如果调研结果未输出，回退分配给 researcher
        if not state.get("research_result"):
            # 标记为 researcher
            decision = "researcher"
        # 判断如果代码未输出且用户需要，回退分配给 coder
        elif "代码" in state["request"] and not state.get("coder_result"):
            # 标记为 coder
            decision = "coder"
        # 判断如果写作未输出，回退分配给 writer
        elif not state.get("writer_result"):
            # 标记为 writer
            decision = "writer"

    # 限制决策只能在合法集合内，若不合法则默认设为 FINISH
    valid_decisions = ["researcher", "coder", "writer", "FINISH"]
    # 检查提取到的决策是否在合法范围中
    if decision not in valid_decisions:
        # 回退至安全值
        decision = "FINISH"

    print(f"🎯 [Node: Supervisor] 决定分派给: -> 【{decision}】")

    # 返回状态更新，写入 next_agent
    return {
        "next_agent": decision
    }


# ============================================================
# 3. 定义各 Workers（工人）节点的执行逻辑
# ============================================================

def researcher_node(state: MultiAgentState):
    """
    调研工人节点 (researcher_node)。

    功能：提取用户的初始任务请求，调用大模型充当专业的调研员，输出详细的技术调研和竞品对比素材。
    输入参数：
        state (MultiAgentState): 共享全局状态字典。
    输出返回值:
        dict: 更新 research_result 和 completed_work 历史。
    """
    print("\n🔍 [Node: Researcher] 调研专家正在搜集资料，开展技术深度拆解...")

    # 从工厂实例化调研模型（researcher 是 2 号 LLM，沿用 deepseek 作为"其他"），0.7 温度丰富内容生成
    model = create_model(provider="deepseek", temperature=0.7)

    # 构建调研人设和任务指引 Prompt
    researcher_prompt = (
        "你是一个资深的前沿技术调研专家。\n"
        f"请针对用户的请求任务：'{state['request']}'，进行深入的资料整理和技术对比分析。\n"
        "你需要提供有条理的要点、核心特点、技术优劣势以及适用场景对比。\n"
        "内容力求客观详实，条理清晰，字数控制在 400 字以内。"
    )

    # 调用大模型生成调研内容
    response = model.invoke([HumanMessage(content=researcher_prompt)])
    # 提取内容
    result_text = response.content.strip()

    print("✅ [Node: Researcher] 调研工作已成功完成！")

    # 获取当前已完成工作的列表副本
    updated_work = list(state["completed_work"])
    # 追加当前节点的完成记录
    updated_work.append("- researcher 节点已完成详细的技术对比调研。")

    # 返回状态更新
    return {
        "research_result": result_text,
        "completed_work": updated_work
    }


def coder_node(state: MultiAgentState):
    """
    编码工人节点 (coder_node)。

    功能：根据用户的任务请求以及 Researcher 已经产出的调研背景，用大模型生成极高质量、符合规范的示例代码。
    输入参数：
        state (MultiAgentState): 共享全局状态字典。
    输出返回值:
        dict: 更新 coder_result 和 completed_work 历史。
    """
    print("\n💻 [Node: Coder] 编码专家正在深入理解调研背景，开始编写完美的示例代码...")

    # 从工厂实例化编码模型（coder 是 3 号 LLM，沿用 deepseek 作为"其他"），0.2 温度防代码逻辑幻觉
    model = create_model(provider="deepseek", temperature=0.2)

    # 提取前置调研结果，用于指导编码
    research_ctx = state.get("research_result", "无前置调研材料")

    # 构建编码人设和任务指引 Prompt
    coder_prompt = (
        "你是一个顶尖的高级软件开发工程师。\n"
        f"用户的开发请求任务是：'{state['request']}'\n\n"
        f"前置的架构与技术调研结果如下：\n\"{research_ctx}\"\n\n"
        "请根据上述背景，编写一个功能完整、排版规范、极其符合最佳实践的 Python 示例代码。\n"
        "要求：\n"
        "- 必须包含清晰的类/函数定义以及完备的输入输出 Docstring 声明。\n"
        "- 代码中的核心语句均需提供清晰可读的中文注释。\n"
        "- 输出的文本应当主要是可运行的 Python 代码块本身，并提供极简的用法演示。"
    )

    # 调用大模型生成示例代码
    response = model.invoke([HumanMessage(content=coder_prompt)])
    # 提取内容
    result_text = response.content.strip()

    print("✅ [Node: Coder] 示例代码编写与自测已成功完成！")

    # 获取当前已完成工作的列表副本
    updated_work = list(state["completed_work"])
    # 追加当前节点的完成记录
    updated_work.append("- coder 节点已完成对应技术栈的高质量示例代码编写。")

    # 返回状态更新
    return {
        "coder_result": result_text,
        "completed_work": updated_work
    }


def writer_node(state: MultiAgentState):
    """
    写作工人节点 (writer_node)。

    功能：综合提取 Researcher 产出的调研文字与 Coder 产出的示例代码，排版并整合撰写一份极具含金量的前沿调研技术报告。
    输入参数：
        state (MultiAgentState): 共享全局状态字典。
    输出返回值:
        dict: 更新 writer_result 和 completed_work 历史。
    """
    print("\n✍️ [Node: Writer] 写作润色专家正在收官，开始高度整合资料与代码，编排 Markdown 技术报告...")

    # 从工厂实例化写作模型（writer 是 4 号 LLM，沿用 deepseek 作为"其他"），0.5 温度提升语言流畅度
    model = create_model(provider="deepseek", temperature=0.5)

    # 提取前置调研和编码数据，进行数据整合
    research_ctx = state.get("research_result", "无调研材料")
    coder_ctx = state.get("coder_result", "未提供示例代码")

    # 构建写作人设和任务指引 Prompt
    writer_prompt = (
        "你是一个高水准的 IT 技术专栏总编辑兼技术写手。\n"
        f"用户的初始需求是：'{state['request']}'\n\n"
        f"【调研专家提供的竞品/技术对比】:\n{research_ctx}\n\n"
        f"【编码专家提供的核心示例代码】:\n{coder_ctx}\n\n"
        "【你的核心职责】:\n"
        "请你充分吸收上述两位专家的工作成果，进行深度重构、逻辑理顺、排版和语言润色，\n"
        "撰写出一篇逻辑极其严密、排版美观（使用优雅的 GitHub Markdown 格式）、兼具理论与实操的高含金量前沿技术调研报告。\n"
        "报告必须包括：标题、技术对比概述、核心优缺点分析、实战代码演练、适用场景总结与展望。\n"
        "不要漏掉专家的任何关键代码或分析成果！"
    )

    # 调用大模型生成技术报告
    response = model.invoke([HumanMessage(content=writer_prompt)])
    # 提取内容
    result_text = response.content.strip()

    print("✅ [Node: Writer] Markdown 技术调研报告组装排版完毕！")

    # 获取当前已完成工作的列表副本
    updated_work = list(state["completed_work"])
    # 追加当前节点的完成记录
    updated_work.append("- writer 节点已完成最终整合版 Markdown 调研报告的润色和编撰。")

    # 返回状态更新
    return {
        "writer_result": result_text,
        "completed_work": updated_work
    }


# ============================================================
# 4. 定义图的路由条件转换函数 (Conditional Edge Router)
# ============================================================

def route_to_worker(state: MultiAgentState) -> str:
    """
    基于共享状态中 next_agent 字段进行下一步节点路由分发。

    功能：接收当前全局状态，读取 Supervisor 的决策字段，指引 LangGraph 跳转至相应节点或终点。
    输入参数：
        state (MultiAgentState): 共享全局状态字典。
    输出返回值:
        str: 跳转的物理节点名称或 "FINISH"。
    """
    # 获取共享状态中的路由目标
    next_agent = state.get("next_agent", "FINISH")
    # 检查路由目标是否在合法指令中
    if next_agent == "researcher":
        # 路由至调研节点
        return "researcher"
    elif next_agent == "coder":
        # 路由至编码节点
        return "coder"
    elif next_agent == "writer":
        # 路由至写作节点
        return "writer"
    else:
        # 回退默认结束
        return "FINISH"


# ============================================================
# 5. 主程序：组装图机并启动执行
# ============================================================

def main():
    """
    主运行入口。

    功能：构建并编译包含 Supervisor 主管及 3 大 Worker 工人的多 Agent LangGraph 有向状态图，
          针对复杂任务请求启动引擎，并打印出最终的高质量合并技术报告。
    """
    # 定义我们的复杂多任务请求话题：调研 FastAPI 相比 Flask 的高并发性能优势，并编写一个 FastAPI 的高并发接口示例代码，最后汇编成专栏文章。
    task_request = (
        "帮我深入调研 FastAPI 相比传统 Flask 的高并发性能优势，"
        "并编写一个 FastAPI 用于支持异步数据查询的高并发示例代码，"
        "最后整合成一篇专栏级别的 Markdown 调研报告。"
    )

    print("🛠️ 正在初始化构建 Supervisor 主管多智能体路由图机...")
    # 基于 MultiAgentState 结构初始化状态图
    workflow = StateGraph(MultiAgentState)

    # 1. 注册主管节点
    workflow.add_node("supervisor", supervisor_node)
    # 2. 注册调研 Worker 节点
    workflow.add_node("researcher", researcher_node)
    # 3. 注册编码 Worker 节点
    workflow.add_node("coder", coder_node)
    # 4. 注册写作 Worker 节点
    workflow.add_node("writer", writer_node)

    # 设定图的唯一起始入口为主管节点，使其首先掌握全局
    workflow.set_entry_point("supervisor")

    # 为主管添加条件分发边，主管将动态决定流向哪一个 Worker 或走向终点
    workflow.add_conditional_edges(
        "supervisor",
        route_to_worker,
        {
            "researcher": "researcher",
            "coder": "coder",
            "writer": "writer",
            "FINISH": END
        }
    )

    # 所有 Workers 执行完毕后，必须无条件流回主管节点，由主管在下一轮决定下一步
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("coder", "supervisor")
    workflow.add_edge("writer", "supervisor")

    # 编译有向状态图，生成最终运行实例
    app = workflow.compile()
    print("✅ 多 Agent 主管模式路由状态图编译成功！")

    print("\n🏃 正在启动多智能体团队引擎...")
    print(f"📋 任务请求: \"{task_request}\"")
    print("=" * 80)

    # 启动工作流引擎，传入初始请求与空状态数据
    final_state = app.invoke({
        "request": task_request,
        "completed_work": [],
        "next_agent": "",
        "research_result": "",
        "coder_result": "",
        "writer_result": ""
    })

    print("\n" + "=" * 80)
    print("⭐ 最终团队产出的专栏级调研报告预览:")
    print("=" * 80)
    # 打印最终共享状态里由 writer 整合好的报告
    print(final_state["writer_result"])
    print("=" * 80)
    print("✨ 多 Agent 主管模式（Supervisor Pattern）实战演示顺利闭环！")


# 判断是否自命令行直接启动
if __name__ == "__main__":
    # 执行主程序
    main()
