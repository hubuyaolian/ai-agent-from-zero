"""
==========================================================================
Day 1 - 课程 1：原始 API 调用（不使用任何框架）
==========================================================================

学习目标：
    1. 理解大模型 API 的底层通信原理（HTTP POST 请求）
    2. 掌握请求结构：URL、Headers、Body 的组成方式
    3. 掌握响应结构：如何从 JSON 响应中提取模型回答
    4. 理解多轮对话的实现原理：手动维护 messages 列表
    5. 为后续使用 LangChain 等框架打下理解基础

知识点概述：
    - 大模型 API 本质上就是一个 HTTP 接口，我们发送 JSON 格式的请求，
      接收 JSON 格式的响应。
    - 所有兼容 OpenAI 格式的大模型（DeepSeek、Qwen、GLM、Kimi 等）
      都遵循相同的请求/响应结构，只是 URL 和 API Key 不同。
    - 请求结构（HTTP POST）：
        URL:     https://api.deepseek.com/chat/completions
        Headers: {"Authorization": "Bearer sk-xxx", "Content-Type": "application/json"}
        Body:    {"model": "deepseek-chat", "messages": [...], "temperature": 0.7}
    - 响应结构（JSON）：
        {
          "choices": [
            {
              "message": {
                "role": "assistant",
                "content": "模型的回答内容"
              }
            }
          ]
        }
    - 多轮对话原理：每次请求都把完整的对话历史（messages 列表）发送给模型，
      模型根据所有历史消息来生成回答。客户端负责维护这个列表。

为什么要学这个？
    使用框架（如 LangChain）虽然方便，但如果不理解底层原理，
    遇到问题时就无法调试。本课程让你"看见"框架帮你做了什么。

前置条件：
    - 已在 .env 文件中配置了 DEEPSEEK_API_KEY
    - 已安装 requests 和 python-dotenv 库
==========================================================================
"""

import os  # 操作系统模块，用于读取环境变量
import json  # JSON 模块，用于格式化输出 JSON 数据
import requests  # HTTP 请求库，用于发送 API 请求

from dotenv import load_dotenv  # 从 .env 文件加载环境变量

# ============================================================
# 加载环境变量
# ============================================================
# load_dotenv() 会自动查找当前目录及父目录中的 .env 文件
# 并将其中的键值对加载为环境变量
load_dotenv()

# ============================================================
# 基础配置常量
# ============================================================
# DeepSeek API 的完整请求地址
# 所有兼容 OpenAI 格式的模型都使用 /chat/completions 这个端点
API_URL = "https://api.deepseek.com/chat/completions"

# 从环境变量中读取 API Key
# 如果没有配置，返回空字符串（后续会检查）
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 使用的模型名称
MODEL_NAME = "deepseek-v4-flash"


def raw_chat(messages, temperature=0.7):
    """
    使用 requests 库直接调用大模型 API 进行对话。

    功能：构建完整的 HTTP POST 请求，发送给 DeepSeek API，
          并解析响应中的模型回答。

    输入参数：
        messages (list[dict]): 对话消息列表，每条消息是一个字典，
                               包含 "role"（角色）和 "content"（内容）。
                               角色可选值：
                                 - "system": 系统提示词，设定模型行为
                                 - "user": 用户输入
                                 - "assistant": 模型回答
        temperature (float): 生成温度，控制输出的随机性，默认 0.7。
                             0.0 = 最确定的输出
                             1.0 = 最随机的输出

    输出返回值：
        str: 模型生成的回答文本。
             如果调用失败，返回包含错误信息的字符串。
    """
    # ---- 第一步：构建请求头 ----
    # HTTP 请求头中需要包含两个关键信息：
    #   1. Content-Type: 告诉服务器我们发送的是 JSON 格式的数据
    #   2. Authorization: 用 Bearer Token 方式传递 API Key 进行身份验证
    headers = {
        "Content-Type": "application/json",  # 指定请求体为 JSON 格式
        "Authorization": f"Bearer {API_KEY}",  # Bearer 认证方式
    }

    # ---- 第二步：构建请求体 ----
    # 请求体是一个 JSON 对象，包含三个必要字段：
    #   1. model: 指定使用哪个模型
    #   2. messages: 完整的对话历史
    #   3. temperature: 控制回答的随机性
    payload = {
        "model": MODEL_NAME,  # 指定模型名称
        "messages": messages,  # 传入完整的对话历史
        "temperature": temperature,  # 设置温度参数
    }

    # ---- 第三步：发送 HTTP POST 请求 ----
    # 使用 try-except 包裹，防止网络错误导致程序崩溃
    try:
        # requests.post() 发送 POST 请求
        # 参数说明：
        #   - API_URL: 请求地址
        #   - headers: 请求头字典
        #   - json: 自动将字典序列化为 JSON 字符串作为请求体
        #   - timeout: 超时时间（秒），防止无限等待
        response = requests.post(
            API_URL,  # 请求地址
            headers=headers,  # 请求头
            json=payload,  # 请求体（自动转 JSON）
            timeout=60,  # 60 秒超时
        )

        # ---- 第四步：检查响应状态码 ----
        # HTTP 状态码 200 表示请求成功
        # raise_for_status() 会在状态码不是 2xx 时自动抛出异常
        response.raise_for_status()

        # ---- 第五步：解析响应 JSON ----
        # 将响应体从 JSON 字符串转换为 Python 字典
        result = response.json()

        # ---- 第六步：提取模型回答 ----
        # 响应结构：result["choices"][0]["message"]["content"]
        # 解释：
        #   - choices: 模型可能返回多个候选回答（通常只有 1 个）
        #   - [0]: 取第一个候选回答
        #   - message: 回答的消息对象
        #   - content: 回答的实际文本内容
        answer = result["choices"][0]["message"]["content"]

        # 返回模型的回答文本
        return answer

    except requests.exceptions.Timeout:
        # 处理请求超时的异常
        return "[错误] 请求超时，请检查网络连接后重试。"

    except requests.exceptions.ConnectionError:
        # 处理网络连接错误的异常
        return "[错误] 无法连接到 API 服务器，请检查网络。"

    except requests.exceptions.HTTPError as e:
        # 处理 HTTP 错误状态码（如 401 未授权、429 频率限制等）
        return f"[错误] API 返回错误状态码: {e}"

    except KeyError:
        # 处理响应 JSON 格式不符合预期的情况
        return "[错误] 响应格式异常，无法解析模型回答。"

    except Exception as e:
        # 处理所有其他未预料到的异常
        return f"[错误] 发生未知错误: {e}"


