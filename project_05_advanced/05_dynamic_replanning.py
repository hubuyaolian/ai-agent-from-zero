# -*- coding: utf-8 -*-
"""
Day 12 演示：基于动态重新规划 (Dynamic Replanning) 的高级自适应 Agent 架构。

功能：利用 LangGraph 状态图构建自适应规划器。在步骤二中人为制造网络超时与数据阻断，
      触发 Replanner 节点启动，重新改写后续的步骤和代偿计划，继续执行，
      最终成功出具代偿性的企业技术报告，展示 Agent 优秀的错误自愈与弹性。
输入参数：无。
输出返回值：控制台打印初始计划、模拟阻断、动态改写的新计划及最终自适应报告。
"""

# 导入 JSON 序列化库，用于解析大模型的规划和重规划数据
import json
# 导入 TypedDict 与 List 结构
from typing import TypedDict, List
# 导入 LangChain 消息类
from langchain_core.messages import HumanMessage
# 导入 LangGraph 状态图机核心类
from langgraph.graph import StateGraph, END

# 导入公共模型工厂函数
from common.model_factory import create_model


# ============================================================
# 1. 定义自适应规划图的全局共享状态 (State)
# ============================================================

class ReplanningState(TypedDict):
    """
    自适应规划图状态结构定义。

    功能：描述并保存带有动态重新规划能力的 Agent 内部所有运行时变量。
    字段说明：
        input: 用户的原始复杂任务请求。
        plan: 动态变化的子步骤计划描述列表（可能被 Replanner 改写）。
        past_steps: 已执行完毕的步骤及其成果元组列表，格式为 [(step_desc, step_result), ...]。
        response: 最终汇总的答复文本。
    """
    # 用户首问输入
    input: str
    # 分步计划列表（动态修改）
    plan: List[str]
    # 已执行步骤及结果轨迹
    past_steps: List[tuple]
    # 最终汇总的代偿性报告
    response: str


# ============================================================
# 2. 定义状态图中的节点逻辑 (Nodes)
# ============================================================

def initial_planner_node(state: ReplanningState):
    """
    初始规划器节点逻辑。

    功能：接收用户的原始复杂任务，调用大模型制定包含 3 个基础步骤的初始计划。
    输入参数：
        state (ReplanningState): 图共享状态字典。
    输出返回值：
        dict: 更新至状态的初始 plan 列表。
    """
    print("\n📋 [Node: Initial Planner] 正在为复杂目标任务建立初始执行计划...")
    # 教学阶段 04 之后默认 LLM 统一走 xiaomi mimo，温度设为 0.1
    planner_model = create_model(provider="xiaomi mimo", temperature=0.1)

    # 初始规划 Prompt
    prompt = (
        "你是一个极其专业、严谨的任务规划专家。\n"
        "请将用户的复杂任务合理拆解为 3 个具体的子步骤计划。\n"
        "每个步骤必须描述清晰、可执行。\n\n"
        "请务必输出标准的 JSON 结构，不要有任何多余的 Markdown 标记。\n"
        "JSON 格式要求如下：\n"
        "{\n"
        "  \"plan\": [\n"
        "    \"步骤 1: 具体的步骤描述。\",\n"
        "    \"步骤 2: 具体的步骤描述。\",\n"
        "    \"步骤 3: 具体的步骤描述。\"\n"
        "  ]\n"
        "}\n\n"
        f"用户的最终目标任务是: '{state['input']}'\n"
        "请现在给出你的 JSON 规划数据："
    )

    # 调用模型
    response = planner_model.invoke([HumanMessage(content=prompt)])
    output_text = response.content.strip()

    # 清理 Markdown 代码包裹标记，防止解析异常
    if output_text.startswith("```"):
        newline_idx = output_text.find("\n")
        output_text = output_text[newline_idx + 1:]
        if output_text.endswith("```"):
            output_text = output_text[:-3].strip()
        else:
            pass
    else:
        pass

    try:
        # 解析 JSON 步骤列表
        data = json.loads(output_text)
        steps_list = data.get("plan", [])
    except Exception as err:
        print(f"⚠️ JSON 解析失败: {str(err)}。使用兜底计划。")
        steps_list = [
            "步骤 1: 搜集企业在微服务架构下采用 Python 作为核心技术栈的优势。",
            "步骤 2: 深入调研行业内知名企业使用 Python 落地高并发微服务的真实商业案例。",
            "步骤 3: 结合行业痛点，输出一份完整的 Python 微服务企业落地与痛点避坑指南。"
        ]

    print("🎯 Planner 成功建立初始路线图:")
    for idx, step_desc in enumerate(steps_list):
        print(f"   [{idx + 1}] {step_desc}")

    # 返回增量状态
    return {"plan": steps_list}


