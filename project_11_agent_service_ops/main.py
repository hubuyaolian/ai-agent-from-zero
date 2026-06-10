"""Project 11 本地服务启动入口。

运行：
    python project_11_agent_service_ops/main.py
"""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from project_11_agent_service_ops.config import SERVICE_HOST, SERVICE_PORT


def main() -> None:
    """启动 Uvicorn 服务。"""
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "缺少 uvicorn，请先执行：pip install -r requirements.txt"
        ) from exc

    uvicorn.run(
        "project_11_agent_service_ops.api.app:app",
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
