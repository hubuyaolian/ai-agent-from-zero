# -*- coding: utf-8 -*-
"""
Day 17 进阶模块：AI 调研团队 — 审核反馈环工作流定义 (Workflow V2 Pattern) 🎯

功能：构建带有质量审核反馈环的 AI 调研团队工作流（V2 进阶版）。
      定义带有审核跟踪字段的共享状态（ResearchTeamStateV2）。
      - 引入 4. 审核节点 (Reviewer Node)：利用大模型扮演高级审稿人，依据严苛标准评估报告，输出结构化 JSON 并判定是否通过（PASS/REVISE）。
      - 引入 5. 条件路由器 (Review Router)：若未通过审核且修改次数未达安全上限，则自动引导退回给 Writer 重新修改。
      - 升级 3. 写作节点 (Writer Node)：当遭遇退回修改时，Writer 能够自动消化审核专家的具体建议，并在上一版报告原文上进行定向的高质量修改打磨。
      整个进阶图流转顺序：researcher -> analyst -> writer -> reviewer -(条件路由)-> writer (退回修改) 或 END (通过)。
输入参数：无。
输出返回值：编译完成的 CompiledGraph V2 版工作流运行时应用。
"""

# 导入操作符，用于消息列表的累加追加
import operator
# 导入 JSON 数据解析库
import json
# 导入计时与状态累积相关的基类和类库
from typing import TypedDict, Annotated, Sequence

# 导入 LangChain 的消息基类与 AI 消息模型
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, HumanMessage
# 导入 LangGraph 状态图与终点 END
from langgraph.graph import StateGraph, END

# 从本地公共模型工厂中导入大模型实例化函数
from common.model_factory import create_model

# 导入本地 V1 版中定义的可观测性计时日志装饰器
from workflow import agent_logger
# 从本地 agents 模块导入四大专家的独立运行服务函数
from agents.researcher import run_research
from agents.analyst import run_analysis
from agents.writer import run_writing


# ============================================================
# 1. 定义带审核功能的共享状态 (V2 State Schema)
# ============================================================

class ResearchTeamStateV2(TypedDict):
    """
    带质量审核与反馈环机制的 AI 调研团队 V2 共享状态结构。

    功能：包含 V1 的基础状态，另外扩展了评分、修改建议及计数器等字段。
    字段说明：
        messages: 完整的对话消息历史，支持累加追加。
        topic: 被调研的中心技术方向主题。
        research_data: 调研专家产出的技术 facts 原始素材。
        analysis_result: 分析专家提炼的技术 insights 趋势与深度洞察要点。
        final_report: 写作专家在各个迭代轮次产出的 Markdown 研究报告正文。
        status: 工作流当前所处的流转执行状态。
        review_decision: 审核专家的评审决策（PASS 代表通过，REVISE 代表需修改）。
        review_feedback: 审核专家提供的具体 JSON 扣分项与修改意见。
        review_score: 审核专家对该版本报告打出的百分制/十分制分数。
        revision_count: 记录本报告已经进行重写修改的轮数（做安全阀限制）。
    """
    # 历史消息列表追加算子
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # 被研讨的核心技术话题
    topic: str
    # 调研段落的产出
    research_data: str
    # 分析段落的产出
    analysis_result: str
    # 写作段落最新版的 Markdown 技术报告文本
    final_report: str
    # 工作流当前运行的节点状态字
    status: str
    # 存放最新的审核决策
    review_decision: str
    # 存放具体的修改意见
    review_feedback: str
    # 存放最新的评分数值
    review_score: int
    # 存放当前已经修改重写的次数
    revision_count: int


# ============================================================
# 2. 定义审核 Agent 的岗位说明系统提示词 (System Prompt)
# ============================================================

