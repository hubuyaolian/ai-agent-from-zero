# -*- coding: utf-8 -*-
"""
Day 14 演示：多 Agent 基础原理 — 角色隔离与独立人格 (Optimist vs. Pessimist) 👥

功能：不依赖任何复杂的图框架，通过纯 Python 串联两次携带不同 System Prompt 的
      大模型（DeepSeek）独立调用，模拟乐观派（AI 程序员必将完全取代人类开发）与
      悲观派（AI 绝对无法替代人类进行深度架构与创造力编码）在同一话题下的思维碰撞。
      以此生动阐释“多 Agent 系统 = 多个不同 System Prompt 的 LLM 调用 + 编排”这一最底层本质。
输入参数：无。
输出返回值：控制台打印两个 Agent 的角色设定、观点陈述以及它们观点交汇的碰撞记录。
"""

# 导入 LangChain 消息历史相关的基类
from langchain_core.messages import SystemMessage, HumanMessage

# 从公共模型工厂导入大模型实例化工具
from common.model_factory import create_model


# ============================================================
# 1. 定义多 Agent 角色的独立 Prompts (System Prompts)
# ============================================================

# 乐观派 Agent 的系统提示词：坚信 AI 的无限潜力，支持全面自动化
OPTIMIST_PROMPT = (
    "你是一个对人工智能技术发展极度乐观、前瞻的技术布道师。\n"
    "你坚信 AI 程序员（如 Devin 等）是软件工程的终极未来，并认为在未来 5 年内，\n"
    "AI 必将全面取代 90% 以上的人类软件工程师，彻底重构整个软件开发流程。\n"
    "在陈述观点时，请保持激情洋溢、论据新颖，多用正面词汇，字数控制在 250 字以内。"
)

# 悲观派 Agent 的系统提示词：持怀疑保守态度，强调人类的独特性
PESSIMIST_PROMPT = (
    "你是一个经验极其丰富、务实冷静的软件架构大师。\n"
    "你对“AI 取代人类程序员”的言论持强烈保留和嘲讽态度。你认为 AI 只是高级的自动补全工具，\n"
    "它缺乏真正突破性的创造力、无法进行顶层复杂架构设计，且受幻觉影响容易制造安全隐患，\n"
    "软件的本质是人类业务逻辑与人际协作的投射，这绝非 AI 所能替代。\n"
    "你需要站在绝对防守和批判的视角，指出对方的漏洞，表述务实犀利，字数控制在 250 字以内。"
)


# ============================================================
# 2. 定义角色类封装 (Agent Interface)
# ============================================================

class SimpleAgent:
    """
    单体 Agent 纯净类封装。

    功能：通过持有一个专属的 System Prompt 并在每次调用时注入，
          使该实例保持特定的人设与行为偏好，实现隔离的独立人格。
    """

    def __init__(self, name: str, system_prompt: str):
        """
        初始化 Agent 人设。

        输入参数：
            name (str): 智能体的角色名称。
            system_prompt (str): 该智能体专属的人设提示词。
        """
        # 保存智能体名称
        self.name = name
        # 保存系统设定提示词
        self.system_prompt = system_prompt
        # 实例化专属的大模型（教学阶段 04 之后默认 LLM 走 xiaomi mimo）
        self.llm = create_model(provider="xiaomi mimo", temperature=0.7)

    def talk(self, input_text: str) -> str:
        """
        针对外部输入的话题或观点进行角色化的回答。

        功能：在对话中自动前置 SystemMessage，确保模型输出完美符合其角色人格特征。
        输入参数：
            input_text (str): 接收到的观点或者话题内容。
        输出返回值：
            str: 带有鲜明人格设定的回复内容。
        """
        # 构建消息链，包含系统人设消息与当前用户的输入消息
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=input_text)
        ]
        # 发送请求给专属大模型
        response = self.llm.invoke(messages)
        # 获取大模型的文本内容
        answer = response.content.strip()
        # 返回最终的角色化回复
        return answer


# ============================================================
# 3. 主程序：开展多 Agent 辩论赛
# ============================================================

def main():
    """
    主运行入口。

    功能：实例化乐观派和悲观派两个独立的 Agent，
          围绕“未来 5 年内 AI 程序员是否会完全取代人类程序员”的话题进行一轮直接对话。
    """
    # 定义辩论的公共核心命题
    debate_topic = "未来 5 年内，AI 程序员（如 Devin）是否会完全取代人类软件工程师？"

    print("🛠️ 正在初始化多 Agent 独立角色实体...")
    # 实例化乐观派 Agent，为其命名并绑定布道师 Prompt
    optimist_agent = SimpleAgent(name="乐观派-布道师", system_prompt=OPTIMIST_PROMPT)
    # 实例化悲观派 Agent，为其命名并绑定架构师 Prompt
    pessimist_agent = SimpleAgent(name="悲观派-架构师", system_prompt=PESSIMIST_PROMPT)
    print("✅ 智能体配置完毕！")

    print("\n🎤 辩论大赛正式开始！")
    # 打印核心话题
    print(f"📊 核心话题: '{debate_topic}'")
    print("=" * 70)

    # 1. 乐观派率先发起论证
    print(f"\n🚀 【{optimist_agent.name}】 发起第一轮攻势:")
    # 乐观派针对核心话题给出其正面宏观见解
    optimist_view = optimist_agent.talk(f"针对话题：'{debate_topic}'，请阐述你的正面主张。")
    # 打印其论点
    print(optimist_view)
    print("-" * 70)

    # 2. 悲观派读取乐观派观点，并进行针锋相对的犀利反驳
    print(f"\n🛡️ 【{pessimist_agent.name}】 展开强力反弹:")
    # 悲观派读取乐观派的输出，并站在其对立人设进行炮轰
    pessimist_rebutt = pessimist_agent.talk(
        f"对方乐观派的技术布道师陈述了如下观点：\n"
        f"\"{optimist_view}\"\n"
        f"请你针对他的所有漏洞进行坚决的反驳！"
    )
    # 打印其论点
    print(pessimist_rebutt)
    print("=" * 70)

    print("\n✨ 辩论演练圆满结束！")
    # 总结性教学说明
    print("💡 教学小结：通过观察控制台，你看到了两个独立的 Agent 分别给出了完全相反的论证特征。")
    print("   它们背后并没有使用特殊的算法，只是使用了两个不同的 SimpleAgent 对象，")
    print("   分别拥有独立的系统人设（System Prompt）。这，就是多 Agent 角色的核心奥秘！")


# 判断是否自命令行直接启动
if __name__ == "__main__":
    # 执行主辩论程序
    main()
