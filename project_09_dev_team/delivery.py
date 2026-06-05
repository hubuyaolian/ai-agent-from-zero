"""安全交付管理。"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from project_09_dev_team.config import OUTPUT_DIR, ensure_runtime_dirs
from project_09_dev_team.messages.models import AgentMessage, Artifact, DevelopmentPlan, TestReport


def sanitize_project_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower()).strip("_")
    return slug or "generated_project"


def validate_artifact_path(path: str) -> Path:
    relative = Path(path)
    if relative.is_absolute():
        raise ValueError(f"禁止绝对路径: {path}")
    if not relative.parts:
        raise ValueError("文件路径不能为空")
    if any(part == ".." for part in relative.parts):
        raise ValueError(f"禁止目录穿越: {path}")
    if any(part in {"", "."} for part in relative.parts):
        raise ValueError(f"文件路径不规范: {path}")
    return relative


@dataclass
class DeliveryResult:
    """交付结果。"""

    project_dir: str
    report_path: str
    artifact_count: int
    quality_passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


class DeliveryManager:
    """唯一允许落盘的交付节点。"""

    def __init__(self, output_dir: str | Path = OUTPUT_DIR):
        ensure_runtime_dirs()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def deliver(
        self,
        plan: DevelopmentPlan,
        code_artifacts: list[Artifact],
        doc_artifacts: list[Artifact],
        test_report: TestReport,
        messages: list[AgentMessage],
    ) -> DeliveryResult:
        quality_passed = test_report.passed and not test_report.high_or_critical_issues()
        project_dir = self.output_dir / sanitize_project_name(plan.project_name)
        project_dir.mkdir(parents=True, exist_ok=True)

        artifacts = code_artifacts + doc_artifacts
        for artifact in artifacts:
            relative = validate_artifact_path(artifact.path)
            target = (project_dir / relative).resolve()
            if project_dir.resolve() not in target.parents and target != project_dir.resolve():
                raise ValueError(f"产物越界: {artifact.path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(artifact.content, encoding="utf-8")

        index = {
            "plan": plan.to_dict(),
            "quality_passed": quality_passed,
            "test_report": test_report.to_dict(),
            "artifacts": [artifact.to_dict() for artifact in artifacts],
            "messages": [message.to_dict() for message in messages],
        }
        (project_dir / "ARTIFACTS_INDEX.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        report_path = project_dir / "DELIVERY_REPORT.md"
        report_path.write_text(self._report(plan, test_report, artifacts, messages), encoding="utf-8")
        return DeliveryResult(
            project_dir=str(project_dir),
            report_path=str(report_path),
            artifact_count=len(artifacts),
            quality_passed=quality_passed,
        )

    @staticmethod
    def _report(
        plan: DevelopmentPlan,
        test_report: TestReport,
        artifacts: list[Artifact],
        messages: list[AgentMessage],
    ) -> str:
        artifact_lines = "\n".join(f"- `{artifact.path}` ({artifact.artifact_type})" for artifact in artifacts)
        issue_lines = "\n".join(
            f"- {issue.severity} `{issue.location}`: {issue.description}"
            for issue in test_report.issues
        ) or "- 无"
        return f"""# Delivery Report

## Project

- Name: {plan.project_name}
- Requirement: {plan.requirement}
- Summary: {plan.summary}

## Quality

- Passed: {test_report.passed}
- Summary: {test_report.summary}

## Issues

{issue_lines}

## Artifacts

{artifact_lines}

## Collaboration

- Message count: {len(messages)}
"""
