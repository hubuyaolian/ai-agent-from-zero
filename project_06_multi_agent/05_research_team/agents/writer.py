# -*- coding: utf-8 -*-
"""
Day 16 模块：AI 调研团队 — 写作专家 (Writer Agent) ✍️

功能：充当流水线协作中的收官收尾成员。主要负责收集调研专家提供的原始数据 facts，
      以及分析专家萃取的高含金量趋势与核心洞察 insights，进行逻辑理顺与结构编排，
      撰写并打磨出一篇排版极精美、高含金量且符合规范的 GitHub Markdown 格式前沿技术研究报告。
      同时支持接收来自审核专家（Reviewer）的修改意见（review_feedback），
      在上一版报告的基础上进行精准的增补与修改，防止生成内容出现偏颇。
输入参数：研讨主题、原始调研素材、核心洞察分析成果、可选的上一版报告及审核反馈。
输出返回值：整合完美的 Markdown 格式专栏级研究报告文本。
"""

# 导入系统路径模块，用于支持从任意位置直接运行本脚本
import sys
# 导入路径处理工具，用于定位项目根目录
from pathlib import Path
# 导入加载环境变量的工具
from dotenv import load_dotenv
# 导入 LangChain 底层消息模型
from langchain_core.messages import SystemMessage, HumanMessage
# 导入大模型底层基类
from langchain_core.language_models.chat_models import BaseChatModel

# 将项目根目录加入模块搜索路径，保证 `python project_06_multi_agent/05_research_team/main.py` 可直接运行
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# 从公共模型工厂导入实例化工具
from common.model_factory import create_model

# 显式加载当前环境变量配置
load_dotenv()

# ============================================================
# 1. 定义写作 Agent 系统人设提示词 (System Prompt)
# ============================================================

WRITER_SYSTEM_PROMPT = (
    "你是一个在科技传媒界享有盛名的高水准专栏作家兼资深报告编撰主编（Writer Agent）。\n\n"
    "## 你的职责\n"
    "你负责汇集整理调研专家的第一手技术数据 facts 与分析专家的高度浓缩洞察 insights，\n"
    "撰写出一篇逻辑严丝合缝、文采斐然、极富说服力的 Markdown 技术研究报告。\n\n"
    "## 工作要求\n"
    "1. **结构严整**：必须严格遵循给定的输出格式大纲开发，不要擅自漏掉关键段落。\n"
    "2. **论据坚实**：所有的段落数据和事实案例必须来源于上游数据，不准主观编造事实或数据。\n"
    "3. **文风专业**：使用专业、流畅、客观中正的语言风格，段落之间要有如流水般自然的承上启下衔接。\n"
    "4. **极致排版**：充分利用 GitHub Markdown 的加粗、引用块、列表等标签，实现完美的视觉阅读体验。\n\n"
    "## 报告大纲格式约束\n"
    "你输出的研究报告必须符合以下大纲骨架：\n\n"
    "# 📋 [在此处编写报告的精炼大标题]\n\n"
    "## 摘要\n"
    "[用 2-3 句话高度浓缩本篇报告的核心研究主题和最颠覆性的分析结论]\n\n"
    "## 1. 技术引言\n"
    "[介绍本次研究的技术历史背景、要解决的工程痛点与研究的核心目的]\n\n"
    "## 2. 现状与事实分析\n"
    "[结合调研专家的原始数据 facts，梳理出该技术目前在国内外的真实发展现状与关键指标表现]\n\n"
    "## 3. 深度洞察与趋势剖析\n"
    "[核心章节！结合分析专家产出的核心趋势和洞察点，进行深度的逻辑铺陈、影响意义挖掘和展开论证]\n\n"
    "## 4. 行业挑战与潜在机遇\n"
    "[辩证对比技术推广中面临的安全风险、落地瓶颈，以及蕴含的市场与工程机遇]\n\n"
    "## 5. 结论与未来展望\n"
    "[总结全篇的核心立论点，并站在行业顶端给出一份未来 3-5 年的发展走向预测与实战倡议]\n\n"
    "---\n"
    "*本报告由 AI 调研团队联袂协作生成*"
)


# ============================================================
# 2. 编写 Agent 实例化与运行服务函数
# ============================================================

