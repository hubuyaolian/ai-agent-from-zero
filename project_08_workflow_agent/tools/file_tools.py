"""文件处理工具。"""

from __future__ import annotations

import glob
import shutil
from pathlib import Path

from project_08_workflow_agent.governance.policy import resolve_safe_path


def read_file(filepath: str) -> str:
    path = resolve_safe_path(filepath)
    return path.read_text(encoding="utf-8")


def write_file(filepath: str, content: str) -> str:
    path = resolve_safe_path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"文件写入成功: {path}"


def archive_files(
    source_dir: str,
    archive_dir: str,
    pattern: str = "*",
    dry_run: bool = False,
) -> str:
    source = resolve_safe_path(source_dir)
    archive = resolve_safe_path(archive_dir)
    archive.mkdir(parents=True, exist_ok=True)
    files = [Path(item) for item in glob.glob(str(source / pattern)) if Path(item).is_file()]
    if dry_run:
        return f"[dry-run] 将归档 {len(files)} 个文件到 {archive}"
    for file_path in files:
        shutil.move(str(file_path), str(archive / file_path.name))
    return f"已归档 {len(files)} 个文件到 {archive}"

