"""
Day 6 - 工具集：网络搜索工具（模拟）。

功能：模拟网页搜索引擎，根据关键词检索实时信息，辅助大模型获取新数据。
输入参数：搜索查询字符串。
输出返回值：检索到的搜索网页片段摘要。
"""

# 导入 LangChain 的 tool 装饰器
from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """
    通过网页搜索引擎检索与输入关键词最相关的实时互联网公开信息。

    Args:
        query: 检索关键词或句子，例如 '今天的新闻'、'大语言模型前沿进展'。

    Returns:
        包含几个最相关网页片段摘要的字符串。
    """
    # 清理查询词的首尾空白
    q_clean = query.strip().lower()

    # 模拟网页数据库
    mock_db = {
        "deepseek": (
            "【DeepSeek官方新闻】DeepSeek-V3 震撼发布！\n"
            "该模型采用混合专家架构（MoE），多项数学、代码及中文"
            "理解指标超越同级别闭源模型，推理成本降低 90% 以上。"
        ),
        "天气": (
            "【全国天气预报网】今日多地发布强降雨预警。\n"
            "北京晴朗，28度；上海中雨，气温骤降，24度；"
            "广州处于高温多云，最高气温达32度。"
        ),
        "gemini": (
            "【Google DeepMind 博客】Gemini 3.5 高效能模型现已全面"
            "向开发人员开放。其上下文理解能力与多模态速度获得"
            "显著提升，为开发者提供极为 premium 的端侧推理能力。"
        ),
    }

    # 初始化存储结果的列表
    found_items = []
    # 遍历模拟网页数据库中的键值对
    for key, value in mock_db.items():
        # 如果检索词中包含库中的某个键
        if key in q_clean:
            # 将匹配到的网页描述追加到结果列表
            found_items.append(value)

    # 判断是否匹配到了模拟结果
    if len(found_items) > 0:
        # 用换行符拼接多个网页摘要返回
        return "\n\n".join(found_items)
    # 没有匹配到预设的内容
    else:
        # 返回通用的模拟搜索回复
        return (
            f"关于 '{query}' 的搜索结果：\n"
            "1. 百度百科：未找到关于该主题的精确词条。\n"
            "2. 科技日报：最新公开的互联网资讯中暂无该主题的新闻线索。\n"
            "3. 知乎热议：当前暂无针对该问题的专业回答与讨论数据。"
        )
