"""工作流执行引擎。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from project_08_workflow_agent.executor.checkpoint_store import CheckpointStore, WorkflowCheckpoint
from project_08_workflow_agent.error_handler.retry import RetryHandler
from project_08_workflow_agent.governance.audit_log import AuditLog
from project_08_workflow_agent.governance.policy import UserContext
from project_08_workflow_agent.planner.models import ExecutionPlan, Step
from project_08_workflow_agent.planner.plan_validator import PlanValidator
from project_08_workflow_agent.planner.task_planner import TaskPlanner
from project_08_workflow_agent.tools.registry import ToolRegistry, create_registry


@dataclass
class StepResult:
    """单步执行结果。"""

    step_id: str
    tool: str
    status: str
    output: str = ""
    error: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "tool": self.tool,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "StepResult":
        return cls(**payload)


@dataclass
class WorkflowResult:
    """一次工作流运行结果。"""

    status: str
    run_id: str
    plan: ExecutionPlan
    step_results: list[StepResult]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"状态: {self.status}", f"运行 ID: {self.run_id}", f"计划 ID: {self.plan.plan_id}", "步骤:"]
        for result in self.step_results:
            detail = result.output or result.error
            detail = detail.replace("\n", " ")[:180]
            lines.append(f"- {result.step_id} [{result.status}] {result.tool}: {detail}")
        if self.warnings:
            lines.append("警告: " + "；".join(self.warnings))
        if self.errors:
            lines.append("错误: " + "；".join(self.errors))
        return "\n".join(lines)


class WorkflowEngine:
    """计划生成、审批判断、重试执行和审计串联。"""

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        planner: TaskPlanner | None = None,
        *,
        audit_log: AuditLog | None = None,
        retry_handler: RetryHandler | None = None,
        checkpoint_store: CheckpointStore | None = None,
    ):
        self.registry = registry or create_registry()
        self.planner = planner or TaskPlanner(self.registry)
        self.validator = PlanValidator(self.registry)
        self.audit_log = audit_log or AuditLog()
        self.retry_handler = retry_handler or RetryHandler(audit_log=self.audit_log)
        self.checkpoint_store = checkpoint_store or CheckpointStore()

    def run(self, instruction: str, user_context: UserContext | None = None) -> WorkflowResult:
        plan = self.planner.create_plan(instruction)
        return self.execute_plan(plan, user_context or UserContext())

    def execute_plan(
        self,
        plan: ExecutionPlan,
        user_context: UserContext,
        *,
        run_id: str | None = None,
        previous_results: list[StepResult] | None = None,
    ) -> WorkflowResult:
        run_id = run_id or uuid4().hex[:12]
        validation = self.validator.validate(plan)
        self.audit_log.record("plan_created", plan.to_dict())
        if not validation.ok:
            self.audit_log.record("plan_rejected", {"plan_id": plan.plan_id, "errors": validation.errors})
            result = WorkflowResult(
                status="invalid",
                run_id=run_id,
                plan=plan,
                step_results=[],
                warnings=validation.warnings,
                errors=validation.errors,
            )
            self._save_checkpoint(result)
            return result

        step_results: list[StepResult] = []
        result_by_step: dict[str, StepResult] = {}
        outputs: dict[str, str] = {}
        for previous in previous_results or []:
            if previous.status != "success":
                continue
            step_results.append(previous)
            result_by_step[previous.step_id] = previous
            outputs[previous.step_id] = previous.output

        for step in self.validator.execution_order(plan):
            if step.id in result_by_step and result_by_step[step.id].status == "success":
                continue
            result = self._execute_step(step, result_by_step, outputs, user_context)
            result_by_step[step.id] = result
            step_results.append(result)
            if result.status == "success":
                outputs[step.id] = result.output

        status = self._overall_status(step_results)
        pending_approvals = [result.step_id for result in step_results if result.status == "approval_required"]
        self.audit_log.record(
            "workflow_finished",
            {
                "run_id": run_id,
                "plan_id": plan.plan_id,
                "status": status,
                "pending_approvals": pending_approvals,
                "steps": [result.to_dict() for result in step_results],
            },
        )
        result = WorkflowResult(
            status=status,
            run_id=run_id,
            plan=plan,
            step_results=step_results,
            warnings=validation.warnings,
        )
        self._save_checkpoint(result)
        return result

    def resume(self, run_id: str, user_context: UserContext) -> WorkflowResult:
        checkpoint = self.checkpoint_store.load(run_id)
        previous_results = [StepResult.from_dict(item) for item in checkpoint.step_results]
        return self.execute_plan(
            checkpoint.execution_plan(),
            user_context,
            run_id=checkpoint.run_id,
            previous_results=previous_results,
        )

    def _execute_step(
        self,
        step: Step,
        result_by_step: dict[str, StepResult],
        outputs: dict[str, str],
        user_context: UserContext,
    ) -> StepResult:
        result = StepResult(step_id=step.id, tool=step.tool, status="running")
        blocked = self._blocked_dependency(step, result_by_step)
        if blocked:
            result.status = "skipped"
            result.error = f"依赖步骤未成功: {blocked}"
            result.finished_at = datetime.now(timezone.utc).isoformat()
            self.audit_log.record("step_skipped", result.to_dict())
            return result

        meta = self.registry.get_meta(step.tool)
        if meta is None:
            result.status = "failed"
            result.error = f"工具不存在: {step.tool}"
            result.finished_at = datetime.now(timezone.utc).isoformat()
            return result

        if (meta.sensitive or step.requires_approval) and not user_context.auto_approve:
            result.status = "approval_required"
            result.error = f"步骤需要审批: {step.name}"
            result.finished_at = datetime.now(timezone.utc).isoformat()
            self.audit_log.record("approval_required", {"step": step.to_dict(), "user": user_context.user_id})
            return result

        args = self.validator.fill_runtime_args(step.args, outputs)
        self.audit_log.record("step_started", {"step": step.to_dict(), "args": args})
        try:
            output = self.retry_handler.execute(
                lambda: self.registry.invoke(step.tool, args, user_context),
                operation_name=step.tool,
                idempotent=meta.idempotent,
                retryable=meta.idempotent,
                idempotency_key=step.idempotency_key,
            )
            result.status = "success"
            result.output = output
            result.finished_at = datetime.now(timezone.utc).isoformat()
            self.audit_log.record("step_finished", result.to_dict())
        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
            result.finished_at = datetime.now(timezone.utc).isoformat()
            self.audit_log.record_error({"step": step.to_dict(), "error": result.error})
        finally:
            if result.finished_at is None:
                result.finished_at = datetime.now(timezone.utc).isoformat()
        return result

    @staticmethod
    def _blocked_dependency(step: Step, result_by_step: dict[str, StepResult]) -> str:
        for dep_id in step.depends_on:
            dep = result_by_step.get(dep_id)
            if dep is None or dep.status != "success":
                return dep_id
        return ""

    @staticmethod
    def _overall_status(step_results: list[StepResult]) -> str:
        statuses = {result.status for result in step_results}
        if "failed" in statuses:
            return "failed"
        if "approval_required" in statuses:
            return "waiting_approval"
        if "skipped" in statuses:
            return "partial"
        return "success"

    def _save_checkpoint(self, result: WorkflowResult) -> None:
        pending_approvals = [item.step_id for item in result.step_results if item.status == "approval_required"]
        self.checkpoint_store.save(
            WorkflowCheckpoint(
                run_id=result.run_id,
                status=result.status,
                plan=result.plan.to_dict(),
                step_results=[item.to_dict() for item in result.step_results],
                pending_approvals=pending_approvals,
            )
        )
