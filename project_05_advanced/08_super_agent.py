# -*- coding: utf-8 -*-
"""
Day 13 演示：综合高级 Super Agent (集大成者) 🦸

功能：构建一个集成了宏观规划 (Planning)、步骤执行 (Execution)、
      敏感操作人工审批中断 (Human-in-the-loop) 以及自我反思质检 (Self-Reflection) 的集大成智能体。
      - 智能判断任务复杂度，对简单任务直接 ReAct 回答，对复杂任务制定两阶段计划。
      - 在计划执行到高危物理写文件时，通过中断机制挂起，等待命令行人类的 y/n 安全确认。
      - 动作恢复后，生成最终技术报告，并交由严格的 Evaluator 节点进行质检，
        若质检不合格（缺乏实操结论或写盘详情）则退回重写，通过后方可输出。
输入参数：无。
输出返回值：控制台流式展示规划、审批挂起、写盘通过/被拒、自我反思以及最终安全出库的完整运行轨迹。
"""

# 导入 JSON 处理库，用于大模型输出计划与反思结果的结构化反序列化
import json
# 导入操作系统相关库，用于敏感动作写物理磁盘与后续文件删除清理
import os
# 导入 TypedDict 结构，定义图的全局共享状态
from typing import TypedDict, List, Dict
# 导入 LangChain 的消息对象，用于多节点 LLM 对话
from langchain_core.messages import HumanMessage
# 导入 LangGraph 核心图组件与状态终点 END
from langgraph.graph import StateGraph, END
# 导入内存保存器，作为人类介入审批的持久化检查点
from langgraph.checkpoint.memory import MemorySaver

# 导入公共模型工厂，构建高精度底层大模型实例
from common.model_factory import create_model


# ============================================================
# 1. 定义 Super Agent 图的全局共享状态 (State)
# ============================================================

class SuperAgentState(TypedDict):
    """
    Super Agent 状态结构定义。

    功能：集中管理和维护 Super Agent 状态图机中所有节点流转的共享变量。
    字段说明：
        task: 用户发出的任务请求。
        task_type: 任务复杂度分类，"simple" (简单问答) 或 "complex" (多步骤任务)。
        plan_steps: 宏观规划阶段生成的具体子任务步骤列表。
        current_step_idx: 复杂任务执行中，当前正运行的步骤索引 (1-indexed)。
        execution_context: 步骤执行器在各阶段执行后累加的运行日志或临时数据上下文。
        response: 最终或阶段性生成的回答文本。
        feedback: 反思评估节点对当前回答给出的纠错反馈，合格则为 "合格"。
        iteration: 反思迭代深度计数器，限制防死循环。
        approval_status: 人类审批状态，可选 "pending" (待定)、"approved" (批准) 或 "rejected" (拒绝)。
        file_path: 敏感操作中拟写入的目标物理文件路径。
        file_content: 敏感操作中拟写入的文件具体文本内容。
    """
    # 用户的提问指令
    task: str
    # 任务复杂度分类
    task_type: str
    # 计划步骤列表
    plan_steps: List[Dict[str, str]]
    # 当前执行步骤 the step index
    current_step_idx: int
    # 累加的执行结果记录
    execution_context: str
    # 生成的最新阶段性回答
    response: str
    # 自我反思纠错反馈
    feedback: str
    # 当前反思迭代次数
    iteration: int
    # 人类介入审批结论
    approval_status: str
    # 写文件的目标路径
    file_path: str
    # 写文件的具体文本
    file_content: str


# ============================================================
# 2. 定义状态图中的节点逻辑 (Nodes)
# ============================================================

