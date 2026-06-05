# -*- coding: utf-8 -*-
"""
Day 13 演示：基于自我反思 (Self-Reflection) 的高质量 AI 生成自检环。

功能：利用 LangGraph 状态图构建 Generator (生成器) 和 Evaluator (评估器) 双节点自适应闭环。
      初始生成宏观空洞回答，被严格的评估器打回，Generator 结合反馈重构并植入物理指令与代码，
      成功通过反思评审，最终输出高可用技术回答。
输入参数：无。
输出返回值：控制台打印初版理论回答、打回重审反馈、改写后的硬核回答与通过审计日志。
"""

# 导入 JSON 序列化解析库，用于处理自检结论
import json
# 导入 TypedDict 结构，用于图状态定义
from typing import TypedDict
# 导入 LangChain 消息类
from langchain_core.messages import HumanMessage
# 导入 LangGraph 状态图机类
from langgraph.graph import StateGraph, END

# 导入公共模型工厂函数
from common.model_factory import create_model


# ============================================================
# 1. 定义自我反思图的全局共享状态 (State)
# ============================================================

class ReflectionState(TypedDict):
    """
    自我反思图状态结构定义。

    功能：描述并维护 Generator 与 Evaluator 交互中的所有变量。
    字段说明：
        input: 用户的原始提问请求。
        response: 当前生成器节点产出的最新回答内容。
        feedback: 评估器节点针对当前回答给出的纠错反馈意见（若合格则为 "合格"）。
        iteration: 当前已重试自检迭代的次数，用于控制最大重试防死循环。
    """
    # 用户原始问题
    input: str
    # AI 产出回答
    response: str
    # 专家反馈意见
    feedback: str
    # 迭代深度计数器
    iteration: int


# ============================================================
# 2. 定义状态图中的节点逻辑 (Nodes)
# ============================================================

def generator_node(state: ReflectionState):
    """
    答案生成器节点逻辑 (Generator)。

    功能：根据用户问题和当前的 Evaluator 专家意见重新编写并丰富回答。如果是首次生成，则生成宏观大纲；如果是重写阶段，则大力代偿充实干货。
    输入参数：
        state (ReflectionState): 图共享状态字典。
    输出返回值：
        dict: 更新 response 字段和 iteration 计数。
    """
    # 获取当前的迭代次数
    current_iter = state.get("iteration", 0)
    # 累加迭代数
    updated_iter = current_iter + 1

    print(f"\n✍️ [Node: Generator] 正在开展第 {updated_iter} 轮内容撰写工作...")

    # 从公共工厂创建生成器模型实例（教学阶段 04 之后默认 LLM 走 xiaomi mimo）
    generator_model = create_model(provider="xiaomi mimo", temperature=0.5)

    # 如果反馈为空，说明是第一轮初始生成
    if not state["feedback"]:
        # 初始 Prompt：故意不提示需要写代码，让模型生成一份理论文章
        gen_prompt = (
            "你是一个知识广博的技术作家。\n"
            f"请针对用户的提问: '{state['input']}'，撰写一篇条理清晰的中文概述。"
        )
    else:
        # 重写 Prompt：强力命令模型必须结合反馈意见，精准代偿具体的终端命令和代码示例
        print("💡 Generator 收到专家反馈，正在吸纳修改意见重构文章...")
        gen_prompt = (
            "你是一个极其负责、技术过硬的资深技术专家。\n"
            f"用户的提问是: '{state['input']}'\n\n"
            f"你上一轮撰写的回答是:\n{state['response']}\n\n"
            "【来自评审专家的严厉打回反馈】:\n"
            f"'{state['feedback']}'\n\n"
            "【重构修改令】\n"
            "请你对原回答进行彻底的全面重构！你必须牢牢吸纳专家的意见，在回答中【精准添加具体的实操终端命令】"
            "以及【核心的基础代码演示】，用详实的物理干货把宏观的空洞理论充实起来，给出一份无可挑剔的高含金量中文指南！"
        )

    # 运行生成
    response = generator_model.invoke([HumanMessage(content=gen_prompt)])
    # 提取内容
    answer_text = response.content.strip()

    # 打印成果概要
    print(f"✅ Generator 撰写完毕！回答字数: {len(answer_text)} 字。")

    # 返回状态增量
    return {
        "response": answer_text,
        "iteration": updated_iter
    }


