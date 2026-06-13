# -*- coding: utf-8 -*-
"""
Day 15 演示：多 Agent 协作架构 — 线性协作流水线模式 (Collaborative/Pipeline Pattern) 🤝

功能：使用 LangGraph 状态机搭建一个由三大专业智能体接力运作的协作流水线系统。
      - 调研节点 (Researcher)：率先启动，针对指定的技术主题搜集大量核心的原始文献和技术特征数据。
      - 分析节点 (Analyst)：第二阶段执行，从共享状态中读取 Researcher 整理的原始材料，提炼深度的洞察要点与发展趋势。
      - 写作节点 (Writer)：终期收尾执行，从共享状态中提取 Analyst 的深度洞察结论，以精美的专栏级 Markdown 格式撰写出结构完备的技术报告。
      生动演示了如何通过 LangGraph 强力的线性 Graph 拓扑结构，将复杂的长链条业务开发逻辑拆解为模块化的节点任务接力协作。
输入参数：无。
输出返回值：控制台打印每一个执行节点的局部输入输出、接力痕迹以及最终出炉的高含金量分析报告。
"""

# 导入系统路径模块，用于支持从任意位置直接运行本脚本
import sys
# 导入路径处理工具，用于定位项目根目录
from pathlib import Path
# 导入 TypedDict 结构，定义流水线图共享状态结构
from typing import TypedDict

# 将项目根目录加入模块搜索路径，保证 `python project_06_multi_agent/04_collaborative_agents.py` 可直接运行
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# 导入 LangChain 基础用户消息模型
from langchain_core.messages import HumanMessage
# 导入 LangGraph 状态图定义及终点 END
from langgraph.graph import StateGraph, END

# 从全局通用模型工厂中导入大模型实例化函数
from common.model_factory import create_model


# ============================================================
# 1. 定义多 Agent 共享的流水线图状态 (State Schema)
# ============================================================

class PipelineState(TypedDict):
    """
    协作流水线模式下的共享全局状态结构。

    功能：用于流水线中各节点传递各自产出，供后续节点读取与消费。
    字段说明：
        topic: 调研研讨的核心技术话题。
        research_data: 调研智能体搜集并归纳整理的原始技术素材。
        analysis_insights: 分析智能体提炼的深度洞察与核心技术趋势。
        final_report: 写作智能体撰写排版的最终版专栏 Markdown 报告。
    """
    # 讨论和研究的核心主题名称
    topic: str
    # 存储第一阶段调研专家收集到的原始文字
    research_data: str
    # 存储第二阶段分析专家提炼的关键洞察文字
    analysis_insights: str
    # 存储第三阶段写作专家润色整合的最终报告
    final_report: str


# ============================================================
# 2. 定义流水线状态图中的三个专业节点逻辑 (Nodes)
# ============================================================

def researcher_node(state: PipelineState):
    """
    阶段 1：调研专家节点 (researcher_node)。

    功能：提取共享状态中的核心议题，调用大模型充当资深调研员，搜集大量前沿的事实、数据与技术原理解释。
    输入参数：
        state (PipelineState): 图共享全局状态字典。
    输出返回值:
        dict: 更新 research_data 字段，作为阶段 1 的产出。
    """
    print("\n🔍 [Node: Researcher] 流水线开启！调研专家正在为主题搜集原始技术事实与材料...")

    # 从工厂获取主力模型（教学阶段 04 之后默认 LLM 走 xiaomi mimo），0.7 温度释放内容生成的创造力和广度
    model = create_model(provider="xiaomi mimo", temperature=0.7)

    # 构造调研提示词，要求提供详实的数据和原理解释
    researcher_prompt = (
        "你是一个极其卓越的技术前沿调研员。\n"
        f"今天我们流水线要研讨的核心主题是: '{state['topic']}'。\n"
        "请你为该主题收集、整理并输出详实的背景事实、核心技术原理解析以及多维度的原始数据素材。\n"
        "你需要保持客观和专业，字数控制在 400 字以内。"
    )

    # 调用大模型生成调研数据
    response = model.invoke([HumanMessage(content=researcher_prompt)])
    # 提取生成的文本内容
    result_text = response.content.strip()

    print("✅ [Node: Researcher] 原始材料搜集完毕，已成功写入共享状态。")

    # 返回状态增量，写入 research_data
    return {
        "research_data": result_text
    }


def analyst_node(state: PipelineState):
    """
    阶段 2：分析专家节点 (analyst_node)。

    功能：读取上游节点（Researcher）产出的 research_data 原始素材，
          调用大模型扮演行业分析师，对原始材料进行脱水提炼，梳理出 3-5 个核心的发展趋势或深层技术漏洞。
    输入参数：
        state (PipelineState): 图共享全局状态字典。
    输出返回值:
        dict: 更新 analysis_insights 字段，作为阶段 2 的产出。
    """
    print("\n📊 [Node: Analyst] 接力棒交接！分析专家正在对上游调研的原始材料实施深度提炼与价值萃取...")

    # 从工厂实例化大模型（analyst 是 2 号 LLM，沿用 deepseek 作为"其他"），0.3 温度保障逻辑严密
    model = create_model(provider="deepseek", temperature=0.3)

    # 提取上游 Researcher 的成果，展示流水线中的状态消费
    raw_materials = state.get("research_data", "未提供任何原始调研素材")

    # 构造分析提示词，要求对原始素材进行梳理与深度加工
    analyst_prompt = (
        "你是一个顶尖的 IT 行业资深技术分析师。\n"
        f"我们今天研讨的核心议题是: '{state['topic']}'\n\n"
        f"以下是上游调研专家为你搜集和梳理的原始技术事实材料:\n\"{raw_materials}\"\n\n"
        "【你的核心职责】:\n"
        "请对上述材料进行深度加工和去粗取精，总结出 3 至 5 个高含金量的核心技术发展趋势、深层洞察要点，\n"
        "或者痛点漏洞分析。要点之间要保持清晰的逻辑排布，字数控制在 350 字以内。"
    )

    # 调用大模型生成分析洞察
    response = model.invoke([HumanMessage(content=analyst_prompt)])
    # 提取生成的文本内容
    result_text = response.content.strip()

    print("✅ [Node: Analyst] 深度技术洞察已提炼完成，已写入共享状态。")

    # 返回状态增量，写入 analysis_insights
    return {
        "analysis_insights": result_text
    }


