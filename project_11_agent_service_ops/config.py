"""Project 11 项目级配置。

本项目演示生产化 Agent 服务的最小闭环。默认配置适合本地教学运行，
生产系统应接入真实密钥管理、集中配置和网关策略。
"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "runtime_data"
LOG_DIR = DATA_DIR / "logs"

SERVICE_HOST = os.getenv("PROJECT_11_HOST", "127.0.0.1")
SERVICE_PORT = int(os.getenv("PROJECT_11_PORT", "8011"))

DEFAULT_API_KEYS = tuple(
    key.strip()
    for key in os.getenv("PROJECT_11_API_KEYS", "dev-key").split(",")
    if key.strip()
)
DEFAULT_TENANT_ID = os.getenv("PROJECT_11_TENANT", "demo-tenant")
DEFAULT_USER_ID = os.getenv("PROJECT_11_USER", "demo-user")

RATE_LIMIT_CAPACITY = int(os.getenv("PROJECT_11_RATE_LIMIT_CAPACITY", "5"))
RATE_LIMIT_REFILL_PER_SECOND = float(
    os.getenv("PROJECT_11_RATE_LIMIT_REFILL_PER_SECOND", "1.0")
)

DAILY_BUDGET_CENTS = float(os.getenv("PROJECT_11_DAILY_BUDGET_CENTS", "20.0"))
DEFAULT_MAX_OUTPUT_TOKENS = int(os.getenv("PROJECT_11_MAX_OUTPUT_TOKENS", "128"))


def ensure_runtime_dirs() -> None:
    """创建服务运行所需目录。"""
    for path in (DATA_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