def evaluator_node(state: ReflectionState):
    """
    评审专家节点逻辑 (Evaluator)。

    功能：对生成器的回答进行逻辑和事实硬核质量检测。检查其中是否包含 actionable 物理命令或代码，决定是 PASS 还是 REVISE。
    输入参数：
        state (ReflectionState): 图共享状态字典。
    输出返回值：
        dict: 更新反馈内容 feedback 字段。
    """
    print("\n🧐 [Node: Evaluator] 评审专家正在对当前的回答质量进行硬核审计...")
    # 从工厂创建评审模型（evaluator 是 2 号 LLM，沿用 deepseek 作为"其他"）
    evaluator_model = create_model(provider="deepseek", temperature=0.0)

    # 构造评审 Prompt，强制要求大模型按照 JSON 决策
    eval_prompt = (
        "你是一个极其严厉、绝不容许敷衍的技术评审专家。\n"
        "你需要对 AI 的回答进行质量核验。你判断的硬性及唯一指标是：\n"
        "回答中是否包含【具体的实操终端配置指令】以及【基础的核心代码演示】？\n\n"
        f"用户提问: '{state['input']}'\n"
        f"待评估的 AI 回答:\n{state['response']}\n\n"
        "【评审抉择规则】\n"
        "1. 如果你发现回答中仅有空洞宏观的理论概念，【缺乏物理实操命令和代码】，必须将其打回重审！\n"
        "   此时，输出 JSON 格式如下：\n"
        "   {\n"
        "     \"verdict\": \"REVISE\",\n"
        "     \"feedback\": \"打回修改原因：你的回答过于务虚，仅仅堆砌了理论概念，完全没有具体的终端安装配置命令或者任何代码演示！请必须补充具体实操干货！\"\n"
        "   }\n"
        "2. 如果回答中已经补充了清晰的实操终端配置命令、可落地的基础代码，且条理极度清晰，直接判定合格，输出：\n"
        "   {\n"
        "     \"verdict\": \"PASS\",\n"
        "     \"feedback\": \"合格\"\n"
        "   }\n\n"
        "请现在给出你的 JSON 评审结论数据："
    )

    response = evaluator_model.invoke([HumanMessage(content=eval_prompt)])
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
        # 解析评审数据
        eval_data = json.loads(output_text)
        verdict = eval_data.get("verdict", "REVISE")
        feedback_text = eval_data.get("feedback", "不合格")
    except Exception as err:
        print(f"⚠️ Evaluator JSON 解析失败: {str(err)}。默认判定需重审。")
        verdict = "REVISE"
        feedback_text = "回答质量尚未达到硬核实操标准，请添加具体的命令与代码。"

    # 如果审核结论是通过
    if verdict == "PASS":
        # 打印通过消息
        print("🎉 审核通过！[Verdict: PASS] 回答质量非常过硬，充满干货，予以出库！")
        # 将反馈置为合格
        return {"feedback": "合格"}
    else:
        # 打印打回日志
        print("🚨 审核不合格！[Verdict: REVISE]")
        print(f"🚨 反馈意见: '{feedback_text}'")
        # 返回专家的修改建议
        return {"feedback": feedback_text}


# ============================================================
# 3. 定义条件边流转路由规则 (Conditional Edges)
# ============================================================

def should_continue(state: ReflectionState):
    """
    自检反思路由判定函数。

    功能：根据专家的反馈意见以及迭代次数，决定是打回重新写，还是直接宣告结束输出。
    输入参数：
        state (ReflectionState): 图共享状态字典。
    输出返回值：
        str: 跳转的下一个节点名（"generate" 或 "end"）。
    """
    # 检查反馈是否为合格
    if state["feedback"] == "合格":
        # 审核合格，去往 END 结束点
        return "end"
    else:
        pass

    # 检查当前迭代深度，防止过多重试消耗 tokens
    if state["iteration"] >= 3:
        # 达到最大 3 次迭代强制出库，去往 END 结束点
        print("\n⚠️ 自我反思已达最大迭代次数限制，开启兜底安全阀，强制输出。")
        return "end"
    else:
        # 否则回大炉重造，去往 generator 节点修改
        return "generate"


def main():
    """
    主运行函数。

    功能：构建有向反思图机，编译并测试“如何使用 Python requests 库进行基本的 API 调用”。
    """
    # 用户的提问任务
    test_question = "帮我讲解一下在 Python 中如何使用 requests 库发送一个带 headers 的 POST 请求？"

    print("🛠️ 正在构建带自我反思机制的智能审核图机...")
    # 初始化状态图机
    workflow = StateGraph(ReflectionState)

    # 载入两大核心节点
    workflow.add_node("generator", generator_node)
    workflow.add_node("evaluator", evaluator_node)

    # 设定起始入口为生成器
    workflow.set_entry_point("generator")

    # 生成器生成后，必须且无条件进入评估器开展硬核质量自检
    workflow.add_edge("generator", "evaluator")

    # 评估完毕后，使用条件边 should_continue 决定动向：
    #   - 判定结果不合格且重试在限制内，返回 "generate" -> 再次跳转到 generator
    #   - 判定结果合格或超出重试，返回 "end" -> 跳转到 END 终点结束
    workflow.add_conditional_edges(
        "evaluator",
        should_continue,
        {
            "generate": "generator",
            "end": END
        }
    )

    # 编译有向图机
    app = workflow.compile()
    print("✅ 自我反思审核图机编译成功！")

    print("\n🚀 正在启动 Self-Reflection Agent 处理流程...")
    print(f"用户提问: '{test_question}'")
    print("=" * 60)

    # 启动图机运行，传入空初始状态
    result = app.invoke({
        "input": test_question,
        "response": "",
        "feedback": "",
        "iteration": 0
    })

    print("\n" + "=" * 60)
    print("⭐ 最终通过专家硬核自审的 AI 高质量回答:")
    print("=" * 60)
    # 打印最终输出的硬核代码指南
    print(result["response"])
    print("=" * 60)
    print("✨ 自我反思与自检闭环演示大获成功。")


# 判断是否自命令行直接启动
if __name__ == "__main__":
    # 执行主程序
    main()
