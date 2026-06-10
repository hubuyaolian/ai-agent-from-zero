"""鉴权和限流测试。"""

from __future__ import annotations

import unittest

from project_11_agent_service_ops.security.auth import (
    APIKeyAuthenticator,
    AuthContext,
    AuthenticationError,
)
from project_11_agent_service_ops.security.rate_limiter import TenantRateLimiter


class SecurityTest(unittest.TestCase):
    def test_api_key_authenticator_returns_context(self) -> None:
        context = AuthContext(
            user_id="u1",
            tenant_id="t1",
            api_key_id="k1",
            scopes=frozenset({"chat"}),
        )
        authenticator = APIKeyAuthenticator({"secret": context})

        result = authenticator.authenticate("secret")

        self.assertEqual(result.tenant_id, "t1")
        authenticator.require_scope(result, "chat")

    def test_invalid_api_key_is_rejected(self) -> None:
        authenticator = APIKeyAuthenticator({})

        with self.assertRaisesRegex(AuthenticationError, "无效"):
            authenticator.authenticate("bad-key")

    def test_token_bucket_limits_and_refills(self) -> None:
        limiter = TenantRateLimiter(capacity=2, refill_per_second=1)

        self.assertTrue(limiter.allow("tenant-a", now=100.0).allowed)
        self.assertTrue(limiter.allow("tenant-a", now=100.0).allowed)
        denied = limiter.allow("tenant-a", now=100.0)
        allowed_after_refill = limiter.allow("tenant-a", now=101.0)

        self.assertFalse(denied.allowed)
        self.assertEqual(denied.retry_after_seconds, 1.0)
        self.assertTrue(allowed_after_refill.allowed)


if __name__ == "__main__":
    unittest.main()
