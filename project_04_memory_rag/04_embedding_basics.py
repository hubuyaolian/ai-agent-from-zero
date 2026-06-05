# -*- coding: utf-8 -*-
"""
Day 9 演示：Embedding 概念与语义相似度手动计算。

功能：演示如何使用通义千问兼容接口将文本转化为高维数值向量，并手动计算余弦相似度。
输入参数：无（内部定义测试文本）。
输出返回值：打印各文本的向量特征以及两两之间的语义相似度。
"""

# 导入 LangChain 的 OpenAIEmbeddings 包装类
from langchain_openai import OpenAIEmbeddings

# 从项目的公共配置模块中导入获取模型配置的函数
from common.config import get_model_config


def calculate_cosine_similarity(vector_a, vector_b):
    """
    手动计算两个数值向量之间的余弦相似度。

    功能：根据余弦相似度数学公式，计算两个向量的点积和各自模长，得出相似度。
    输入参数：
        vector_a (list[float]): 第一个高维数值向量。
        vector_b (list[float]): 第二个高维数值向量。
    输出返回值：
        float: 两个向量的余弦相似度，取值范围为 [-1, 1]。
    """
    # 初始化两个向量的点积之和
    dot_product = 0.0
    # 初始化向量 A 的模长平方和
    norm_a = 0.0
    # 初始化向量 B 的模长平方和
    norm_b = 0.0

    # 循环遍历向量的每一个维度进行累加计算
    for i in range(len(vector_a)):
        # 获取向量 A 在当前维度的数值
        val_a = vector_a[i]
        # 获取向量 B 在当前维度的数值
        val_b = vector_b[i]
        # 累加点积：当前维度的两数值相乘
        dot_product += val_a * val_b
        # 累加向量 A 该维度的平方值
        norm_a += val_a * val_a
        # 累加向量 B 该维度的平方值
        norm_b += val_b * val_b

    # 计算向量 A 的欧几里得模长（开平方）
    length_a = norm_a ** 0.5
    # 计算向量 B 的欧几里得模长（开平方）
    length_b = norm_b ** 0.5

    # 检查分母是否为 0，防止除以零的计算异常
    if length_a * length_b == 0:
        # 如果其中一个向量模长为零，则返回相似度 0.0
        return 0.0

    # 计算最终的余弦相似度
    similarity = dot_product / (length_a * length_b)
    # 返回计算结果
    return similarity


def main():
    """
    主运行函数。

    功能：执行 Embedding 向量化流程，并计算两组文本之间的余弦相似度。
    """
    print("🔮 正在初始化 Embedding 模型...")

    # 教学阶段 04 之后统一以 xiaomi mimo 为默认 LLM；
    # 本文件仅使用 embedding 服务，因此沿用 deepseek 作为兼容 OpenAI 格式的 embedding 提供方。
    embedding_config = get_model_config("deepseek")

    # 初始化 OpenAIEmbeddings，使用 deepseek 的 OpenAI 兼容接口
    embeddings = OpenAIEmbeddings(
        model="text-embedding-v3",  # 占位：deepseek 暂未提供文本 embedding，可按需切到支持的服务
        base_url=embedding_config["base_url"],  # 兼容 OpenAI 的 API 基地址
        api_key=embedding_config["api_key"]  # 从配置中获取的 API Key
    )

    # 准备用于语义测试的文本列表
    text_1 = "今天北京天气很好"
    text_2 = "北京今日天气晴朗"
    text_3 = "量子力学的基本原理"

    print("\n1. 正在将文本向量化...")
    print(f"文本 A: '{text_1}'")
    print(f"文本 B: '{text_2}'")
    print(f"文本 C: '{text_3}'")

    # 对文本 A 进行单条向量化
    vector_a = embeddings.embed_query(text_1)
    # 对文本 B 进行单条向量化
    vector_b = embeddings.embed_query(text_2)
    # 对文本 C 进行单条向量化
    vector_c = embeddings.embed_query(text_3)

    # 打印向量化后的特征信息
    print("\n2. 向量化结果分析:")
    print(f"文本 A 向量维度: {len(vector_a)}")
    print(f"文本 A 前 5 维数据: {vector_a[:5]}")

    # 计算文本两两之间的余弦相似度
    sim_ab = calculate_cosine_similarity(vector_a, vector_b)
    sim_ac = calculate_cosine_similarity(vector_a, vector_c)

    print("\n3. 余弦相似度计算结果:")
    # 打印文本 A 和文本 B 的相似度（语义相近，相似度应该较高）
    print(f"A 与 B 相似度 (天气 vs. 天气): {sim_ab:.4f}")
    # 打印文本 A 和文本 C 的相似度（语义无关，相似度应该较低）
    print(f"A 与 C 相似度 (天气 vs. 量子力学): {sim_ac:.4f}")

    # 根据相似度结果打印简单说明
    if sim_ab > sim_ac:
        print("\n💡 实验验证成功：语义相近的文本向量距离确实更近！")
    else:
        print("\n⚠️ 提示：计算结果不符合预期，请检查输入或配置。")


# 判断是否作为主脚本直接运行
if __name__ == "__main__":
    # 执行主程序
    main()
