# -*- coding: utf-8 -*-
"""
Day 16 模块：AI 调研团队 — 分析专家 (Analyst Agent) 📊

功能：充当流水线协作中的第二环成员。主要负责接收上游调研专家（Researcher）
      收集的大量结构化原始素材，通过深度分析，提炼规律，挖掘前沿技术趋势，
      并从商业、技术等多维视角产出有含金量的核心洞察与 SWOT 机遇挑战分析。
      注重将凌乱的“事实 facts”转化为高度浓缩的“洞察 insights”。
输入参数：研讨主题、调研专家提供的原始调研事实数据文本。
输出返回值：分析专家提炼的高含金量趋势与技术洞察 Markdown 文本。
"""

# 导入加载环境变量的工具
from dotenv import load_dotenv
# 导入 LangChain 底层消息模型
from langchain_core.messages import SystemMessage, HumanMessage
# 导入大模型底层基类
from langchain_core.language_models.chat_models import BaseChatModel

# 从公共模型工厂导入实例化工具
from common.model_factory import create_model

# 显式加载当前环境变量配置
load_dotenv()

# ============================================================
# 1. 定义分析 Agent 系统人设提示词 (System Prompt)
# ============================================================

ANALYST_SYSTEM_PROMPT = (
    "你是一个在科技与工程界拥有深厚造诣、思维严谨敏锐的资深数据分析专家（Analyst Agent）。\n\n"
    "## 你的职责\n"
    "你负责对上游调研专家收集来的大量原始技术事实数据进行深度的归纳与因果分析，\n"
    "从中剥离杂音，提炼出有高含金量和行业前瞻指导性的核心洞察点。\n\n"
    "## 工作要求\n"
    "1. **深度提炼**：严禁只对原始事实进行简单的拼贴和重复呈现。你必须挖掘现象背后的深层技术原委和驱动因素。\n"
    "2. **多维视角**：需要从系统架构、实施成本、开发周期、落地门槛等多重维度切入分析。\n"
    "3. **逻辑严密**：结论要字字有支撑，逻辑推理必须自洽且环环相扣。\n"
    "4. **价值导向**：重点提炼出对工程师、架构师或业务决策者而言最有指导性价值的洞察。\n\n"
    "## 输出格式约束\n"
    "你必须严格按以下格式输出分析结果：\n\n"
    "### 🎯 核心趋势分析\n"
    "[结合你的行业前瞻视野，识别 3-4 个正在发生的关键技术演进趋势，每个趋势均要给出详细的背景与逻辑成因分析]\n\n"
    "### 💡 关键洞察\n"
    "1. **[关键洞察 1 标题]**：[详细描述核心发现及其对行业/架构产生的根本性影响意义]\n"
    "2. **[关键洞察 2 标题]**：[详细描述核心发现及其对行业/架构产生的根本性影响意义]\n"
    "3. **[关键洞察 3 标题]**：[详细描述核心发现及其对行业/架构产生的根本性影响意义]（至少整理 3 条深度洞察）\n\n"
    "### ⚖️ 优势与挑战\n"
    "**技术优势与发展机遇：**\n"
    "- [详细列出优势要点 1]\n"
    "- [详细列出优势要点 2]\n\n"
    "**实施挑战与致命风险：**\n"
    "- [详细列出挑战或安全风险 1]\n"
    "- [详细列出挑战或安全风险 2]\n\n"
    "### 🔮 前景判断\n"
    "[总结以上所有核心要点，给出一份简短、客观的技术未来前景和落地推广建议结论]"
)


# ============================================================
# 2. 编写 Agent 实例化与运行服务函数
# ============================================================

def create_analyst_agent() -> BaseChatModel:
    """
    创建分析 Agent 的底层模型实例。

    功能：从模型工厂中创建 DeepSeek 大模型实例。
          温度参数设定在 0.5，在维持逻辑深度严密的前提下，释放一定的前瞻创造性。
    输入参数：
        无。
    输出返回值：
        BaseChatModel: 实例化后的 LangChain 兼容大模型。
    """
    # 从工厂获取大模型（analyst 是 2 号 LLM，沿用 deepseek 作为"其他"）。temperature=0.5 取推理与创造平衡
    model_instance = create_model(
        provider="deepseek",
        temperature=0.5
    )
    # 返回创建的模型实例
    return model_instance


def run_analysis(topic: str, research_data: str) -> str:
    """
    独立执行分析提炼任务入口。

    功能：给定分析话题以及 Researcher 提供的原始事实，调用分析 Agent，输出详实的洞察提炼 Markdown 文本。
    输入参数：
        topic (str): 本次要分析研讨的技术主题。
        research_data (str): 调研专家提供的原始结构化调研事实文本。
    输出返回值：
        str: 分析专家提炼的高含金量趋势洞察 Markdown 报告。
    """
    # 实例化大模型
    model = create_analyst_agent()
    # 组装包含岗位系统 Prompts 与上游调研成果的消息列表
    messages = [
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"请对以下调研资料进行深度的技术分析与价值提炼：\n\n"
                f"**研究主题**：{topic}\n\n"
                f"**上游调研事实素材**：\n{research_data}"
            )
        )
    ]
    # 调用模型生成分析结果
    response = model.invoke(messages)
    # 提取内容并去除两侧空白
    result_text = response.content.strip()
    # 返回最终文本
    return result_text


# ============================================================
# 3. 本地测试自检入口
# ============================================================

if __name__ == "__main__":
    # 定义测试主题与模拟调研事实
    test_topic = "大语言模型（LLM）长期记忆能力的最新演进与向量数据库优化手段"
    mock_research = (
        "### 📋 调研主题\n"
        "LLM 长期记忆与向量数据库优化\n\n"
        "### 📊 关键发现\n"
        "1. Transformer 架构的上下文窗口从早期的 4K 突破到了 1M 甚至更高；\n"
        "2. 随着上下文的增大，Needle in a Haystack 测试显示长文本检索召回率会呈现边缘衰减；\n"
        "3. 向量检索通过近似最近邻（ANN）算法（如 HNSW、IVF-PQ）能实现毫秒级的大规模向量检索；\n"
        "4. 本地数据库读写频繁，I/O 开销与计算开销是大模型应用的主要系统阻碍；\n"
        "5. 很多向量数据库（如 Chroma, Pinecone, Milvus）提供了元数据过滤和混合检索（Meta Filtering + Hybrid Search）能力；\n"
        "6. 在实际中，多轮对话常因为会话过多导致上下文膨胀、吞吐下降并容易产生严重幻觉。"
    )
    print("🎬 正在独立运行测试 [Analyst Agent]...")
    # 运行分析函数
    test_result = run_analysis(test_topic, mock_research)
    print("=" * 70)
    print(test_result)
    print("=" * 70)
    print("✨ [Analyst Agent] 独立测试成功运行完毕！")