def create_writer_agent() -> BaseChatModel:
    """
    创建写作 Agent 的底层模型实例。

    功能：从模型工厂中创建 DeepSeek 大模型实例。
          为了让文章的用词文采更生动、语言组织更流畅，将温度参数调高至 0.7。
    输入参数：
        无。
    输出返回值：
        BaseChatModel: 实例化后的 LangChain 兼容大模型。
    """
    # 从工厂获取大模型（writer 是 3 号 LLM，沿用 deepseek 作为"其他"）。temperature=0.7 释放文笔流畅度
    model_instance = create_model(
        provider="deepseek",
        temperature=0.7
    )
    # 返回创建的模型实例
    return model_instance


def run_writing(
    topic: str,
    research_data: str,
    analysis_result: str,
    previous_report: str = "",
    review_feedback: str = ""
) -> str:
    """
    独立执行写作与润色整合任务入口。

    功能：给定技术主题、调研数据、分析结论，生成 Markdown 格式的完整研究报告。
          如果提供了上一版报告与审核意见，将在上一版的基础上做优化与二次润色。
    输入参数：
        topic (str): 本次要编写的技术研究主题名称。
        research_data (str): 调研专家提供的原始技术素材。
        analysis_result (str): 分析专家提炼的技术洞察与核心趋势分析。
        previous_report (str): 可选。上一次由本 Agent 撰写但未通过审核的报告文本。
        review_feedback (str): 可选。审核专家给出的结构化 JSON 扣分项与修改建议。
    输出返回值：
        str: 写作专家最终润色编撰的 Markdown 研究报告文本。
    """
    # 实例化大模型
    model = create_writer_agent()

    # 声明用户上下文内容字符串变量
    user_content = ""

    # 判断是否为退回重写流程（即存在审核反馈意见）
    if review_feedback and previous_report:
        # 组装包含前版报告和审核意见的重写提示词
        user_content = (
            f"我们之前针对主题 '{topic}' 生成的上一版研究报告未能通过审核专家的评估。\n\n"
            f"【审核专家给出的具体修改建议如下】:\n"
            f"\"{review_feedback}\"\n\n"
            f"【上一版技术报告的完整原文如下】:\n"
            f"\"\"\"\n{previous_report}\n\"\"\"\n\n"
            "【请你的重构任务】:\n"
            "请你认真阅读审核意见，在原报告的架构基础上进行定向的文字重构、增补与语句修辞打磨，\n"
            "弥补上一版的缺陷，输出更加趋近完美的最终报告。请保持输出大纲格式不变！"
        )
    else:
        # 组装全新的撰写提示词
        user_content = (
            f"请基于以下两位专家为你输送的技术原材料，撰写一篇完整且高质量的技术研究报告：\n\n"
            f"**研究主题**：{topic}\n\n"
            f"**调研专家的技术 facts 原始事实**：\n{research_data}\n\n"
            f"**分析专家的技术 insights 深度洞察**：\n{analysis_result}"
        )

    # 组装系统人设消息和用户具体上下文消息
    messages = [
        SystemMessage(content=WRITER_SYSTEM_PROMPT),
        HumanMessage(content=user_content)
    ]

    # 调用模型执行生成
    response = model.invoke(messages)
    # 提取内容并去除前后空白
    result_text = response.content.strip()
    # 返回最终的研究报告文本
    return result_text


# ============================================================
# 3. 本地测试自检入口
# ============================================================

if __name__ == "__main__":
    # 定义测试主题与模拟上游成果
    test_topic = "大语言模型（LLM）长期记忆能力的最新演进与向量数据库优化手段"
    mock_research = "调研事实：上下文窗口在 2025 年激增至 1M；长文本召回存在‘大海捞针’边缘衰减；向量数据库 HNSW 性能优异。"
    mock_analysis = "分析洞察：1. 混合检索（向量+元数据）是落地标配；2. 纯长文本上下文无法解决实时高并发问题，必须向量分块；3. 安全审计是最大瓶颈。"

    print("🎬 正在独立运行测试 [Writer Agent]...")
    # 运行写作函数
    test_result = run_writing(test_topic, mock_research, mock_analysis)
    print("=" * 70)
    print(test_result)
    print("=" * 70)
    print("✨ [Writer Agent] 独立测试成功运行完毕！")
