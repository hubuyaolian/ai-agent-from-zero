"""项目级配置。"""

from __future__ import annotations

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
REPORTS_DIR = PROJECT_DIR / "reports"
OUTPUT_DIR = DATA_DIR / "output"
LOG_DIR = OUTPUT_DIR / "logs"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
SCHEDULE_FILE = OUTPUT_DIR / "schedules.json"

SAFE_ROOTS = (DATA_DIR, REPORTS_DIR)
MAX_RETRIES = 2
BASE_RETRY_DELAY = 0.2
MAX_RETRY_DELAY = 2.0


def ensure_runtime_dirs() -> None:
    """创建本项目运行所需目录。"""
    for path in (DATA_DIR, REPORTS_DIR, OUTPUT_DIR, LOG_DIR, CHECKPOINT_DIR):
        path.mkdir(parents=True, exist_ok=True)
