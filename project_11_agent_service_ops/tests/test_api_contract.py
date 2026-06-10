"""FastAPI 接口契约测试。"""

from __future__ import annotations

import unittest

try:
    from fastapi.testclient import TestClient

    FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    TestClient = None  # type: ignore[assignment]
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi 未安装，跳过接口契约测试")
class APIContractTest(unittest.TestCase):
    def test_health_and_chat_contract(self) -> None:
        from project_11_agent_service_ops.api.app import create_app

        client = TestClient(create_app())

        health = client.get("/health")
        chat = client.post(
            "/chat",
            headers={"X-API-Key": "dev-key"},
            json={"message": "如何上线一个企业 Agent 服务？"},
        )
        metrics = client.get("/metrics", headers={"X-API-Key": "dev-key"})

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertEqual(chat.status_code, 200)
        self.assertIn("run_id", chat.json())
        self.assertGreater(chat.json()["input_tokens"], 0)
        self.assertEqual(metrics.status_code, 200)
        self.assertGreaterEqual(metrics.json()["request_count"], 1)

    def test_missing_api_key_is_rejected(self) -> None:
        from project_11_agent_service_ops.api.app import create_app

        client = TestClient(create_app())

        response = client.post("/chat", json={"message": "hello"})
        metrics = client.get("/metrics")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(metrics.status_code, 401)

    def test_stream_contract_returns_sse(self) -> None:
        from project_11_agent_service_ops.api.app import create_app

        client = TestClient(create_app())

        response = client.post(
            "/stream",
            headers={"X-API-Key": "dev-key"},
            json={"message": "解释 Agent 服务的流式输出。"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("data:", response.text)
        self.assertIn("event: done", response.text)


if __name__ == "__main__":
    unittest.main()
