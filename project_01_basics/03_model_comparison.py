"""
==========================================================================
Day 1 - 课程 3：多模型对比（同一问题，不同模型回答）
==========================================================================

学习目标：
    1. 实践用统一的代码调用多个大模型
    2. 对比不同模型在知识问答、创意写作、逻辑推理上的表现
    3. 学会计时对比各模型的响应速度
    4. 掌握异常处理技巧：某个模型失败不影响其他模型
    5. 通过实际对比，建立对各模型能力的直觉认知

为什么要做模型对比？
    - 不同模型在不同任务上的表现差异很大
    - 有些模型擅长知识问答，有些擅长创意写作
    - 了解各模型的特点后，才能在实际项目中做出最优选择
    - 响应速度也是选择模型的重要参考因素

前置条件：
    - 已在 .env 文件中配置了至少两个模型的 API Key
    - 已安装 langchain-openai 和 langchain-google-genai
==========================================================================
"""

import sys  # 系统模块，用于修改 Python 模块搜索路径
import os  # 操作系统模块，用于路径操作
import time  # 时间模块，用于计算响应耗时

# ============================================================
# 路径配置：将项目根目录添加到 Python 模块搜索路径
# ============================================================
# 获取当前脚本所在目录的上级目录（即项目根目录）
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
# 将项目根目录插入到搜索路径的最前面
sys.path.insert(0, project_root)

# 从公共模块导入工厂函数和配置函数
from common.model_factory import create_model  # noqa: E402  # 创建模型实例的工厂函数
from common.config import list_available_providers  # noqa: E402  # 列出可用的模型提供商

# ============================================================
# 测试问题定义
# ============================================================
# 精心设计的测试问题，覆盖三个不同的能力维度
TEST_QUESTIONS = [
    {
        "category": "知识问答",  # 问题类别
        "question": "请简要解释量子计算和传统计算的核心区别是什么？",  # 问题内容
        "description": "测试模型的知识储备和概念解释能力",  # 问题说明
    },
    {
        "category": "创意写作",  # 问题类别
        "question": "请写一首关于人工智能的五言绝句（四句，每句五个字）。",  # 问题内容
        "description": "测试模型的中文创作能力和格式遵循能力",  # 问题说明
    },
    {
        "category": "逻辑推理",  # 问题类别
        "question": (
            "一个房间里有三盏灯和三个开关，"
            "每个开关控制一盏灯。你在房间外面，"
            "只能进入房间一次。如何确定每个开关"
            "分别控制哪盏灯？"
        ),  # 问题内容
        "description": "测试模型的逻辑思维和问题解决能力",  # 问题说明
    },
]


def call_model_with_timing(provider, question):
    """
    调用指定模型并记录响应时间。

    功能：创建模型实例，发送问题，记录耗时，返回结果。
    输入参数：
        provider (str): 模型提供商名称，如 "deepseek"、"qwen" 等。
        question (str): 要发送给模型的问题文本。
    输出返回值：
        dict: 包含以下字段的结果字典：
            - "provider" (str): 模型提供商名称
            - "answer" (str): 模型的回答文本
            - "time" (float): 响应耗时（秒）
            - "success" (bool): 是否调用成功
            - "error" (str): 错误信息（仅在失败时有值）
    """
    # 初始化结果字典
    result = {
        "provider": provider,  # 记录提供商名称
        "answer": "",  # 初始化回答为空
        "time": 0.0,  # 初始化耗时为 0
        "success": False,  # 初始化为未成功
        "error": "",  # 初始化错误信息为空
    }

    try:
        # 记录开始时间
        start_time = time.time()

        # 创建模型实例
        model = create_model(provider=provider)

        # 调用模型获取回答
        response = model.invoke(question)

        # 记录结束时间
        end_time = time.time()

        # 计算响应耗时（保留两位小数）
        elapsed_time = round(end_time - start_time, 2)

        # 填充结果字典
        result["answer"] = response.content  # 模型回答
        result["time"] = elapsed_time  # 响应耗时
        result["success"] = True  # 标记为成功

    except Exception as e:
        # 如果调用失败，记录错误信息
        result["error"] = str(e)  # 保存错误消息
        result["success"] = False  # 标记为失败

    # 返回结果字典
    return result


