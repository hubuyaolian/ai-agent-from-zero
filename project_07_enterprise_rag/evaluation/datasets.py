"""最小评估集示例。"""

EVAL_CASES = [
    {
        "question": "员工入职满一年后年假是多少天？",
        "expected_answer_contains": ["15 天"],
        "gold_chunk_ids": ["employee_handbook:v2024:chunk_0018"],
        "type": "fact_lookup",
    },
    {
        "question": "SKU-2024-A 的保修周期是什么？",
        "expected_answer_contains": ["12 个月"],
        "gold_chunk_ids": ["product_policy:v3:chunk_0041"],
        "type": "exact_match",
    },
    {
        "question": "它支持哪些工作流能力？",
        "expected_answer_contains": ["状态", "条件分支"],
        "gold_chunk_ids": ["langgraph_manual:v1:chunk_0002"],
        "type": "follow_up",
    },
]