def writer_node(state: PipelineState):
    """
    阶段 3：写作专家节点 (writer_node)。

    功能：读取上游节点（Analyst）产出的 analysis_insights 深度分析成果，
          调用大模型充当专栏作家，将纯逻辑要点转化为排版美观、极富说服力的 Markdown 技术专栏报告。
    输入参数：
        state (PipelineState): 图共享全局状态字典。
    输出返回值:
        dict: 更新 final_report 字段，完成整个流水线的最终产品产出。
    """
    print("\n✍️ [Node: Writer] 临门一脚！专栏作家正在将分析师的深度洞察改写为排版精美的 Markdown 报告...")

    # 从工厂获取大模型（writer 是 3 号 LLM，沿用 deepseek 作为"其他"），0.5 温度保证语言自然又专业
    model = create_model(provider="deepseek", temperature=0.5)

    # 提取上游 Analyst 提炼好的高含金量要点
    insights = state.get("analysis_insights", "未提供任何前置洞察点")

    # 构造写作提示词，重点要求 Markdown 结构化排版和修辞润色
    writer_prompt = (
        "你是一个深受读者喜爱的顶级 IT 专栏特约作家。\n"
        f"本次写作的中心议题是: '{state['topic']}'\n\n"
        f"以下是上游技术分析大师为你淬炼的深度洞察与趋势点:\n\"{insights}\"\n\n"
        "【你的核心职责】:\n"
        "请以此为依据，撰写一篇排版极其精美、极具行业影响力的 GitHub 风格 Markdown 报告。\n"
        "报告需要包括：主标题、核心背景综述、深度洞察剖析（对分析师的各点进行合理润色与展开）、\n"
        "行业未来展望与实战建议。\n"
        "排版上要多使用引用块、黑体加粗以及清晰的二级标题来提高可读性，字数控制在 450 字左右。"
    )

    # 调用大模型生成最终报告
    response = model.invoke([HumanMessage(content=writer_prompt)])
    # 提取最终生成的 Markdown 内容
    result_text = response.content.strip()

    print("✅ [Node: Writer] 技术报告编撰润色完毕，流水线圆满收官！")

    # 返回状态增量，写入 final_report
    return {
        "final_report": result_text
    }


# ============================================================
# 3. 主程序：线性流水线图组装与实际启动
# ============================================================

def main():
    """
    主运行入口。

    功能：构建并编译基于 PipelineState 状态共享的线性接力多 Agent 状态图，
          给定一个复杂的技术主题，一键触发全自动流水线，并最终将完美的报告呈现出来。
    """
    # 定义研讨主题：AI 智能体工作流（Agentic Workflow）在未来企业级业务系统中的爆发趋势
    workflow_topic = "AI 智能体工作流 (Agentic Workflow) 在未来企业级业务系统中的落地爆发趋势"

    print("🛠️ 正在初始化多 Agent 线性接力流水线图机...")
    # 基于 PipelineState 声明状态图机
    workflow = StateGraph(PipelineState)

    # 添加流水线上的三大核心逻辑节点
    # 注册第一阶段的调研专家节点
    workflow.add_node("researcher", researcher_node)
    # 注册第二阶段的分析专家节点
    workflow.add_node("analyst", analyst_node)
    # 注册第三阶段的写作专家节点
    workflow.add_node("writer", writer_node)

    # 设定图的唯一入口点为 researcher 调研节点，使其最先触发
    workflow.set_entry_point("researcher")

    # 配置严格的线性流转边：researcher 完成后流向 analyst 提炼
    workflow.add_edge("researcher", "analyst")
    # analyst 提炼完成后流向 writer 撰写报告
    workflow.add_edge("analyst", "writer")
    # writer 撰写润色完毕后直接通往 END 终点结束
    workflow.add_edge("writer", END)

    # 编译有向状态图
    app = workflow.compile()
    print("✅ 线性协作流水线图机编译成功！")

    print("\n🎬 协作流水线引擎正式启动！")
    print(f"📊 研讨主题: '{workflow_topic}'")
    print("=" * 80)

    # 启动工作流，传入话题作为初始参数，其余字段留空待节点自动加工传递
    result = app.invoke({
        "topic": workflow_topic,
        "research_data": "",
        "analysis_insights": "",
        "final_report": ""
    })

    print("\n" + "=" * 80)
    print("⭐ 最终流水线产出的专栏级深度研究报告:")
    print("=" * 80)
    # 打印最终共享状态里的 final_report 最终报告
    print(result["final_report"])
    print("=" * 80)
    print("✨ 多 Agent 线性流水线协作（Collaborative Pattern）实战演示大获成功！")


# 判断是否自命令行直接启动
if __name__ == "__main__":
    # 执行主程序
    main()