def demo_single_turn():
    """
    演示单轮对话：发送一个问题，获取一个回答。

    功能：展示最简单的 API 调用方式，一问一答。
    输入参数：无。
    输出返回值：无（直接打印结果到控制台）。
    """
    # 打印分隔线和标题
    print("=" * 60)
    print("演示 1：单轮对话")
    print("=" * 60)

    # 构建消息列表
    # 单轮对话只需要一条 user 消息
    messages = [
        {
            "role": "user",  # 角色：用户
            "content": "请用一句话解释什么是人工智能。",  # 内容：用户问题
        }
    ]

    # 打印发送的请求信息，便于学习者理解请求结构
    print("\n--- 发送的请求 ---")
    print(f"URL: {API_URL}")  # 打印请求地址
    print(f"Model: {MODEL_NAME}")  # 打印模型名称
    print(f"消息: {json.dumps(messages, ensure_ascii=False, indent=2)}")  # 格式化打印消息

    # 调用 raw_chat 函数发送请求
    answer = raw_chat(messages)

    # 打印模型的回答
    print("\n--- 模型回答 ---")
    print(answer)
    print()


def demo_with_system_prompt():
    """
    演示带系统提示词的对话：通过 system 消息设定模型的行为。

    功能：展示如何使用 system 角色来控制模型的回答风格。
          system 消息是"幕后导演"，用户看不到，但模型会遵守。
    输入参数：无。
    输出返回值：无（直接打印结果到控制台）。
    """
    # 打印分隔线和标题
    print("=" * 60)
    print("演示 2：带系统提示词的对话")
    print("=" * 60)

    # 构建消息列表
    # 这里包含两条消息：
    #   1. system 消息：告诉模型它应该扮演什么角色
    #   2. user 消息：用户的实际问题
    messages = [
        {
            "role": "system",  # 角色：系统（设定模型行为）
            "content": "你是一位幽默风趣的科技博主，擅长用生动的比喻来解释技术概念。",
        },
        {
            "role": "user",  # 角色：用户
            "content": "请解释什么是 API？",
        },
    ]

    # 打印消息列表
    print("\n--- 发送的消息 ---")
    print(json.dumps(messages, ensure_ascii=False, indent=2))

    # 调用 raw_chat 函数
    answer = raw_chat(messages)

    # 打印模型回答
    print("\n--- 模型回答 ---")
    print(answer)
    print()


