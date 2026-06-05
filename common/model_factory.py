"""
模型工厂模块。

功能：提供统一的接口来创建不同提供商的 LLM 模型实例。
      通过工厂模式（Factory Pattern），用一行代码即可切换不同的大模型。
输入参数：模型提供商名称（如 "deepseek"）和可选的模型参数。
输出返回值：LangChain 的 BaseChatModel 实例，可直接调用 .invoke() 进行对话。

原理说明：
    工厂模式是一种设计模式，它把"创建对象"的逻辑封装在一个函数里。
    调用者不需要知道具体怎么创建，只需要告诉工厂"我要什么"就行。
    在这里：
        - 国产模型（DeepSeek/Qwen/GLM/Kimi）都兼容 OpenAI 接口
          → 统一使用 ChatOpenAI，只是 base_url 不同
        - Gemini 有自己的接口
          → 使用 ChatGoogleGenerativeAI
"""

from langchain_openai import ChatOpenAI  # OpenAI 兼容接口的模型类

# 从 config 模块导入配置获取函数和 Gemini 配置
from common.config import get_model_config  # 获取指定提供商的配置
from common.config import GEMINI_API_KEY  # Gemini 的 API Key
from common.config import GEMINI_DEFAULT_MODEL  # Gemini 的默认模型名


def create_model(
    provider="deepseek",
    model_name=None,
    temperature=0.7,
    **kwargs
):
    """
    创建指定提供商的 LLM 模型实例（工厂函数）。

    功能：根据提供商名称，自动选择正确的模型类和配置来创建实例。
    输入参数：
        provider (str): 模型提供商名称，默认 "deepseek"。
                        可选值: "deepseek", "xiaomi mimo", "minimax", "gemini"。
        model_name (str): 模型名称，为 None 时使用该提供商的默认模型。
                          例如: "deepseek-chat", "mimo-v2.5" 等。
        temperature (float): 生成温度，控制输出的随机性，默认 0.7。
                             0.0 = 确定性输出，1.0 = 高随机性。
        **kwargs: 其他传递给模型构造函数的额外参数。
                  例如: max_tokens=1000, top_p=0.9 等。
    输出返回值：
        BaseChatModel: LangChain 的聊天模型实例，可直接调用：
                       - model.invoke("你好") 进行单次对话
                       - model.stream("你好") 进行流式对话
    """
    # 将提供商名称统一转为小写，避免大小写问题
    provider = provider.lower()

    # ---- Gemini 需要单独处理 ----
    # 因为 Gemini 不走 OpenAI 兼容接口，需要使用 Google 的专用 SDK
    if provider == "gemini":
        # 延迟导入：只在需要时才导入 Gemini 模块
        # 这样如果用户没安装 langchain-google-genai，也不会在启动时报错
        from langchain_google_genai import ChatGoogleGenerativeAI
        # 如果用户没有指定具体模型名，使用默认的 Gemini 模型
        if model_name is None:
            model_name = GEMINI_DEFAULT_MODEL
        # 创建并返回 Gemini 模型实例
        return ChatGoogleGenerativeAI(
            model=model_name,  # 模型名称
            google_api_key=GEMINI_API_KEY,  # API Key
            temperature=temperature,  # 温度参数
            **kwargs  # 其他额外参数
        )

    # ---- 国产模型：统一走 OpenAI 兼容接口 ----
    # 获取该提供商的配置信息（base_url, api_key, default_model）
    config = get_model_config(provider)

    # 如果用户没有指定具体模型名，使用该提供商的默认模型
    if model_name is None:
        model_name = config["default_model"]

    # 创建 ChatOpenAI 实例
    # 关键点：通过 base_url 参数，ChatOpenAI 可以连接任何兼容 OpenAI 格式的 API
    return ChatOpenAI(
        base_url=config["base_url"],  # API 请求地址（不同模型不同）
        api_key=config["api_key"],  # API 密钥
        model=model_name,  # 模型名称
        temperature=temperature,  # 温度参数
        **kwargs  # 其他额外参数
    )