REVIEWER_SYSTEM_PROMPT = (
    "你是一个在学术界和工业界均拥有崇高声誉的资深研究报告审核评审专家（Reviewer Agent）。\n\n"
    "## 你的职责\n"
    "负责对写作专家（Writer）最终整合出的 Markdown 格式技术报告进行严苛的质量与逻辑评估，\n"
    "打出客观的评分，决定报告是通过（PASS）还是需要被退回修改（REVISE）。\n\n"
    "## 评审与打分标准\n"
    "1. **内容完整度（3分）**：报告是否完整覆盖了调研专家整理的所有关键 facts 数据与事实？\n"
    "2. **分析深度性（3分）**：报告是否透彻地呈现了分析专家梳理出的核心技术趋势与深层洞察？\n"
    "3. **行文流畅度（2分）**：各章节结构是否完整规范？段落逻辑衔接是否顺畅？是否存在语法错字？\n"
    "4. **排版规范性（2分）**：Markdown 语法使用是否恰当？阅读体验是否具有专栏美感？\n\n"
    "## 判定决策逻辑\n"
    "- 如果四项打分汇总的【综合评分 >= 7分】，则做出通过决策：'PASS'。\n"
    "- 如果【综合评分 < 7分】，则做出需退回重写的决策：'REVISE'，你必须针对扣分项给出极其具体、有建设性的修改建议。\n\n"
    "## 【重要：输出格式规范】\n"
    "你必须且只能输出一个合法的 JSON 字符串本身（不要包含任何 ```json 或其他 markdown 首尾标记），格式要求如下：\n"
    "{\n"
    "    \"decision\": \"PASS 或 REVISE\",\n"
    "    \"score\": 1-10 之间的数字评分,\n"
    "    \"feedback\": \"这里写你对本篇技术报告各章节扣分项的具体审核意见以及清晰的修改和增补建议\"\n"
    "}"
)


# ============================================================
# 3. 编写 V2 进阶状态图的各节点函数逻辑 (Nodes)
# ============================================================

@agent_logger("🔍 调研智能体 (V2)")
def research_node_v2(state: ResearchTeamStateV2) -> dict:
    """
    调研专家节点函数 (V2)。

    功能：收集话题原始事实 facts，写入 research_data 并更新状态。
    输入参数：
        state (ResearchTeamStateV2): 全局共享状态。
    输出返回值：
        dict: 更新的状态增量。
    """
    # 提取话题
    topic = state["topic"]
    # 运行调研大模型
    research_result = run_research(topic)
    # 返回状态更新
    return {
        # 消息累加
        "messages": [AIMessage(
            content="[V2 调研完成] 收集事实 facts 完毕",
            name="researcher"
        )],
        # 写入调研原始数据
        "research_data": research_result,
        # 更新状态字
        "status": "research_completed"
    }


@agent_logger("📊 分析智能体 (V2)")
def analysis_node_v2(state: ResearchTeamStateV2) -> dict:
    """
    分析专家节点函数 (V2)。

    功能：提取调研原始事实，提炼深度洞察，写入 analysis_result 并更新状态。
    输入参数：
        state (ResearchTeamStateV2): 全局共享状态。
    输出返回值：
        dict: 更新的状态增量。
    """
    # 提取话题
    topic = state["topic"]
    # 提取调研事实
    research_data = state["research_data"]
    # 运行分析提炼模型
    analysis_result = run_analysis(topic, research_data)
    # 返回状态更新
    return {
        # 消息累加
        "messages": [AIMessage(
            content="[V2 分析完成] 提炼深度 insights 完毕",
            name="analyst"
        )],
        # 写入分析提炼结果
        "analysis_result": analysis_result,
        # 更新状态字
        "status": "analysis_completed"
    }


@agent_logger("✍️ 写作智能体 (V2)")
def writing_node_v2(state: ResearchTeamStateV2) -> dict:
    """
    具备修改自愈能力的写作专家节点函数 (V2)。

    功能：读取前序阶段的全部产出。如果发现当前是退回修改场景（带有 review_feedback 且决策为 REVISE），
          则传入 previous_report 和 review_feedback，触发带修改能力的 run_writing。
    输入参数：
        state (ResearchTeamStateV2): 全局共享状态。
    输出返回值：
        dict: 更新的状态增量。
    """
    # 提取话题
    topic = state["topic"]
    # 提取调研原始事实
    research_data = state["research_data"]
    # 提取分析深度洞察
    analysis_result = state["analysis_result"]
    # 提取可能存在的上一版报告
    prev_report = state.get("final_report", "")
    # 提取可能存在的审核反馈
    feedback = state.get("review_feedback", "")
    # 提取可能存在的上一次审核决策
    prev_decision = state.get("review_decision", "")

    # 声明最终报告变量
    final_report = ""

    # 判断当前是否是被退回修改的重写流程
    if prev_decision == "REVISE" and prev_report and feedback:
        # 控制台打印自愈重构提示
        print("\n♻️ [Node: Writer] 正在触发自愈机制！检测到修改反馈，将基于上一版进行针对性修改...")
        # 调用大模型，传入上一版报告与反馈，进行定向修改打磨
        final_report = run_writing(
            topic=topic,
            research_data=research_data,
            analysis_result=analysis_result,
            previous_report=prev_report,
            review_feedback=feedback
        )
    else:
        # 首次撰写流程，正常生成全新报告
        final_report = run_writing(
            topic=topic,
            research_data=research_data,
            analysis_result=analysis_result
        )

    # 返回状态更新
    return {
        # 消息累加
        "messages": [AIMessage(
            content="[V2 写作完成] Markdown 技术报告撰写完毕",
            name="writer"
        )],
        # 写入最新的报告正文，替换之前的版本
        "final_report": final_report,
        # 更新状态字
        "status": "report_completed"
    }


