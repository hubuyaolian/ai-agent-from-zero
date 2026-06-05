"""执行计划校验与依赖排序。"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from project_08_workflow_agent.planner.models import ExecutionPlan, Step
from project_08_workflow_agent.tools.registry import ToolRegistry


@dataclass
class ValidationResult:
    """计划校验结果。"""

    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PlanValidator:
    """校验工具存在性、参数、审批标记和依赖图。"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def validate(self, plan: ExecutionPlan) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        step_ids = [step.id for step in plan.steps]
        duplicates = sorted({step_id for step_id in step_ids if step_ids.count(step_id) > 1})
        if duplicates:
            errors.append(f"步骤 ID 重复: {duplicates}")

        known_ids = set(step_ids)
        for step in plan.steps:
            meta = self.registry.get_meta(step.tool)
            if meta is None:
                errors.append(f"{step.id}: 未注册工具 {step.tool}")
                continue

            ok, reason = self.registry.validate_args(step.tool, step.args)
            if not ok:
                errors.append(f"{step.id}: {reason}")

            if meta.sensitive and not step.requires_approval:
                warnings.append(f"{step.id}: 敏感工具 {step.tool} 未标记 requires_approval")

            for dep in step.depends_on:
                if dep not in known_ids:
                    errors.append(f"{step.id}: 依赖不存在: {dep}")
                if dep == step.id:
                    errors.append(f"{step.id}: 不能依赖自身")

        cycle = self._detect_cycle(plan.steps)
        if cycle:
            errors.append(f"依赖图存在环: {' -> '.join(cycle)}")
        return ValidationResult(ok=not errors, errors=errors, warnings=warnings)

    def execution_order(self, plan: ExecutionPlan) -> list[Step]:
        """返回拓扑排序后的步骤；若计划无效，由 validate 给出原因。"""
        by_id = {step.id: step for step in plan.steps}
        visited: set[str] = set()
        visiting: set[str] = set()
        ordered: list[Step] = []

        def visit(step: Step) -> None:
            if step.id in visited:
                return
            if step.id in visiting:
                return
            visiting.add(step.id)
            for dep_id in step.depends_on:
                dep = by_id.get(dep_id)
                if dep is not None:
                    visit(dep)
            visiting.remove(step.id)
            visited.add(step.id)
            ordered.append(step)

        for step in plan.steps:
            visit(step)
        return ordered

    @staticmethod
    def fill_runtime_args(args: dict, results: dict[str, str]) -> dict:
        """将 {{step_id}} 占位符替换为依赖步骤输出。"""
        resolved = copy.deepcopy(args)

        def replace(value):
            if isinstance(value, str):
                for step_id, output in results.items():
                    value = value.replace("{{" + step_id + "}}", str(output))
                return value
            if isinstance(value, list):
                return [replace(item) for item in value]
            if isinstance(value, dict):
                return {key: replace(item) for key, item in value.items()}
            return value

        return replace(resolved)

    @staticmethod
    def _detect_cycle(steps: list[Step]) -> list[str]:
        by_id = {step.id: step for step in steps}
        visiting: list[str] = []
        visited: set[str] = set()

        def visit(step_id: str) -> list[str]:
            if step_id in visiting:
                index = visiting.index(step_id)
                return visiting[index:] + [step_id]
            if step_id in visited:
                return []
            visiting.append(step_id)
            for dep_id in by_id.get(step_id, Step(step_id, "", "")).depends_on:
                if dep_id in by_id:
                    cycle = visit(dep_id)
                    if cycle:
                        return cycle
            visiting.pop()
            visited.add(step_id)
            return []

        for step in steps:
            cycle = visit(step.id)
            if cycle:
                return cycle
        return []
