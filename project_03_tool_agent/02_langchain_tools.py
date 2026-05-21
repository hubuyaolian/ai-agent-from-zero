"""
Day 5 - 课程 2：使用 LangChain 的 @tool 装饰器定义工具。

学习目标：
    1. 掌握 LangChain 中的 @tool 装饰器。
    2. 理解 @tool 是如何自动根据函数 Docstring、参数类型推导生成 JSON Schema 的。
    3. 掌握如何在 Python 代码中直接触发并测试 tool.invoke()。
"""

# 导入系统模块
import sys
# 导入系统路径模块
import os
# 导入 JSON 模块用于格式化输出
import json
# 导入类型提示中的可选参数类型
from typing import Optional


# 取得当前脚本的绝对目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将项目根目录置入搜索路径首位
sys.path.insert(0, os.path.join(CURRENT_DIR, '..'))

# 导入 LangChain 的 tool 装饰器
from langchain_core.tools import tool  # noqa: E402


@tool
def get_weather(city: str) -> str:
    """
    获取指定中国城市的当前天气情况。

    Args:
        city: 城市名称，例如 '北京'、'上海'、'广州'。

    Returns:
        包含温度、湿度及天气状态的字符串。
    """
    # 模拟简单的本地天气字典
    weather_dict = {
        "北京": "北京今天晴天，气温28°C，微风。",
        "上海": "上海今天小雨，气温24°C，东风3级。",
        "广州": "广州今天多云，气温32°C，南风2级。",
    }
    # 从字典中读取天气，若不存在则返回默认描述
    weather_result = weather_dict.get(city, f"{city}天气晴朗，气温26°C。")
    # 返回天气数据
    return weather_result


@tool
def search_products(
    keyword: str,
    category: Optional[str] = None,
    max_price: float = 1000.0
) -> str:
    """
    根据关键词、商品类别和最高价格限制搜索商品。

    Args:
        keyword: 搜索关键词，例如 '手机'、'书'。
        category: 可选的商品分类，例如 '电子'、'图书'、'服装'。
        max_price: 最高价格限制，默认为 1000.0 元。

    Returns:
        搜索结果的列表描述字符串。
    """
    # 模拟商品数据库
    products = [
        {"name": "Python编程从入门到精通", "category": "图书", "price": 89.0},
        {"name": "极客蓝牙耳机", "category": "电子", "price": 299.0},
        {"name": "智能运动手表", "category": "电子", "price": 899.0},
        {"name": "纯棉商务衬衫", "category": "服装", "price": 199.0},
        {"name": "高档皮包", "category": "皮具", "price": 1200.0},
    ]

    # 初始化空的结果列表
    results = []
    # 遍历所有模拟商品
    for p in products:
        # 如果商品价格超出了限制的最大价格
        if p["price"] > max_price:
            # 跳过当前商品
            continue

        # 如果指定了商品类别且该商品的类别不匹配
        if category is not None:
            # 判断是否不一致
            if p["category"] != category:
                # 跳过当前商品
                continue

        # 检查商品的名称是否包含搜索关键词
        if keyword in p["name"]:
            # 将匹配的商品名称和价格格式化追加到结果中
            results.append(f"{p['name']} (价格: {p['price']}元)")

    # 如果找到了符合条件的商品列表
    if len(results) > 0:
        # 用换行符拼接后返回
        return "\n".join(results)
    # 没有找到任何匹配的商品
    else:
        # 返回未找到的提示信息
        return f"未找到在类别 '{category}' 中价格不超过 {max_price} 元且包含关键字 '{keyword}' 的商品。"


def print_tool_info(target_tool):
    """
    打印 LangChain 工具的 Schema 细节。

    功能：演示工具是如何把 Python 函数反射并转换成 JSON 模式的。
    输入参数：
        target_tool: LangChain 工具实例。
    输出返回值：无。
    """
    # 打印工具头部提示
    print("-" * 50)
    # 打印工具名称
    print(f"🔧 工具名称 (name): {target_tool.name}")
    # 打印工具的文本描述
    print(f"📄 工具描述 (description):\n{target_tool.description}")
    # 打印工具提取的参数输入 Schema
    print("📋 工具输入 Schema (args):")
    # 将 args 属性以 JSON 格式美化打印
    print(json.dumps(target_tool.args, indent=2, ensure_ascii=False))
    # 打印工具头部尾线
    print("-" * 50)


def main():
    """
    Day 5 课程 2 主测试程序。
    """
    # 打印标题
    print("=" * 60)
    print("🚀 Day 5 - 课程 2：用 @tool 装饰器自动生成 Schema")
    print("=" * 60)

    # 1. 打印 get_weather 工具的反射 Schema
    print("\n[示例 1] 查看 get_weather 工具的 Schema 定义")
    print_tool_info(get_weather)

    # 2. 打印 search_products 工具的反射 Schema（多参数、可选参数）
    print("\n[示例 2] 查看 search_products 工具的 Schema 定义")
    print_tool_info(search_products)

    # 3. 直接在 Python 本地调用和测试工具
    print("\n[示例 3] 在本地调用并运行工具实例进行单元测试")

    # 测试 1: 直接以 invoke 传参调用天气工具
    weather_result = get_weather.invoke({"city": "北京"})
    print(f"  get_weather.invoke('北京') => {weather_result}")

    # 测试 2: 直接以 invoke 传参调用商品搜索工具
    search_result_1 = search_products.invoke({
        "keyword": "智能",
        "category": "电子",
        "max_price": 1000.0
    })
    print(f"\n  search_products.invoke('智能', '电子', 1000.0) 结果:\n{search_result_1}")

    # 测试 3: 测试价格过滤
    search_result_2 = search_products.invoke({
        "keyword": "皮包",
        "max_price": 500.0
    })
    print(f"\n  search_products.invoke('皮包', max_price=500) 结果:\n{search_result_2}")


# 主程序入口常规判定
if __name__ == "__main__":
    # 运行 main
    main()
