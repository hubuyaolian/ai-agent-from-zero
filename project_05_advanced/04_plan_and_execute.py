# -*- coding: utf-8 -*-
"""
Day 12 演示：Plan-and-Execute (计划与执行) 经典 Agent 架构实现。

功能：利用 LangGraph 状态图构建一个宏观规划 Agent。Planner 节点制定多步有序计划，
      Executor 节点利用大模型逐步执行各子步骤，并通过条件路由进行判断，
      最后由 Summarizer 节点汇总所有执行结果，生成总结答复。
输入参数：无。
输出返回值：控制台打印制定出的计划以及各步骤运行产生的物理轨迹和最终总结。
"""

# 导入 JSON 解析库，用于解析大模型规划的步骤数组
import json
# 导入 TypedDict 与 List 扩展，用于图状态定义
from typing import TypedDict, List
# 导入 LangChain 的消息类
from langchain_core.messages import HumanMessage
# 导入 LangGraph 状态图机核心类
from langgraph.graph import StateGraph, END

# 导入公共模型工厂函数
from common.model_factory import create_model


# ============================================================
# 1. 定义 Plan-and-Execute 图的全局共享状态 (State)
# ============================================================

class PlanExecuteState(TypedDict):
    """
    Plan-and-Execute 图状态结构定义。

    功能：描述并记录任务流转中的所有变量，包括原始任务、有序步骤计划、已执行步骤明细以及最终总结。
    字段说明：
        input: 用户的原始复杂任务请求。
        plan: 规划器生成的有序子步骤描述列表（如：["步骤1...", "步骤2..."]）。
        past_steps: 已经执行完毕的步骤及其结果的元组列表，格式为 [(step_desc, step_result), ...]。
        response: 最终的总结性回答。
    """
    # 用户原始输入
    input: str
    # 分步计划列表
    plan: List[str]
    # 已完成的步骤轨迹
    past_steps: List[tuple]
    # 最终汇总答复
    response: str


# ============================================================
# 2. 定义状态图中的各个节点逻辑 (Nodes)
# ============================================================

def planner_node(state: PlanExecuteState):
    """
    规划器节点逻辑。

    功能：接收用户的原始复杂任务，调用大模型将其合理拆解为有序的、具体的子步骤计划，并以标准的 JSON 数组返回。
    输入参数：
        state (PlanExecuteState): 图的共享状态字典。
    输出返回值：
        dict: 更新到状态中的分步计划 plan 列表。
    """
    print("\n📋 [Node: Planner] 正在为复杂任务制定全局分步计划...")
    # 教学阶段 04 之后默认 LLM 统一走 xiaomi mimo，温度设为 0.1 以保障计划的规律和稳定
    planner_model = create_model(provider="xiaomi mimo", temperature=0.1)

    # 编写专门的规划器 Prompt，要求必须输出标准的 JSON 对象
    planner_prompt = (
        "你是一个极其专业、严谨的任务规划专家。\n"
        "请将用户的复杂任务合理拆解为一系列有序的、可独立执行的子步骤计划。\n"
        "每个步骤必须描述明确、高度可操作，后面的步骤可以依赖并承接前面步骤的执行成果。\n\n"
        "【重要规则】\n"
        "请务必输出标准的 JSON 结构，不能有任何多余的 Markdown 标记或干扰性解释文字。\n"
        "JSON 格式要求如下：\n"
        "{\n"
        "  \"plan\": [\n"
        "    \"步骤 1: 具体的步骤描述。\",\n"
        "    \"步骤 2: 具体的步骤描述。\"\n"
        "  ]\n"
        "}\n\n"
        f"用户的最终目标任务是: '{state['input']}'\n"
        "请现在给出你的 JSON 规划数据："
    )

    # 调用大模型生成计划
    response = planner_model.invoke([HumanMessage(content=planner_prompt)])
    # 提取内容
    output_text = response.content.strip()

    # 清理掉可能存在的 Markdown 代码块包裹标记，确保 json.loads 成功
    if output_text.startswith("```"):
        # 移除前导反引号
        # 寻找第一个换行，截断之后的内容
        newline_idx = output_text.find("\n")
        # 提取换行后的文本
        output_text = output_text[newline_idx + 1:]
        # 如果末尾有反引号，移除
        if output_text.endswith("```"):
            # 剥离末尾三个反引号
            output_text = output_text[:-3].strip()
        else:
            pass
    else:
        pass

    try:
        # 解析大模型返回的 JSON 数据
        plan_data = json.loads(output_text)
        # 获取计划步骤列表
        steps_list = plan_data.get("plan", [])
    except Exception as err:
        # 如果解析失败，进行退回保底处理
        print(f"⚠️ Planner JSON 解析出错: {str(err)}。正使用兜底分步机制。")
        steps_list = [
            "步骤 1: 搜索整理目前最前沿的主流 AI Agent 框架。",
            "步骤 2: 对比各框架的核心特性与生态繁荣度。",
            "步骤 3: 综合给出对框架的发展与落地方向的深度见解。"
        ]

    # 打印生成的步骤计划
    print("🎯 Planner 成功制定如下执行路线图:")
    for idx, step_desc in enumerate(steps_list):
        print(f"   [{idx + 1}] {step_desc}")

    # 将生成的步骤列表写入状态并返回
    return {"plan": steps_list}