def adaptive_executor_node(state: ReplanningState):
    """
    自适应执行器节点逻辑。

    功能：读取计划中的当前步骤进行执行。在执行【步骤二】时，故意模拟发生“由于权限和机密数据限制导致信息阻断”的失败状态，以触发重新规划。
    输入参数：
        state (ReplanningState): 图共享状态字典。
    输出返回值：
        dict: 更新已执行步骤 past_steps 轨迹列表。
    """
    # 获取当前执行的步骤索引，等于目前已执行成功的步骤数
    current_idx = len(state["past_steps"])
    # 提取当前子任务描述
    current_step_desc = state["plan"][current_idx]

    print(
        f"\n🏃 [Node: Executor] 正在执行子任务 "
        f"[{current_idx + 1}/{len(state['plan'])}]: '{current_step_desc}'..."
    )

    # ============================================================
    # 教学亮点：在步骤二（索引值为 1）中故意模拟阻断，人为制造失败！
    # ============================================================
    if current_idx == 1:
        print("🚨🚨 [系统网络监控] 警告：在访问外部商业案例数据库时遭遇防火墙拦截！")
        print("🚨🚨 错误详情: 'HTTP 403 Forbidden: 访问受限。商业机密数据限制，无法提取真实案例。'")
        # 写入一个失败的 Observation 结果
        step_result = (
            "【执行失败报错】：由于网络防火墙封锁以及相关互联网商业数据的高度机密限制，"
            "系统无法获取任何关于企业落地 Python 微服务的真实商业细节数据，检索结果空空如也。"
        )
    else:
        # 正常的步骤使用大模型计算成果（executor 是 2 号 LLM，沿用 deepseek 作为"其他"）
        executor_model = create_model(provider="deepseek", temperature=0.3)

        # 拼接前置轨迹
        history_list = []
        for step_item in state["past_steps"]:
            history_list.append(f"子任务: {step_item[0]}\n执行产出: {step_item[1]}")
        history_context = "\n\n".join(history_list)

        # 构造执行 Prompt
        exec_prompt = (
            "你是一个极其优秀的任务执行专家。\n"
            "请结合之前已完成的步骤成果，完成你当前负责的子任务。\n\n"
            "【前置步骤轨迹成果】\n"
            f"{history_context if history_context else '前置步骤：无。'}\n\n"
            "【你当前的子任务】\n"
            f"{current_step_desc}\n\n"
            "请围绕该子任务给出精准、详实的产出成果："
        )

        response = executor_model.invoke([HumanMessage(content=exec_prompt)])
        step_result = response.content.strip()

    print(f"✅ 步骤 [{current_idx + 1}] 执行完毕！成果概要: '{step_result[:60]}...'")

    # 拷贝已有的 past_steps，并追加当前步骤与结果的元组
    updated_past = list(state["past_steps"])
    updated_past.append((current_step_desc, step_result))

    # 返回更新的状态
    return {"past_steps": updated_past}