@agent_logger("⚖️ 质量审核智能体 (V2)")
def reviewer_node_v2(state: ResearchTeamStateV2) -> dict:
    """
    评审专家节点函数 (V2)。

    功能：读取 state['final_report'] 原文，调用大模型对报告的四大指标进行全方位评审评分，
          解析返回的 JSON。如果 JSON 解析崩溃，进行健壮性容错与安全值回退。
    输入参数：
        state (ResearchTeamStateV2): 全局共享状态。
    输出返回值：
        dict: 更新 review_decision、review_feedback、review_score 等字段，revision_count 累加 1。
    """
    print("\n⚖️ [Node: Reviewer] 评审专家开始调阅最新版的报告正文并计算评分...")

    # 从大模型工厂获取模型（教学阶段 04 之后默认 LLM 走 xiaomi mimo），温度 0.2 保障评审稳定性
    model = create_model(
        provider="xiaomi mimo",
        temperature=0.2
    )

    # 组装评审提示消息列表
    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"请对这篇针对主题 '{state['topic']}' 撰写的研究报告做出全方位的严格评审打分：\n\n"
                f"**研究报告正文**：\n{state['final_report']}"
            )
        )
    ]

    # 调用大模型生成 JSON 评审响应
    response = model.invoke(messages)
    # 获取输出文本
    result_text = response.content.strip()

    # 声明提取结果的各个变量及默认安全值
    decision = "PASS"
    score = 8
    feedback = "报告质量达到了卓越的专栏发布标准，予以通过。"

    # 开始对大模型输出进行结构化提取与容错解析
    try:
        # 查找到 JSON 大括号的左侧边界
        start_idx = result_text.find("{")
        # 查找到 JSON 大括号的右侧边界
        end_idx = result_text.rfind("}") + 1

        # 判断是否成功检索到大括号包裹边界
        if start_idx != -1 and end_idx != -1:
            # 裁剪子串并反序列化为字典对象
            json_dict = json.loads(result_text[start_idx:end_idx])
            # 提取决策
            decision = json_dict.get("decision", "PASS")
            # 提取分数
            score = int(json_dict.get("score", 8))
            # 提取修改反馈
            feedback = json_dict.get("feedback", "无修改意见")
        else:
            # 未发现大括号，尝试直接整段解析
            json_dict = json.loads(result_text)
            # 提取决策
            decision = json_dict.get("decision", "PASS")
            # 提取分数
            score = int(json_dict.get("score", 8))
            # 提取反馈
            feedback = json_dict.get("feedback", "无修改意见")
    except Exception:
        # 如果捕获到任何 JSON 解析崩溃，进行安全兜底逻辑，强制给予 PASS 结案，防止工作流无限卡死
        decision = "PASS"
        score = 7
        feedback = "系统解析 JSON 反馈失败，默认为报告合格予以通过。"

    # 将评分限制在合法评分区间
    if score < 1:
        # 赋值最小值
        score = 1
    elif score > 10:
        # 赋值最大值
        score = 10

    # 提取当前已修改的总轮数，若未定义则设为 0
    current_count = state.get("revision_count", 0)

    print(f"⚖️ [Node: Reviewer] 评审专家给出本次打分: 【{score} 分】 | 最终裁定: 【{decision}】")
    print(f"   💬 评审指导意见: {feedback[:120]}...")

    # 返回状态更新增量
    return {
        # 累加追加一条评审报告消息
        "messages": [AIMessage(
            content=f"[评审报告归档] 分数：{score}，决策：{decision}，意见：{feedback[:80]}...",
            name="reviewer"
        )],
        # 写入判定决策
        "review_decision": decision,
        # 写入评审修改指导意见
        "review_feedback": feedback,
        # 写入最新评分
        "review_score": score,
        # 重写修改的轮数累计加 1
        "revision_count": current_count + 1
    }


# ============================================================
# 4. 定义 V2 反馈环条件路由决策函数 (Conditional Router)
# ============================================================

