"""
项目级别的配置文件。

功能：为 project_02_chat_agent 项目提供统一的配置管理，
      包括默认模型提供商、默认温度、预定义角色的 System Prompt 等。
      通过封装 common 公共模块，为本项目的所有课程脚本提供便捷的模型获取接口。
输入参数：无。
输出返回值：提供 get_default_model() 函数和 SYSTEM_PROMPTS 字典。
"""

import sys  # 导入系统模块，用于修改 Python 模块搜索路径
import os  # 导入操作系统模块，用于路径操作

# 将上级目录（项目根目录）添加到 Python 模块搜索路径中
# 这样才能正确导入 common 包中的公共模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.model_factory import create_model  # 导入模型工厂函数  # noqa: E402
from common.config import list_available_providers  # 导入可用提供商列表函数  # noqa: E402

# ============================================================
# 项目默认配置
# ============================================================
# 默认使用的模型提供商（可选: deepseek, qwen, glm, kimi, gemini）
DEFAULT_PROVIDER = "deepseek"

# 默认模型名称（设为 None 表示使用该提供商的默认模型）
DEFAULT_MODEL_NAME = None

# 默认生成温度（0.0 = 最确定性, 1.0 = 最随机）
# 对话场景推荐 0.7，既有创造性又不会太离谱
DEFAULT_TEMPERATURE = 0.7


# ============================================================
# 预定义角色的 System Prompt 字典
# ============================================================
# System Prompt 是给 AI 的"角色说明书"，它决定了 AI 的行为模式、
# 回答风格、专业领域和限制条件。
# 每个角色都包含：角色身份、行为规则、输出风格、限制条件
# ============================================================
SYSTEM_PROMPTS = {
    "默认助手": (
        "你是一个友好、专业的 AI 助手。"
        "你的任务是帮助用户解决各种问题。"
        "请用清晰、易懂的中文回答。"
        "如果你不确定答案，请诚实地告知用户，而不是编造信息。"
        "回答要简洁但完整，避免不必要的冗长。"
    ),
    "Python编程导师": (
        "你是一位经验丰富、耐心细致的 Python 编程导师。"
        "你的目标是帮助初学者理解 Python 编程的核心概念。"
        "回答时请遵循以下规则：\n"
        "1. 用简单易懂的语言解释复杂概念\n"
        "2. 尽量提供可运行的代码示例\n"
        "3. 代码示例要包含详细的中文注释\n"
        "4. 解释代码的执行过程和原理\n"
        "5. 如果用户的代码有错误，先肯定做得好的部分，再指出问题\n"
        "6. 鼓励用户动手实践，而不只是阅读\n"
        "7. 适当推荐相关的进阶知识点"
    ),
    "翻译专家": (
        "你是一位精通中英文的翻译专家。"
        "你的主要任务是进行中英文互译，并提供详细的语言解析。"
        "请遵循以下规则：\n"
        "1. 如果用户输入中文，翻译成地道的英文\n"
        "2. 如果用户输入英文，翻译成自然流畅的中文\n"
        "3. 翻译后需要解释关键词汇的用法和语境\n"
        "4. 如果有多种翻译方式，列出不同版本并说明区别\n"
        "5. 指出容易出错的语法点或常见误用\n"
        "6. 对于专业术语，提供专业领域的标准译法"
    ),
    "苏格拉底式提问者": (
        "你是一位采用苏格拉底式教学法的智慧导师。"
        "你的核心原则是：永远不直接给出答案，而是通过提问引导用户自己思考和发现。"
        "请遵循以下规则：\n"
        "1. 用户提问时，不要直接回答，而是反问用户\n"
        "2. 通过一系列由浅入深的问题，引导用户自己得出答案\n"
        "3. 当用户的思路正确时，给予肯定并继续引导深入\n"
        "4. 当用户的思路偏离时，用温和的问题将其引回正轨\n"
        "5. 每次回复最多提 2-3 个问题，避免一次性给太多问题\n"
        "6. 如果用户明确表示希望直接得到答案，可以适当给出提示"
    ),
}

# 角色名称列表（方便遍历和选择）
ROLE_NAMES = list(SYSTEM_PROMPTS.keys())


def get_default_model(
    provider=None,
    model_name=None,
    temperature=None
):
    """
    获取配置好的默认模型实例。

    功能：基于项目默认配置（或用户覆盖参数）创建并返回一个 LLM 模型实例。
          这是对 create_model 工厂函数的便捷封装。
    输入参数：
        provider (str, optional): 模型提供商名称。
                                   为 None 时使用项目默认配置 DEFAULT_PROVIDER。
        model_name (str, optional): 模型名称。
                                     为 None 时使用项目默认配置 DEFAULT_MODEL_NAME。
        temperature (float, optional): 生成温度。
                                        为 None 时使用项目默认配置 DEFAULT_TEMPERATURE。
    输出返回值：
        BaseChatModel: LangChain 的聊天模型实例，可直接调用 .invoke() 进行对话。
    """
    # 如果未指定提供商，使用项目默认提供商
    if provider is None:
        provider = DEFAULT_PROVIDER
    # 如果未指定模型名称，使用项目默认模型名称
    if model_name is None:
        model_name = DEFAULT_MODEL_NAME
    # 如果未指定温度，使用项目默认温度
    if temperature is None:
        temperature = DEFAULT_TEMPERATURE

    # 调用公共模块的工厂函数创建模型实例
    model = create_model(
        provider=provider,  # 模型提供商
        model_name=model_name,  # 模型名称
        temperature=temperature  # 生成温度
    )
    # 返回创建好的模型实例
    return model


def show_config_info():
    """
    打印当前项目的配置信息（用于调试和确认）。

    功能：输出当前的默认配置和可用的模型提供商列表。
    输入参数：无。
    输出返回值：无（直接打印到终端）。
    """
    # 打印分隔线
    print("=" * 50)
    # 打印标题
    print("📋 Project 02 - 对话 Agent 项目配置")
    # 打印分隔线
    print("=" * 50)
    # 打印默认提供商
    print(f"  默认提供商: {DEFAULT_PROVIDER}")
    # 打印默认模型名称
    print(f"  默认模型:   {DEFAULT_MODEL_NAME or '(使用提供商默认)'}")
    # 打印默认温度
    print(f"  默认温度:   {DEFAULT_TEMPERATURE}")
    # 打印空行
    print()

    # 获取所有可用的模型提供商
    available = list_available_providers()
    # 打印可用提供商数量
    print(f"🔑 可用的模型提供商 ({len(available)} 个):")
    # 遍历并打印每个可用的提供商
    for provider_name in available:
        print(f"  ✅ {provider_name}")
    # 打印空行
    print()

    # 打印预定义角色信息
    print(f"🎭 预定义角色 ({len(SYSTEM_PROMPTS)} 个):")
    # 遍历并打印每个角色的名称和简要描述（取前 30 个字符）
    for role_name, prompt_text in SYSTEM_PROMPTS.items():
        # 截取 prompt 的前 30 个字符作为预览
        preview = prompt_text[:30] + "..."
        print(f"  🔹 {role_name}: {preview}")
    # 打印分隔线
    print("=" * 50)


# ============================================================
# 主程序入口：直接运行此文件可查看当前配置信息
# ============================================================
if __name__ == '__main__':
    # 显示当前项目的配置信息
    show_config_info()
