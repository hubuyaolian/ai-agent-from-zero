# -*- coding: utf-8 -*-
"""
Day 14 演示：多 Agent 状态管理与数据通信 (State Sharing & Communication) 👥

功能：使用 LangGraph 状态机搭建一个三阶段的线性辩论与裁判工作流。
      - 乐观派节点 (Optimist)：读取用户话题，给出正面狂热观点，写入共享状态 State；
      - 悲观派节点 (Pessimist)：从共享状态 State 中读取乐观派的观点，给予冷酷驳回，写入共享状态 State；
      - 裁判节点 (Referee)：从共享状态 State 中读取双方观点，进行绝对客观的统筹评判，产出兼听则明的客观报告。
      生动演示多 Agent 之间如何利用 LangGraph 共享的 TypedDict 机制进行零摩擦的数据交互与串联。
输入参数：无。
输出返回值：控制台流式展示乐观观点、悲观驳回以及裁判最终高含金量中立评估的报告文本。
"""

# 导入 TypedDict 结构，定义图的共享状态
from typing import TypedDict
# 导入 LangChain 的消息消息类
from langchain_core.messages import HumanMessage
# 导入 LangGraph 状态图类及终点 END
from langgraph.graph import StateGraph, END

# 从公共大模型工厂中导入模型创建函数
from common.model_factory import create_model


# ============================================================
# 1. 定义多 Agent 共享的全局图状态 (State Schema)
# ============================================================

class DebateState(TypedDict):
    """
    辩论状态结构定义。

    功能：描述多 Agent 辩论赛图工作流中所有的共享变量。
    字段说明：
        topic: 辩论核心话题。
        optimist_opinion: 乐观派发表的观点文本。
        pessimist_opinion: 悲观派进行犀利反驳的文本。
        referee_verdict: 最终中立裁判给出的客观评判报告。
    """
    # 辩论的核心话题
    topic: str
    # 乐观派的论证文字
    optimist_opinion: str
    # 悲观派的驳回文字
    pessimist_opinion: str
    # 裁判给出的最终客观意见
    referee_verdict: str


# ============================================================
# 2. 定义状态图中的节点逻辑 (Nodes)
# ============================================================

def optimist_node(state: DebateState):
    """
    乐观派发言节点 (optimist_node)。

    功能：从共享状态中读取核心话题，以乐观技术布道师的角度输出正面拥抱的观点。
    输入参数：
        state (DebateState): 图共享全局状态字典。
    输出返回值：
        dict: 更新 optimist_opinion 字段，以供后续悲观派和裁判使用。
    """
    print("\n🚀 [Node: Optimist] 乐观布道师正在积极组织正面观点陈述...")

    # 从工厂获取主力 DeepSeek 模型，设置较高随机性释放创造力
    model = create_model(provider="deepseek", temperature=0.7)

    # 构造针对性人设提示词
    optimist_prompt = (
        "你是一个对未来智能科技充满无限憧憬的狂热乐观主义者。\n"
        f"请针对今天辩论的核心命题: '{state['topic']}'，撰写一段慷慨激昂、极富前瞻与感染力的正面主张。\n"
        "你需要多用技术演进、生产力极大释放等论据，字数控制在 200 字左右。"
    )

    # 模型生成
    response = model.invoke([HumanMessage(content=optimist_prompt)])
    # 提取内容
    opinion_text = response.content.strip()

    print(f"✅ [Node: Optimist] 观点阐明: \"{opinion_text[:30]}...\"")

    # 返回状态更新，写入 optimist_opinion
    return {
        "optimist_opinion": opinion_text
    }


def pessimist_node(state: DebateState):
    """
    悲观派反驳节点 (pessimist_node)。

    功能：从共享状态（DebateState）中精准读取 optimist_opinion 字段的正面观点，
          以务实严苛的架构大师立场，有针对性地对乐观论点实施漏洞分析与冷酷反驳。
    输入参数：
        state (DebateState): 图共享全局状态字典。
    输出返回值：
        dict: 更新 pessimist_opinion 字段，以供后续裁判评估。
    """
    print("\n🛡️ [Node: Pessimist] 冷酷架构师正在审阅对方观点并展开防御性反击...")

    # 从工厂实例化大模型
    model = create_model(provider="deepseek", temperature=0.5)

    # 提取对方观点，展示共享状态的数据读取
    opponent_view = state.get("optimist_opinion", "")

    # 构造人设与反驳提示词
    pessimist_prompt = (
        "你是一个极其务实冷静、对技术吹毛求疵的顶尖软件架构师。\n"
        f"今天讨论的话题是: '{state['topic']}'\n\n"
        f"对方乐观主义者陈述了如下论点:\n\"{opponent_view}\"\n\n"
        "请你针对他的发言，有逻辑、有依据地进行逐条痛击与反弹！\n"
        "你需要指出他理想化背后的巨大安全风险、现实落地障碍以及幻觉等硬性致命缺陷。\n"
        "态度务实冷静且一针见血，字数控制在 200 字左右。"
    )

    # 模型生成
    response = model.invoke([HumanMessage(content=pessimist_prompt)])
    # 提取反驳内容
    rebuttal_text = response.content.strip()

    print(f"✅ [Node: Pessimist] 驳回观点发表: \"{rebuttal_text[:30]}...\"")

    # 返回状态更新，写入 pessimist_opinion
    return {
        "pessimist_opinion": rebuttal_text
    }