def planner_node(state: SuperAgentState):
    """
    宏观规划与任务分类节点 (Planner)。

    功能：根据用户指令研判任务复杂度。如果是简单问答直接分类为 simple；
          如果是复杂多步任务（如需要计算并物理写入报告），则制定多步骤的 JSON 计划。
    输入参数：
        state (SuperAgentState): 图共享状态。
    输出返回值：
        dict: 更新 task_type 和 plan_steps。
    """
    print("\n🗺️ [Node: Planner] 正在研判任务复杂度并制定全局路线图...")

    # 从工厂获取主力 DeepSeek 模型，用于做严谨的任务拆解
    model = create_model(provider="deepseek", temperature=0.0)

    # 构造规划 Prompt
    planner_prompt = (
        "你是一个极其理智的系统分析与任务规划大师。\n"
        "你需要分析用户的请求，判断其是一步到位的简单问答，还是需要多步执行的复杂任务（尤其是涉及计算加物理写盘的操作）。\n\n"
        "【分类与规划规则】\n"
        "1. 如果用户请求只是普通知识问答或单步骤查询，不需要写入文件，直接判定为 'simple'，并输出如下 JSON：\n"
        "   {\n"
        "     \"task_type\": \"simple\",\n"
        "     \"plan_steps\": []\n"
        "   }\n"
        "2. 如果用户请求需要进行计算、汇总并将其保存/物理写入到本地文件，判定为 'complex'，并制定恰好 2 个步骤的计划列表。\n"
        "   步骤 1 必须是进行数学计算或数据汇总，步骤 2 必须是将结果写入物理文件。\n"
        "   必须输出如下 JSON 格式：\n"
        "   {\n"
        "     \"task_type\": \"complex\",\n"
        "     \"plan_steps\": [\n"
        "       {\"step_id\": \"1\", \"desc\": \"[计算/汇总任务描述]\"},\n"
        "       {\"step_id\": \"2\", \"desc\": \"[保存物理文件任务描述]\"}\n"
        "     ]\n"
        "   }\n\n"
        f"用户提问: '{state['task']}'\n"
        "请直接给出对应的 JSON 格式分析数据，不需要任何其他解释："
    )

    # 调用大模型执行分析
    response = model.invoke([HumanMessage(content=planner_prompt)])
    # 提取并清理文本
    cleaned_content = response.content.strip()

    # 清理 markdown 反引号
    if cleaned_content.startswith("```"):
        # 寻找首个换行符
        newline_idx = cleaned_content.find("\n")
        # 截取核心 JSON
        cleaned_content = cleaned_content[newline_idx + 1:]
        # 去掉结尾的反引号
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3].strip()
        else:
            pass
    else:
        pass

    try:
        # 解析 JSON 规划结论
        plan_data = json.loads(cleaned_content)
        # 提取分类
        task_type = plan_data.get("task_type", "simple")
        # 提取规划步骤
        plan_steps = plan_data.get("plan_steps", [])
    except Exception as err:
        # 异常兜底，默认按 simple 流程安全走完
        print(f"⚠️ Planner 节点 JSON 解析失败: {str(err)}。已启用 simple 安全自适应分支。")
        task_type = "simple"
        plan_steps = []

    print(f"💡 [Node: Planner] 复杂度研判结果: {task_type}")
    if task_type == "complex":
        # 打印生成的步骤计划
        for step in plan_steps:
            print(f"   📍 步骤 {step.get('step_id')}: {step.get('desc')}")
    else:
        pass

    # 返回状态更新
    return {
        "task_type": task_type,
        "plan_steps": plan_steps,
        "current_step_idx": 1,
        "execution_context": ""
    }


def react_agent_node(state: SuperAgentState):
    """
    简单任务反应代理节点 (react_agent)。

    功能：处理简单任务类别，由大模型针对用户提问直接思考生成一份中文问答响应。
    输入参数：
        state (SuperAgentState): 图共享状态。
    输出返回值：
        dict: 更新 response 字段。
    """
    print("\n💬 [Node: ReAct Agent] 正在对简单任务执行极速推理与回答...")

    # 从工厂获取大模型实例
    model = create_model(provider="deepseek", temperature=0.7)

    # 构造简单生成提示
    prompt = (
        "你是一个学识渊博、表述亲切的专业 AI 技术顾问。\n"
        f"请针对用户的提问，给出一份详实、清晰、便于理解的中文解答。\n"
        f"用户提问: '{state['task']}'"
    )

    # 调用模型生成
    ai_response = model.invoke([HumanMessage(content=prompt)])
    # 提取回答
    response_text = ai_response.content.strip()

    print(f"✅ [Node: ReAct Agent] 回答生成完毕 (字数: {len(response_text)})")

    # 返回响应
    return {
        "response": response_text
    }


