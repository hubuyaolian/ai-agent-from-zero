# -*- coding: utf-8 -*-
"""
Day 13 演示：基于 LangGraph interrupt_before 实现的人工介入审批流 (Human-in-the-Loop)。

功能：在 Agent 尝试执行高风险敏感操作（例如向本地磁盘物理写文件）之前，
      通过 LangGraph 的图中断机制强制暂停并挂起，在命令行终端提示人类管理员审批。
      如果管理员输入 'y' 批准，则图机恢复并执行写文件；如果输入 'n' 拒绝，则图机绕过敏感操作，
      提示拒绝信息并优雅结束，确保敏感动作的安全可控。
输入参数：无。
输出返回值：控制台打印图的暂停状态、人类审批提示符以及不同审批流下的物理执行结果。
"""

# 导入 JSON 解析库，用于解析大模型做出的规划和内容
import json
# 导入操作系统相关库，用于物理写入和清理测试文件
import os
# 导入 TypedDict 类型，用于定义图状态
from typing import TypedDict
# 导入 LangChain 消息类，用于与大模型交互
from langchain_core.messages import HumanMessage
# 导入 LangGraph 状态图核心类
from langgraph.graph import StateGraph, END
# 导入 LangGraph 内存状态保存器，人类介入中断必须使用 Checkpointer 持久化
from langgraph.checkpoint.memory import MemorySaver

# 导入公共大模型工厂接口
from common.model_factory import create_model


# ============================================================
# 1. 定义人工介入流程图的全局共享状态 (State)
# ============================================================

class SafetyState(TypedDict):
    """
    敏感操作审批图状态结构定义。

    功能：描述并记录在安全审批决策流中所有的状态字段。
    字段说明：
        task: 用户发出的任务请求指令。
        action: 拟执行的物理动作，如 "write_file"。
        file_path: 拟写入的目标文件物理路径。
        file_content: 拟写入的文件内容。
        approval_status: 人类审批状态，可选 "pending" (待定)、"approved" (批准) 或 "rejected" (拒绝)。
        response: 动作执行后的总结性答复信息。
    """
    # 用户的任务原始描述
    task: str
    # 识别出的动作类型
    action: str
    # 拟写入的目标物理文件路径
    file_path: str
    # 拟写入的具体文件文本内容
    file_content: str
    # 人类审批意见状态
    approval_status: str
    # 物理执行结果或对用户的反馈
    response: str


# ============================================================
# 2. 定义状态图中的节点逻辑 (Nodes)
# ============================================================