def replanner_node(state: ReplanningState):
    """
    重新规划器节点逻辑 (Replanner)。

    功能：审查刚刚执行步骤的产出成果。如果检测到“执行失败报错”，主动触发 REPLAN，
          废弃原计划的剩余步骤，重新制定一组代偿性的替代方案步骤，完成自适应重组。
    输入参数：
        state (ReplanningState): 图共享状态字典。
    输出返回值：
        dict: 更新后的 plan 列表。
    """
    print("\n🔄 [Node: Replanner] 正在检查当前步骤的执行成果质量...")

    # 初始化重规划大模型（replanner 是 3 号 LLM，沿用 deepseek 作为"其他"）
    replanning_model = create_model(provider="deepseek", temperature=0.1)

    # 整理全部已经执行过的步骤（包括刚刚失败的这一步）作为上下文
    completed_steps_list = []
    for idx, item in enumerate(state["past_steps"]):
        completed_steps_list.append(f"步骤 {idx + 1}: {item[0]}\n执行成果: {item[1]}")
    completed_steps_context = "\n\n".join(completed_steps_list)

    # 构造重规划 Prompt，引入标准 JSON 返回约束
    replanner_prompt = (
        "你是一个任务重新规划与错误自愈专家。\n"
        "你需要评估当前步骤的成果。如果上一步骤【执行失败报错】，说明原计划的路线已经走不通了！\n"
        "你必须丢弃原先还未执行的剩余计划步骤，并根据已有的残缺信息，制定一条【代偿性的替代步骤】来挽救任务，"
        "确保我们依然能为用户出具一份有价值的最终报告！\n\n"
        f"用户的原始宏观总目标是: '{state['input']}'\n"
        f"原定完整计划步骤: {state['plan']}\n\n"
        "【已完成的执行轨迹（包含失败步骤）】:\n"
        f"{completed_steps_context}\n\n"
        "【你当前的重新规划准则】\n"
        "1. 如果你发现刚刚执行的步骤存在【执行失败报错】，请将 action 设置为 'REPLAN'，"
        "并丢弃剩余原计划，重新拟定一份包含已完成步骤和代偿后续步骤的【全新完整计划列表】！\n"
        "   代偿方案建议：虽然获取不到知名的商业落地案例，但我们可以通过'分析开源微服务架构基准性能指标'，"
        "   以及'依据软件工程理论模型推演大型分布式高并发方案'来进行代偿性报告拟定！\n"
        "   此时，输出 JSON 格式如下：\n"
        "   {\n"
        "     \"action\": \"REPLAN\",\n"
        "     \"plan\": [\n"
        "       \"已完成的第一步描述...\",\n"
        "       \"已尝试但阻断的第二步描述...\",\n"
        "       \"【代偿调整】新加入的替代步骤：分析开源微服务基准指标并推演模型。\",\n"
        "       \"【代偿调整】新加入的替代步骤：根据理论推演设计一份高吞吐架构方案及避坑总结。\"\n"
        "     ]\n"
        "   }\n"
        "2. 如果你认为刚刚的步骤执行【非常成功，没有发生任何异常阻断】，无须重规划，直接且仅输出以下 JSON：\n"
        "   {\n"
        "     \"action\": \"PLAN_OK\",\n"
        "     \"plan\": []\n"
        "   }\n\n"
        "请现在给出你的 JSON 评估决策数据："
    )

    # 调用模型
    response = replanning_model.invoke([HumanMessage(content=replanner_prompt)])
    output_text = response.content.strip()

    # 过滤 Markdown 包裹
    if output_text.startswith("```"):
        newline_idx = output_text.find("\n")
        output_text = output_text[newline_idx + 1:]
        if output_text.endswith("```"):
            output_text = output_text[:-3].strip()
        else:
            pass
    else:
        pass

    try:
        # 解析决策 JSON
        decision_data = json.loads(output_text)
        action_type = decision_data.get("action", "PLAN_OK")
    except Exception as err:
        print(f"⚠️ Replanner JSON 解析失败: {str(err)}。默认保持原计划。")
        action_type = "PLAN_OK"

    # 如果模型决定触发重规划，改写路线图
    if action_type == "REPLAN":
        new_plan = decision_data.get("plan", [])
        print("\n🔄 🚨 [Replanner 动作] 识别到关键步骤发生数据阻断！")
        print("🔄 🚨 正在动态改写原先计划，自适应替换为【代偿性代偿路线】！")
        print("🔄 🎯 重新规划后的自适应路线图为:")
        for idx, step_desc in enumerate(new_plan):
            print(f"   [{idx + 1}] {step_desc}")

        # 将新改写的 plan 写回状态字典并返回
        return {"plan": new_plan}
    else:
        # 正常继续，不修改计划
        print("🔄 [Replanner 动作] 检查无误。当前子任务成果质量完备，原计划执行路线无需修改。")
        return {}