def demo_multi_turn():
    """
    演示多轮对话：手动维护消息历史，实现连续对话。

    功能：展示多轮对话的核心原理——
          每次请求都把完整的对话历史发送给模型，
          模型根据所有历史消息来理解上下文。
    输入参数：无。
    输出返回值：无（直接打印结果到控制台）。

    核心原理：
        大模型本身是"无状态"的，它不会记住之前的对话。
        所谓"多轮对话"，是客户端（我们的代码）在本地维护一个
        messages 列表，每次请求时都把完整的列表发送过去。
        模型看到完整的历史后，就能理解上下文并生成连贯的回答。
    """
    # 打印分隔线和标题
    print("=" * 60)
    print("演示 3：多轮对话（手动维护消息历史）")
    print("=" * 60)

    # 初始化消息列表
    # 先放入一条 system 消息，设定模型为 Python 编程导师
    messages = [
        {
            "role": "system",  # 角色：系统
            "content": "你是一位耐心的 Python 编程导师，回答简洁明了。",
        },
    ]

    # 定义多轮对话中用户要依次提出的问题列表
    # 这些问题是层层递进的，后面的问题依赖前面的上下文
    user_questions = [
        "Python 中的列表和元组有什么区别？",  # 第一轮：基础概念
        "你能给我举个具体的代码例子吗？",  # 第二轮：要求举例（依赖上下文）
        "那在实际项目中，我应该怎么选择用哪个？",  # 第三轮：进一步深入
    ]

    # 遍历每个问题，逐轮进行对话
    for turn_index, question in enumerate(user_questions):
        # 打印当前轮次信息
        print(f"\n--- 第 {turn_index + 1} 轮对话 ---")
        print(f"用户: {question}")

        # 将用户的新问题添加到消息列表中
        messages.append({
            "role": "user",  # 角色：用户
            "content": question,  # 内容：当前轮的问题
        })

        # 发送包含完整历史的消息列表给 API
        # 注意：每次都发送完整的 messages 列表，不是只发当前问题
        answer = raw_chat(messages)

        # 打印模型的回答
        print(f"模型: {answer}")

        # 将模型的回答也添加到消息列表中
        # 这样下一轮对话时，模型就能看到之前的问答记录
        messages.append({
            "role": "assistant",  # 角色：助手（模型回答）
            "content": answer,  # 内容：模型的回答
        })

    # 对话结束后，打印完整的消息历史
    print("\n--- 完整对话历史 ---")
    print(f"消息总数: {len(messages)} 条")
    # 遍历消息列表，展示每条消息的角色和内容摘要
    for i, msg in enumerate(messages):
        # 截取消息内容的前 50 个字符用于预览
        content_preview = msg["content"][:50]
        # 如果内容超过 50 个字符，添加省略号
        if len(msg["content"]) > 50:
            content_preview = content_preview + "..."
        # 打印消息序号、角色和内容预览
        print(f"  [{i}] {msg['role']}: {content_preview}")

    print()


def check_api_key():
    """
    检查 API Key 是否已配置。

    功能：在运行演示之前，先确认 API Key 已正确设置。
    输入参数：无。
    输出返回值：
        bool: True 表示已配置，False 表示未配置。
    """
    # 检查 API_KEY 是否为空或者仍是示例值
    if not API_KEY:
        # 如果 API Key 为空，提示用户配置
        print("[警告] 未检测到 DEEPSEEK_API_KEY！")
        print("请按以下步骤配置：")
        print("  1. 复制 .env.example 为 .env")
        print("  2. 在 .env 中填入真实的 DEEPSEEK_API_KEY")
        return False
    # 检查是否仍是 .env.example 中的占位符
    if API_KEY.startswith("sk-your"):
        # 如果是占位符，提示用户替换
        print("[警告] 检测到 DEEPSEEK_API_KEY 仍是示例值！")
        print("请在 .env 文件中替换为真实的 API Key。")
        return False
    # API Key 已正确配置
    print(f"[✓] API Key 已配置（末尾: ...{API_KEY[-4:]}）")
    return True


# ============================================================
# 主程序入口
# ============================================================
if __name__ == "__main__":
    # 打印课程标题
    print()
    print("*" * 60)
    print("*  Day 1 - 课程 1：原始 API 调用（理解底层原理）")
    print("*" * 60)
    print()

    # 检查 API Key 是否已配置
    is_key_ready = check_api_key()

    # 如果 API Key 未配置，终止运行
    if not is_key_ready:
        print("\n请配置好 API Key 后重新运行本脚本。")
    else:
        # API Key 已配置，依次运行三个演示
        print("\n开始运行演示...\n")

        # 演示 1：单轮对话
        demo_single_turn()

        # 演示 2：带系统提示词的对话
        demo_with_system_prompt()

        # 演示 3：多轮对话
        demo_multi_turn()

        # 打印课程总结
        print("=" * 60)
        print("课程 1 总结")
        print("=" * 60)
        print("你已经学会了：")
        print("  1. 如何用 requests 库直接调用大模型 API")
        print("  2. 请求结构：URL + Headers + Body")
        print("  3. 响应结构：choices[0].message.content")
        print("  4. 多轮对话原理：维护 messages 列表")
        print()
        print("下一课，我们将学习如何用 LangChain 框架")
        print("来简化这些操作，一行代码完成上面的所有步骤！")
        print("=" * 60)