def supervisor_agent(state: SafetyState):
    """
    规划与识别代理节点逻辑 (supervisor_agent)。

    功能：分析用户的输入指令，识别是否包含写文件等敏感行为。如果包含，则结构化提取出文件路径和文件内容。
    输入参数：
        state (SafetyState): 图当前的全局状态字典。
    输出返回值：
        dict: 更新识别到的敏感动作、文件路径、文件内容及初始的待审批状态。
    """
    print("\n🔍 [Node: Supervisor] 正在评估用户请求的安全等级与具体意图...")

    # 从工厂实例化一个高确定性的 LLM (temperature=0.0) 展开意图提取
    llm = create_model(provider="deepseek", temperature=0.0)

    # 构造强力结构化 Prompt，强制要求模型返回 JSON 数据
    system_prompt = (
        "你是一个高度严谨的意图识别与参数提取专家。\n"
        "你需要对用户的提问进行分析，确定用户是否希望将内容写入物理文件。\n\n"
        "【判断规则】\n"
        "1. 如果用户提问要求创建、生成或写入文件，你必须提取拟写入的文件名和完整文本内容。\n"
        "   返回如下 JSON 格式：\n"
        "   {\n"
        "     \"action\": \"write_file\",\n"
        "     \"file_path\": \"[提取的文件名，例如 test.txt]\",\n"
        "     \"file_content\": \"[提取或由你针对任务生成的完整文本内容]\"\n"
        "   }\n"
        "2. 如果用户只是进行普通问答，不涉及写文件，则返回：\n"
        "   {\n"
        "     \"action\": \"none\",\n"
        "     \"file_path\": \"\",\n"
        "     \"file_content\": \"\"\n"
        "   }\n\n"
        f"用户请求: '{state['task']}'\n"
        "请直接给出对应的 JSON 格式分析数据，不需要任何其他解释："
    )

    # 调用模型进行意图识别
    ai_response = llm.invoke([HumanMessage(content=system_prompt)])
    # 清理前后可能存在的 markdown 包裹字符
    cleaned_content = ai_response.content.strip()

    # 移除首尾的 markdown 代码块标识符，如果存在的话
    if cleaned_content.startswith("```"):
        # 寻找换行符，跳过代码块开头
        first_newline = cleaned_content.find("\n")
        # 提取核心 JSON 文本
        cleaned_content = cleaned_content[first_newline + 1:]
        # 如果以代码块尾部结尾，则截断
        if cleaned_content.endswith("```"):
            # 截取掉末尾的三个反引号
            cleaned_content = cleaned_content[:-3].strip()
        else:
            # 否则不做处理
            pass
    else:
        # 如果本身就是纯 JSON，无需处理
        pass

    try:
        # 尝试将大模型的回答解析为字典
        parsed_intent = json.loads(cleaned_content)
        # 获取提取的 action 动作
        action = parsed_intent.get("action", "none")
        # 获取提取的文件路径
        file_path = parsed_intent.get("file_path", "")
        # 获取提取的文本内容
        file_content = parsed_intent.get("file_content", "")
    except Exception as err:
        # 如果解析异常，触发安全防线兜底，将动设定为 none
        print(f"⚠️ 解析大模型意图出错: {str(err)}。已启用安全兜底。")
        # 将动作设为无操作
        action = "none"
        # 文件路径置空
        file_path = ""
        # 文件内容置空
        file_content = ""

    # 打印 Supervisor 节点的评估日志
    print("💡 [Node: Supervisor] 意图研判结论:")
    # 打印研判动作
    print(f"   - 动作识别: {action}")
    # 打印目标路径
    print(f"   - 目标路径: {file_path}")

    # 返回状态更新，将审批状态初始化为 'pending' (待处理)
    return {
        "action": action,
        "file_path": file_path,
        "file_content": file_content,
        "approval_status": "pending"
    }


def execute_action(state: SafetyState):
    """
    高风险动作物理执行节点 (execute_action)。

    功能：如果审批通过，则在物理磁盘上创建文件并写入对应内容；如果被拒绝，则跳过物理写入操作。
    输入参数：
        state (SafetyState): 图当前的全局状态字典。
    输出返回值：
        dict: 更新执行完毕后的 response 信息。
    """
    print("\n💾 [Node: Execute] 接收到进入物理执行节点的调用指令...")

    # 获取当前状态中的人类审批状态
    approval = state.get("approval_status", "pending")
    # 获取需要写入的目标路径
    file_path = state.get("file_path", "")
    # 获取需要写入的文本内容
    file_content = state.get("file_content", "")

    # 判断管理员是否已经给予授权
    if approval == "approved":
        # 只有在明确 approved 时才能够执行物理写入
        print("📂 [Node: Execute] 检测到安全密钥：【人类已授权】。启动物理写入过程...")
        try:
            # 物理写入文本文件，使用 utf-8 编码确保中文不乱码
            with open(file_path, "w", encoding="utf-8") as writer:
                # 真正写入内容
                writer.write(file_content)
            # 记录成功提示
            status_text = f"【操作执行成功】物理文件 '{file_path}' 已安全创建，内容已完整落地写入。"
            # 打印控制台成功日志
            print(f"🎉 {status_text}")
        except Exception as file_err:
            # 捕获物理 I/O 写入异常
            status_text = f"【物理写入报错】在尝试创建文件时产生系统异常: {str(file_err)}"
            # 打印控制台错误日志
            print(f"❌ {status_text}")
    elif approval == "rejected":
        # 如果检测到人类管理员明确拒绝了操作
        status_text = "【操作安全拦截】人类管理员明确拒绝了该项物理写盘申请。已跳过敏感行为，未向磁盘写入任何字节。"
        # 打印控制台拦截日志
        print(f"🛡️ {status_text}")
    else:
        # 兜底情况，如果状态仍为 pending，说明有越权节点调度，判定为未获授权
        status_text = "【安全拦截异常】系统在未经安全审批拦截的情况下触发执行，执行器自动拦截越权写入。"
        # 打印异常拦截日志
        print(f"⚠️ {status_text}")

    # 返回状态更新，保存响应结果
    return {
        "response": status_text
    }


