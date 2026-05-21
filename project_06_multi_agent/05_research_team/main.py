# -*- coding: utf-8 -*-
"""
Day 17 模块：AI 调研团队 — 主入口程序 (Command Line Entry) 🎬

功能：多 Agent 协作 AI 调研团队项目的命令行控制台入口。
      获取用户的研讨主题输入，一键拉起编译好的 V1 基础版 LangGraph 工作流引擎。
      运行结束后，在终端流式呈现完美的专栏级 Markdown 报告。
      并利用持久化写入服务，自动将研究报告生成包含日期戳和主题名称的安全文件名，
      安全保存至当前项目目录下的 output/ 目录中，确保调研资料可随时离线查阅。
输入参数：无（命令行交互式输入主题）。
输出返回值：控制台打印整个工作流流转日志、总耗时统计、最终报告以及保存的文件物理绝对路径。
"""

# 导入操作系统路径相关库
import os
# 导入时间计算库
import time
# 导入日期格式化库
from datetime import datetime
# 导入 LangChain 底层人类消息模型
from langchain_core.messages import HumanMessage

# 从本地工作流定义模块中导入工作流图编译构建函数
from workflow import build_research_team_workflow


# ============================================================
# 1. 编写研究报告的持久化文件保存函数
# ============================================================

def save_report(topic: str, report: str) -> str:
    """
    将生成的 Markdown 技术研究报告持久化保存到本地硬盘物理文件中。

    功能：自动计算 main.py 所在目录，并在同级目录下创建 output/ 目录。
          将主题中的空格或斜杠进行安全转换，自动注入当前日期戳，生成专属的 .md 报告文件。
    输入参数：
        topic (str): 研讨的中心主题（用于净化文件名）。
        report (str): 最终写作专家整合出的完整 Markdown 格式报告正文。
    输出返回值：
        str: 写入成功的本地报告文件绝对物理路径。
    """
    # 获取当前 main.py 所在的绝对物理目录路径
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 拼接并声明 output/ 文件夹的绝对物理路径
    output_dir = os.path.join(current_dir, "output")

    # 检查 output 物理目录是否已经存在，如果不存在则自动创建，防止写盘崩溃
    if not os.path.exists(output_dir):
        # 创建多层物理目录
        os.makedirs(output_dir)

    # 提取当前本地时间的日期戳字符串，用于防文件名冲突
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 净化主题名称，为了防止文件名非法，将空格、斜杠、反斜杠统一替换为下划线
    safe_topic = topic[:20]
    # 替换空格
    safe_topic = safe_topic.replace(" ", "_")
    # 替换正斜杠
    safe_topic = safe_topic.replace("/", "_")
    # 替换反斜杠
    safe_topic = safe_topic.replace("\\", "_")

    # 拼接出独一无二的文件名称
    filename = f"report_{timestamp}_{safe_topic}.md"

    # 拼接出完整的文件绝对物理路径
    filepath = os.path.join(output_dir, filename)

    # 以 UTF-8 编码格式打开文件，开始安全写盘
    with open(filepath, "w", encoding="utf-8") as file_writer:
        # 将报告写入文件
        file_writer.write(report)

    # 打印控制台提示，方便学员明确知道文件保存在哪了
    print("\n💾 [系统提示] 调研报告已成功持久化写入磁盘！")
    print(f"   📂 物理文件保存路径: [ {filepath} ]")

    # 返回最终的写入文件路径
    return filepath


# ============================================================
# 2. 编写主程序运行服务函数
# ============================================================

def main():
    """
    AI 调研团队主运行入口。

    功能：显示欢迎界面，接收用户主题输入，编译工作流，
          执行流水线接力，统计执行时间并最终落盘为文件。
    """
    # 打印欢迎界面边框
    print("=" * 70)
    print("🏢   欢迎光临 AI 调研团队命令行系统 (Research Team V1)   🏆")
    print("=" * 70)
    # 打印成员分工
    print("📋 团队成员就位并就绪：")
    print("  1. 🔍 调研智能体 (Researcher) - 搜集技术 facts 原始材料 (DeepSeek 驱动)")
    print("  2. 📊 分析智能体 (Analyst)    - 提炼深度 insights 技术要点 (DeepSeek 驱动)")
    print("  3. ✍️ 写作智能体 (Writer)     - 润色排版专栏级 Markdown 报告 (DeepSeek 驱动)")
    print("=" * 70)

    # 尝试捕获非交互模式下的 EOFError 异常，保障命令行与容器部署稳定性
    try:
        # 获取学员输入的主题，如果直接回车，采用默认的主流前沿主题
        user_input = input("\n🎯 请输入你本次想要调研的技术研究主题\n(直接回车默认: 'AI Agent 技术的发展现状与未来趋势'): ").strip()
    except (EOFError, KeyboardInterrupt):
        # 捕获异常后，强制设置为空值，以便走默认话题逻辑
        user_input = ""

    # 判定用户是否直接回车或输入为空
    if not user_input:
        # 使用默认的经典话题
        topic_to_run = "AI Agent 技术的发展现状与未来趋势"
    else:
        # 采用用户手动输入的话题
        topic_to_run = user_input

    print(f"\n🚀 引擎启动！本次调研主题定格为: [ {topic_to_run} ]")
    print("🤝 各 Worker 正在接力协作，这可能需要约 30-50 秒，请耐心等待...")

    # 记录流水线总的启动时间戳
    global_start_time = time.time()

    # 编译 V1 基础版的多智能体协作状态图
    workflow_app = build_research_team_workflow()

    # 启动工作流应用，传入初始状态结构
    final_state = workflow_app.invoke({
        # 传递包含用户初始请求的消息列表
        "messages": [HumanMessage(content=f"请对以下主题进行全面研讨：{topic_to_run}")],
        # 传入研讨主题
        "topic": topic_to_run,
        # 预设空调研事实数据
        "research_data": "",
        # 预设空分析洞察结论
        "analysis_result": "",
        # 预设空最终研究报告
        "final_report": "",
        # 标记为 started 状态
        "status": "started"
    })

    # 计算整条流水线跑完所消耗的累计时间
    total_elapsed = time.time() - global_start_time

    # 流式输出最终的完美 Markdown 报告
    print("\n" + "*" * 70)
    print("⭐ ⭐ 最终团队产出的专栏级研究报告 ⭐ ⭐")
    print("*" * 70)
    # 打印正文内容
    print(final_state["final_report"])
    print("*" * 70)

    # 打印可观测性综合统计汇总指标
    print("\n📊 【可观测性执行统计汇总】:")
    # 统计总耗时
    print(f"   ⏱️ 团队接力协作总计耗时: {total_elapsed:.2f} 秒")
    # 统计各环节输出字符数
    print(f"   📈 数据加工链路: 调研 {len(final_state['research_data'])} 字 "
          f"→ 分析 {len(final_state['analysis_result'])} 字 "
          f"→ 报告 {len(final_state['final_report'])} 字")

    # 执行文件落盘，将 Markdown 技术报告保存到 output/ 目录下
    save_report(topic=topic_to_run, report=final_state["final_report"])

    print("\n🎉 多智能体团队线性流水线 V1 基础协作演练圆满收官！")
    print("=" * 70)


# 判断是否直接自命令行执行
if __name__ == "__main__":
    # 执行主流程
    main()
