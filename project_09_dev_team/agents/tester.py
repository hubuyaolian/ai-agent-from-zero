"""测试 Agent。"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path

from project_09_dev_team.config import BANNED_CODE_PATTERNS
from project_09_dev_team.delivery import validate_artifact_path
from project_09_dev_team.messages.models import Artifact, TestIssue, TestReport


class TesterAgent:
    """静态检查 + 白名单 unittest 执行。"""

    def review(self, artifacts: list[Artifact]) -> TestReport:
        issues: list[TestIssue] = []
        for artifact in artifacts:
            try:
                validate_artifact_path(artifact.path)
            except ValueError as exc:
                issues.append(TestIssue("CRITICAL", artifact.path, str(exc), "修正文件路径"))
                continue
            issues.extend(self._static_check(artifact))

        if not any(artifact.path.startswith("tests/") for artifact in artifacts):
            issues.append(TestIssue("HIGH", "tests/", "缺少单元测试", "至少生成一组 unittest 测试"))

        run_report = self._run_unittest(artifacts) if not issues else None
        if run_report is not None:
            issues.extend(run_report.issues)
            passed = run_report.passed and not [item for item in issues if item.severity in {"CRITICAL", "HIGH"}]
            return TestReport(
                passed=passed,
                summary=run_report.summary,
                issues=issues,
                command=run_report.command,
                stdout=run_report.stdout,
                stderr=run_report.stderr,
            )

        passed = not [item for item in issues if item.severity in {"CRITICAL", "HIGH"}]
        return TestReport(passed=passed, summary=f"静态检查完成，发现 {len(issues)} 个问题", issues=issues)

    @staticmethod
    def _static_check(artifact: Artifact) -> list[TestIssue]:
        issues: list[TestIssue] = []
        for pattern in BANNED_CODE_PATTERNS:
            if pattern in artifact.content:
                issues.append(
                    TestIssue(
                        "CRITICAL",
                        artifact.path,
                        f"发现危险代码模式: {pattern}",
                        "移除危险调用，改用白名单能力",
                    )
                )
        if artifact.path.endswith(".py"):
            try:
                ast.parse(artifact.content)
            except SyntaxError as exc:
                issues.append(
                    TestIssue(
                        "HIGH",
                        artifact.path,
                        f"Python 语法错误: {exc}",
                        "修正语法后重新测试",
                    )
                )
        return issues

    @staticmethod
    def _run_unittest(artifacts: list[Artifact]) -> TestReport:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for artifact in artifacts:
                relative = validate_artifact_path(artifact.path)
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(artifact.content, encoding="utf-8")
            command = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
            completed = subprocess.run(
                command,
                cwd=root,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
            issues = []
            if completed.returncode != 0:
                issues.append(
                    TestIssue(
                        "HIGH",
                        "unittest",
                        "单元测试失败",
                        "根据测试输出修复代码",
                    )
                )
            return TestReport(
                passed=completed.returncode == 0,
                summary="unittest 通过" if completed.returncode == 0 else "unittest 失败",
                issues=issues,
                command=command,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
