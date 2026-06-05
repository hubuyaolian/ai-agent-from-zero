"""带抖动的轻量重试器。"""

from __future__ import annotations

import random
import time
from collections.abc import Callable

from project_08_workflow_agent.config import BASE_RETRY_DELAY, MAX_RETRIES, MAX_RETRY_DELAY
from project_08_workflow_agent.governance.audit_log import AuditLog


class RetryHandler:
    """只对幂等操作重试，避免重复发送通知或移动文件。"""

    def __init__(
        self,
        *,
        max_retries: int = MAX_RETRIES,
        base_delay: float = BASE_RETRY_DELAY,
        max_delay: float = MAX_RETRY_DELAY,
        audit_log: AuditLog | None = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.audit_log = audit_log or AuditLog()

    def execute(
        self,
        operation: Callable[[], str],
        *,
        operation_name: str,
        idempotent: bool = True,
        retryable: bool = True,
        idempotency_key: str | None = None,
    ) -> str:
        attempts = self.max_retries + 1 if idempotent and retryable else 1
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return operation()
            except Exception as exc:
                last_error = exc
                self.audit_log.record_error(
                    {
                        "operation": operation_name,
                        "attempt": attempt,
                        "attempts": attempts,
                        "idempotent": idempotent,
                        "idempotency_key": idempotency_key,
                        "error": str(exc),
                    }
                )
                if attempt >= attempts:
                    break
                time.sleep(self._delay(attempt))
        raise RuntimeError(f"{operation_name} 执行失败: {last_error}") from last_error

    def _delay(self, attempt: int) -> float:
        delay = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
        return delay * random.uniform(0.5, 1.5)