def print_separator(char="=", length=60):
    """
    打印分隔线。

    功能：打印指定字符和长度的分隔线，用于美化输出。
    输入参数：
        char (str): 分隔线使用的字符，默认 "="。
        length (int): 分隔线的长度，默认 60。
    输出返回值：无（直接打印到控制台）。
    """
    # 打印由指定字符重复指定次数组成的分隔线
    print(char * length)


def print_question_header(question_info, question_index):
    """
    打印问题标题信息。

    功能：格式化打印当前测试问题的标题、类别和说明。
    输入参数：
        question_info (dict): 问题信息字典，包含 category、question、description。
        question_index (int): 问题的序号（从 0 开始）。
    输出返回值：无（直接打印到控制台）。
    """
    # 打印空行和分隔线
    print()
    print_separator("=")
    # 打印问题序号和类别
    print(f"问题 {question_index + 1}：【{question_info['category']}】")
    # 打印分隔线
    print_separator("=")
    # 打印问题内容
    print(f"问题: {question_info['question']}")
    # 打印问题说明
    print(f"说明: {question_info['description']}")
    # 打印分隔线
    print_separator("-")


def print_model_result(result):
    """
    打印单个模型的回答结果。

    功能：格式化打印模型的提供商名称、回答内容和耗时。
    输入参数：
        result (dict): 调用结果字典，由 call_model_with_timing() 返回。
    输出返回值：无（直接打印到控制台）。
    """
    # 打印模型提供商名称（大写）
    print(f"\n🤖 {result['provider'].upper()}")

    # 判断调用是否成功
    if result["success"]:
        # 调用成功，打印回答内容
        print(f"   回答: {result['answer']}")
        # 打印响应耗时
        print(f"   ⏱️  耗时: {result['time']} 秒")
    else:
        # 调用失败，打印错误信息
        print(f"   ❌ 调用失败: {result['error']}")


def print_speed_ranking(all_results):
    """
    打印所有模型的响应速度排名。

    功能：将所有成功调用的模型按响应时间排序，打印排名表。
    输入参数：
        all_results (list[dict]): 所有调用结果的列表。
    输出返回值：无（直接打印到控制台）。
    """
    # 打印标题
    print()
    print_separator("=")
    print("📊 响应速度总排名")
    print_separator("=")

    # 从所有结果中筛选出成功调用的结果
    successful_results = []
    for result in all_results:
        # 只保留调用成功的结果
        if result["success"]:
            successful_results.append(result)

    # 如果没有成功的结果，提示并返回
    if not successful_results:
        print("没有成功的调用结果可以排名。")
        return

    # 按响应时间升序排序（最快的在前面）
    # key 参数指定排序依据，lambda 表达式取出 time 字段
    successful_results.sort(key=lambda x: x["time"])

    # 打印排名表
    for rank, result in enumerate(successful_results):
        # 为前三名添加奖牌表情
        # 根据排名选择不同的奖牌符号
        if rank == 0:
            medal = "🥇"
        elif rank == 1:
            medal = "🥈"
        elif rank == 2:
            medal = "🥉"
        else:
            medal = "  "

        # 打印排名信息
        print(
            f"  {medal} 第 {rank + 1} 名: "
            f"{result['provider'].upper()} "
            f"- {result['time']} 秒"
        )

    # 计算平均响应时间
    total_time = 0.0
    for result in successful_results:
        total_time = total_time + result["time"]
    # 平均值 = 总时间 / 成功调用数
    average_time = round(total_time / len(successful_results), 2)

    # 打印统计信息
    print(f"\n  平均响应时间: {average_time} 秒")
    # 打印最快和最慢的模型
    print(f"  最快: {successful_results[0]['provider'].upper()} ({successful_results[0]['time']} 秒)")
    print(f"  最慢: {successful_results[-1]['provider'].upper()} ({successful_results[-1]['time']} 秒)")


