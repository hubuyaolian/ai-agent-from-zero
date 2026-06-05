"""项目级配置。"""

from __future__ import annotations

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = DATA_DIR / "output"
LOG_DIR = OUTPUT_DIR / "logs"

MAX_FIX_ROUNDS = 3
BANNED_CODE_PATTERNS = ("eval(", "exec(", "os.system(", "subprocess.Popen(")


def ensure_runtime_dirs() -> None:
    """创建本项目运行所需目录。"""
    for path in (DATA_DIR, OUTPUT_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
