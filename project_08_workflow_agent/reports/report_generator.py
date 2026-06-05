"""CSV 日报生成器。"""

from __future__ import annotations

import csv
from pathlib import Path

from project_08_workflow_agent.governance.policy import resolve_safe_path


def _numeric_stats(rows: list[dict], headers: list[str]) -> list[dict]:
    stats = []
    for column in headers:
        values = []
        for row in rows:
            raw = row.get(column, "")
            try:
                values.append(float(str(raw).replace(",", "")))
            except ValueError:
                continue
        if values:
            stats.extend(
                [
                    {"metric": "count", "column": column, "value": len(values)},
                    {"metric": "sum", "column": column, "value": round(sum(values), 2)},
                    {"metric": "avg", "column": column, "value": round(sum(values) / len(values), 2)},
                    {"metric": "min", "column": column, "value": min(values)},
                    {"metric": "max", "column": column, "value": max(values)},
                ]
            )
    return stats


def generate_daily_report(data_path: str, output_path: str) -> str:
    """读取 CSV 并生成简易日报 CSV。"""
    input_file = resolve_safe_path(data_path)
    output_file = resolve_safe_path(output_path)
    with input_file.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        headers = reader.fieldnames or []

    output_file.parent.mkdir(parents=True, exist_ok=True)
    stats = _numeric_stats(rows, headers)
    with output_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["metric", "column", "value"])
        writer.writeheader()
        writer.writerows(stats)

    display_path = Path(output_path)
    return f"日报已生成: {display_path}，数据行数: {len(rows)}，统计项: {len(stats)}"