def run_comparison():
    """
    运行完整的多模型对比测试。

    功能：对所有可用模型提出所有测试问题，收集结果并打印对比报告。
    输入参数：无。
    输出返回值：无（直接打印结果到控制台）。
    """
    # 获取所有已配置 API Key 的模型提供商
    available_providers = list_available_providers()

    # 打印可用的模型信息
    print(f"检测到 {len(available_providers)} 个可用模型: {available_providers}")
    print(f"共 {len(TEST_QUESTIONS)} 道测试题目")

    # 检查可用模型数量
    if len(available_providers) < 2:
        # 如果可用模型少于 2 个，对比意义不大
        print("\n[提示] 建议至少配置 2 个模型的 API Key 来进行有意义的对比。")
        print("请在 .env 文件中配置更多模型的 API Key。")

    # 如果没有可用模型，直接返回
    if not available_providers:
        print("\n[错误] 没有可用的模型！请先配置 API Key。")
        return

    # 创建一个列表，收集所有调用结果（用于最终的速度排名）
    all_results = []

    # 遍历每个测试问题
    for q_index, question_info in enumerate(TEST_QUESTIONS):
        # 打印当前问题的标题信息
        print_question_header(question_info, q_index)

        # 遍历每个可用的模型提供商
        for provider in available_providers:
            # 打印正在调用的模型信息
            print(f"\n  正在调用 {provider}...", end="", flush=True)

            # 调用模型并获取结果（包含回答和耗时）
            result = call_model_with_timing(
                provider=provider,
                question=question_info["question"],
            )

            # 在结果中额外记录问题类别（用于后续分析）
            result["category"] = question_info["category"]

            # 打印该模型的回答结果
            print_model_result(result)

            # 将结果添加到总列表中
            all_results.append(result)

        # 每个问题结束后打印分隔线
        print_separator("-")

    # 所有问题回答完毕，打印速度排名
    print_speed_ranking(all_results)

    # 打印按类别的统计信息
    print_category_summary(all_results)


def print_category_summary(all_results):
    """
    按问题类别打印统计摘要。

    功能：将调用结果按类别分组，打印每个类别下各模型的表现。
    输入参数：
        all_results (list[dict]): 所有调用结果的列表。
    输出返回值：无（直接打印到控制台）。
    """
    # 打印标题
    print()
    print_separator("=")
    print("📋 按类别统计")
    print_separator("=")

    # 收集所有出现的类别
    categories = []
    for result in all_results:
        # 获取当前结果的类别
        category = result["category"]
        # 如果该类别还没有记录，就添加
        if category not in categories:
            categories.append(category)

    # 遍历每个类别
    for category in categories:
        # 打印类别标题
        print(f"\n【{category}】")

        # 筛选出该类别下的所有结果
        category_results = []
        for result in all_results:
            if result["category"] == category:
                category_results.append(result)

        # 打印该类别下每个模型的耗时
        for result in category_results:
            # 判断是否成功
            if result["success"]:
                print(
                    f"  {result['provider'].upper()}: "
                    f"{result['time']} 秒"
                )
            else:
                print(
                    f"  {result['provider'].upper()}: "
                    f"调用失败"
                )


# ============================================================
# 主程序入口
# ============================================================
if __name__ == "__main__":
    # 打印课程标题
    print()
    print("*" * 60)
    print("*  Day 1 - 课程 3：多模型对比测试")
    print("*" * 60)
    print()

    # 运行对比测试
    run_comparison()

    # 打印课程总结
    print()
    print_separator("=")
    print("课程 3 总结")
    print_separator("=")
    print("你已经学会了：")
    print("  1. 用统一的代码调用多个不同的大模型")
    print("  2. 对比不同模型在不同任务上的表现")
    print("  3. 计时对比各模型的响应速度")
    print("  4. 使用异常处理确保程序的健壮性")
    print()
    print("Day 1 的所有课程到此结束！")
    print("你已经完成了：")
    print("  课程 1：理解了 API 调用的底层原理（HTTP 请求）")
    print("  课程 2：学会了用 LangChain 框架简化开发")
    print("  课程 3：通过实际对比，认识了各模型的特点")
    print()
    print("明天我们将进入 Day 2，学习更多高级功能！")
    print_separator("=")
