"""启发式任务计划器。

教学项目里先用规则规划，方便观察工作流闭环。生产环境可将本模块替换为
LLM 结构化输出，但仍应保留 PlanValidator 作为硬校验边界。
"""

from __future__ import annotations

import hashlib
import re

from project_08_workflow_agent.planner.models import ExecutionPlan, Step
from project_08_workflow_agent.tools.registry import ToolRegistry


class TaskPlanner:
    """把自然语言任务转成可校验的 ExecutionPlan。"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def create_plan(self, instruction: str) -> ExecutionPlan:
        text = instruction.strip()
        lowered = text.lower()
        if self._looks_like_report_task(lowered):
            return self._report_plan(text)
        if "归档" in text or "archive" in lowered:
            return self._archive_plan(text)
        if "统计" in text or "statistics" in lowered or "sum" in lowered:
            return self._statistics_plan(text)
        if "通知" in text or "notify" in lowered:
            return self._notification_plan(text)
        if self._extract_path(text):
            return self._read_plan(text)
        return self._note_plan(text)

    @staticmethod
    def _looks_like_report_task(text: str) -> bool:
        return any(keyword in text for keyword in ("日报", "report", "销售", "daily"))

    @staticmethod
    def _extract_path(text: str) -> str | None:
        patterns = [
            r"(?:data|reports)/[^\s，,。；;]+",
            r"project_08_workflow_agent/(?:data|reports)/[^\s，,。；;]+",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                path = match.group(0)
                prefix = "project_08_workflow_agent/"
                if path.startswith(prefix):
                    path = path[len(prefix) :]
                return path
        return None

    def _report_plan(self, instruction: str) -> ExecutionPlan:
        data_path = self._extract_path(instruction) or "data/sales.csv"
        output_path = "reports/daily_report.csv"
        steps = [
            Step(
                id="read_data",
                name="读取销售数据",
                tool="read_csv_summary",
                args={"filepath": data_path},
                description="确认 CSV 数据结构和样例。",
            ),
            Step(
                id="calc_stats",
                name="统计数值指标",
                tool="calc_csv_statistics",
                args={"filepath": data_path},
                depends_on=["read_data"],
                description="计算数值列的 count/sum/avg/min/max。",
            ),
            Step(
                id="write_report",
                name="生成日报",
                tool="generate_daily_report",
                args={"data_path": data_path, "output_path": output_path},
                depends_on=["calc_stats"],
                requires_approval=True,
                idempotency_key=f"report:{data_path}:{output_path}",
                description="写入 reports/daily_report.csv。",
            ),
            Step(
                id="notify",
                name="发送完成通知",
                tool="send_notification",
                args={
                    "title": "工作流完成",
                    "content": f"日报已生成: {output_path}",
                    "channel": "local",
                },
                depends_on=["write_report"],
                requires_approval=True,
                idempotency_key=f"notify:daily_report:{output_path}",
                description="写入本地通知日志。",
            ),
        ]
        return ExecutionPlan(instruction=instruction, steps=steps)

    def _statistics_plan(self, instruction: str) -> ExecutionPlan:
        data_path = self._extract_path(instruction) or "data/sales.csv"
        steps = [
            Step(
                id="calc_stats",
                name="统计 CSV",
                tool="calc_csv_statistics",
                args={"filepath": data_path},
            )
        ]
        return ExecutionPlan(instruction=instruction, steps=steps)

    def _read_plan(self, instruction: str) -> ExecutionPlan:
        path = self._extract_path(instruction) or "data/sales.csv"
        tool = "read_csv_summary" if path.lower().endswith(".csv") else "read_file"
        steps = [
            Step(
                id="read_input",
                name="读取文件",
                tool=tool,
                args={"filepath": path},
            )
        ]
        return ExecutionPlan(instruction=instruction, steps=steps)

    def _archive_plan(self, instruction: str) -> ExecutionPlan:
        paths = re.findall(r"(?:data|reports)/[^\s，,。；;]+", instruction)
        source_dir = paths[0] if paths else "data/output"
        archive_dir = paths[1] if len(paths) > 1 else "data/output/archive"
        steps = [
            Step(
                id="archive",
                name="归档文件",
                tool="archive_files",
                args={"source_dir": source_dir, "archive_dir": archive_dir, "pattern": "*"},
                requires_approval=True,
                idempotency_key=f"archive:{source_dir}:{archive_dir}",
            )
        ]
        return ExecutionPlan(instruction=instruction, steps=steps)

    def _notification_plan(self, instruction: str) -> ExecutionPlan:
        key = self._stable_key(instruction)
        steps = [
            Step(
                id="notify",
                name="发送通知",
                tool="send_notification",
                args={"title": "工作流通知", "content": instruction, "channel": "local"},
                requires_approval=True,
                idempotency_key=f"notify:{key}",
            )
        ]
        return ExecutionPlan(instruction=instruction, steps=steps)

    def _note_plan(self, instruction: str) -> ExecutionPlan:
        key = self._stable_key(instruction)
        steps = [
            Step(
                id="write_note",
                name="记录未识别任务",
                tool="write_file",
                args={
                    "filepath": "reports/workflow_note.txt",
                    "content": f"待人工细化的任务:\n{instruction}\n",
                },
                requires_approval=True,
                idempotency_key=f"note:{key}",
            )
        ]
        return ExecutionPlan(instruction=instruction, steps=steps)

    @staticmethod
    def _stable_key(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
