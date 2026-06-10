"""线上冒烟评估。

冒烟评估不是完整评测集，而是上线前和发布后快速确认服务没有明显退化。
"""

from __future__ import annotations

from dataclasses import dataclass

from project_11_agent_service_ops.gateway.model_gateway import ModelGateway


@dataclass(frozen=True)
class EvalCase:
    """一条冒烟评估用例。"""

    question: str
    expected_keywords: tuple[str, ...]


@dataclass(frozen=True)
class SmokeEvalResult:
    """冒烟评估结果。"""

    total: int
    passed: int
    failed_questions: tuple[str, ...]
    score: float


DEFAULT_EVAL_CASES = (
    EvalCase(
        question="企业 Agent 服务上线前要检查哪些生产治理能力？",
        expected_keywords=("生产", "Agent"),
    ),
    EvalCase(
        question="模型网关为什么需要成本治理？",
        expected_keywords=("模型", "网关"),
    ),
)


class SmokeEvaluator:
    """对 Agent 服务做最小冒烟评估。"""

    def __init__(self, gateway: ModelGateway, cases: tuple[EvalCase, ...] | None = None):
        self.gateway = gateway
        self.cases = cases or DEFAULT_EVAL_CASES

    def run(self, tenant_id: str) -> SmokeEvalResult:
        """执行冒烟评估并返回通过率。"""
        failed: list[str] = []
        for case in self.cases:
            response = self.gateway.generate(case.question, tenant_id=tenant_id)
            if not all(keyword in response.text for keyword in case.expected_keywords):
                failed.append(case.question)

        total = len(self.cases)
        passed = total - len(failed)
        score = passed / total if total else 0.0
        return SmokeEvalResult(
            total=total,
            passed=passed,
            failed_questions=tuple(failed),
            score=round(score, 4),
        )