# ============================================================
# 3. 定义条件边流转路由规则 (Conditional Edges)
# ============================================================

def route_after_agent(state: SafetyState):
    """
    路由决策函数。

    功能：根据 Agent 研判的 action 动作，决定是去往物理敏感操作节点，还是直接结束。
    输入参数：
        state (SafetyState): 图当前的全局状态字典。
    输出返回值：
        str: 跳转的目标节点名（"execute" 或 "end"）。
    """
    # 检查动作是否为敏感的物理写文件
    if state["action"] == "write_file":
        # 如果是写文件，路由到 execute 节点
        return "execute"
    else:
        # 普通问答无风险，直接去往 END 终点结束
        return "end"


# ============================================================
# 4. 主程序：构建并仿真模拟人工介入与中断恢复
# ============================================================

def main():
    """
    主运行入口函数。

    功能：配置带有 interrupt_before=['execute_action'] 以及持久化 Checkpointer 的状态图机，
          分别进行【允许写入】和【拒绝写入】的两次控制台人机交互实验。
    """
    print("🛠️ 正在构建带有人工介入拦截 (Human-in-the-Loop) 的状态图机...")
    # 实例化基于 SafetyState 结构的图机对象
    workflow = StateGraph(SafetyState)

    # 添加两大主要工作节点
    # 负责研判的智能代理节点
    workflow.add_node("supervisor_agent", supervisor_agent)
    # 负责敏感操作的执行节点
    workflow.add_node("execute_action", execute_action)

    # 设定有向图的入口节点为 supervisor_agent
    workflow.set_entry_point("supervisor_agent")

    # 根据分析结果跳转到敏感执行或结束
    workflow.add_conditional_edges(
        "supervisor_agent",
        route_after_agent,
        {
            "execute": "execute_action",
            "end": END
        }
    )

    # 敏感节点执行完毕后直接结束
    workflow.add_edge("execute_action", END)

    # 声明一个内存级的状态持久化器，用于在暂停后恢复运行
    checkpointer = MemorySaver()

    # 编译有向图！
    # 核心设计：声明在 execute_action 节点【执行之前】强制触发中断挂起！
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["execute_action"]
    )
    print("✅ 带有人工介入安全阀的图工作流编译就绪！")

    # 定义测试用的任务请求
    test_task = "帮我生成一个名为 'deploy_test.sh' 的部署测试脚本，内容包含一行：echo 'Hello Human!'"
    # 模拟两个不同的会话线程，独立进行授权与拒绝的对比实验
    approve_thread_id = "user_approve_session_101"
    reject_thread_id = "user_reject_session_202"

    # =========================================================================
    # 实验一：人类管理员 【确认授权 (Approve)】 场景实验
    # =========================================================================
    print("\n" + "=" * 70)
    print("🧪 场景一实验：人类管理员给与安全授权 (APPROVE)")
    print("=" * 70)
    print(f"用户发出请求: '{test_task}'")

    # 配置线程配置字典，用于持久化追踪
    config_approve = {"configurable": {"thread_id": approve_thread_id}}

    # 启动第一轮执行。图机遇到 execute_action 节点前会自动挂起
    print("\n🚀 启动图机执行...")
    app.invoke({
        "task": test_task,
        "action": "",
        "file_path": "",
        "file_content": "",
        "approval_status": "pending",
        "response": ""
    }, config=config_approve)

    # 读取被中断时的当前图节点内部状态数据
    current_state = app.get_state(config_approve)
    print("\n⏸️ 状态机已在敏感执行节点 [execute_action] 前成功挂起暂停！")
    print("📊 提取当前待执行任务参数:")
    # 打印准备写入的文件名
    print(f"   - 目标文件: {current_state.values.get('file_path')}")
    # 打印准备写入的文本内容
    print(f"   - 拟写入内容:\n\"\"\"\n{current_state.values.get('file_content')}\n\"\"\"")

    # 仿真模拟控制台人类管理员批准动作：输入 'y'
    user_input = "y"
    print(f"❓ 【人类审批控制台】是否准许将此文件写入到本地物理磁盘？(y/n): {user_input}")

    # 检查管理员决定
    if user_input.lower() == "y":
        print("🟢 管理员通过了该动作。更新图状态，将 approval_status 修改为 'approved'...")
        # 利用 update_state 手动将当前线程的图状态字段更新为授权通过
        app.update_state(
            config_approve,
            {"approval_status": "approved"},
            as_node="supervisor_agent"
        )
        print("⏯️ 正在唤醒图状态机，恢复后续物理执行...")
        # 传递 None 作为输入，告诉 LangGraph 沿着之前被中断的断点直接继续向后走
        final_result = app.invoke(None, config=config_approve)
        print("\n⭐ 场景一最终运行应答:")
        # 打印场景一结果
        print(final_result["response"])
    else:
        # 仿真中默认不走此处
        pass

    # 清理物理测试生成的文件，保持工作区整洁
    if os.path.exists("deploy_test.sh"):
        # 存在则物理删除
        os.remove("deploy_test.sh")
        print("\n🗑️ [清理工作区] 测试生成的 deploy_test.sh 文件已被物理移除。")
    else:
        # 不存在则不做操作
        pass

    # =========================================================================
    # 实验二：人类管理员 【拒绝授权 (Reject)】 场景实验
    # =========================================================================
    print("\n" + "=" * 70)
    print("🧪 场景二实验：人类管理员拒绝授权 (REJECT)")
    print("=" * 70)
    print(f"用户发出请求: '{test_task}'")

    # 配置独立的拒绝线程配置字典
    config_reject = {"configurable": {"thread_id": reject_thread_id}}

    print("\n🚀 启动图机执行...")
    # 启动会话运行
    app.invoke({
        "task": test_task,
        "action": "",
        "file_path": "",
        "file_content": "",
        "approval_status": "pending",
        "response": ""
    }, config=config_reject)

    print("\n⏸️ 状态机已在敏感执行节点 [execute_action] 前成功挂起暂停！")

    # 仿真模拟控制台人类管理员拒绝动作：输入 'n'
    user_input_reject = "n"
    print(f"❓ 【人类审批控制台】是否准许将此文件写入到本地物理磁盘？(y/n): {user_input_reject}")

    # 检查管理员决定
    if user_input_reject.lower() == "n":
        print("🔴 管理员驳回了该动作。更新图状态，将 approval_status 修改为 'rejected'...")
        # 利用 update_state 将状态修改为 rejected 状态
        app.update_state(
            config_reject,
            {"approval_status": "rejected"},
            as_node="supervisor_agent"
        )
        print("⏯️ 正在唤醒图状态机，恢复后续处理以执行安全绕过分支...")
        # 恢复图机继续执行
        final_result_reject = app.invoke(None, config=config_reject)
        print("\n⭐ 场景二最终运行应答:")
        # 打印场景二结果
        print(final_result_reject["response"])
    else:
        # 仿真中不走此处
        pass

    print("=" * 70)
    print("✨ LangGraph interrupt 人工介入拦截与安全恢复演示大获成功。")


# 判断是否自命令行直接启动
if __name__ == "__main__":
    # 执行主程序
    main()
