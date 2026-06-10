"""可观测性与冒烟评估测试。"""

from __future__ import annotations

import unittest

from project_11_agent_service_ops.evaluation.smoke_eval import SmokeEvaluator
from project_11_agent_service_ops.gateway.cost_tracker import BudgetTracker
from project_11_agent_service_ops.gateway.model_gateway import ModelGateway, default_routes
from project_11_agent_service_ops.observability.metrics import MetricsRegistry
from project_11_agent_service_ops.observability.tracing import TraceRecorder


class ObservabilityTest(unittest.TestCase):
    def test_trace_recorder_groups_events_by_run_id(self) -> None:
        recorder = TraceRecorder()
        run_id = recorder.new_run_id()

        recorder.record(run_id, "auth.accepted", {"tenant_id": "tenant-a"})
        recorder.record(run_id, "model.completed", {"model": "demo"})

        events = recorder.events_for_run(run_id)
        as_dicts = recorder.to_dicts(run_id)

        self.assertEqual(len(events), 2)
        self.assertEqual(as_dicts[0]["name"], "auth.accepted")
        self.assertEqual(as_dicts[1]["attributes"]["model"], "demo")

    def test_metrics_registry_records_success_and_error(self) -> None:
        registry = MetricsRegistry()

        registry.record_success(
            model_name="deepseek-chat",
            input_tokens=10,
            output_tokens=20,
            cost_cents=0.01,
            latency_ms=12.5,
        )
        registry.record_error()
        snapshot = registry.snapshot()

        self.assertEqual(snapshot.request_count, 2)
        self.assertEqual(snapshot.error_count, 1)
        self.assertEqual(snapshot.model_calls["deepseek-chat"], 1)
        self.assertEqual(snapshot.average_latency_ms, 12.5)

    def test_smoke_eval_runs_against_gateway(self) -> None:
        gateway = ModelGateway(
            routes=default_routes(),
            budget_tracker=BudgetTracker(daily_budget_cents=10),
        )
        evaluator = SmokeEvaluator(gateway)

        result = evaluator.run(tenant_id="tenant-a")

        self.assertEqual(result.total, 2)
        self.assertEqual(result.passed, 2)
        self.assertEqual(result.score, 1.0)


if __name__ == "__main__":
    unittest.main()
