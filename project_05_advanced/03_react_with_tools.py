# -*- coding: utf-8 -*-
"""
Day 11 演示：ReAct Agent + 丰富工具集处理复杂多步推理任务。

功能：利用 LangGraph 编译包含搜索、物理写文件、物理读文件等工具的 ReAct 智能体，
      执行包含检索、代码编写、文件保存、文件校验以及最终总结的多步骤宏观复合任务。
输入参数：无。
输出返回值：控制台输出 Agent 执行流程和保存在磁盘的文件，并自动清理恢复现场。
"""

# 导入操作系统相关模块，用于后续文件物理删除
import os
# 导入 LangChain 的 @tool 装饰器
from langchain_core.tools import tool
# 导入 LangChain 基础消息类
from langchain_core.messages import HumanMessage
# 导入 LangGraph 预构建的 ReAct 状态图构建器
from langgraph.prebuilt import create_react_agent

# 从公共模型工厂中导入模型创建函数
from common.model_factory import create_model


# ============================================================
# 定义丰富、实用的 @tool 外部工具集（包含磁盘物理读写）
# ============================================================

@tool
def web_search(query: str) -> str:
    """搜索互联网获取最新的技术知识和事实信息。

    当用户询问关于某项新技术的定义、版本特性、API 说明或目前互联网上的最新发展动态时，
    调用此工具来获取真实可靠的技术资料。

    Args:
        query: 检索关键词或具体提问句。

    Returns:
        str: 检索到的相关互联网网页文字摘要。
    """
    # 剔除首尾无用空格
    query_clean = query.strip()
    print(f"\n   [工具 web_search] 正在联网搜索: '{query_clean}'...")

    # 对 'Python 3.12' 进行关键词判断
    if "python 3.12" in query_clean.lower() or "3.12" in query_clean:
        # 返回模拟的 Python 3.12 官方新特性说明
        return (
            "Python 3.12 于 2023 年 10 月正式发布。其核心的重大改进与新特性包括：\n"
            "1. PEP 695 引入了更简洁的类型参数语法 (Type Parameter Syntax)，支持直接在"
            "函数和类名后使用方括号声明泛型，如: def max_val[T](x: list[T]) -> T。\n"
            "2. PEP 701 彻底改进了 f-string 的语法限制，使得 f-string 内部可以嵌套使用相同"
            "的单双引号、多行表达式、反斜杠转义符以及中文注释。\n"
            "3. 引入了 PEP 684 独立的子解释器 (Per-Interpreter GIL)，并进一步优化了性能。"
        )
    else:
        # 其他查询返回默认模板
        return f"互联网上关于 '{query_clean}' 的相关讨论非常广泛，推荐使用官方文档进行查证。"


@tool
def write_file(filename: str, content: str) -> str:
    """将指定的内容物理写入本地磁盘文件中。

    当需要保存大模型生成的代码清单、测试用例、部署总结或者普通的 TXT/MD 说明文档时，
    调用此工具将文本保存至磁盘中。

    Args:
        filename: 物理保存的文件名（如：temp_demo.py）。
        content: 写入文件的完整文本内容。

    Returns:
        str: 文件写入操作的状态结果说明。
    """
    # 打印写入日志
    print(f"\n   [工具 write_file] 正在物理写入文件: {filename}...")
    try:
        # 以 UTF-8 编码将内容写入文件中
        with open(filename, "w", encoding="utf-8") as f:
            # 物理写入
            f.write(content)
        # 返回成功提示
        return f"✅ 物理文件 '{filename}' 成功保存至当前目录！写入字符数: {len(content)}"
    except Exception as err:
        # 捕获文件写入权限或磁盘空间异常
        return f"❌ 物理文件写入失败，原因: {str(err)}"


@tool
def read_file(filename: str) -> str:
    """读取并返回本地磁盘指定文件中的全部文本内容。

    当需要对刚刚生成或已有的本地文件进行内容核对、逻辑校验或二次解析重写时，
    调用此工具获取文件中的数据。

    Args:
        filename: 待读取的文件名。

    Returns:
        str: 读取到的文件内全部文本。
    """
    # 打印读取日志
    print(f"\n   [工具 read_file] 正在物理读取文件: {filename}...")
    # 检查该文件是否在当前目录中存在
    if not os.path.exists(filename):
        # 不存在则返回报错
        return f"❌ 错误：在当前目录下找不到文件 '{filename}'。"
    else:
        # 存在则继续
        pass

    try:
        # 以 UTF-8 编码读取该文件的全部文本
        with open(filename, "r", encoding="utf-8") as f:
            # 读取
            content = f.read()
        # 返回读取成功的数据
        return content
    except Exception as err:
        # 捕获文件读取权限或损坏异常
        return f"❌ 物理文件读取失败，原因: {str(err)}"