def referee_node(state: DebateState):
    """
    统筹中立裁判节点 (referee_node)。

    功能：同时读取 optimist_opinion 和 pessimist_opinion 的数据，
          在大脑中合并对比两方的优缺点，撰写一份高度中立客观、高含金量的辩论总结报告。
    输入参数：
        state (DebateState): 图共享全局状态字典。
    输出返回值：
        dict: 更新 referee_verdict 字段，完成终点答复。
    """
    print("\n⚖️ [Node: Referee] 客观裁判正在对双方辩证论点进行全面分析与统筹裁判...")

    # 从工厂创建一个极其稳定的裁判模型 (temperature=0.0)
    model = create_model(provider="deepseek", temperature=0.0)

    # 同时读取共享状态中双方留下的文字，充分展示多 Agent 通信交互
    opt = state.get("optimist_opinion", "")
    pes = state.get("pessimist_opinion", "")

    # 构造裁判指令
    referee_prompt = (
        "你是一个拥有绝对公正客观视角的行业顶尖智囊专家。\n"
        f"今天辩论的话题是: '{state['topic']}'\n\n"
        f"【乐观派的核心主张如下】:\n\"{opt}\"\n\n"
        f"【悲观派的反击论证如下】:\n\"{pes}\"\n\n"
        "【你的裁判职责】\n"
        "请你高度总结并对比双方的核心论点，辩证客观地指出各方的可取之处与偏颇之处，\n"
        "并结合前沿行业视角，得出一份兼听则明、极具实用参考价值的客观中立评判报告。\n"
        "字数控制在 400 字以内。"
    )

    # 调用模型
    response = model.invoke([HumanMessage(content=referee_prompt)])
    # 提取裁判结论
    verdict_text = response.content.strip()

    print("🎉 [Node: Referee] 裁判报告出炉！")

    # 返回状态更新，写入最终结论
    return {
        "referee_verdict": verdict_text
    }


# ============================================================
# 3. 主程序：构建 LangGraph 辩论状态图并实际演练
# ============================================================

def main():
    """
    主运行入口。

    功能：编译并流式执行由三大 Agent 节点接力协作构成的 DebateState 状态图。
    """
    # 辩论命题话题
    topic = "我们应该在企业级核心架构中大规模推广无服务架构 (Serverless) 吗？"

    print("🛠️ 正在构建多 Agent 状态共享通信图机...")
    # 基于 DebateState 声明状态图机
    workflow = StateGraph(DebateState)

    # 添加三大逻辑节点
    # 负责狂热正面描述的节点
    workflow.add_node("optimist", optimist_node)
    # 负责冷静指出风险的节点
    workflow.add_node("pessimist", pessimist_node)
    # 负责综合裁决的节点
    workflow.add_node("referee", referee_node)

    # 设定图的唯一起始点为 optimist 乐观节点
    workflow.set_entry_point("optimist")

    # 配置线性流转边：optimist 发言完后流向 pessimist 进行驳回
    workflow.add_edge("optimist", "pessimist")
    # pessimist 驳回完毕后流向 referee 裁判做总结
    workflow.add_edge("pessimist", "referee")
    # 裁判判定后流向 END 终点结束
    workflow.add_edge("referee", END)

    # 编译有向状态图
    app = workflow.compile()
    print("✅ 辩论通信状态图编译成功！")

    print("\n⚔️ 辩论会流程引擎启动！")
    print(f"📊 研讨议题: '{topic}'")
    print("=" * 80)

    # 启动工作流，传入话题作为初始参数，其余字段留空待节点自动填充
    result = app.invoke({
        "topic": topic,
        "optimist_opinion": "",
        "pessimist_opinion": "",
        "referee_verdict": ""
    })

    print("\n" + "=" * 80)
    print("⭐ 最终出炉的辩证中立裁判报告:")
    print("=" * 80)
    # 打印最终共享状态里的 referee_verdict 裁判意见
    print(result["referee_verdict"])
    print("=" * 80)
    print("✨ 多 Agent 基于 LangGraph 共享状态的无摩擦数据通信演练大获成功！")


# 判断是否自命令行直接启动
if __name__ == "__main__":
    # 执行主程序
    main()