def executor_node(state: PlanExecuteState):
    """
    步骤执行器节点逻辑。

    功能：识别当前需要执行的步骤，结合之前所有已执行步骤的上下文轨迹，驱动 Worker 模型计算出当前步骤的高质量结果。
    输入参数：
        state (PlanExecuteState): 图的共享状态字典。
    输出返回值：
        dict: 更新已执行步骤 past_steps 轨迹元组。
    """
    # 确认计划中的步骤总数
    total_steps = len(state["plan"])
    # 当前待执行步骤的索引，等于目前已执行步骤的数量
    current_idx = len(state["past_steps"])

    # 获取当前执行的步骤描述
    current_step_desc = state["plan"][current_idx]

    print(
        f"\n🏃 [Node: Executor] 正在执行步骤 "
        f"[{current_idx + 1}/{total_steps}]: '{current_step_desc}'..."
    )

    # 从工厂创建执行器模型实例（executor 是 2 号 LLM，沿用 deepseek 作为"其他"）
    executor_model = create_model(provider="deepseek", temperature=0.3)

    # 整理之前已执行完所有步骤的历史成果上下文（坚决不用单行推导式）
    history_context_list = []
    for step_item in state["past_steps"]:
        # 拆包元组
        desc = step_item[0]
        res = step_item[1]
        # 拼接单条记录
        history_context_list.append(f"已完成步骤: {desc}\n执行成果: {res}")
    # 融合成大文本
    history_context = "\n\n".join(history_context_list)

    # 如果历史轨迹为空，进行特殊说明
    if not history_context:
        # 无前置步骤
        history_context = "前置步骤：无（此步骤为计划的第一步，请直接开展工作）。"
    else:
        pass

    # 编写执行器专用 Prompt，提供充足的历史上下文支持
    executor_prompt = (
        "你是一个卓越的任务执行专家。你目前被委派执行整个全局计划中的一个子步骤。\n"
        "请认真分析当前步骤要求，结合之前已执行步骤的成果上下文，给出当前步骤的精确执行结果。\n\n"
        "【前置步骤成果轨迹】\n"
        f"{history_context}\n\n"
        "【你当前需要攻克的步骤任务】\n"
        f"{current_step_desc}\n\n"
        "请围绕该步骤给出详实的执行成果："
    )

    # 调用 Worker 运行
    response = executor_model.invoke([HumanMessage(content=executor_prompt)])
    # 提取结果
    step_result = response.content.strip()

    print(f"✅ 步骤 [{current_idx + 1}] 执行完毕！成果概要: '{step_result[:60]}...'")

    # 拷贝已有的 past_steps，并追加当前步骤与结果的元组
    updated_past = list(state["past_steps"])
    updated_past.append((current_step_desc, step_result))

    # 返回增量状态
    return {"past_steps": updated_past}