def executor_node(state: SuperAgentState):
    """
    复杂任务步骤执行器节点 (Executor)。

    功能：负责复杂任务中【第一阶段：数学计算/数据汇总】的具体处理。
          它会根据第一个步骤的描述进行严谨计算，将计算结果计入 execution_context，
          并输出下一阶段要写入的文件参数，准备流向敏感操作安全拦截拦截点。
    输入参数：
        state (SuperAgentState): 图共享状态。
    输出返回值：
        dict: 更新 execution_context 以及拟写文件的 file_path 与 file_content，
              并将 approval_status 初始化为 pending。
    """
    # 提取当前的步骤指针
    step_idx = state.get("current_step_idx", 1)
    # 提取全局规划步骤
    steps = state.get("plan_steps", [])

    print(f"\n⚙️ [Node: Executor] 正在执行步骤 {step_idx}/{len(steps)}...")

    # 获取当前步骤的具体任务描述
    current_step_desc = steps[0].get("desc", "计算任务")

    # 实例化高精度的分析模型
    model = create_model(provider="deepseek", temperature=0.0)

    # 构造执行计算的提示词
    execution_prompt = (
        "你是一个极其精确的数据分析与计算工具。\n"
        "你需要对下述具体任务描述进行严密计算，并以详实的中文给出计算和汇总过程，必须确保数值的精确无误。\n\n"
        f"当前子任务: '{current_step_desc}'\n"
        "请给出你的详细计算推理及最终数据答案："
    )

    # 触发模型运算
    ai_response = model.invoke([HumanMessage(content=execution_prompt)])
    # 获得计算结果
    calc_result = ai_response.content.strip()

    print("📊 [Node: Executor] 第一步数学计算/汇总完成！")
    # 记录执行日志
    log_text = f"【步骤1执行日志】: 已成功计算数据。计算详情为:\n{calc_result}\n"

    # ============================================================
    # 自动为下一步骤【敏感文件落地】进行参数构建与赋值
    # ============================================================
    # 指定拟写入的本地报告文件名
    target_file = "bonus_report.txt"
    # 生成拟物理写入的内容，结合步骤 1 的精确计算结果
    target_content = (
        "=========================================\n"
        "       AI 自动生成 - 资金测算与分配报告\n"
        "=========================================\n"
        f"原始任务需求: {state['task']}\n\n"
        f"【核心计算数据详情】:\n{calc_result}\n"
        "=========================================\n"
        "报告生成完毕，已经过 Super Agent 安全审批。\n"
    )

    # 打印Executor的准备工作
    print("📂 [Node: Executor] 已为步骤 2 生成写盘数据参数：")
    print(f"   - 目标路径: {target_file}")

    # 返回状态，指针指向第 2 步，并将状态置为 'pending' 触发中断
    return {
        "execution_context": log_text,
        "current_step_idx": 2,
        "file_path": target_file,
        "file_content": target_content,
        "approval_status": "pending"
    }