def summarizer_node(state: ReplanningState):
    """
    终期自适应总结器节点逻辑。

    功能：汇总包括失败和代偿新步骤的所有物理痕迹，为用户出具一份优雅、具有极高指导意义的代偿性技术报告。
    输入参数：
        state (ReplanningState): 图共享状态字典。
    输出返回值：
        dict: 更新 response 最终回答。
    """
    print("\n🎓 [Node: Summarizer] 所有子任务（包含代偿子任务）已顺利搞定。正在撰写终期自适应架构选型建议报告...")
    # summarizer 是 4 号 LLM，沿用 deepseek 作为"其他"
    summarizer_model = create_model(provider="deepseek", temperature=0.2)

    # 串联所有步骤成果
    report_list = []
    for idx, item in enumerate(state["past_steps"]):
        report_list.append(f"### 规划阶段 {idx + 1}: {item[0]}\n**物理产出成果**:\n{item[1]}")
    report_context = "\n\n".join(report_list)

    # 编写总结 Prompt，明确告知包含代偿性内容，体现系统的韧性
    prompt = (
        "你是一个极其资深、懂得权衡的企业级技术咨询专家。\n"
        "在刚才的项目执行中，我们不幸遭遇了商业机密网络拦截，导致未能直接拿到知名的企业真实落地案例数据，"
        "但是，我们的团队迅速启动了【代偿性备用方案】，通过分析开源基准指标和推演理论工程模型完成了代偿分析！\n\n"
        "以下是团队本次运转的完整子任务轨迹与真实成果：\n"
        f"{report_context}\n\n"
        "【用户的原始诉求是】:\n"
        f"'{state['input']}'\n\n"
        "请根据上述执行产出，撰写一篇逻辑周密、结构优雅的企业级架构技术建议书。\n"
        "注意：请在报告开头专门设立一个【执行韧性说明】小章节，大方得体地说明我们克服了商业机密访问受限的困难，"
        "通过学术与开源数据代偿推演，依然保障了报告的高可用性与客观参考价值！"
    )

    response = summarizer_model.invoke([HumanMessage(content=prompt)])
    final_report = response.content.strip()

    return {"response": final_report}


# ============================================================
# 3. 定义条件边流转路由规则 (Conditional Edges)
# ============================================================

def should_continue(state: ReplanningState):
    """
    路由跳转判定函数。

    功能：比对已完成的步骤数与当前的计划总步数，决定是循环回执行器还是走向总结。
    输入参数：
        state (ReplanningState): 图共享状态字典。
    输出返回值：
        str: 下一步骤节点名（"execute" 或 "summarize"）。
    """
    completed = len(state["past_steps"])
    total = len(state["plan"])

    # 如果已完成数小于计划数
    if completed < total:
        # 还有没干完的活，回执行器
        return "execute"
    else:
        # 全都干完了，去总结
        return "summarize"


def main():
    """
    主运行函数。

    功能：组装自适应 Replanning 图机，设定节点边及条件路由，编译并执行企业高并发 Python 微服务选型任务。
    """
    # 用户的复杂提问任务
    complex_request = (
        "帮我分析大型互联网企业使用 Python 落地高并发微服务的可行性与痛点比对，"
        "并结合行业落地案例，给出一份 500 字左右的精炼建议书。"
    )

    print("🛠️ 正在构建带错误自愈能力的自适应规划图机...")
    # 初始化状态图机
    workflow = StateGraph(ReplanningState)

    # 载入 4 个核心节点
    workflow.add_node("initial_planner", initial_planner_node)
    workflow.add_node("executor", adaptive_executor_node)
    workflow.add_node("replanner", replanner_node)
    workflow.add_node("summarizer", summarizer_node)

    # 设定起始入口为初始规划节点
    workflow.set_entry_point("initial_planner")

    # 初始规划完成后，无条件去执行器进行第一步落地
    workflow.add_edge("initial_planner", "executor")

    # 执行器每完成一步后，必须且立即进入 Replanner 节点进行成果质量自检与重新评估
    workflow.add_edge("executor", "replanner")

    # 重新评估完成后，使用条件路由 should_continue 决定未来动向：
    #   - 还有子步骤没干完，跳转到 "executor" 节点继续做
    #   - 步骤已全量覆盖，跳转到 "summarizer" 节点开展终期撰写
    workflow.add_conditional_edges(
        "replanner",
        should_continue,
        {
            "execute": "executor",
            "summarize": "summarizer"
        }
    )

    # 总结完报告后，无条件指向图终点 END
    workflow.add_edge("summarizer", END)

    # 编译有向图机
    app = workflow.compile()
    print("✅ 带重新规划能力的自适应图机编译成功！")

    print("\n🚀 正在启动自适应 Planning Agent 处理流程...")
    print(f"用户原始诉求: '{complex_request}'")
    print("=" * 60)

    # 启动图机运行
    result = app.invoke({
        "input": complex_request,
        "plan": [],
        "past_steps": [],
        "response": ""
    })

    print("\n" + "=" * 60)
    print("⭐ 最终自适应 Planning Agent 架构选型建议书:")
    print("=" * 60)
    # 打印包含【执行韧性说明】的高可用自适应技术报告
    print(result["response"])
    print("=" * 60)
    print("✨ 自适应重新规划 Agent 流程演练大获成功。")


# 判断是否由命令行直接启动
if __name__ == "__main__":
    # 执行主程序
    main()