def summarizer_node(state: PlanExecuteState):
    """
    总结器节点逻辑。

    功能：在所有计划子步骤全部执行完后被唤醒，综合整个执行轨迹，给用户出具一份逻辑严密、排版精美的终期报告。
    输入参数：
        state (PlanExecuteState): 图的共享状态字典。
    输出返回值：
        dict: 更新 response 最终答复字段。
    """
    print("\n🎓 [Node: Summarizer] 恭喜！所有步骤已顺利执行完毕。正在撰写终期汇总汇报报告...")
    # 从工厂创建总结器大模型实例（summarizer 是 3 号 LLM，沿用 deepseek 作为"其他"）
    summarizer_model = create_model(provider="deepseek", temperature=0.2)

    # 汇总所有的执行痕迹
    report_context_list = []
    for step_item in state["past_steps"]:
        # 拆包
        desc = step_item[0]
        res = step_item[1]
        # 格式化拼接
        report_context_list.append(f"### 规划步骤: {desc}\n**执行产出成果**:\n{res}")
    # 融合
    report_context = "\n\n".join(report_context_list)

    # 编写总结 Prompt
    summarize_prompt = (
        "你是一个资深的技术总结和报告专家。\n"
        "现在，项目的全部子计划步骤已经执行完毕，以下是完整的规划路线及每一步的物理成果痕迹：\n\n"
        f"{report_context}\n\n"
        "【用户的原始最终目标是】:\n"
        f"'{state['input']}'\n\n"
        "请根据每一步的真实产出，围绕用户的最终目标，撰写一篇逻辑严密、排版美观且通俗易懂的中文总结性技术报告："
    )

    # 执行大模型总结
    response = summarizer_model.invoke([HumanMessage(content=summarize_prompt)])
    # 获取答案
    final_report = response.content.strip()

    # 返回最终结果
    return {"response": final_report}


# ============================================================
# 3. 定义图中的条件路由规则 (Conditional Edges)
# ============================================================

def should_continue(state: PlanExecuteState):
    """
    条件路由决策函数。

    功能：根据已执行完毕的步骤数量 (past_steps) 与总规划步骤数 (plan) 相对比，动态决定去往何处。
    输入参数：
        state (PlanExecuteState): 图的共享状态字典。
    输出返回值：
        str: 跳转的下一个节点指示器（"execute" 或 "summarize"）。
    """
    # 已完成步骤数
    completed = len(state["past_steps"])
    # 规划的步骤总数
    total = len(state["plan"])

    # 校验是否全部完成
    if completed < total:
        # 说明还有剩余步骤未执行，继续跳转到执行器节点
        return "execute"
    else:
        # 所有计划步骤均已完成，跳转到总结器节点
        return "summarize"


def main():
    """
    主运行函数。

    功能：构建有向图，绑定节点，设定路由，编译图并对“AI Agent 落地建议”复杂需求进行规划执行与展示。
    """
    # 定义用户的复杂宏观目标任务
    complex_task = (
        "帮我分析目前最火爆的 AI Agent 两大开发框架：LangChain 与 Semantic Kernel，"
        "并针对企业落地场景，给出一个客观且条理分明的落地选型建议报告。"
    )

    print("🛠️ 正在构建 Plan-and-Execute 状态图机...")
    # 初始化状态图，指定状态结构为 PlanExecuteState
    workflow = StateGraph(PlanExecuteState)

    # 添加各个逻辑节点
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("summarizer", summarizer_node)

    # 设置整个图的入口点为 planner 节点（第一步做规划）
    workflow.set_entry_point("planner")

    # 规划器执行完后，必须无条件跳转到执行器节点进行步骤落地
    workflow.add_edge("planner", "executor")

    # 执行器执行完一步后，使用条件路由 should_continue 进行流转判定：
    #   - 如果还有未完步骤，返回 "execute" -> 跳转到 executor 节点继续
    #   - 如果步骤全部完结，返回 "summarize" -> 跳转到 summarizer 节点
    workflow.add_conditional_edges(
        "executor",  # 起始节点
        should_continue,  # 判定路由函数
        {
            "execute": "executor",  # 跳转映射 1：循环执行
            "summarize": "summarizer"  # 跳转映射 2：去往总结
        }
    )

    # 总结器汇总完结果后，无条件指向图终点 END
    workflow.add_edge("summarizer", END)

    # 编译有向图机
    app = workflow.compile()
    print("✅ Plan-and-Execute 状态图编译完成！")

    print("\n🚀 正在启动 Planning Agent 任务处理...")
    print(f"用户最终目标: '{complex_task}'")
    print("=" * 60)

    # 运行图机，传入首状态数据
    result = app.invoke({
        "input": complex_task,
        "plan": [],
        "past_steps": [],
        "response": ""
    })

    print("\n" + "=" * 60)
    print("⭐ 最终 Planning Agent 落地建议报告:")
    print("=" * 60)
    # 打印最终输出的汇总技术报告
    print(result["response"])
    print("=" * 60)
    print("✨ Plan-and-Execute 完整规划与执行引擎运转结束。")


# 判断是否自命令行直接启动
if __name__ == "__main__":
    # 执行主程序
    main()