def safety_check_node(state: SuperAgentState):
    """
    高风险敏感行为安全拦截与物理落地节点 (safety_check_node)。

    功能：在此节点执行前会强行发生 interrupt 中断挂起。
          当外部输入 y 授权或 n 拒绝后恢复运行。
          - 授权批准：真正物理写入测试文件，更新 response 为报告数据及成功日志。
          - 拒绝驳回：跳过物理写盘，更新 response 为安全驳回日志。
    输入参数：
        state (SuperAgentState): 图共享状态。
    输出返回值：
        dict: 更新 response、execution_context 及 approval_status。
    """
    print("\n🛡️ [Node: Safety Check] 正在进入安全过滤审查流程...")

    # 获取当前人类管理员的审批状态
    approval = state.get("approval_status", "pending")
    # 获取目标文件路径
    file_path = state.get("file_path", "")
    # 获取要写入的内容
    file_content = state.get("file_content", "")
    # 提取已有的上下文
    current_context = state.get("execution_context", "")

    # 判断是否授权
    if approval == "approved":
        print("🟢 [Node: Safety Check] 安全口令已校验：【人类授权允许】。执行物理磁盘落地...")
        try:
            # 写入物理磁盘，采用 utf-8 防止中文损坏
            with open(file_path, "w", encoding="utf-8") as writer:
                writer.write(file_content)
            # 标记为写入成功
            status_text = f"【步骤2执行日志】: 物理写入成功。文件 '{file_path}' 已创建，数据已落地保存。"
            print(f"🎉 {status_text}")
        except Exception as err:
            # 捕获写入失败
            status_text = f"【步骤2执行日志】: 物理写入异常失败。错误原因为: {str(err)}"
            print(f"❌ {status_text}")

        # 拼接综合技术报告作为回答
        report_response = (
            f"你好！我已经为您完成了本次资金预算规划任务。\n\n"
            f"【实体报告已成功保存】\n"
            f"物理文件路径: {file_path}\n\n"
            f"【测算分析摘要】\n"
            f"{current_context}"
        )
    elif approval == "rejected":
        # 拦截驳回
        status_text = "【步骤2执行日志】: 人类管理员明确拒绝了物理写入申请，操作被拦截安全中断。"
        print(f"🛡️ {status_text}")
        # 返回安全友好答复
        report_response = (
            "你好！在本次资金预算规划任务中，我已为您算清了所有数据分配细则。\n"
            "但是，【由于人类管理员拒绝了写盘申请】，数据未能在本地保存为 bonus_report.txt 文件。\n\n"
            f"【测算分析摘要】\n"
            f"{current_context}"
        )
    else:
        # 未获授权的异常拦截
        status_text = "【步骤2执行日志】: 安全节点检测到未获审批指令，强制切断物理写盘。"
        print(f"⚠️ {status_text}")
        report_response = "⚠️ 系统在未获人工安全审批通过前越权试图物理写入，已予以安全切断。"

    # 更新全局上下文日志
    updated_context = current_context + f"\n{status_text}\n"

    # 返回状态，完成步骤 2 汇报
    return {
        "execution_context": updated_context,
        "response": report_response
    }