def main():
    """
    主运行函数。

    功能：初始化 Qwen 聊天模型，配置三个工具，注入 ReAct 最佳实践 Prompt 提示，执行复杂多步指令，并在结束后物理删除临时文件。
    """
    # 定义测试用的临时文件名
    demo_filename = "temp_python312_demo.py"

    # 初始化重置，防止历史遗留干扰
    if os.path.exists(demo_filename):
        # 删除已有文件
        os.remove(demo_filename)
    else:
        pass

    print("🧠 正在配置底层大模型（xiaomi mimo）并注入丰富工具集...")
    # 教学阶段 04 之后默认 LLM 统一走 xiaomi mimo，温度设为 0.0 保障逻辑严密性
    base_model = create_model(provider="xiaomi mimo", temperature=0.0)

    # 包含 web_search, write_file, read_file 的多维工具组
    tool_list = [web_search, write_file, read_file]

    # 定义 ReAct 最佳实践系统提示词，规范多步规划行为
    system_prompt = (
        "你是一个极其卓越、考虑极为周全的技术 Agent 助理。\n"
        "在处理用户的复杂复合任务时，请严格遵守以下核心指导法则：\n"
        "1. **拆解规划**：首先将用户的复杂请求，合理细分成多个小步骤进行全局策略编排。\n"
        "2. **稳健行事**：必须且仅在获得必不可少的外部数据后，方能开展下一步动作。\n"
        "3. **闭环校验**：在通过 write_file 写入代码到本地后，你必须紧接着调用 read_file "
        "工具读出代码文件中的全部内容进行二次确认，校准格式、确保无乱码和缺失后，方能宣告任务完成。\n\n"
        "请使用最清晰、条理分明的中文格式，汇报你每一步的执行过程与最终校验成果。"
    )

    print("\n📦 正在使用 LangGraph 编译高级多工具 ReAct 智能体...")
    # 编译生成状态图
    agent = create_react_agent(
        model=base_model,
        tools=tool_list,
        prompt=system_prompt
    )
    print("✅ 智能体状态图编译就绪！")

    # 构建极度硬核的多步骤复合型技术指令
    hard_instruction = (
        "1. 帮我搜索 Python 3.12 引入的新特性。\n"
        "2. 针对类型参数语法和 f-string 的改进，帮我编写一个最简的 Python 3.12 示例代码。\n"
        f"3. 调用 write_file 工具，将这个示例代码保存到本地临时文件 '{demo_filename}' 中。\n"
        f"4. 物理文件保存成功后，调用 read_file 工具读取 '{demo_filename}' 的内容进行闭环检验。\n"
        "5. 校验无误后，向我汇报你本次操作的完整步骤和最终代码内容。"
    )

    print("\n🚀 正在发送高难度技术任务...")
    print(f"任务内容:\n{hard_instruction}")
    print("=" * 60)

    # 启动状态图运行，流式追踪 values 变化
    initial_state = {
        "messages": [HumanMessage(content=hard_instruction)]
    }

    # 遍历事件流
    for event in agent.stream(initial_state, stream_mode="values"):
        # 确认事件中存有 messages 属性
        if "messages" in event and event["messages"]:
            # 抓取最后一条最新的消息
            last_msg = event["messages"][-1]
            msg_type = last_msg.type.upper()

            # 区分类型输出，保持控制台视觉美感
            if msg_type == "HUMAN":
                # 用户提问
                print("\n👤 [用户首问] >>> 发送任务指令。")
            elif msg_type == "AI":
                # 大模型生成
                print("\n🤖 [AI 推理思考]:")
                if last_msg.tool_calls:
                    # 遍历打印工具执行建议
                    for tc in last_msg.tool_calls:
                        print(f"   🛠️ 建议调用: '{tc['name']}'，参数为: {tc['args']}")
                else:
                    # 正常汇报
                    print(last_msg.content)
            elif msg_type == "TOOL":
                # 工具执行结果
                print("\n📥 [工具反馈]:")
                # 截断打印长内容，保证排版整洁
                lines = last_msg.content.splitlines()
                if len(lines) > 6:
                    preview = "\n".join(lines[:6]) + "\n   ... (后略) ..."
                else:
                    preview = last_msg.content
                print(f"   数据: {preview}")
            else:
                pass
        else:
            pass

    print("=" * 60)
    print("🎉 复合任务流式执行成功！")

    # 进行物理校验与收尾，清理环境
    print("\n🧹 正在执行环境清理自检...")
    # 检查本地是否生成了该文件
    if os.path.exists(demo_filename):
        print(f"  - 校验：物理文件 '{demo_filename}' 确实成功生成在当前文件夹中！")
        # 读取内容展示给学员以资鼓励
        with open(demo_filename, "r", encoding="utf-8") as rf:
            print(f"  - 文件内容展示:\n{rf.read()}")
        # 执行删除，恢复现场
        os.remove(demo_filename)
        print(f"  - 物理文件 '{demo_filename}' 已被安全清理，还原了工作区整洁。")
    else:
        print(f"  - 警告：未能检测到本地文件 '{demo_filename}'，请确认 write_file 工具的运行情况。")

    print("\n✨ 多工具 ReAct 智能体处理复杂任务演示圆满完成。")


# 判断是否自命令行启动
if __name__ == "__main__":
    # 执行主程序
    main()
