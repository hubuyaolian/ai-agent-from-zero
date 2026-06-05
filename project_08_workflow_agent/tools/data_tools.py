"""CSV 数据处理工具。"""

from __future__ import annotations

import csv

from project_08_workflow_agent.governance.policy import resolve_safe_path


def _read_csv_rows(filepath: str) -> tuple[list[str], list[dict]]:
    path = resolve_safe_path(filepath)
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        headers = reader.fieldnames or []
    return headers, rows


def read_csv_summary(filepath: str, preview_rows: int = 5) -> str:
    headers, rows = _read_csv_rows(filepath)
    preview = rows[: int(preview_rows)]
    return f"CSV: {filepath}\n列名: {headers}\n总行数: {len(rows)}\n前 {len(preview)} 行: {preview}"


def calc_csv_statistics(filepath: str, column: str | None = None) -> str:
    headers, rows = _read_csv_rows(filepath)
    if not rows:
        return "CSV 文件无数据行。"

    candidate_columns = [column] if column else headers
    stats = []
    for col in candidate_columns:
        values = []
        for row in rows:
            raw = row.get(col, "")
            try:
                values.append(float(str(raw).replace(",", "")))
            except ValueError:
                continue
        if values:
            stats.append(
                {
                    "column": col,
                    "count": len(values),
                    "sum": round(sum(values), 2),
                    "avg": round(sum(values) / len(values), 2),
                    "min": min(values),
                    "max": max(values),
                }
            )
    if not stats:
        return f"未找到可统计的数值列。列名: {headers}"
    lines = []
    for item in stats:
        lines.append(
            f"{item['column']}: count={item['count']}, sum={item['sum']}, "
            f"avg={item['avg']}, min={item['min']}, max={item['max']}"
        )
    return "\n".join(lines)

