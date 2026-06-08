"""
Day 8 - 课程 1：短期记忆的局限性复习与演练。

学习目标：
    1. 温习短期记忆（运行期间消息列表）在维持会话连贯性中的作用。
    2. 直观体验程序关闭或重置后，短期记忆彻底消失的局限。
    3. 为引入基于 SQLite 的长期记忆做铺垫。
"""

# 导入系统模块
import sys
# 导入系统路径模块
import os

# 取得当前脚本所在的绝对路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将项目根目录置入搜索路径首位
sys.path.insert(0, os.path.join(CURRENT_DIR, '..'))

# 从公共模块中导入模型构建工厂函数
from common.model_factory import create_model  # noqa: E402
# 导入 LangChain 的消息基础类
from langchain_core.messages import (  # noqa: E402
    HumanMessage,    # 用户发送的消息
)

# 终端 ANSI 颜色定义，用于美化控制台输出
COLOR_RESET = "\033[0m"      # 重置样式
COLOR_GREEN = "\033[32m"     # 绿色表示用户
COLOR_BLUE = "\033[34m"      # 蓝色表示 AI 回复
COLOR_CYAN = "\033[36m"      # 青色表示系统状态
COLOR_YELLOW = "\033[33m"    # 黄色表示警告


class ShortTermChatSession:
    """
    短期记忆对话会话类。

    维护一个内存中的消息列表，模拟生命周期仅限于程序运行期间的短期上下文。
    """

    def __init__(self):
        """
        初始化短期会话类。
        """
        # 初始化用于缓存消息列表的内存数组
        self.messages = []
        # 创建默认大模型实例
        self.model = create_model("xiaomi mimo", temperature=0.7)

    def chat(self, user_input: str):
        """
        向大模型发送消息并维护对话历史。

        Args:
            user_input: 用户输入的文本字符串。
        """
        # 将用户当前输入封装成 HumanMessage 并追加至短期记忆
        self.messages.append(HumanMessage(content=user_input))

        try:
            # 携带完整的短期记忆列表调用大模型
            response = self.model.invoke(self.messages)
            # 将大模型的 AIMessage 响应追加至记忆列表
            self.messages.append(response)
            # 打印大模型答复
            print(f"{COLOR_BLUE}AI > {response.content}{COLOR_RESET}")
        # 捕获请求过程中的任何异常
        except Exception as e:
            # 打印出错提示
            print(f"❌ 运行异常: {e}")

    def clear(self):
        """
        清空短期记忆消息列表。
        """
        # 重新将消息列表置为空列表，模拟内存释放或程序重启
        self.messages = []
        # 打印清空提示
        print(f"{COLOR_YELLOW}⚠️ [系统提示] 短期内存已被重置清空！{COLOR_RESET}")


def main():
    """
    Day 8 课程 1 主测试入口。
    """
    # 打印欢迎标题
    print("=" * 60)
    print("🚀 Day 8 - 课程 1：内存短期记忆局限性演练")
    print("=" * 60)

    # 实例化会话对象
    session = ShortTermChatSession()

    # 第一轮交互：告知 AI 用户身份
    print(f"\n{COLOR_CYAN}--- 模拟正常多轮会话（短期记忆生效中）---{COLOR_RESET}")
    print(f"{COLOR_GREEN}User > 你好，我叫小明，我现在正在自学 AI Agent 开发。{COLOR_RESET}")
    session.chat("你好，我叫小明，我现在正在自学 AI Agent 开发。")

    # 第二轮交互：测试 AI 是否能从历史消息中读出名字
    print(f"\n{COLOR_GREEN}User > 刚才告诉你我正在学什么来着？我叫什么名字？{COLOR_RESET}")
    session.chat("刚才告诉你我正在学什么来着？我叫什么名字？")

    # 模拟程序重启：清空内存里的消息列表
    print(f"\n{COLOR_CYAN}--- 模拟程序关闭并重新启动 ---{COLOR_RESET}")
    session.clear()

    # 重启后第三轮交互：再次提问同样的问题
    print(f"\n{COLOR_GREEN}User > 你好，还记得我刚才说我叫什么名字以及在学什么吗？{COLOR_RESET}")
    session.chat("你好，还记得我刚才说我叫什么名字以及在学什么吗？")
    print("=" * 60 + "\n")


# 主程序入口运行判定
if __name__ == "__main__":
    # 执行 main
    main()
