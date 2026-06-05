"""评估运行器。"""

from __future__ import annotations

from project_07_enterprise_rag.evaluation.datasets import EVAL_CASES
from project_07_enterprise_rag.evaluation.metrics import evaluate_retrieval
from project_07_enterprise_rag.governance.access_filter import UserContext


def run_retrieval_eval(retriever, user_context: UserContext, k: int = 5) -> dict:
    results = []
    for case in EVAL_CASES:
        docs = retriever.retrieve(case["question"], k=k, user_context=user_context)
        results.append(docs)
    return evaluate_retrieval(EVAL_CASES, results, k=k)
