"""
全局配置模块。

功能：集中管理所有大模型的 API 配置信息，包括 base_url、api_key 和默认模型名称。
      从 .env 文件中读取敏感的 API Key，避免硬编码在代码中。
输入参数：无（自动从环境变量读取）。
输出返回值：提供 MODEL_CONFIGS 字典、get_model_config() 和 list_available_providers() 函数。
"""

import os  # 导入操作系统模块，用于读取环境变量
from dotenv import load_dotenv  # 导入 dotenv 库，用于加载 .env 文件

# 加载项目根目录下的 .env 文件中的环境变量到当前进程
# 如果 .env 文件不存在也不会报错，只是不加载任何内容
load_dotenv()


# ============================================================
# 国产模型配置字典
# ============================================================
# 每个模型包含三个关键信息：
#   - base_url: API 的请求地址（OpenAI 兼容格式）
#   - api_key: 从环境变量读取的密钥（安全存储）
#   - default_model: 默认使用的模型名称
# ============================================================
MODEL_CONFIGS = {
    "xiaomi mimo": {
        "base_url": "https://api.xiaomimimo.com/v1",  # mimo 官方 API 地址
        "api_key": os.getenv("MIMO_API_KEY", ""),  # 从环境变量读取 Key
        "default_model": "mimo-v2.5",  # 默认模型：MiMo-V2.5
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",  # DeepSeek 官方 API 地址
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),  # 从环境变量读取 Key
        "default_model": "deepseek-v4-flash",  # 默认模型：DeepSeek-V3
    },
    "minimax": {
        "base_url": "https://api.minimaxi.com/v1",  # 火山方舟 OpenAI 兼容接口
        "api_key": os.getenv("MINIMAX_API_KEY", ""),  # 从环境变量读取 Key
        "default_model": "MiniMax-M3",  # 默认模型：方舟-M3.1
    },
}

# ============================================================
# Gemini 单独配置（不走 OpenAI 兼容接口，使用 Google 官方 SDK）
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # Gemini 的 API Key
GEMINI_DEFAULT_MODEL = "gemini-3.1-flash-lite"  # 默认使用 Gemini 3.1 Flash Lite


def get_model_config(provider):
    """
    根据模型提供商名称获取对应的配置信息。

    功能：从 MODEL_CONFIGS 字典中查找指定提供商的配置。
    输入参数：
        provider (str): 模型提供商名称，如 "deepseek"、"xiaomi mimo"、"minimax"。
    输出返回值：
        dict: 包含 base_url、api_key、default_model 的配置字典。
    异常：
        ValueError: 当提供的 provider 名称不在支持列表中时抛出。
    """
    # 将输入转为小写，避免大小写不一致的问题
    provider = provider.lower()
    # 检查该提供商是否在我们的配置列表中
    if provider not in MODEL_CONFIGS:
        # 获取所有支持的提供商名称，用逗号拼接成字符串
        supported = ", ".join(MODEL_CONFIGS.keys())
        # 抛出异常，告知用户支持哪些提供商
        raise ValueError(
            f"不支持的模型提供商: {provider}。"
            f"支持的选项: {supported}"
        )
    # 返回该提供商对应的配置字典
    return MODEL_CONFIGS[provider]


def list_available_providers():
    """
    列出所有已配置 API Key 的（可用的）模型提供商。

    功能：遍历所有配置，检查哪些提供商已经填写了 API Key。
    输入参数：无。
    输出返回值：
        list[str]: 已配置 API Key 的提供商名称列表。
    """
    # 创建一个空列表，用于存储可用的提供商
    available = []
    # 遍历所有国产模型的配置
    for provider, config in MODEL_CONFIGS.items():
        # 检查该提供商是否配置了有效的 API Key（非空字符串）
        if config["api_key"]:
            # 如果有 Key，将提供商名称添加到可用列表中
            available.append(provider)
    # 单独检查 Gemini 是否配置了 API Key
    if GEMINI_API_KEY:
        # 如果有 Key，也加入可用列表
        available.append("gemini")
    # 返回所有可用的提供商列表
    return available