def reflector_node(state: SuperAgentState):
    """
    自我反思与专家质检节点 (reflector_node)。

    功能：对生成的最终 response 进行自我检验。
          - 评估维度：最终回答中是否包含了明确的“测算分析”或“报告保存/未保存”的状态总结？
          - 决策：若包含，判定合格并输出 JSON(PASS)；若敷衍了事，判定 REVISE 强令打回。
    输入参数：
        state (SuperAgentState): 图共享状态。
    输出返回值：
        dict: 更新 feedback 及 iteration 计数器。
    """
    # 累加当前的自检次数
    current_iter = state.get("iteration", 0)
    updated_iter = current_iter + 1

    print(f"\n🧐 [Node: Reflector] 正在对当前输出内容开展第 {updated_iter} 轮专家质检...")

    # 从工厂获取严厉的评估模型
    evaluator_model = create_model(provider="deepseek", temperature=0.0)

    # 构造质检 Prompt
    eval_prompt = (
        "你是一个极其苛刻、不容许敷衍的技术审查专家。\n"
        "你需要对 Agent 最终生成的回答进行严格审计，判定其回答质量是否合格。\n\n"
        "【审计硬性合格标准】\n"
        "1. 回答中必须有具体的测算总结或者分析数据，不能只有敷衍的理论空话！\n"
        "2. 如果是复杂任务，回答中必须明确向用户汇报物理文件的保存状态（例如：文件成功写入，或者人类拒绝写盘未写入）！\n\n"
        f"用户提问: '{state['task']}'\n"
        f"待审计的 AI 回答:\n{state['response']}\n\n"
        "【评审抉择规则】\n"
        "- 如果符合上述两项标准，返回：\n"
        "  {\n"
        "    \"verdict\": \"PASS\",\n"
        "    \"feedback\": \"合格\"\n"
        "  }\n"
        "- 如果不符合，判定为不合格，指出具体缺失的地方，返回：\n"
        "  {\n"
        "    \"verdict\": \"REVISE\",\n"
        "    \"feedback\": \"打回修改意见：[这里具体写出哪里不符合标准，要求怎么修改]\"\n"
        "  }\n\n"
        "请直接给出对应的 JSON 格式分析数据，不需要任何其他解释："
    )

    # 调用评估
    response = evaluator_model.invoke([HumanMessage(content=eval_prompt)])
    # 提取内容
    cleaned_content = response.content.strip()

    # 去除 Markdown 包裹
    if cleaned_content.startswith("```"):
        newline_idx = cleaned_content.find("\n")
        cleaned_content = cleaned_content[newline_idx + 1:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3].strip()
        else:
            pass
    else:
        pass

    try:
        # 解析评审结论
        eval_data = json.loads(cleaned_content)
        verdict = eval_data.get("verdict", "REVISE")
        feedback_text = eval_data.get("feedback", "质量未达标，需重修。")
    except Exception as err:
        # 异常兜底重修
        print(f"⚠️ Reflector JSON 解析失败: {str(err)}。默认判定需重审。")
        verdict = "REVISE"
        feedback_text = "回答质量尚未通过硬核审查，请补充资金测算细节与报告写盘状态。"

    # 评估结论逻辑处理
    if verdict == "PASS":
        print("🎉 [Node: Reflector] 审计通过！最终内容干货满满，准予出库安全发布！")
        # 将反馈标为合格
        feedback_text = "合格"
    else:
        print("🚨 [Node: Reflector] 质检不合格！内容被打回！")
        print(f"🚨 纠错建议: '{feedback_text}'")

    # 返回状态更新
    return {
        "feedback": feedback_text,
        "iteration": updated_iter
    }


# ============================================================
# 3. 定义条件边流转路由规则 (Conditional Edges)
# ============================================================

def route_after_planner(state: SuperAgentState):
    """
    Planner 节点后的条件路由函数。

    功能：根据任务复杂度，决定跳转到简单 ReAct 路径还是复杂 Executor 路径。
    输入参数：
        state (SuperAgentState): 图共享状态。
    输出返回值：
        str: "simple" 或 "complex"。
    """
    # 获取任务复杂度
    task_type = state.get("task_type", "simple")
    # 判断跳转逻辑
    if task_type == "complex":
        # 复杂路由
        return "complex"
    else:
        # 简单路由
        return "simple"


def route_after_reflector(state: SuperAgentState):
    """
    Reflector 节点后的条件反思路由函数。

    功能：判定是通过自审走向 END，还是根据任务类型打回对应的修改节点。
    输入参数：
        state (SuperAgentState): 图共享状态.
    输出返回值：
        str: "pass" (合格通过)、"complex_executor" (复杂任务重修) 或 "simple_agent" (简单任务重修)。
    """
    # 检查反馈是否为合格
    if state.get("feedback", "") == "合格":
        # 允许输出
        return "pass"
    else:
        pass

    # 检查重试次数，防止无限循环
    if state.get("iteration", 0) >= 3:
        print("\n⚠️ 专家反思重试深度已达上限 (3次)，启动兜底安全阀，强制出库。")
        # 强制允许输出
        return "pass"
    else:
        # 如果不合格，根据任务复杂度分发给对应的重修节点
        if state.get("task_type", "simple") == "complex":
            # 复杂任务返回对应的执行器重修分支
            return "complex_executor"
        else:
            # 简单任务返回反应代理重修分支
            return "simple_agent"


# ============================================================
# 4. 主程序：构建 Super Agent 图机并仿真运行
# ============================================================