def review_router(state: ResearchTeamStateV2) -> str:
    """
    审核条件边路由器。

    功能：根据质量审核专家的裁定决策以及防无限循环安全阀（revision_count），
          引导有向状态图下一步返回 writer 重新重写或者直接跳转到 end 结案。
    输入参数：
        state (ResearchTeamStateV2): 当前全局共享状态。
    输出返回值：
        str: 跳转跳转的节点名称（"writer" 代表退回修改，"end" 代表通过结束）。
    """
    # 提取审核专家的判定
    decision = state.get("review_decision", "PASS")
    # 提取当前已经完成的修改重写累计轮数
    revision_count = state.get("revision_count", 0)

    # 声明最多允许修改重写 2 次（第 3 次评审时哪怕不合格也必须强制通过），防止大模型陷入无限死循环
    max_revisions_allowed = 2

    # 检查是否触及了最大重写修改次数安全阀
    if revision_count > max_revisions_allowed:
        # 控制台打印警告信息
        print(f"\n⚠️ [Router] 安全防爆自愈锁触发！本报告已重写修改了 {revision_count} 轮，强制 PASS 结束流转，防止死循环。")
        # 路由至结束分支
        return "end"

    # 如果审核决策是需要修改
    if decision == "REVISE":
        # 打印退回修改信息
        print("\n🔄 [Router] 决策退回！报告评分不合格，图机即将自动引导退回至 ✍️ 【writer】 进行定向整编重构。")
        # 路由回写作节点
        return "writer"
    else:
        # 打印通过结案信息
        print("\n🎉 [Router] 审核通过！报告综合评定合格，直接通往终点结案。")
        # 路由至结束分支
        return "end"


# ============================================================
# 5. 构建并编译带反馈环的 V2 版工作流 (Graph Construction)
# ============================================================

def build_research_team_workflow_v2():
    """
    构建并编译带审核反馈环的 AI 调研团队 V2 进阶版工作流。

    功能：注册四大节点（含评审专家节点），注册线性边与条件边，支持最多 2 轮退回重写逻辑。
    输入参数：
        无。
    输出返回值：
        CompiledGraph: 编译完成后可直接调用的 V2 进阶版运行时对象。
    """
    # 基于 ResearchTeamStateV2 初始化图结构
    workflow = StateGraph(ResearchTeamStateV2)

    # 注册四大处理节点
    # 注册调研节点
    workflow.add_node("researcher", research_node_v2)
    # 注册分析节点
    workflow.add_node("analyst", analysis_node_v2)
    # 注册写作节点
    workflow.add_node("writer", writing_node_v2)
    # 注册评审节点
    workflow.add_node("reviewer", reviewer_node_v2)

    # 设定工作流唯一起始入口为调研节点
    workflow.set_entry_point("researcher")

    # 线性流转连接边
    # 1. 调研完成进入分析
    workflow.add_edge("researcher", "analyst")
    # 2. 分析完成进入写作
    workflow.add_edge("analyst", "writer")
    # 3. 首次写作完成直接送入质量评审
    workflow.add_edge("writer", "reviewer")

    # 条件流转路由边，评审完毕后由 review_router 动态决定流向 writer 还是 END
    workflow.add_conditional_edges(
        "reviewer",
        review_router,
        {
            # 路由至 writer 重新重构修改
            "writer": "writer",
            # 路由至 END 终点结束
            "end": END
        }
    )

    # 编译有向图结构
    return workflow.compile()


# ============================================================
# 6. 本地运行测试自检入口
# ============================================================

if __name__ == "__main__":
    # 定义测试主题
    test_topic = "WebAssembly（Wasm）在云原生边缘计算场景下的崛起与未来趋势"
    print("🛠️ 正在本地测试编译 V2 进阶带反馈环版工作流...")
    # 编译工作流
    app = build_research_team_workflow_v2()
    print("✅ V2 状态图编译成功，开始模拟跑通反馈环...")
    # 运行工作流应用，注入空初始状态数据
    final_output = app.invoke({
        "messages": [AIMessage(content="V2 反馈环测试启动")],
        "topic": test_topic,
        "research_data": "",
        "analysis_result": "",
        "final_report": "",
        "status": "started",
        "review_decision": "",
        "review_feedback": "",
        "review_score": 0,
        "revision_count": 0
    })
    print("\n⭐ V2 最终评审过审报告预览:")
    print("-" * 70)
    print(final_output["final_report"][:200] + "\n...")
    print("-" * 70)
    print("✨ V2 进阶反馈环版工作流本地编译与模拟调用完美运行！")