def main():
    """
    主运行入口函数。

    功能：配置带有安全审批挂起 interrupt_before=['safety_check_node'] 的集大成 Super Agent 状态图机，
          进行【复杂任务测算并自动写报告】且分别触发人类【同意】与【拒绝】的完美闭环流程演示。
    """
    print("🛠️ 正在构建集大成 Super Agent 有向状态图机...")
    # 基于 SuperAgentState 实例化状态图
    workflow = StateGraph(SuperAgentState)

    # 1. 载入所有的功能型逻辑节点
    # 宏观分析与规划
    workflow.add_node("planner", planner_node)
    # 简单任务执行节点
    workflow.add_node("react_agent", react_agent_node)
    # 复杂任务步骤执行节点
    workflow.add_node("executor", executor_node)
    # 敏感操作安全审批物理节点
    workflow.add_node("safety_check_node", safety_check_node)
    # 自我反思质检节点
    workflow.add_node("reflector", reflector_node)

    # 2. 配置节点间的核心跳转与条件边
    # 设定有向图的唯一起始点为 planner 规划器
    workflow.set_entry_point("planner")

    # 规划完毕后，利用条件边判断路由到哪个处理节点：
    #   - 如果是 complex，跳转到 "executor" 节点
    #   - 如果是 simple，跳转到 "react_agent" 节点
    workflow.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "complex": "executor",
            "simple": "react_agent"
        }
    )

    # 简单生成完毕后，统一送交 reflector 专家进行硬核自审
    workflow.add_edge("react_agent", "reflector")

    # 复杂第一步计算完毕后，无条件流向敏感操作审批节点 safety_check_node。
    # 特别注意：我们将在这个节点执行前强制触发 interrupt 中断！
    workflow.add_edge("executor", "safety_check_node")

    # 审批物理动作（通过或拦截）完成后，同样送交 reflector 专家开展出库自审
    workflow.add_edge("safety_check_node", "reflector")

    # 评估自审完成后，利用条件边 route_after_reflector 决定后续流转：
    #   - 质检通过合格(pass)，直接去往 END 终点结束
    #   - 质检不合格，如果是 complex 跳转回 executor，如果是 simple 跳转回 react_agent
    workflow.add_conditional_edges(
        "reflector",
        route_after_reflector,
        {
            "pass": END,
            "complex_executor": "executor",
            "simple_agent": "react_agent"
        }
    )

    # 3. 编译图机并注入核心安全审批中断挂起参数！
    # 内存级持久化检查点，人类介入的核心底层依赖
    memory = MemorySaver()

    # 编译！
    # 关键参数设计：interrupt_before=["safety_check_node"] 保证在物理写入发生前强制暂停并等待管理员指令！
    app = workflow.compile(
        checkpointer=memory,
        interrupt_before=["safety_check_node"]
    )
    print("✅ 终极 Super Agent 状态图机编译大功告成！")

    # 定义本次测试的复杂任务提问（包含精密测算并要求落地保存）
    test_question = (
        "我们部门今年拿到了 120,000 元年终奖总额。"
        "请帮我按照 60% 分配给核心研发组，40% 分配给测试运营组进行测算。"
        "计算无误后请将这份测算报告保存到本地 'bonus_report.txt' 中。"
    )

    # 模拟审批授权与拒绝的两个会话线程 ID
    session_approve_id = "super_agent_approve_thread"
    session_reject_id = "super_agent_reject_thread"

    # =========================================================================
    # 仿真模拟场景一：人类管理员给予安全授权 (y)
    # =========================================================================
    print("\n" + "=" * 80)
    print("🦸 终极 Super Agent 实战演练 - 场景一：【人类管理员批准写盘】")
    print("=" * 80)
    print(f"用户复杂提问: '{test_question}'")

    # 配置授权线程配置字典
    config_approve = {"configurable": {"thread_id": session_approve_id}}

    print("\n🚀 启动 Super Agent 流程引擎...")
    # 第一阶段激活：图机自动运行 planner 和 executor 节点，并会在 safety_check_node 之前挂起
    app.invoke({
        "task": test_question,
        "task_type": "",
        "plan_steps": [],
        "current_step_idx": 0,
        "execution_context": "",
        "response": "",
        "feedback": "",
        "iteration": 0,
        "approval_status": "pending",
        "file_path": "",
        "file_content": ""
    }, config=config_approve)

    # 读取被中断时的当前图节点内部状态数据
    state_data = app.get_state(config_approve)
    print("\n⏸️ 【安全拦截信号】Super Agent 已自动在敏感写盘节点 [safety_check_node] 前触发中断挂起！")
    print("📊 提取当前申请写盘的参数数据:")
    print(f"   - 目标物理路径: {state_data.values.get('file_path')}")
    print(f"   - 拟写盘数据摘要:\n\"\"\"\n{state_data.values.get('file_content')}\n\"\"\"")

    # 仿真模拟人类管理员在命令行控制台输入批准 'y'
    user_approval_input = "y"
    print(f"❓ 【人类审批控制台】是否准许 Super Agent 写入此文件到您的本地磁盘？(y/n): {user_approval_input}")

    # 判断管理员的授权
    if user_approval_input.lower() == "y":
        print("🟢 收到授权！更新图状态，将 approval_status 修改为 'approved'...")
        # 利用 update_state 更新审批状态为 approved
        app.update_state(
            config_approve,
            {"approval_status": "approved"},
            as_node="executor"
        )
        print("⏯️ 正在唤醒流程引擎，恢复敏感操作执行及后续的自我反思质检闭环...")
        # 传入 None 恢复挂起
        final_state = app.invoke(None, config=config_approve)

        print("\n" + "=" * 80)
        print("⭐ 场景一最终出库安全答复:")
        print("=" * 80)
        # 最终回答展示
        print(final_state["response"])
    else:
        pass

    # 清理物理测试生成的文件，保持工作区干净整洁
    if os.path.exists("bonus_report.txt"):
        os.remove("bonus_report.txt")
        print("\n🗑️ [清理工作区] 测试生成的 bonus_report.txt 报告已被物理移除。")
    else:
        pass

    # =========================================================================
    # 仿真模拟场景二：人类管理员拒绝授权并拦截 (n)
    # =========================================================================
    print("\n" + "=" * 80)
    print("🦸 终极 Super Agent 实战演练 - 场景二：【人类管理员拒绝写盘】")
    print("=" * 80)
    print(f"用户复杂提问: '{test_question}'")

    # 配置拒绝线程配置字典
    config_reject = {"configurable": {"thread_id": session_reject_id}}

    print("\n🚀 启动 Super Agent 流程引擎...")
    # 图机运行，并在 safety_check_node 前触发中断挂起
    app.invoke({
        "task": test_question,
        "task_type": "",
        "plan_steps": [],
        "current_step_idx": 0,
        "execution_context": "",
        "response": "",
        "feedback": "",
        "iteration": 0,
        "approval_status": "pending",
        "file_path": "",
        "file_content": ""
    }, config=config_reject)

    print("\n⏸️ 【安全拦截信号】Super Agent 已自动在敏感写盘节点 [safety_check_node] 前触发中断挂起！")

    # 仿真模拟人类管理员在命令行控制台输入拒绝 'n'
    user_approval_input_reject = "n"
    print(f"❓ 【人类审批控制台】是否准许 Super Agent 写入此文件到您的本地磁盘？(y/n): {user_approval_input_reject}")

    # 判断管理员的驳回指令
    if user_approval_input_reject.lower() == "n":
        print("🔴 收到驳回！更新图状态，将 approval_status 修改为 'rejected'...")
        # 更新审批状态为 rejected
        app.update_state(
            config_reject,
            {"approval_status": "rejected"},
            as_node="executor"
        )
        print("⏯️ 正在唤醒流程引擎，恢复后续安全绕过分支执行及自我反思质检闭环...")
        # 传入 None 恢复挂起
        final_state_reject = app.invoke(None, config=config_reject)

        print("\n" + "=" * 80)
        print("⭐ 场景二最终出库安全答复:")
        print("=" * 80)
        # 最终回答展示
        print(final_state_reject["response"])
    else:
        pass

    print("=" * 80)
    print("✨ LangGraph 综合高级 Super Agent 流程闭环演示大获成功！")


# 判断是否自命令行直接启动
if __name__ == "__main__":
    # 执行主程序
    main()
